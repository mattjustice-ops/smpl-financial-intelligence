"""Clarify / plan fragments for MD&A + Copilot (Rillet-style, product-shaped).

Export paths cannot ask the user interactively — they resolve from payload/freeze
or emit insufficient-evidence language. Interactive Copilot asks first when the
question is underspecified.
"""

from __future__ import annotations

# Prompt 2 / Prompt 5 / slide regenerate — batch exports
CLARIFY_BEFORE_WRITE_EXPORT = """
CLARIFY / PLAN BEFORE WRITE (mandatory preflight — do not invent)
Resolve these from the DATA PAYLOAD, EVIDENCE / ATTRIBUTION packages, and freeze
context only — never from outside knowledge:
1. Period and scenario (Actual vs Budget vs Forecast) for every figure you state.
2. Metric definitions already bound in the payload / nomenclature rules (ARR, N$R,
   G$R, New Business). Do not switch methodologies mid-package (e.g. bookings or
   new ARR by close date vs start/service date) unless the payload states the rule.
3. Causal drivers — only attribution_package.allowed_drivers (or freeze labels
   that match). If none fit, restate the variance without inventing a story.
If a row lacks evidence for a material claim, write a short insufficient-evidence /
don't-know cell for that claim — never fabricate dollars, %, or drivers.
""".strip()

# Copilot / interactive commentary
CLARIFY_BEFORE_WRITE_INTERACTIVE = """
CLARIFY BEFORE ANSWERING (interactive)
If the question is underspecified — missing focus month/period, unclear which
metric or definition (e.g. bookings/new ARR by close date vs start date), or which
scenario (Actual / Budget / Forecast) — ask up to three clarifying questions first
inside section 1, and keep sections 2–3 short until the user answers.
When the question plus the evidence package are sufficient, skip clarifying
questions and answer in the three labeled sections as usual.
Never invent methodologies or numbers to fill gaps.
""".strip()
