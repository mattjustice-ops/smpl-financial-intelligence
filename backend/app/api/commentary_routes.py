"""HTTP route for the AI commentary service."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.services.commentary.openai_client import (
    CommentaryLLMClient,
    LLMError,
    OpenAICommentaryClient,
)
from app.services.commentary.schemas import CommentaryInputs, CommentaryOutput
from app.services.commentary.service import generate_commentary

commentary_router = APIRouter(prefix="/commentary", tags=["commentary"])


# A module-level slot so tests (and future routes) can inject a fake client.
_llm_client_override: CommentaryLLMClient | None = None


def set_llm_client_override(client: CommentaryLLMClient | None) -> None:
    """Used by tests / programmatic callers to swap in a fake LLM."""
    global _llm_client_override
    _llm_client_override = client


def get_llm_client(settings: Settings = Depends(get_settings)) -> CommentaryLLMClient:
    if _llm_client_override is not None:
        return _llm_client_override
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "OPENAI_API_KEY is not set on the server. "
                "Add it to your .env file or environment to enable the commentary endpoint."
            ),
        )
    return OpenAICommentaryClient(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        timeout_seconds=settings.openai_timeout_seconds,
    )


@commentary_router.post("/generate", response_model=CommentaryOutput)
def generate_commentary_endpoint(
    inputs: CommentaryInputs,
    client: CommentaryLLMClient = Depends(get_llm_client),
) -> CommentaryOutput:
    """Generate CFO-grade commentary from structured finance data."""
    try:
        return generate_commentary(inputs, client)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
