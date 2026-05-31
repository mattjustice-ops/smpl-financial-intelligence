"""Operational narrative chain: GTM → Cash (guides slide subtitles and takeaways)."""

from __future__ import annotations

STORY_CHAIN: list[tuple[str, str, str]] = [
    ("executive_summary", "Executive lens", "Full operating & financial trajectory"),
    ("mda_summary", "MD&A", "What changed and why it matters"),
    ("gtm_performance", "① GTM", "Demand generation → pipeline creation"),
    ("marketing_channels", "① GTM · Channels", "Where efficiency is won or lost"),
    ("funnel_conversion", "② Funnel", "Lead progression and conversion quality"),
    ("pipeline_health", "③ Pipeline", "Active pipeline quality & coverage"),
    ("pipeline_movement", "③ Pipeline · Movement", "CRM activity — not same-month creation only"),
    ("opportunity_drilldown", "③ Pipeline · Deals", "Named opportunities driving variance"),
    ("arr_waterfall", "④ ARR", "SaaS growth mechanics (MRR waterfall)"),
    ("retention_churn", "④ ARR · Retention", "Expansion vs churn concentration"),
    ("gaap_revenue", "⑤ Revenue", "ARR → billings → GAAP recognition"),
    ("deferred_revenue", "⑤ Revenue · Deferred", "Billings vs recognized revenue"),
    ("cash_forecast", "⑥ Cash", "Liquidity and working capital"),
    ("headcount", "⑥ Cash · Capacity", "Hiring vs growth capacity"),
    ("department_spend", "⑦ Financials", "Operating leverage & spend discipline"),
    ("risks_opportunities", "Decisions", "Risks, opportunities, and actions"),
    ("validation", "Appendix", "Source-of-truth validation"),
]

STORY_BY_ID: dict[str, tuple[str, str]] = {sid: (step, hint) for sid, step, hint in STORY_CHAIN}

SECTION_TRANSITIONS: dict[str, dict[str, str]] = {
    "executive_summary": {
        "title": "Operating Review",
        "chain": "GTM → Funnel → Pipeline → ARR → Revenue → Cash",
        "narrative_key": "executive_summary",
    },
    "gtm_performance": {
        "title": "GTM · Demand & Pipeline Creation",
        "chain": "GTM → Funnel → Pipeline",
        "narrative_key": "gtm_performance",
    },
    "pipeline_health": {
        "title": "Pipeline · Quality & Movement",
        "chain": "Creation → Conversion → Forecast confidence",
        "narrative_key": "pipeline_health",
    },
    "arr_waterfall": {
        "title": "ARR · Growth & Retention",
        "chain": "Pipeline → ARR → Revenue",
        "narrative_key": "arr_waterfall",
    },
    "gaap_revenue": {
        "title": "Revenue · Recognition & Deferred",
        "chain": "ARR → Billings → GAAP → Cash",
        "narrative_key": "gaap_revenue",
    },
    "cash_forecast": {
        "title": "Cash · Liquidity & Capacity",
        "chain": "Collections → Working capital → Headcount",
        "narrative_key": "cash_forecast",
    },
}

NEXT_LINK: dict[str, str] = {
    "executive_summary": "GTM demand → funnel → pipeline",
    "mda_summary": "Operational drivers in GTM and ARR",
    "gtm_performance": "Funnel conversion → pipeline quality",
    "marketing_channels": "Funnel & pipeline outcomes",
    "funnel_conversion": "Pipeline health & movement",
    "pipeline_health": "Opportunity execution → ARR",
    "pipeline_movement": "Deal-level drivers → ARR bridge",
    "opportunity_drilldown": "ARR waterfall & retention",
    "arr_waterfall": "GAAP revenue & deferred revenue",
    "retention_churn": "Revenue recognition path",
    "gaap_revenue": "Cash & liquidity",
    "deferred_revenue": "Cash collections timing",
    "cash_forecast": "Headcount & operating spend",
    "headcount": "Department P&L variance",
    "department_spend": "Executive risks & decisions",
}


def story_subtitle(slide_id: str, default: str) -> str:
    step, hint = STORY_BY_ID.get(slide_id, ("", default))
    nxt = NEXT_LINK.get(slide_id, "")
    parts = [p for p in (step, hint, f"→ {nxt}" if nxt else "") if p]
    return " · ".join(parts[:2]) if parts else default


def key_takeaway_from_commentary(comm) -> str:
    if comm.impact:
        return comm.impact[:160]
    if comm.why_it_happened:
        return comm.why_it_happened[:160]
    if comm.what_happened:
        return comm.what_happened[:160]
    return ""
