"""Board Platform Risks & Opportunities evidence for Prompt 5.

Source of truth: frontend/canonical/board/index.html ``renderRisks`` cards
(Operational risk matrix · Strategic opportunities). Injected into Prompt 5
as authorship *evidence* Claude may use when writing Strategic Assessment cards —
not a blank-slot template to fill after the fact.
"""

from __future__ import annotations

import json
from typing import Any

# Stable phrases asserted by tests — keep labels aligned with the board tab.
BOARD_RO_SEED_MARKER = "BOARD R&O EVIDENCE (AUTHORSHIP INPUT)"
GTM_NARRATIVE_SEED_MARKER = "GTM NARRATIVE REQUIREMENTS (CRAFT CRITERIA)"

# Cards match board platform Risks & Opps tab (renderRisks). Actions are the
# board-implied next step split out for PPTX card Action lines.
BOARD_PLATFORM_RISKS_OPPORTUNITIES: dict[str, list[dict[str, Any]]] = {
    "risks": [
        {
            "level": "HIGH",
            "type": "RISK",
            "category": "GTM",
            "title": "Paid channel inefficiency",
            "detail": (
                "Paid Search + Social absorb $3.84M (50% of total spend) at 1.2–1.3x "
                "pipeline efficiency and sub-6% win rates. Zero closed-won improvement. "
                "Estimated annual drag $2–3M vs high-efficiency alternatives."
            ),
            "action": (
                "Reallocate Paid budget toward Partner/Referral; quantify $2–3M annual "
                "drag vs high-efficiency channels."
            ),
            "impact": "$2–3M annual drag",
            "evidence_amounts": [3840000, 2.0, 3.0, 1.2, 1.3, 6.0],
        },
        {
            "level": "HIGH",
            "type": "RISK",
            "category": "Retention",
            "title": "SMB churn concentration",
            "detail": (
                "78% of gross churn is SMB. G$R could deteriorate 30–50bps in H2, "
                "impacting ARR by ~$0.8M and pushing N$R below 100%. Targeted CSM "
                "intervention required before Q3 renewal cycle."
            ),
            "action": (
                "Run SMB renewal cohort analysis before Q3; CSM intervention on "
                "at-risk accounts to protect G$R/N$R."
            ),
            "impact": "~$0.8M ARR / N$R <100%",
            "evidence_amounts": [78.0, 30.0, 50.0, 800000, 100.0],
        },
        {
            "level": "MEDIUM",
            "type": "RISK",
            "category": "Pipeline",
            "title": "New logo $325k behind plan",
            "detail": (
                "Deal timing slippage in 20+ seat segment. Close rates improving "
                "(Q2: 13%) but volume trailing. H2 new business revenue at risk if "
                "enterprise pipeline doesn't convert within cycle."
            ),
            "action": (
                "Prioritize enterprise close plans; validate 20+ seat segment "
                "conversion within the H2 cycle."
            ),
            "impact": "$325k behind plan",
            "evidence_amounts": [325000, 20.0, 13.0],
        },
        {
            "level": "MEDIUM",
            "type": "RISK",
            "category": "Cash",
            "title": "H2 collections moderation",
            "detail": (
                "March's $13.6M collections spike reflects annual billing concentration. "
                "H2 monthly collections expected at $6–8M — a 40% reduction from Q1 "
                "average. Cash model needs H2 update."
            ),
            "action": (
                "Update H2 cash model for $6–8M monthly collections (≈40% below Q1 avg)."
            ),
            "impact": "H2 collections −40% vs Q1",
            "evidence_amounts": [13600000, 6000000, 8000000, 40.0],
        },
    ],
    "opportunities": [
        {
            "level": "HIGH",
            "type": "OPP",
            "category": "GTM",
            "title": "Partner + Referral reallocation",
            "detail": (
                "Partner (5.8x, 59.1% WR) and Referral (141x, 65.7% WR) are severely "
                "under-invested. A budget-neutral $0.96M reallocation from Paid could "
                "generate est. +$5M pipeline at 5x+ efficiency."
            ),
            "action": (
                "Approve budget-neutral $0.96M shift from Paid to Partner/Referral "
                "for est. +$5M pipeline."
            ),
            "upside": "+$5M pipeline / 5x+ efficiency",
            "evidence_amounts": [5.8, 59.1, 141.0, 65.7, 960000, 5000000, 5.0],
        },
        {
            "level": "HIGH",
            "type": "OPP",
            "category": "ARR",
            "title": "Expansion ARR momentum",
            "detail": (
                "Expansion outperformed budget 4 of 5 months. CS-led enterprise "
                "expansion plays could add $0.5–1.0M ARR per quarter at near-zero "
                "incremental CAC."
            ),
            "action": (
                "Fund CS-led enterprise expansion plays targeting $0.5–1.0M ARR/quarter."
            ),
            "upside": "$0.5–1.0M ARR/quarter",
            "evidence_amounts": [4.0, 5.0, 500000, 1000000],
        },
        {
            "level": "MEDIUM",
            "type": "OPP",
            "category": "Cash",
            "title": "Annual contract expansion",
            "detail": (
                "Annual billing penetration in mid-market adds est. $5–8M to YE 2026 "
                "cash. Include annual terms in all mid-market renewals and new "
                "business starting Q3. Revenue recognition neutral."
            ),
            "action": (
                "Mandate annual terms on mid-market renewals/NB starting Q3 "
                "(est. +$5–8M YE cash)."
            ),
            "upside": "$5–8M YE 2026 cash",
            "evidence_amounts": [5000000, 8000000],
        },
        {
            "level": "MEDIUM",
            "type": "OPP",
            "category": "Margin",
            "title": "Operating leverage improvement",
            "detail": (
                "Revenue +9% YoY vs headcount +2.3%. If maintained through H2, "
                "EBITDA margin improvement of 150–200bps is achievable without "
                "headcount reduction — purely through GTM efficiency gains."
            ),
            "action": (
                "Hold opex/headcount discipline; capture 150–200bps EBITDA margin "
                "via GTM efficiency through H2."
            ),
            "upside": "150–200bps EBITDA margin",
            "evidence_amounts": [9.0, 2.3, 150.0, 200.0],
        },
    ],
}


