"""Orchestrator: build prompt -> call LLM -> validate JSON -> fail-closed verify."""

from __future__ import annotations

import logging

from pydantic import ValidationError

from app.services.commentary.attribution_verify import (
    apply_fail_closed_attribution_to_commentary,
    build_attribution_package_from_commentary_inputs,
)
from app.services.commentary.citation_verify import (
    apply_fail_closed_citations_to_commentary,
)
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

    P15 fail-closed: after schema validation, (1) material numeric claims are
    checked against the evidence package, (2) causal / driver claims are
    checked against the attribution allowlist, then (3) material numbers must
    cite ``_sources`` keys (or table.column / formula_id / path). Mismatched
    or unverifiable claims are omitted / replaced with don't-know — never emitted.

    Raises `LLMError` if the model returns malformed JSON or a payload that
    doesn't conform to `CommentaryOutput`.
    """
    evidence = build_evidence_package(inputs)
    attribution = build_attribution_package_from_commentary_inputs(inputs)
    user_prompt = build_user_prompt(
        inputs,
        evidence_package=evidence,
        attribution_package=attribution,
    )
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

    verified, attr_result = apply_fail_closed_attribution_to_commentary(
        verified, attribution
    )
    if not attr_result.ok:
        logger.warning(
            "P15 attribution-verify fail-closed on /commentary/generate: %s",
            attr_result.summary(),
        )

    verified, cite_result = apply_fail_closed_citations_to_commentary(
        verified, evidence
    )
    if not cite_result.ok:
        logger.warning(
            "P15 citation-verify fail-closed on /commentary/generate: %s",
            cite_result.summary(),
        )
    return verified
