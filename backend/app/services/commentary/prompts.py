"""Prompt templates for the AI commentary service.

The system prompt locks the model into CFO-grade, evidence-only output. The
user prompt embeds a JSON snapshot of every input so the model can quote
specific numbers and the prompt also pins the exact JSON output schema it must
return.
"""

from __future__ import annotations

import json
from typing import Any

from app.services.commentary.schemas import CommentaryInputs, CommentaryOutput

SYSTEM_PROMPT = """You are a senior SaaS CFO writing board-level financial commentary.

Strict rules — violations are unacceptable:
1. Use only the numbers and facts contained in the JSON data block. Do not
   invent revenue, customer names, market events, product launches, macro
   conditions, or anything not explicitly present.
2. When you make a claim, cite the supporting data point verbatim in the
   `citations` list of that section (e.g. label "NRR", value "1.05").
3. If the data does not support a confident root cause, say so plainly and
   add a `data_gaps` entry naming the specific input that would resolve it.
   Never speculate on causes you cannot evidence.
4. Tone: concise, analytical, executive-ready. Avoid filler ("it's important
   to note", "as we can see"). Avoid marketing language. Prefer dollar figures
   and rates over adjectives.
5. Length: each section is 3 to 6 sentences. Risks, opportunities, and
   follow-up questions should be specific and actionable.
6. Currency: format all money values using the currency code in the input
   (e.g. "$1.20M USD"). Format rates as percentages with one decimal place.
7. If a required input is missing or null, acknowledge it ("MRR waterfall not
   provided this period") rather than fabricating numbers.

Output: a single JSON object that conforms exactly to the schema given in the
user message. Do not include markdown, prose outside the JSON, or trailing
commentary.
"""


def output_schema_json() -> str:
    """JSON Schema string for `CommentaryOutput`, embedded in the user prompt."""
    return json.dumps(CommentaryOutput.model_json_schema(), indent=2)


def build_user_prompt(inputs: CommentaryInputs) -> str:
    """Render the input JSON plus the required output schema into a single user message."""
    data_block: dict[str, Any] = inputs.model_dump(mode="json", exclude_none=False)
    return (
        f"Period: {inputs.period_label}\n"
        f"Organization: {inputs.organization_name or 'Unspecified'}\n"
        f"Currency: {inputs.currency}\n\n"
        "DATA (only source of truth — do not use anything outside this block):\n"
        "```json\n"
        f"{json.dumps(data_block, indent=2, default=str)}\n"
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
