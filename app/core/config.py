from pydantic import AliasChoices, Field, model_validator, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_url_shortener"

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_access_token_exp_minutes: int = Field(
        default=60,
        validation_alias=AliasChoices(
            "JWT_ACCESS_TOKEN_EXP_MINUTES", "JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
        ),
    )

    # App
    app_name: str = "AI URL Shortner"
    debug: bool = True
    public_base_url: str = "http://127.0.0.1:8000"

    # AI Provider
    ai_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_primary_model: str = "gemini-2.5-flash"
    ai_request_timeout_seconds: float = 20.0

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_flag(cls, value: bool | str) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "dev", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "prod", "production", "release"}:
                return False
        raise ValueError("Invalid DEBUG value.")

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_asyncpg_database_url(cls, value: str) -> str:
        if not isinstance(value, str):
            return value

        normalized = value.strip()
        if normalized.startswith("postgres://"):
            normalized = normalized.replace("postgres://", "postgresql+asyncpg://", 1)
        elif normalized.startswith("postgresql://"):
            normalized = normalized.replace("postgresql://", "postgresql+asyncpg://", 1)

        if normalized.startswith("postgresql+asyncpg://") and "sslmode=" in normalized:
            normalized = normalized.replace("sslmode=require", "ssl=require")
            normalized = normalized.replace("sslmode=prefer", "ssl=prefer")
            normalized = normalized.replace("sslmode=allow", "ssl=allow")
            normalized = normalized.replace("sslmode=disable", "ssl=disable")
            normalized = normalized.replace("sslmode=verify-ca", "ssl=verify-ca")
            normalized = normalized.replace("sslmode=verify-full", "ssl=verify-full")

        return normalized

    class Config:
        env_file = ".env"
        case_sensitive = False

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if not self.debug and self.jwt_secret_key == "change-me-in-production":
            raise ValueError(
                "JWT_SECRET_KEY must be changed when DEBUG is false."
            )
        return self


settings = Settings()
