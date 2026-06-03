import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Always resolve env files from backend/ (not the process cwd).
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables and optional .env file."""

    model_config = SettingsConfigDict(
        # secrets.env is gitignored — use for OPENAI_API_KEY (see scripts/import-openai-key.ps1)
        env_file=(
            str(_BACKEND_ROOT / ".env"),
            str(_BACKEND_ROOT / "secrets.env"),
        ),
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )

    database_url: str = (
        "postgresql+psycopg://sfi:sfi_dev_password@localhost:5432/sfi"
    )
    api_cors_origins: str = ",".join(
        origin
        for host in ("localhost", "127.0.0.1")
        for p in range(3000, 3011)
        for origin in (f"http://{host}:{p}",)
    )

    # OpenAI / AI commentary (env file + OS env use OPENAI_API_KEY)
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.2
    openai_timeout_seconds: float = 60.0

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def _empty_openai_key_is_none(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]


def _read_openai_key_from_secrets_file() -> str | None:
    """Fallback when pydantic-settings does not bind OPENAI_API_KEY from secrets.env."""
    path = _BACKEND_ROOT / "secrets.env"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8-sig")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        upper = stripped.upper()
        if upper.startswith("OPENAI_API_KEY="):
            value = stripped.split("=", 1)[1].strip().strip('"').strip("'")
            return value or None
    return None


def _resolve_openai_api_key(settings: Settings) -> str | None:
    if settings.openai_api_key:
        return settings.openai_api_key
    env_val = os.environ.get("OPENAI_API_KEY")
    if env_val and str(env_val).strip():
        return str(env_val).strip()
    return _read_openai_key_from_secrets_file()


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    key = _resolve_openai_api_key(settings)
    if key and key != settings.openai_api_key:
        return settings.model_copy(update={"openai_api_key": key})
    return settings


def clear_settings_cache() -> None:
    get_settings.cache_clear()
