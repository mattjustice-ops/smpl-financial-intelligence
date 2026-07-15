"""Build the configured LLM client — prefers Anthropic, falls back to OpenAI."""

from __future__ import annotations

from typing import Literal

from app.core.config import get_settings
from app.services.commentary.anthropic_client import AnthropicCommentaryClient, LLMError
from app.services.commentary.openai_client import CommentaryLLMClient, OpenAICommentaryClient

LlmPurpose = Literal["export", "interactive"]


def build_commentary_llm_client(*, purpose: LlmPurpose = "export") -> CommentaryLLMClient:
    """Return an LLM client.

    With SMPL_FAST_AI (default True for demos): all surfaces use Haiku.
    - interactive: Copilot / slide regenerate (short timeout)
    - export: Prompt 2 / Prompt 5 (Haiku + longer timeout for big scripts)

    Set SMPL_FAST_AI=false to restore Sonnet on export paths.
    """
    settings = get_settings()
    fast = bool(getattr(settings, "smpl_fast_ai", True))

    if settings.anthropic_api_key:
        if fast or purpose == "interactive":
            model = settings.anthropic_interactive_model
            if purpose == "export":
                timeout = float(getattr(settings, "anthropic_fast_export_timeout_seconds", 120.0))
            else:
                timeout = settings.anthropic_interactive_timeout_seconds
        else:
            model = settings.anthropic_model
            timeout = settings.anthropic_timeout_seconds
        return AnthropicCommentaryClient(
            api_key=settings.anthropic_api_key,
            model=model,
            temperature=settings.anthropic_temperature,
            timeout_seconds=timeout,
        )
    if settings.openai_api_key:
        timeout = (
            min(settings.openai_timeout_seconds, 45.0)
            if purpose == "interactive"
            else settings.openai_timeout_seconds
        )
        return OpenAICommentaryClient(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            temperature=settings.openai_temperature,
            timeout_seconds=timeout,
        )
    raise LLMError(
        "No LLM configured. Set ANTHROPIC_API_KEY (preferred) or OPENAI_API_KEY."
    )
