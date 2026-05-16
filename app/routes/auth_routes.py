from urllib.parse import quote

from authlib.integrations.starlette_client import OAuth, OAuthError
import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token
from app.db.database import get_db_session
from app.schemas.auth import (
    AuthStatusResponse,
    MessageResponse,
    ResendVerificationRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    VerifyEmailRequest,
)
from app.models.user import User
from app.services.auth_service import (
    authenticate_user,
    create_or_update_google_user,
    create_user,
    get_user_by_email,
    get_user_by_id,
    mark_verification_sent,
    send_verification_email,
    verify_user_email_by_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])
oauth = OAuth()

if settings.google_oauth_enabled:
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2:
        return None
    scheme, token = parts
    if scheme.lower() != "bearer":
        return None
    return token


async def get_optional_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> User | None:
    token = _extract_bearer_token(authorization)
    if not token:
        return None

    payload = decode_access_token(token, settings.jwt_secret_key)
    if not payload:
        return None

    user_id = payload.get("sub")
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        return None

    return await get_user_by_id(db, user_id_int)


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    user = await get_optional_current_user(authorization=authorization, db=db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token."
        )
    return user


def _issue_access_token_for_user(user: User) -> str:
    return create_access_token(
        subject=str(user.id),
        secret_key=settings.jwt_secret_key,
        expires_minutes=settings.jwt_access_token_exp_minutes,
    )


def _auth_page_redirect_url(**params: str) -> str:
    base = settings.public_base_url.rstrip("/")
    query = "&".join(f"{key}={quote(value)}" for key, value in params.items() if value)
    return f"{base}/web/auth.html?{query}" if query else f"{base}/web/auth.html"


def _auth_page_fragment_url(**params: str) -> str:
    base = settings.public_base_url.rstrip("/")
    fragment = "&".join(f"{key}={quote(value)}" for key, value in params.items() if value)
    return f"{base}/web/auth.html#{fragment}" if fragment else f"{base}/web/auth.html"


@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status() -> AuthStatusResponse:
    return AuthStatusResponse(
        google_oauth_enabled=settings.google_oauth_enabled,
        mail_enabled=settings.mail_enabled,
        debug_mode=settings.debug,
    )


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: UserRegisterRequest, db: AsyncSession = Depends(get_db_session)
) -> MessageResponse:
    existing_user = await get_user_by_email(db, payload.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email is already registered."
        )

    user = await create_user(db, email=payload.email, password=payload.password)
    try:
        verification_url = await send_verification_email(user)
    except Exception:
        # Keep the account so the user can retry resend verification.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account created, but the verification email could not be sent yet.",
        )

    return MessageResponse(
        message="Account created. Check your email to verify your account before signing in.",
        verification_url=verification_url if settings.debug and not settings.mail_enabled else None,
    )


@router.post("/verify", response_model=MessageResponse)
async def verify_email(
    payload: VerifyEmailRequest, db: AsyncSession = Depends(get_db_session)
) -> MessageResponse:
    try:
        await verify_user_email_by_token(db, payload.token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MessageResponse(message="Email verified successfully. You can sign in now.")


@router.get("/verify-email", include_in_schema=False)
async def verify_email_link(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db_session),
) -> RedirectResponse:
    try:
        await verify_user_email_by_token(db, token)
    except ValueError as exc:
        return RedirectResponse(
            url=_auth_page_redirect_url(verified="0", message=str(exc)),
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )

    return RedirectResponse(
        url=_auth_page_redirect_url(verified="1", mode="login"),
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )


@router.post("/verify/resend", response_model=MessageResponse)
async def resend_verification_email(
    payload: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    user = await get_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")
    if user.is_verified:
        return MessageResponse(message="This email is already verified.")

    await mark_verification_sent(db, user)
    try:
        verification_url = await send_verification_email(user)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to resend verification email right now.",
        )

    return MessageResponse(
        message="Verification email sent. Check your inbox.",
        verification_url=verification_url if settings.debug and not settings.mail_enabled else None,
    )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    payload: UserLoginRequest, db: AsyncSession = Depends(get_db_session)
) -> TokenResponse:
    existing_user = await get_user_by_email(db, payload.email)
    if existing_user and not existing_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account uses Google sign in. Continue with Google instead.",
        )

    user = await authenticate_user(db, email=payload.email, password=payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email before signing in.",
        )

    token = _issue_access_token_for_user(user)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    user = await get_current_user(authorization=authorization, db=db)
    return UserResponse.model_validate(user)


@router.get("/google/login", include_in_schema=False)
async def google_login(request: Request) -> RedirectResponse:
    if not settings.google_oauth_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign in is not configured yet.",
        )

    redirect_uri = f"{settings.public_base_url.rstrip('/')}/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", include_in_schema=False)
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> RedirectResponse:
    if not settings.google_oauth_enabled:
        return RedirectResponse(
            url=_auth_page_redirect_url(oauth="error", message="Google sign in is not configured."),
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )

    try:
        token = await oauth.google.authorize_access_token(request)
        userinfo = token.get("userinfo")
        if not userinfo:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://openidconnect.googleapis.com/v1/userinfo",
                    headers={"Authorization": f"Bearer {token['access_token']}"},
                )
                response.raise_for_status()
                userinfo = response.json()
    except OAuthError as exc:
        return RedirectResponse(
            url=_auth_page_redirect_url(oauth="error", message=str(exc)),
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
    except Exception:
        return RedirectResponse(
            url=_auth_page_redirect_url(oauth="error", message="Google sign in failed."),
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )

    email = str(userinfo.get("email", "")).strip().lower()
    google_sub = str(userinfo.get("sub", "")).strip()
    email_verified = bool(userinfo.get("email_verified"))

    if not email or not google_sub or not email_verified:
        return RedirectResponse(
            url=_auth_page_redirect_url(
                oauth="error",
                message="Google account did not provide a verified email.",
            ),
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )

    user = await create_or_update_google_user(db, email=email, google_sub=google_sub)
    app_token = _issue_access_token_for_user(user)
    return RedirectResponse(
        url=_auth_page_fragment_url(token=app_token, oauth="google"),
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
