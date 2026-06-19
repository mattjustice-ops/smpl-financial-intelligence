"""Build the configured LLM client — prefers Anthropic, falls back to OpenAI."""

from __future__ import annotations

from app.core.config import get_settings
from app.services.commentary.anthropic_client import AnthropicCommentaryClient, LLMError
from app.services.commentary.openai_client import CommentaryLLMClient, OpenAICommentaryClient


def build_commentary_llm_client() -> CommentaryLLMClient:
    settings = get_settings()
    if settings.anthropic_api_key:
        return AnthropicCommentaryClient(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            temperature=settings.anthropic_temperature,
            timeout_seconds=settings.anthropic_timeout_seconds,
        )
    if settings.openai_api_key:
        return OpenAICommentaryClient(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            temperature=settings.openai_temperature,
            timeout_seconds=settings.openai_timeout_seconds,
        )
    raise LLMError(
        "No LLM configured. Set ANTHROPIC_API_KEY (preferred) or OPENAI_API_KEY."
    )
