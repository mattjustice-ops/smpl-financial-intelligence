"""Interactive LLM settings default to Haiku + short timeout."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.core.config import Settings, get_settings
from app.services.commentary.llm_factory import build_commentary_llm_client


def test_interactive_defaults_are_demo_fast() -> None:
    s = Settings(
        ANTHROPIC_API_KEY="test-key",
        anthropic_model="claude-sonnet-4-6",
        anthropic_interactive_model="claude-haiku-4-5",
        anthropic_timeout_seconds=300,
        anthropic_interactive_timeout_seconds=45,
    )
    assert s.anthropic_interactive_model == "claude-haiku-4-5"
    assert s.anthropic_interactive_timeout_seconds == 45.0
    assert s.anthropic_timeout_seconds == 300.0


def test_build_interactive_client_passes_haiku(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_INTERACTIVE_MODEL", "claude-haiku-4-5")
    monkeypatch.setenv("ANTHROPIC_INTERACTIVE_TIMEOUT_SECONDS", "45")
    get_settings.cache_clear()
    mock_cls = MagicMock()
    try:
        with patch("app.services.commentary.llm_factory.AnthropicCommentaryClient", mock_cls):
            build_commentary_llm_client(purpose="interactive")
        kwargs = mock_cls.call_args.kwargs
        assert kwargs["model"] == "claude-haiku-4-5"
        assert kwargs["timeout_seconds"] == 45.0
    finally:
        get_settings.cache_clear()


def test_build_export_client_passes_sonnet(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
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
