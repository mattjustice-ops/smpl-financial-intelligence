"""Executive chart archetypes — shared typography, density, and axis rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.services.board_package.schemas import ChartSpec

ChartArchetype = Literal[
    "executive_kpi_trend",
    "arr_waterfall",
    "funnel_conversion",
    "pipeline_movement_bridge",
    "revenue_bridge",
    "cash_bridge",
    "variance_heatmap",
    "scatter_plot",
    "aging_distribution",
    "opportunity_spotlight",
    "risk_matrix",
    "department_spend",
    "headcount_bridge",
    "generic",
]


@dataclass(frozen=True)
class ArchetypeStyle:
    chart_type: str
    max_categories: int
    max_series: int
    legend: bool
    y_axis_label: str | None
    number_format: str  # excel-style for value axis
    title_max_len: int
    prefer_line: bool = False


ARCHETYPE_STYLES: dict[ChartArchetype, ArchetypeStyle] = {
    "executive_kpi_trend": ArchetypeStyle("line", 8, 2, True, None, '#,##0', 56),
    "arr_waterfall": ArchetypeStyle("column", 7, 1, False, "ARR", '#,##0', 48),
    "funnel_conversion": ArchetypeStyle("column", 6, 1, False, "%", '0%', 52),
    "pipeline_movement_bridge": ArchetypeStyle("column", 7, 1, False, "ARR", '#,##0', 52),
    "revenue_bridge": ArchetypeStyle("column", 7, 2, True, "Revenue", '#,##0', 52),
    "cash_bridge": ArchetypeStyle("line", 8, 2, True, "Cash", '#,##0', 48),
    "variance_heatmap": ArchetypeStyle("column", 8, 1, False, "Variance", '#,##0', 48),
    "scatter_plot": ArchetypeStyle("column", 8, 1, False, None, '#,##0', 48),
    "aging_distribution": ArchetypeStyle("column", 6, 1, False, "ARR", '#,##0', 48),
    "opportunity_spotlight": ArchetypeStyle("bar", 6, 1, False, "ARR", '#,##0', 48),
    "risk_matrix": ArchetypeStyle("column", 5, 1, False, None, '#,##0', 44),
    "department_spend": ArchetypeStyle("column", 7, 1, False, "Spend", '#,##0', 48),
    "headcount_bridge": ArchetypeStyle("column", 7, 1, False, "FTE", '#,##0', 48),
    "generic": ArchetypeStyle("column", 7, 2, True, None, '#,##0', 64),
}


SLIDE_ARCHETYPE: dict[str, ChartArchetype] = {
    "executive_summary": "executive_kpi_trend",
    "gtm_performance": "executive_kpi_trend",
    "funnel_conversion": "funnel_conversion",
    "pipeline_health": "pipeline_movement_bridge",
    "pipeline_movement": "pipeline_movement_bridge",
    "arr_waterfall": "arr_waterfall",
    "retention_churn": "executive_kpi_trend",
    "gaap_revenue": "revenue_bridge",
    "deferred_revenue": "revenue_bridge",
    "cash_forecast": "cash_bridge",
    "headcount": "headcount_bridge",
    "department_spend": "department_spend",
}


def infer_archetype(spec: ChartSpec, slide_id: str | None = None) -> ChartArchetype:
    if slide_id and slide_id in SLIDE_ARCHETYPE:
        return SLIDE_ARCHETYPE[slide_id]
    title = (spec.title or "").lower()
    if "waterfall" in title or "arr" in title:
        return "arr_waterfall"
    if "pipeline" in title and "movement" in title:
        return "pipeline_movement_bridge"
    if "cash" in title:
        return "cash_bridge"
    if "funnel" in title or "conversion" in title:
        return "funnel_conversion"
    if spec.chart_type == "line":
        return "executive_kpi_trend"
    return "generic"


def apply_archetype(spec: ChartSpec, archetype: ChartArchetype | None = None) -> ChartSpec:
    """Tag and trim chart spec for executive rendering."""
    arch = archetype or infer_archetype(spec)
    style = ARCHETYPE_STYLES[arch]
    cats = spec.categories[: style.max_categories]
    series = {k: v[: len(cats)] for k, v in list(spec.series.items())[: style.max_series]}
    y_label = spec.y_axis_label or style.y_axis_label
    chart_type = spec.chart_type
    if style.prefer_line or arch == "executive_kpi_trend":
        chart_type = "line"
    elif arch == "arr_waterfall":
        chart_type = "column"
    return spec.model_copy(
        update={
            "archetype": arch,
            "chart_type": chart_type,  # type: ignore[arg-type]
            "categories": cats,
            "series": series,
            "y_axis_label": y_label,
            "max_categories": style.max_categories,
            "title": spec.title[: style.title_max_len],
        },
    )


def render_hints(archetype: ChartArchetype) -> ArchetypeStyle:
    return ARCHETYPE_STYLES[archetype]
