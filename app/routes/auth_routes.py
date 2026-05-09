from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token
from app.db.database import get_db_session
from app.schemas.auth import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from app.models.user import User
from app.services.auth_service import (
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_id,
)

router = APIRouter(prefix="/auth", tags=["auth"])


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


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: UserRegisterRequest, db: AsyncSession = Depends(get_db_session)
) -> UserResponse:
    existing_user = await get_user_by_email(db, payload.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email is already registered."
        )

    user = await create_user(db, email=payload.email, password=payload.password)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login_user(
    payload: UserLoginRequest, db: AsyncSession = Depends(get_db_session)
) -> TokenResponse:
    user = await authenticate_user(db, email=payload.email, password=payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token(
        subject=str(user.id),
        secret_key=settings.jwt_secret_key,
        expires_minutes=settings.jwt_access_token_exp_minutes,
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    user = await get_optional_current_user(authorization=authorization, db=db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token."
        )
    return UserResponse.model_validate(user)
