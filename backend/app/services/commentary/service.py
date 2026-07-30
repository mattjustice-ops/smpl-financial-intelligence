"""Orchestrator: build prompt -> call LLM -> validate JSON -> fail-closed claim verify."""

from __future__ import annotations

import logging

from pydantic import ValidationError

from app.services.commentary.claim_verify import (
    apply_fail_closed_to_commentary,
    build_evidence_package,
)
from app.services.commentary.openai_client import CommentaryLLMClient, LLMError
from app.services.commentary.prompts import SYSTEM_PROMPT, build_user_prompt
from app.services.commentary.schemas import CommentaryInputs, CommentaryOutput

logger = logging.getLogger(__name__)


def generate_commentary(
    inputs: CommentaryInputs,
    client: CommentaryLLMClient,
) -> CommentaryOutput:
    """Generate validated CFO commentary from structured finance inputs.

    P15 fail-closed: after schema validation, material numeric claims are checked
    against the same evidence package embedded in the prompt. Mismatched or
    unverifiable claims are omitted / replaced with don't-know — never emitted.

    Raises `LLMError` if the model returns malformed JSON or a payload that
    doesn't conform to `CommentaryOutput`.
    """
    evidence = build_evidence_package(inputs)
    user_prompt = build_user_prompt(inputs, evidence_package=evidence)
    raw = client.generate(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)
    if not isinstance(raw, dict):
        raise LLMError(f"Expected a JSON object from the LLM, got {type(raw).__name__}.")

    # The model sometimes echoes the period_label in a different form; force it
    # to match the caller's input so downstream filters can rely on it.
    raw.setdefault("period_label", inputs.period_label)

    try:
        output = CommentaryOutput.model_validate(raw)
    except ValidationError as exc:
        raise LLMError(
            "LLM response did not conform to CommentaryOutput schema: "
            f"{exc.errors()[:3]}"
        ) from exc

    verified, result = apply_fail_closed_to_commentary(output, evidence)
    if not result.ok:
        logger.warning(
            "P15 claim-verify fail-closed on /commentary/generate: %s",
            result.summary(),
        )
    return verified
