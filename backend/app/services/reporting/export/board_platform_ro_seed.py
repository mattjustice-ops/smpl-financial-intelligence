"""Risks & Opportunities evidence and GTM craft criteria for Prompt 5.

Risk/opportunity evidence is built from the close payload (ranked budget variances)
and injected into Prompt 5 as authorship *evidence* for Strategic Assessment cards —
not a blank-slot template to fill after the fact.
"""

from __future__ import annotations

import json
from typing import Any

# Stable phrases asserted by tests.
BOARD_RO_SEED_MARKER = "BOARD R&O EVIDENCE (AUTHORSHIP INPUT)"
GTM_NARRATIVE_SEED_MARKER = "GTM NARRATIVE REQUIREMENTS (CRAFT CRITERIA)"


def format_board_ro_seed_block(payload: dict[str, Any] | None = None) -> str:
    """R&O evidence block for the Prompt 5 preamble, built from the close payload."""
    ro = (payload or {}).get("risks_and_opportunities") or {}
    seed = {
        "source": ro.get("source") or "close package budget variances",
        "policy": (
            "Author Strategic Assessment Risks/Opportunities cards only for the "
            "variances listed here (driver + magnitude from this evidence / EVIDENCE "
            "PACKAGE). If fewer than four of a side are listed, author fewer cards — "
            "never invent a risk, opportunity or magnitude to fill the grid."
        ),
        "risks": ro.get("risks") or [],
        "opportunities": ro.get("opportunities") or [],
    }
    return (
        f"{BOARD_RO_SEED_MARKER} — close-package variance evidence for authoring "
        "Strategic Assessment cards:\n"
        f"{json.dumps(seed, separators=(',', ':'))}\n\n"
    )


def format_gtm_narrative_requirements_block() -> str:
    """Copilot-depth GTM takeaway structure for Prompt 5 slide GTM/Pipeline."""
    req = {
        "slide": "GTM / Pipeline Performance Key Takeaways",
        "required_insight_shape": [
            (
                "CLOSED-LOST / LOSS QUALITY — closed-lost ARR actual vs budget from "
                "gtm_performance / pipeline waterfall / EVIDENCE PACKAGE; % variance; "
                "implication (premature pipeline booking vs competitive/pricing pressure)."
            ),
            (
                "SLIPPAGE / DEFERRAL — slipped pipeline ARR actual vs budget; deals "
                "pushed beyond close; next-quarter coverage implication."
            ),
            (
                "COVERAGE + EFFICIENCY — pipeline coverage vs ending ARR (package "
                "coverage_x / ending_pipeline); channel efficiency / win-rate signal "
                "from gtm_performance.channels when present."
            ),
            (
                "RECOMMENDED BOARD ACTION — deal-by-deal review of close-month losses/slips "
                "OR channel reallocation (Partner/Referral vs Paid) when evidence "
                "supports it; prioritize lead quality over volume / pipeline discipline."
            ),
        ],
        "policy": (
            "Craft criteria when authoring GTM/Pipeline takeaways: cover closed-lost, "
            "slipped, coverage, recommended action at Copilot depth. Use package "
            "evidence only (TOL_ACTUALS=$1). Label pipeline as pipeline, not actual "
            "revenue. KPI/table cells stay numbers or '—' — narrative carries the "
            "story. Author complete bullets; never thin closed-won-only stubs or "
            "blank/— takeaways."
        ),
    }
    return (
        f"{GTM_NARRATIVE_SEED_MARKER} — when you write GTM/Pipeline takeaways, "
        "follow this Copilot-depth structure using package evidence:\n"
        f"{json.dumps(req, separators=(',', ':'))}\n\n"
    )
