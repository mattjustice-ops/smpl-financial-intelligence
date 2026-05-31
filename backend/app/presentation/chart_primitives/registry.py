"""Chart primitives — standardized archetypes tied to slide templates."""

from __future__ import annotations

from app.presentation.templates.archetypes import ChartPrimitive, resolve_template
from app.services.board_package.pptx_chart_archetypes import (
    ARCHETYPE_STYLES,
    SLIDE_ARCHETYPE,
    ChartArchetype,
    apply_archetype,
    infer_archetype,
)
from app.services.board_package.schemas import ChartSpec


def primitive_for_slide(slide_id: str) -> ChartPrimitive:
    spec = resolve_template(slide_id)
    if spec:
        return spec.chart_primitive  # type: ignore[return-value]
    return "none"


def chart_archetype_for_slide(slide_id: str, chart: ChartSpec | None) -> ChartArchetype:
    """Map template primitive → renderer archetype (no title-based guessing when slide_id known)."""
    prim = primitive_for_slide(slide_id)
    if prim == "none" or chart is None:
        return "generic"
    mapping: dict[ChartPrimitive, ChartArchetype] = {
        "executive_kpi_trend": "executive_kpi_trend",
        "arr_waterfall": "arr_waterfall",
        "funnel_conversion": "funnel_conversion",
        "pipeline_movement_bridge": "pipeline_movement_bridge",
        "revenue_bridge": "revenue_bridge",
        "cash_bridge": "cash_bridge",
        "headcount_bridge": "headcount_bridge",
        "department_spend": "department_spend",
        "scatter_plot": "scatter_plot",
        "aging_distribution": "aging_distribution",
        "opportunity_spotlight": "opportunity_spotlight",
    }
    if slide_id in SLIDE_ARCHETYPE:
        return SLIDE_ARCHETYPE[slide_id]
    return mapping.get(prim, infer_archetype(chart, slide_id))


def apply_primitive(chart: ChartSpec, slide_id: str) -> ChartSpec:
    arch = chart_archetype_for_slide(slide_id, chart)
    return apply_archetype(chart, arch)


__all__ = [
    "ARCHETYPE_STYLES",
    "apply_primitive",
    "chart_archetype_for_slide",
    "primitive_for_slide",
]
