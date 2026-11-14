"""Application settings, read from environment variables / backend/.env."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    environment: str = "development"  # development | production | test
    database_url: str = "postgresql+psycopg://mediai:change-me@localhost:5432/mediai"

    # Sessions
    session_cookie_name: str = "mediai_session"
    csrf_cookie_name: str = "mediai_csrf"
    session_ttl_hours: int = 12
    cookie_secure: bool = False  # must be True behind HTTPS in production

    # Comma-separated list of browser origins allowed to call the API directly.
    # The Next.js frontend proxies /api, so in the default setup this stays empty.
    allowed_origins: str = ""

    # AI
    anthropic_api_key: SecretStr | None = None
    ai_model: str = "claude-opus-5-5"
    ai_effort_analysis: str = "high"
    ai_effort_chat: str = "medium"

    # Uploads
    max_files_per_analysis: int = 5
    max_file_bytes: int = 10 * 1024 * 1024
    max_image_bytes: int = 5 * 1024 * 1024
    max_extracted_chars: int = 300_000

    # Default account created at startup when both are set
    default_user_email: str | None = None
    default_user_password: SecretStr | None = None
    default_user_name: str = "Administrateur MediAI"

    # Rate limits (per window)
    login_attempts_per_15min: int = 10
    register_per_hour: int = 5
    analyses_per_hour: int = 30
    chat_messages_per_hour: int = 120

    account_lockout_threshold: int = 5
    account_lockout_minutes: int = 15

    log_level: str = Field(default="INFO")

    @field_validator("anthropic_api_key", "default_user_password", "default_user_email", mode="before")
    @classmethod
    def blank_is_unset(cls, v):
        return None if isinstance(v, str) and not v.strip() else v

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
