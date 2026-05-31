"""Presentation semantic mappings: metric families, narrative order, export packages."""

from __future__ import annotations

from typing import Literal

MetricGroup = Literal["growth", "profitability", "liquidity", "gtm", "efficiency"]

PackageMode = Literal[
    "full_board",
    "executive_summary",
    "gtm_deep_dive",
    "finance_deep_dive",
    "variance_commentary",
]

# Section divider slides inserted before these content slides (full_board only)
SECTION_DIVIDERS: dict[str, tuple[str, str]] = {
    "gtm_performance": ("OPERATING REVIEW", "GTM · Pipeline, Bookings & Marketing"),
    "arr_waterfall": ("OPERATING REVIEW", "Revenue · ARR & Retention"),
}

# Narrative flow: operational story from GTM → ARR → cash → finance → decisions
NARRATIVE_SLIDE_ORDER: list[str] = [
    "executive_summary",
    "mda_summary",
    "gtm_performance",
    "marketing_channels",
    "funnel_conversion",
    "pipeline_health",
    "pipeline_movement",
    "opportunity_drilldown",
    "arr_waterfall",
    "retention_churn",
    "gaap_revenue",
    "deferred_revenue",
    "cash_forecast",
    "headcount",
    "department_spend",
    "risks_opportunities",
    "validation",
]

PACKAGE_SLIDES: dict[PackageMode, list[str]] = {
    "full_board": NARRATIVE_SLIDE_ORDER,
    "executive_summary": [
        "executive_summary",
        "mda_summary",
        "arr_waterfall",
        "cash_forecast",
        "risks_opportunities",
    ],
    "gtm_deep_dive": [
        "executive_summary",
        "gtm_performance",
        "marketing_channels",
        "funnel_conversion",
        "pipeline_health",
        "pipeline_movement",
        "opportunity_drilldown",
        "risks_opportunities",
    ],
    "finance_deep_dive": [
        "executive_summary",
        "arr_waterfall",
        "retention_churn",
        "gaap_revenue",
        "deferred_revenue",
        "cash_forecast",
        "headcount",
        "department_spend",
        "risks_opportunities",
        "validation",
    ],
    "variance_commentary": [
        "executive_summary",
        "mda_summary",
        "department_spend",
        "cash_forecast",
        "risks_opportunities",
    ],
}

GROWTH_METRICS = frozenset(
    {"ending_arr", "net_new_arr", "nrr", "grr", "new_business", "expansion", "pipeline_created", "closed_won_arr"}
)
PROFITABILITY_METRICS = frozenset({"revenue", "ebitda", "gross_margin", "department_spend"})
LIQUIDITY_METRICS = frozenset({"cash", "collections", "ending_cash", "burn", "runway"})
GTM_METRICS = frozenset(
    {"marketing_spend", "mql", "sql", "sal", "pipeline_created", "pipeline_coverage", "win_rate", "cac"}
)
EFFICIENCY_METRICS = frozenset({"pipeline_per_spend", "cac", "magic_number", "sales_efficiency", "revenue_per_employee"})


def metric_group_for(label: str) -> MetricGroup:
    key = label.lower().replace(" ", "_")
    if any(k in key for k in GROWTH_METRICS):
        return "growth"
    if any(k in key for k in PROFITABILITY_METRICS):
        return "profitability"
    if any(k in key for k in LIQUIDITY_METRICS):
        return "liquidity"
    if any(k in key for k in EFFICIENCY_METRICS):
        return "efficiency"
    if any(k in key for k in GTM_METRICS):
        return "gtm"
    return "growth"


def filter_slides_for_package(slide_ids: list[str], package_mode: PackageMode) -> list[str]:
    allowed = set(PACKAGE_SLIDES.get(package_mode, NARRATIVE_SLIDE_ORDER))
    return [sid for sid in NARRATIVE_SLIDE_ORDER if sid in allowed and sid in slide_ids]
