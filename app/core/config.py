import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_url_shortener",
    )
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    jwt_access_token_exp_minutes: int = int(
        os.getenv("JWT_ACCESS_TOKEN_EXP_MINUTES", "60")
    )


settings = Settings()
