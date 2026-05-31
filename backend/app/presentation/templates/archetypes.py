"""Fixed slide archetypes — CFO operating-review template catalog.

Each board slide_id maps to exactly one layout template and chart primitive.
Content builders supply slot data only; they must not choose layouts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.presentation.design_system.tokens import PRESENTATION_ENGINE_ID
from app.services.board_package.schemas import SlideContent

ChartPrimitive = Literal[
    "executive_kpi_trend",
    "arr_waterfall",
    "funnel_conversion",
    "pipeline_movement_bridge",
    "revenue_bridge",
    "cash_bridge",
    "headcount_bridge",
    "department_spend",
    "scatter_plot",
    "aging_distribution",
    "opportunity_spotlight",
    "none",
]

ContentSlot = Literal[
    "kpi_strip",
    "primary_chart",
    "secondary_chart",
    "period_table",
    "source_table",
    "commentary_panel",
    "narrative_cards",
    "callout_matrix",
    "spotlight_cards",
    "section_narrative",
]

@dataclass(frozen=True)
class SlideTemplateSpec:
    slide_id: str
    layout: str
    chart_primitive: ChartPrimitive
    slots: frozenset[ContentSlot]
    reference: str
    narrative_role: str
    section_label: str | None = None


# Deterministic catalog — derived from docs/reference-decks/INDEX.md grammar
SLIDE_TEMPLATE_REGISTRY: dict[str, SlideTemplateSpec] = {
    "executive_summary": SlideTemplateSpec(
        slide_id="executive_summary",
        layout="executive_scorecard",
        chart_primitive="executive_kpi_trend",
        slots=frozenset(
            {"kpi_strip", "period_table", "primary_chart", "commentary_panel"}
        ),
        reference="IMG_8039 · CARET Slide5",
        narrative_role="open_with_scorecard",
        section_label="EXECUTIVE SUMMARY",
    ),
    "mda_summary": SlideTemplateSpec(
        slide_id="mda_summary",
        layout="mda_narrative",
        chart_primitive="none",
        slots=frozenset({"narrative_cards", "commentary_panel"}),
        reference="IMG_8050 · CARET Slide5 commentary",
        narrative_role="management_interpretation",
        section_label="MD&A",
    ),
    "gtm_performance": SlideTemplateSpec(
        slide_id="gtm_performance",
        layout="story_slide",
        chart_primitive="executive_kpi_trend",
        slots=frozenset({"kpi_strip", "primary_chart", "commentary_panel"}),
        reference="CARET Slide8–11",
        narrative_role="gtm_operating",
        section_label="GTM",
    ),
    "marketing_channels": SlideTemplateSpec(
        slide_id="marketing_channels",
        layout="marketing_source",
        chart_primitive="scatter_plot",
        slots=frozenset({"source_table", "commentary_panel"}),
        reference="CARET Slide13–20",
        narrative_role="channel_efficiency",
        section_label="GTM · CHANNELS",
    ),
    "funnel_conversion": SlideTemplateSpec(
        slide_id="funnel_conversion",
        layout="story_slide",
        chart_primitive="funnel_conversion",
        slots=frozenset({"primary_chart", "source_table", "commentary_panel"}),
        reference="CARET Slide3–4",
        narrative_role="funnel_operating",
        section_label="FUNNEL",
    ),
    "pipeline_health": SlideTemplateSpec(
        slide_id="pipeline_health",
        layout="story_slide",
        chart_primitive="pipeline_movement_bridge",
        slots=frozenset({"kpi_strip", "primary_chart", "commentary_panel"}),
        reference="CARET Slide8–9",
        narrative_role="pipeline_coverage",
        section_label="PIPELINE",
    ),
    "pipeline_movement": SlideTemplateSpec(
        slide_id="pipeline_movement",
        layout="story_slide",
        chart_primitive="pipeline_movement_bridge",
        slots=frozenset({"primary_chart", "commentary_panel"}),
        reference="CARET Slide8–9",
        narrative_role="crm_activity",
        section_label="PIPELINE · MOVEMENT",
    ),
    "opportunity_drilldown": SlideTemplateSpec(
        slide_id="opportunity_drilldown",
        layout="spotlight",
        chart_primitive="opportunity_spotlight",
        slots=frozenset({"spotlight_cards", "commentary_panel"}),
        reference="CARET appendix deal tables",
        narrative_role="deal_spotlight",
        section_label="PIPELINE · DEALS",
    ),
    "arr_waterfall": SlideTemplateSpec(
        slide_id="arr_waterfall",
        layout="story_slide",
        chart_primitive="arr_waterfall",
        slots=frozenset({"kpi_strip", "primary_chart", "source_table", "commentary_panel"}),
        reference="CARET Slide6",
        narrative_role="arr_rollforward",
        section_label="ARR",
    ),
    "retention_churn": SlideTemplateSpec(
        slide_id="retention_churn",
        layout="story_slide",
        chart_primitive="executive_kpi_trend",
        slots=frozenset({"kpi_strip", "primary_chart", "source_table", "commentary_panel"}),
        reference="CARET Slide6 retention rows",
        narrative_role="retention_operating",
        section_label="ARR · RETENTION",
    ),
    "gaap_revenue": SlideTemplateSpec(
        slide_id="gaap_revenue",
        layout="story_slide",
        chart_primitive="revenue_bridge",
        slots=frozenset({"primary_chart", "commentary_panel"}),
        reference="Excel 8022 revenue bridge",
        narrative_role="revenue_bridge",
        section_label="REVENUE",
    ),
    "deferred_revenue": SlideTemplateSpec(
        slide_id="deferred_revenue",
        layout="story_slide",
        chart_primitive="revenue_bridge",
        slots=frozenset({"primary_chart", "commentary_panel"}),
        reference="Excel deferred waterfall",
        narrative_role="deferred_billings",
        section_label="REVENUE · DEFERRED",
    ),
    "cash_forecast": SlideTemplateSpec(
        slide_id="cash_forecast",
        layout="cash_trend",
        chart_primitive="cash_bridge",
        slots=frozenset({"kpi_strip", "primary_chart", "source_table", "commentary_panel"}),
        reference="IMG_8055",
        narrative_role="liquidity_trajectory",
        section_label="CASH",
    ),
    "headcount": SlideTemplateSpec(
        slide_id="headcount",
        layout="story_slide",
        chart_primitive="headcount_bridge",
        slots=frozenset({"kpi_strip", "primary_chart", "commentary_panel"}),
        reference="IMG_8045",
        narrative_role="capacity",
        section_label="CAPACITY",
    ),
    "department_spend": SlideTemplateSpec(
        slide_id="department_spend",
        layout="marketing_source",
        chart_primitive="department_spend",
        slots=frozenset({"source_table", "commentary_panel"}),
        reference="IMG_8027 · CARET variance table",
        narrative_role="spend_variance",
        section_label="FINANCIALS",
    ),
    "risks_opportunities": SlideTemplateSpec(
        slide_id="risks_opportunities",
        layout="risk_matrix",
        chart_primitive="none",
        slots=frozenset({"callout_matrix", "commentary_panel"}),
        reference="IMG_8050 strategy bullets",
        narrative_role="board_decisions",
        section_label="DECISIONS",
    ),
    "validation": SlideTemplateSpec(
        slide_id="validation",
        layout="compact_table",
        chart_primitive="none",
        slots=frozenset({"source_table"}),
        reference="CFO appendix — data quality",
        narrative_role="appendix_validation",
        section_label="APPENDIX",
    ),
}

# Section transitions use a dedicated template (not in narrative order registry)
SECTION_TRANSITION_TEMPLATE = SlideTemplateSpec(
    slide_id="section_transition",
    layout="section_transition",
    chart_primitive="none",
    slots=frozenset({"section_narrative", "kpi_strip"}),
    reference="CARET Slide1–2 · section dividers",
    narrative_role="section_bridge",
    section_label="OPERATING REVIEW",
)

# Legacy / dynamic layouts — never assign at build time; remap if seen
DEPRECATED_LAYOUTS: dict[str, str] = {
    "chart_primary": "story_slide",
    "dual_metric": "story_slide",
    "narrative_table_split": "marketing_source",
    "executive_dashboard": "executive_scorecard",
    "executive_ytd": "executive_scorecard",
    "section_divider": "section_transition",
    "narrative": "mda_narrative",
}


def resolve_template(slide_id: str) -> SlideTemplateSpec | None:
    if slide_id.startswith("section_"):
        return SECTION_TRANSITION_TEMPLATE
    return SLIDE_TEMPLATE_REGISTRY.get(slide_id)


def allowed_layouts() -> frozenset[str]:
    layouts = {s.layout for s in SLIDE_TEMPLATE_REGISTRY.values()}
    layouts.add(SECTION_TRANSITION_TEMPLATE.layout)
    return frozenset(layouts)


def apply_template_to_slide(slide: SlideContent) -> SlideContent:
    """Force canonical layout from registry; strip dynamic composition hints."""
    spec = resolve_template(slide.slide_id)
    if not spec:
        layout = DEPRECATED_LAYOUTS.get(slide.layout or "story_slide", slide.layout)
        return slide.model_copy(update={"layout": layout, "secondary_chart": None})  # type: ignore[arg-type]

    layout = spec.layout
    if slide.layout in DEPRECATED_LAYOUTS:
        layout = DEPRECATED_LAYOUTS[slide.layout]

    updates: dict = {"layout": layout, "secondary_chart": None}
    if spec.section_label and not slide.section_label:
        updates["section_label"] = spec.section_label
    return slide.model_copy(update=updates)  # type: ignore[arg-type]
