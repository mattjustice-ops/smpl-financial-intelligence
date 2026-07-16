"""Fast-AI mode forces Haiku across interactive + export surfaces."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.core.config import Settings, get_settings
from app.services.commentary.llm_factory import build_commentary_llm_client


def test_fast_ai_defaults_on() -> None:
    s = Settings(ANTHROPIC_API_KEY="test-key")
    assert s.smpl_fast_ai is True
    assert s.anthropic_interactive_model == "claude-haiku-4-5"
    assert s.anthropic_fast_export_timeout_seconds == 180.0
    assert s.anthropic_interactive_timeout_seconds == 120.0


def test_fast_ai_export_uses_haiku_even_if_sonnet_configured(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    monkeypatch.setenv("ANTHROPIC_INTERACTIVE_MODEL", "claude-haiku-4-5")
    monkeypatch.setenv("SMPL_FAST_AI", "true")
    get_settings.cache_clear()
    mock_cls = MagicMock()
    try:
        with patch("app.services.commentary.llm_factory.AnthropicCommentaryClient", mock_cls):
            build_commentary_llm_client(purpose="export")
        kwargs = mock_cls.call_args.kwargs
        assert kwargs["model"] == "claude-haiku-4-5"
        assert kwargs["timeout_seconds"] == 180.0
    finally:
        get_settings.cache_clear()


def test_fast_ai_interactive_uses_haiku_with_quality_headroom(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_INTERACTIVE_MODEL", "claude-haiku-4-5")
    monkeypatch.setenv("SMPL_FAST_AI", "true")
    get_settings.cache_clear()
    mock_cls = MagicMock()
    try:
        with patch("app.services.commentary.llm_factory.AnthropicCommentaryClient", mock_cls):
            build_commentary_llm_client(purpose="interactive")
        kwargs = mock_cls.call_args.kwargs
        assert kwargs["model"] == "claude-haiku-4-5"
        assert kwargs["timeout_seconds"] == 120.0
    finally:
        get_settings.cache_clear()


def test_quality_mode_export_uses_sonnet(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    monkeypatch.setenv("SMPL_FAST_AI", "false")
    get_settings.cache_clear()
    mock_cls = MagicMock()
    try:
        with patch("app.services.commentary.llm_factory.AnthropicCommentaryClient", mock_cls):
            build_commentary_llm_client(purpose="export")
        kwargs = mock_cls.call_args.kwargs
        assert kwargs["model"] == "claude-sonnet-4-6"
        assert kwargs["timeout_seconds"] == 300.0
    finally:
        get_settings.cache_clear()
