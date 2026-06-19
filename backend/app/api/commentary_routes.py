"""HTTP route for the AI commentary service."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.services.commentary.llm_factory import build_commentary_llm_client
from app.services.commentary.openai_client import (
    CommentaryLLMClient,
    LLMError,
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
    try:
        return build_commentary_llm_client()
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


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
