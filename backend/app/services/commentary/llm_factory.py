"""Build the configured LLM client — prefers Anthropic, falls back to OpenAI."""

from __future__ import annotations

from typing import Literal

from app.core.config import get_settings
from app.services.commentary.anthropic_client import AnthropicCommentaryClient, LLMError
from app.services.commentary.openai_client import CommentaryLLMClient, OpenAICommentaryClient

LlmPurpose = Literal["export", "interactive"]


def build_commentary_llm_client(*, purpose: LlmPurpose = "export") -> CommentaryLLMClient:
    """Return an LLM client.

    - export: Prompt 2 / Prompt 5 (Sonnet + long timeout)
    - interactive: Copilot + slide regenerate (Haiku + short timeout)
    """
    settings = get_settings()
    if settings.anthropic_api_key:
        if purpose == "interactive":
            return AnthropicCommentaryClient(
                api_key=settings.anthropic_api_key,
                model=settings.anthropic_interactive_model,
                temperature=settings.anthropic_temperature,
                timeout_seconds=settings.anthropic_interactive_timeout_seconds,
            )
        return AnthropicCommentaryClient(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            temperature=settings.anthropic_temperature,
            timeout_seconds=settings.anthropic_timeout_seconds,
        )
    if settings.openai_api_key:
        # OpenAI path uses the same mini model for both; timeout stays short for interactive.
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
