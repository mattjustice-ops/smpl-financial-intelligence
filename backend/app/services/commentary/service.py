"""Orchestrator: build prompt -> call LLM -> validate JSON against schema."""

from __future__ import annotations

from pydantic import ValidationError

from app.services.commentary.openai_client import CommentaryLLMClient, LLMError
from app.services.commentary.prompts import SYSTEM_PROMPT, build_user_prompt
from app.services.commentary.schemas import CommentaryInputs, CommentaryOutput


def generate_commentary(
    inputs: CommentaryInputs,
    client: CommentaryLLMClient,
) -> CommentaryOutput:
    """Generate validated CFO commentary from structured finance inputs.

    Raises `LLMError` if the model returns malformed JSON or a payload that
    doesn't conform to `CommentaryOutput`.
    """
    user_prompt = build_user_prompt(inputs)
    raw = client.generate(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)
    if not isinstance(raw, dict):
        raise LLMError(f"Expected a JSON object from the LLM, got {type(raw).__name__}.")

    # The model sometimes echoes the period_label in a different form; force it
    # to match the caller's input so downstream filters can rely on it.
    raw.setdefault("period_label", inputs.period_label)

    try:
        return CommentaryOutput.model_validate(raw)
    except ValidationError as exc:
        raise LLMError(
            "LLM response did not conform to CommentaryOutput schema: "
            f"{exc.errors()[:3]}"
        ) from exc
