"""Shared LLM configuration checks (used by main ping + export routes)."""

from __future__ import annotations

from app.core.config import (
    _BACKEND_ROOT,
    _read_anthropic_key_from_secrets_file,
    _read_openai_key_from_secrets_file,
    clear_settings_cache,
    get_settings,
    normalize_anthropic_model,
)


def is_openai_configured() -> bool:
    clear_settings_cache()
    settings = get_settings()
    return bool(settings.openai_api_key or _read_openai_key_from_secrets_file())


def is_anthropic_configured() -> bool:
    clear_settings_cache()
    settings = get_settings()
    return bool(settings.anthropic_api_key or _read_anthropic_key_from_secrets_file())


def is_llm_configured() -> bool:
    return is_anthropic_configured() or is_openai_configured()


def active_llm_provider() -> str | None:
    if is_anthropic_configured():
        return "anthropic"
    if is_openai_configured():
        return "openai"
    return None


def active_llm_model() -> str:
    settings = get_settings()
    if is_anthropic_configured():
        return normalize_anthropic_model(settings.anthropic_model)
    if is_openai_configured():
        return settings.openai_model or "gpt-4o-mini"
    return ""


def openai_ping_payload() -> dict[str, str | bool]:
    import sys

    from app.services.board_package.pptx_builder import PRESENTATION_ENGINE_VERSION

    clear_settings_cache()
    settings = get_settings()
    openai_ok = bool(settings.openai_api_key or _read_openai_key_from_secrets_file())
    anthropic_ok = bool(settings.anthropic_api_key or _read_anthropic_key_from_secrets_file())
    ai_ok = anthropic_ok or openai_ok
    provider = "anthropic" if anthropic_ok else ("openai" if openai_ok else "")
    llm_model = (
        normalize_anthropic_model(settings.anthropic_model)
        if anthropic_ok
        else ((settings.openai_model or "gpt-4o-mini") if openai_ok else "")
    )
    return {
        "status": "ok",
        "service": "export",
        "api_build": "llm-ping-v4",
        "board_engine": PRESENTATION_ENGINE_VERSION,
        "pipeline": "reporting.export.board_slides",
        "executive_slide_layout": "executive_scorecard",
        "marketing_channels_layout": "marketing_source",
        "ai_configured": ai_ok,
        "llm_provider": provider,
        "llm_model": llm_model,
        "anthropic_configured": anthropic_ok,
        "anthropic_model": normalize_anthropic_model(settings.anthropic_model),
        "openai_configured": openai_ok,
        "openai_model": settings.openai_model or "gpt-4o-mini",
        "secrets_env_exists": (_BACKEND_ROOT / "secrets.env").is_file(),
        "env_file_exists": (_BACKEND_ROOT / ".env").is_file(),
        "backend_root": str(_BACKEND_ROOT),
        "python_executable": sys.executable,
        "settings_loader": "v4-llm-ping",
    }
