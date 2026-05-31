"""Settings must load OpenAI key from backend/secrets.env regardless of cwd."""

from __future__ import annotations

import os
from pathlib import Path

from app.core.config import (
    Settings,
    _read_openai_key_from_secrets_file,
    clear_settings_cache,
    get_settings,
)

_BACKEND = Path(__file__).resolve().parent.parent
_SECRETS = _BACKEND / "secrets.env"


def test_openai_key_loads_from_backend_secrets_env(monkeypatch):
    if not _SECRETS.is_file():
        return  # local dev only; secrets.env is gitignored
    monkeypatch.chdir(_BACKEND.parent.parent)  # repo root — wrong cwd on purpose
    clear_settings_cache()
    try:
        settings = Settings()
        assert settings.openai_api_key
        assert settings.openai_api_key.startswith("sk-")
    finally:
        clear_settings_cache()


def test_get_settings_cached_instance(monkeypatch):
    if not _SECRETS.is_file():
        return
    clear_settings_cache()
    try:
        assert get_settings().openai_api_key
    finally:
        clear_settings_cache()


def test_secrets_file_fallback_reader():
    if not _SECRETS.is_file():
        return
    key = _read_openai_key_from_secrets_file()
    assert key
    assert key.startswith("sk-")
