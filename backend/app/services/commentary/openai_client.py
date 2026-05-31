"""Pluggable LLM client wrapper used by the commentary service.

The service depends only on `CommentaryLLMClient` (a Protocol), so tests can
inject a fake. `OpenAICommentaryClient` wraps the official `openai` SDK and
enforces JSON-object responses.
"""

from __future__ import annotations

import json
from typing import Any, Protocol


class LLMError(RuntimeError):
    """Raised when the LLM call or its parsed payload is unusable."""


class CommentaryLLMClient(Protocol):
    """Anything that turns a (system, user) pair into a JSON-shaped dict."""

    def generate(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]: ...


class OpenAICommentaryClient:
    """Thin wrapper around `openai.OpenAI.chat.completions.create`.

    Lazy-imports `openai` so the rest of the codebase doesn't require it at
    import time (and tests can run without the package installed).
    """

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "gpt-4o-mini",
        temperature: float = 0.2,
        timeout_seconds: float = 60.0,
    ) -> None:
        try:
            from openai import OpenAI  # local import; not required for tests
        except ImportError as exc:  # pragma: no cover
            raise LLMError(
                "openai package is not installed. Run `pip install openai`."
            ) from exc
        if not api_key:
            raise LLMError("OpenAI API key is required to build OpenAICommentaryClient.")
        self._client = OpenAI(api_key=api_key, timeout=timeout_seconds)
        self._model = model
        self._temperature = temperature

    def generate(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                temperature=self._temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:  # pragma: no cover - network / auth errors
            raise LLMError(f"OpenAI request failed: {exc}") from exc

        if not resp.choices or not resp.choices[0].message.content:
            raise LLMError("OpenAI returned an empty response.")
        content = resp.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError(
                f"OpenAI response was not valid JSON. First 200 chars: {content[:200]!r}"
            ) from exc


def build_openai_commentary_client() -> OpenAICommentaryClient:
    """Build the default OpenAI client from app settings (``OPENAI_API_KEY`` in .env)."""
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.openai_api_key:
        raise LLMError(
            "OPENAI_API_KEY is not set. Add it to backend/.env to enable AI draft commentary."
        )
    return OpenAICommentaryClient(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        timeout_seconds=settings.openai_timeout_seconds,
    )
