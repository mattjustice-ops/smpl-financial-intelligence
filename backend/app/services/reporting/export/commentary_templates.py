"""CFO-style commentary templates (no numeric values — fill from API or user edit)."""

from __future__ import annotations

from app.services.reporting.export.schemas import CommentaryField

DEFAULT_SECTIONS: tuple[str, ...] = (
    "Executive Summary",
    "KPI Scorecard",
    "Income Statement",
    "Balance Sheet",
    "Cash Flow Statement",
    "MRR / ARR Waterfall",
    "Pipeline Waterfall",
    "Cash Forecast",
    "Deferred Revenue",
    "Headcount & Hiring",
    "GTM Performance",
    "Department Spend / P&L",
    "Risks & Opportunities",
)

SECTION_PROMPTS: dict[str, dict[str, str]] = {
    "Executive Summary": {
        "what_changed": "Summarize the largest movements in ARR, revenue, EBITDA, and cash versus plan.",
        "variance_driver": "Identify 2–3 quantified drivers tied to API metrics (expansion, churn, pipeline, timing).",
        "leadership_attention": "Call out items requiring board or executive decision this month.",
        "recommended_actions": "List specific owners and dates for follow-up actions.",
    },
    "MRR / ARR Waterfall": {
        "what_changed": "Explain beginning vs ending ARR and the rank-order of movement categories.",
        "variance_driver": "Tie new, expansion, contraction, churn, and reactivation to customer segments or products.",
        "favorable": "Highlight over-performance vs budget/forecast.",
        "unfavorable": "Highlight under-performance and whether it is volume, price, or timing.",
    },
    "Pipeline Waterfall": {
        "what_changed": "Describe pipeline created, closed won/lost, and slipped versus prior period.",
        "variance_driver": "Link movements to regions, stages, or campaigns using drilldown detail.",
        "leadership_attention": "Note coverage ratio and sufficiency to hit bookings targets.",
    },
    "Cash Forecast": {
        "what_changed": "Walk beginning cash through collections and major outflows to ending cash.",
        "variance_driver": "Explain DSO, payroll, vendor, and commission timing vs plan.",
        "leadership_attention": "State runway and minimum cash floor relative to policy.",
    },
}


def commentary_fields_for_period(period: str) -> list[CommentaryField]:
    fields: list[CommentaryField] = []
    for section in DEFAULT_SECTIONS:
        prompts = SECTION_PROMPTS.get(section, {})
        fields.append(
            CommentaryField(
                section=section,
                period=period,
                what_changed=prompts.get("what_changed", ""),
                variance_driver=prompts.get("variance_driver", ""),
                favorable=prompts.get("favorable", ""),
                unfavorable=prompts.get("unfavorable", ""),
                leadership_attention=prompts.get("leadership_attention", ""),
                recommended_actions=prompts.get("recommended_actions", ""),
                source="template",
            )
        )
    return fields
