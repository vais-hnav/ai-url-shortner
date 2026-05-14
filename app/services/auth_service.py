import logging
from datetime import datetime, timezone

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models.user import User

logger = logging.getLogger(__name__)


def _verification_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.jwt_secret_key, salt="email-verification")


def create_email_verification_token(user: User) -> str:
    serializer = _verification_serializer()
    return serializer.dumps({"user_id": user.id, "email": user.email})


def decode_email_verification_token(token: str) -> tuple[int, str]:
    serializer = _verification_serializer()
    payload = serializer.loads(
        token,
        max_age=settings.email_verification_token_exp_hours * 60 * 60,
    )
    user_id = int(payload["user_id"])
    email = str(payload["email"]).strip().lower()
    return user_id, email


def get_email_verification_link(token: str) -> str:
    base = settings.public_base_url.rstrip("/")
    return f"{base}/auth/verify-email?token={token}"


def _mail_config() -> ConnectionConfig:
    return ConnectionConfig(
        MAIL_USERNAME=settings.mail_username,
        MAIL_PASSWORD=settings.mail_password,
        MAIL_FROM=settings.mail_from,
        MAIL_PORT=settings.mail_port,
        MAIL_SERVER=settings.mail_server,
        MAIL_FROM_NAME=settings.mail_from_name,
        MAIL_STARTTLS=settings.mail_starttls,
        MAIL_SSL_TLS=settings.mail_ssl_tls,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
        TEMPLATE_FOLDER=None,
    )


async def send_verification_email(user: User) -> str:
    token = create_email_verification_token(user)
    verification_link = get_email_verification_link(token)

    if not settings.mail_enabled:
        logger.warning(
            "Mail is not configured. Verification link for %s: %s",
            user.email,
            verification_link,
        )
        return verification_link

    message = MessageSchema(
        subject="Verify your email",
        recipients=[user.email],
        body=(
            "<p>Welcome to AI URL Shortner.</p>"
            "<p>Verify your email to activate email/password sign in.</p>"
            f'<p><a href="{verification_link}">Verify email</a></p>'
            f"<p>This link expires in {settings.email_verification_token_exp_hours} hours.</p>"
        ),
        subtype=MessageType.html,
    )
    fast_mail = FastMail(_mail_config())
    await fast_mail.send_message(message)
    return verification_link


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    return await db.scalar(select(User).where(User.email == email.lower()))


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    return await db.scalar(select(User).where(User.id == user_id))


async def get_user_by_google_sub(db: AsyncSession, google_sub: str) -> User | None:
    return await db.scalar(select(User).where(User.google_sub == google_sub))


async def create_user(
    db: AsyncSession,
    email: str,
    password: str | None = None,
    *,
    is_verified: bool = False,
    google_sub: str | None = None,
) -> User:
    now = datetime.now(timezone.utc)
    user = User(
        email=email.lower(),
        password_hash=hash_password(password) if password else None,
        is_verified=is_verified,
        verified_at=now if is_verified else None,
        verification_sent_at=None if is_verified else now,
        google_sub=google_sub,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def mark_user_verified(db: AsyncSession, user: User) -> User:
    if not user.is_verified:
        user.is_verified = True
        user.verified_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(user)
    return user


async def mark_verification_sent(db: AsyncSession, user: User) -> User:
    user.verification_sent_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    return user


async def verify_user_email_by_token(db: AsyncSession, token: str) -> User:
    try:
        user_id, email = decode_email_verification_token(token)
    except SignatureExpired as exc:
        raise ValueError("Verification link has expired.") from exc
    except (BadSignature, KeyError, TypeError, ValueError) as exc:
        raise ValueError("Verification link is invalid.") from exc

    user = await get_user_by_id(db, user_id)
    if not user or user.email != email:
        raise ValueError("Verification link is invalid.")

    return await mark_user_verified(db, user)


async def create_or_update_google_user(
    db: AsyncSession,
    *,
    email: str,
    google_sub: str,
) -> User:
    existing_by_sub = await get_user_by_google_sub(db, google_sub)
    if existing_by_sub:
        if not existing_by_sub.is_verified:
            await mark_user_verified(db, existing_by_sub)
        return existing_by_sub

    existing_by_email = await get_user_by_email(db, email)
    if existing_by_email:
        existing_by_email.google_sub = google_sub
        existing_by_email.is_verified = True
        existing_by_email.verified_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing_by_email)
        return existing_by_email

    return await create_user(
        db,
        email=email,
        password=None,
        is_verified=True,
        google_sub=google_sub,
    )
