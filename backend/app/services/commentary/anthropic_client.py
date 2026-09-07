"""Anthropic Claude client for CFO commentary (mirrors openai_client.py)."""

from __future__ import annotations

import json
import re
from typing import Any

# One LLMError class across providers: routes catch the openai_client symbol, so a
# separate Anthropic class would escape `except LLMError` and surface as a 500.
from app.services.commentary.openai_client import LLMError


class CommentaryLLMClient:
    """Protocol-compatible client — see openai_client.CommentaryLLMClient."""

    def generate(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]: ...


class AnthropicCommentaryClient:
    def __init__(
        self,
        api_key: str,
        *,
        model: str = "claude-sonnet-4-6",
        temperature: float = 0.2,
        timeout_seconds: float = 60.0,
        # Plan Assurance packets (stress cases + MC) run long; 4096 truncated the
        # JSON mid-object and the whole call failed.
        max_tokens: int = 8192,
    ) -> None:
        try:
            import anthropic  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise LLMError(
                "anthropic package is not installed. Run `pip install anthropic`."
            ) from exc
        if not api_key:
            raise LLMError("Anthropic API key is required.")
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout_seconds)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        text = self.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
        )
        return _parse_json_response(text)

    def generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
    ) -> str:
        from app.services.ops.usage_tracking import (
            LlmCallTimer,
            record_llm_usage_from_anthropic_response,
        )

        timer = LlmCallTimer()
        try:
            resp = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens if max_tokens is not None else self._max_tokens,
                temperature=self._temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except Exception as exc:  # pragma: no cover
            raise LLMError(f"Anthropic request failed: {exc}") from exc

        record_llm_usage_from_anthropic_response(
            resp,
            model=self._model,
            duration_ms=timer.duration_ms,
        )

        text_parts: list[str] = []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(getattr(block, "text", ""))
        content = "\n".join(text_parts).strip()
        if not content:
            raise LLMError("Anthropic returned an empty response.")
        return content


_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def _parse_json_response(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        unfenced = _FENCE_RE.sub("", content).strip()
        if unfenced != content:
            try:
                return json.loads(unfenced)
            except json.JSONDecodeError:
                pass
        match = re.search(r"\{[\s\S]*\}", content)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        raise LLMError(
            f"Anthropic response was not valid JSON. First 200 chars: {content[:200]!r}"
        )


def build_anthropic_commentary_client() -> AnthropicCommentaryClient:
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.anthropic_api_key:
        raise LLMError(
            "ANTHROPIC_API_KEY is not set. Add it to backend/.env or Railway/Vercel env."
        )
    return AnthropicCommentaryClient(
        api_key=settings.anthropic_api_key,
        model=settings.anthropic_model,
        temperature=settings.anthropic_temperature,
        timeout_seconds=settings.anthropic_timeout_seconds,
    )
