import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Always resolve env files from backend/ (not the process cwd).
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent

# Railway / legacy envs may still reference retired Anthropic model ids.
_ANTHROPIC_MODEL_ALIASES: dict[str, str] = {
    "claude-sonnet-4-20250514": "claude-sonnet-4-6",
}


def normalize_anthropic_model(model: str | None) -> str:
    raw = (model or "").strip() or "claude-sonnet-4-6"
    return _ANTHROPIC_MODEL_ALIASES.get(raw, raw)


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
        [
            *(f"http://{host}:{p}" for host in ("localhost", "127.0.0.1") for p in range(3000, 3011)),
            "https://smpl-financial-intelligence.vercel.app",
            "https://smpl-ai.com",
            "https://www.smpl-ai.com",
        ]
    )

    # OpenAI / AI commentary (env file + OS env use OPENAI_API_KEY)
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.2
    openai_timeout_seconds: float = 60.0

    anthropic_api_key: str | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    # Heavy exports (Prompt 2 / Prompt 5) — quality-first, longer timeout OK.
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_temperature: float = 0.2
    anthropic_timeout_seconds: float = 300.0
    # Interactive board AI (Copilot + slide regenerate) — must stay demo-fast.
    anthropic_interactive_model: str = Field(
        default="claude-haiku-4-5",
        validation_alias="ANTHROPIC_INTERACTIVE_MODEL",
    )
    anthropic_interactive_timeout_seconds: float = Field(
        default=45.0,
        validation_alias="ANTHROPIC_INTERACTIVE_TIMEOUT_SECONDS",
    )

    # Board MD&A deck — reference PPTX (SMPL Board Review Q2 2026 template).
    board_pptx_template: str | None = Field(
        default="/app/templates/board/SMPL_Board_Review_Template.pptx",
        validation_alias="BOARD_PPTX_TEMPLATE",
    )
    board_pptx_export_mode: str = Field(
        default="template_first",
        validation_alias="BOARD_PPTX_EXPORT_MODE",
        description="template_first | template_only | programmatic",
    )
    smpl_usage_limits_enabled: bool = Field(
        default=True,
        validation_alias="SMPL_USAGE_LIMITS_ENABLED",
    )
    # Prompt 5 MD&A deck soft cap per org × close period (YYYY-MM).
    smpl_prompt5_deck_per_close: int = Field(
        default=5,
        validation_alias="SMPL_PROMPT5_DECK_PER_CLOSE",
    )
    # Close-week ops: deploy freeze banner + queue alert thresholds.
    smpl_deploy_freeze: bool = Field(
        default=False,
        validation_alias="SMPL_DEPLOY_FREEZE",
    )
    smpl_deploy_freeze_note: str = Field(
        default="Close-week deploy freeze is active — avoid non-critical production deploys.",
        validation_alias="SMPL_DEPLOY_FREEZE_NOTE",
    )
    smpl_deploy_freeze_until: str | None = Field(
        default=None,
        validation_alias="SMPL_DEPLOY_FREEZE_UNTIL",
        description="Optional ISO date or human note for when freeze lifts",
    )
    smpl_close_queue_alert_depth: int = Field(
        default=4,
        validation_alias="SMPL_CLOSE_QUEUE_ALERT_DEPTH",
    )
    smpl_close_queue_alert_oldest_seconds: int = Field(
        default=600,
        validation_alias="SMPL_CLOSE_QUEUE_ALERT_OLDEST_SECONDS",
    )
    smpl_close_export_fail_alert_24h: int = Field(
        default=2,
        validation_alias="SMPL_CLOSE_EXPORT_FAIL_ALERT_24H",
    )

    @field_validator("openai_api_key", "anthropic_api_key", mode="before")
    @classmethod
    def _empty_key_is_none(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("anthropic_model", "anthropic_interactive_model", mode="before")
    @classmethod
    def _normalize_anthropic_model(cls, value: object) -> str:
        if value is None:
            return normalize_anthropic_model(None)
        return normalize_anthropic_model(str(value))

    @property
    def cors_origins_list(self) -> list[str]:
        origins = [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]
        seen = set(origins)
        for origin in (
            "https://smpl-financial-intelligence.vercel.app",
            "https://smpl-ai.com",
            "https://www.smpl-ai.com",
        ):
            if origin not in seen:
                origins.append(origin)
                seen.add(origin)
        return origins


def _read_secret_value_from_secrets_file(env_name: str) -> str | None:
    """Fallback when pydantic-settings does not bind a key from secrets.env."""
    path = _BACKEND_ROOT / "secrets.env"
    if not path.is_file():
        return None
    prefix = f"{env_name.upper()}="
    text = path.read_text(encoding="utf-8-sig")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.upper().startswith(prefix):
            value = stripped.split("=", 1)[1].strip().strip('"').strip("'")
            return value or None
    return None


def _read_openai_key_from_secrets_file() -> str | None:
    return _read_secret_value_from_secrets_file("OPENAI_API_KEY")


def _read_anthropic_key_from_secrets_file() -> str | None:
    return _read_secret_value_from_secrets_file("ANTHROPIC_API_KEY")


def _resolve_openai_api_key(settings: Settings) -> str | None:
    if settings.openai_api_key:
        return settings.openai_api_key
    env_val = os.environ.get("OPENAI_API_KEY")
    if env_val and str(env_val).strip():
        return str(env_val).strip()
    return _read_openai_key_from_secrets_file()


def _resolve_anthropic_api_key(settings: Settings) -> str | None:
    if settings.anthropic_api_key:
        return settings.anthropic_api_key
    env_val = os.environ.get("ANTHROPIC_API_KEY")
    if env_val and str(env_val).strip():
        return str(env_val).strip()
    return _read_anthropic_key_from_secrets_file()


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    updates: dict[str, str] = {}
    openai_key = _resolve_openai_api_key(settings)
    if openai_key and openai_key != settings.openai_api_key:
        updates["openai_api_key"] = openai_key
    anthropic_key = _resolve_anthropic_api_key(settings)
    if anthropic_key and anthropic_key != settings.anthropic_api_key:
        updates["anthropic_api_key"] = anthropic_key
    if updates:
        return settings.model_copy(update=updates)
    return settings


def clear_settings_cache() -> None:
    get_settings.cache_clear()