def board_ro_cards_for_payload() -> dict[str, list[dict[str, str]]]:
    """Payload-shaped risks/opportunities (4+4) for Prompt 5 slide 8 cards."""
    out: dict[str, list[dict[str, str]]] = {"risks": [], "opportunities": []}
    for side in ("risks", "opportunities"):
        for card in BOARD_PLATFORM_RISKS_OPPORTUNITIES[side]:
            row = {
                "level": str(card["level"]),
                "type": str(card["type"]),
                "title": str(card["title"]),
                "detail": str(card["detail"]),
                "action": str(card["action"]),
            }
            if side == "risks":
                row["impact"] = str(card.get("impact") or "")
            else:
                row["upside"] = str(card.get("upside") or "")
            # Raw amounts ground claim_verify when Claude copies board magnitudes.
            amounts = card.get("evidence_amounts") or []
            for i, amt in enumerate(amounts):
                row[f"evidence_amount_{i}"] = str(amt)
            out[side].append(row)
    return out


def format_board_ro_seed_block() -> str:
    """R&O evidence block for Prompt 5 package preamble (fresh + adapt)."""
    seed = {
        "source": "Board Platform Risks & Opportunities tab (renderRisks)",
        "policy": (
            "When you author Strategic Assessment Risks/Opportunities cards, use "
            "these board-platform insights as evidence (driver + magnitude + action). "
            "Adapt wording for PPTX brevity (detail ~35–55 words; action one crisp "
            "line). Do NOT emit thin stubs ('Deferred pipeline', 'Close validation', "
            "empty '-'). Not a slot-fill template — author the cards; cite magnitudes "
            "from this evidence / EVIDENCE PACKAGE."
        ),
        "risks": BOARD_PLATFORM_RISKS_OPPORTUNITIES["risks"],
        "opportunities": BOARD_PLATFORM_RISKS_OPPORTUNITIES["opportunities"],
    }
    return (
        f"{BOARD_RO_SEED_MARKER} — board risk matrix evidence for authoring "
        "Strategic Assessment cards (driver, $, action):\n"
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
                "RECOMMENDED BOARD ACTION — deal-by-deal review of June losses/slips "
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
