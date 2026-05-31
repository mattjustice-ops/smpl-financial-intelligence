"""Shared OpenAI configuration checks (used by main ping + export routes)."""

from __future__ import annotations

from app.core.config import (
    _BACKEND_ROOT,
    _read_openai_key_from_secrets_file,
    clear_settings_cache,
    get_settings,
)


def is_openai_configured() -> bool:
    clear_settings_cache()
    settings = get_settings()
    return bool(settings.openai_api_key or _read_openai_key_from_secrets_file())


def openai_ping_payload() -> dict[str, str | bool]:
    import sys

    from app.services.board_package.pptx_builder import PRESENTATION_ENGINE_VERSION

    clear_settings_cache()
    settings = get_settings()
    key_ok = bool(settings.openai_api_key or _read_openai_key_from_secrets_file())
    return {
        "status": "ok",
        "service": "export",
        "api_build": "openai-ping-v3",
        "board_engine": PRESENTATION_ENGINE_VERSION,
        "pipeline": "reporting.export.board_slides",
        "executive_slide_layout": "executive_scorecard",
        "marketing_channels_layout": "marketing_source",
        "openai_configured": key_ok,
        "openai_model": settings.openai_model or "gpt-4o-mini",
        "secrets_env_exists": (_BACKEND_ROOT / "secrets.env").is_file(),
        "env_file_exists": (_BACKEND_ROOT / ".env").is_file(),
        "backend_root": str(_BACKEND_ROOT),
        "python_executable": sys.executable,
        "settings_loader": "v3-main-ping-override",
    }
