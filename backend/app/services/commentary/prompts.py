"""Prompt templates for the AI commentary service.

The system prompt locks the model into CFO-grade, evidence-only output. The
user prompt embeds a JSON snapshot of every input so the model can quote
specific numbers and the prompt also pins the exact JSON output schema it must
return.
"""

from __future__ import annotations

import json
from typing import Any

from app.services.commentary.clarify_before_write import CLARIFY_BEFORE_WRITE_EXPORT
from app.services.commentary.schemas import CommentaryInputs, CommentaryOutput

SYSTEM_PROMPT = f"""You are a senior SaaS CFO writing board-level financial commentary.

{CLARIFY_BEFORE_WRITE_EXPORT}

Strict rules — violations are unacceptable:
1. Use only the numbers and facts contained in the JSON data block and the
   EVIDENCE PACKAGE. Do not invent revenue, customer names, market events,
   product launches, macro conditions, or anything not explicitly present.
2. Every material dollar or rate you state MUST appear in EVIDENCE PACKAGE
   values (or the DATA block that produced it). If a metric is missing, say
   "I don't know" / decline — never guess.
3. When you state a material dollar or rate, cite a `_sources` key from the
   EVIDENCE PACKAGE — put the key in `citations[].label` (e.g. label
   "mrr_waterfall.ending_mrr", value "$110,000") and/or inline as
   "$110,000 (mrr_waterfall.ending_mrr)". table.column / formula_id / path
   also count. Missing citation → that claim is omitted post-verify.
4. If the data does not support a confident root cause, say so plainly and
   add a `data_gaps` entry naming the specific input that would resolve it.
   Never speculate on causes you cannot evidence.
5. Causal / attribution language ("driven by", "due to", "because of",
   "offset by", etc.) may ONLY name drivers present in ATTRIBUTION PACKAGE
   allowed_drivers (id / label / aliases). If a phrase joins multiple drivers
   with "and" or commas, EVERY named driver must be allowlisted. If the
   allowlist is empty, do not assert material causes — restate metrics
   without inventing drivers.
6. Tone: concise, analytical, executive-ready. Avoid filler ("it's important
   to note", "as we can see"). Avoid marketing language. Prefer dollar figures
   and rates over adjectives.
7. Length: each section is 3 to 6 sentences. Risks, opportunities, and
   follow-up questions should be specific and actionable.
8. Currency: format all money values using the currency code in the input
   (e.g. "$1.20M USD"). Format rates as percentages with one decimal place.
9. If a required input is missing or null, acknowledge it ("MRR waterfall not
   provided this period") rather than fabricating numbers.

Output: a single JSON object that conforms exactly to the schema given in the
user message. Do not include markdown, prose outside the JSON, or trailing
commentary.
"""


def output_schema_json() -> str:
    """JSON Schema string for `CommentaryOutput`, embedded in the user prompt."""
    return json.dumps(CommentaryOutput.model_json_schema(), indent=2)


def build_user_prompt(
    inputs: CommentaryInputs,
    *,
    evidence_package: dict[str, Any] | None = None,
    attribution_package: dict[str, Any] | None = None,
) -> str:
    """Render the input JSON plus the required output schema into a single user message."""
    from app.services.commentary.attribution_verify import (
        build_attribution_package_from_commentary_inputs,
    )
    from app.services.commentary.claim_verify import (
        build_evidence_package,
        evidence_package_for_prompt,
    )

    data_block: dict[str, Any] = inputs.model_dump(mode="json", exclude_none=False)
    evidence = evidence_package or build_evidence_package(inputs)
    attribution = attribution_package or build_attribution_package_from_commentary_inputs(
        inputs
    )
    # LLM-facing evidence omits Decimal map; includes values + _sources.
    evidence_for_prompt = evidence_package_for_prompt(evidence)
    attribution_for_prompt = {
        "metric": attribution.get("metric"),
        "period": attribution.get("period"),
        "allowed_drivers": attribution.get("allowed_drivers") or [],
        "policy": attribution.get("policy"),
    }
    return (
        f"Period: {inputs.period_label}\n"
        f"Organization: {inputs.organization_name or 'Unspecified'}\n"
        f"Currency: {inputs.currency}\n\n"
        "DATA (only source of truth — do not use anything outside this block):\n"
        "```json\n"
        f"{json.dumps(data_block, indent=2, default=str)}\n"
        "```\n\n"
        "EVIDENCE PACKAGE (post-LLM verify uses this same dict; state only these values):\n"
        "```json\n"
        f"{json.dumps(evidence_for_prompt, indent=2, default=str)}\n"
        "```\n\n"
        "ATTRIBUTION PACKAGE (post-LLM attribution verify; name only these drivers):\n"
        "```json\n"
        f"{json.dumps(attribution_for_prompt, indent=2, default=str)}\n"
        "```\n\n"
        "Produce a JSON object that strictly conforms to this schema:\n"
        "```json\n"
        f"{output_schema_json()}\n"
        "```\n\n"
        "Required sections (each is a CommentarySection unless noted):\n"
        "  - executive_summary: 1-paragraph board-ready overview of the period.\n"
        "  - revenue_commentary: revenue actuals, growth, and forecast read-through.\n"
        "  - mrr_waterfall_commentary: movement-by-movement walk of MRR with NRR/GRR.\n"
        "  - bookings_forecast_commentary: pipeline coverage, scenarios, confidence.\n"
        "  - cash_forecast_commentary: collections outlook, DSO, AR aging risk.\n"
        "  - risks_and_opportunities: list of typed call-outs with evidence.\n"
        "  - followup_questions: list of specific questions for finance leadership.\n"
        "  - data_gaps: list of missing inputs needed to draw stronger conclusions.\n\n"
        "Return the JSON object only."
    )
