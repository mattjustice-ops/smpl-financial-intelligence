"""Executive reporting governance — density, lineage, appendix, chart selection.

Layered on top of board_slides / semantic reporting. See docs/EXECUTIVE_REPORTING_GOVERNANCE.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.services.board_package.schemas import ChartSpec, SlideContent, TableSpec

# ---------------------------------------------------------------------------
# Semantic source-of-truth hierarchy (primary CSV/API datasets)
# ---------------------------------------------------------------------------

SOURCE_HIERARCHY: dict[str, tuple[str, ...]] = {
    "arr": (
        "actual_mrr_waterfall",
        "forecast_mrr_waterfall",
        "budget_mrr_waterfall",
    ),
    "pipeline": (
        "actual_pipeline_waterfall",
        "forecast_pipeline_waterfall",
        "budget_pipeline_waterfall",
    ),
    "opportunity_movements": (
        "actual_opportunity_movements",
        "forecast_opportunity_movements",
        "budget_opportunity_movements",
    ),
    "gtm": (
        "actual_marketing_pipeline",
        "forecast_marketing_pipeline",
        "budget_marketing_pipeline",
    ),
    "revenue": (
        "deferred_revenue_waterfall",
        "income_statement",
    ),
    "cash": ("cash_flow_bridge",),
    "gl": ("gl_detail",),
}

FORBIDDEN_DERIVATIONS: dict[str, str] = {
    "arr_from_revenue": "Never derive ARR from GAAP revenue.",
    "cash_from_ebitda": "Never derive ending cash from EBITDA.",
    "collections_from_revenue": "Never derive collections from revenue — use cash_flow_bridge.",
    "pipeline_from_opportunities_only": (
        "Never derive pipeline movement totals from opportunity rows alone when pipeline waterfall exists."
    ),
}

DISALLOWED_CHART_TYPES = frozenset({"pie", "radar", "donut", "gauge", "3d"})

ChartKind = Literal[
    "line",
    "column",
    "bar",
    "waterfall",
    "funnel",
    "scatter",
    "heatmap",
    "treemap",
]


@dataclass(frozen=True)
class DensityLimits:
    max_primary_visuals: int = 1
    max_secondary_visuals: int = 1
    max_bullets: int = 5
    max_table_rows_executive: int = 5
    max_table_rows_trigger_appendix: int = 8
    max_chart_categories_executive: int = 7
    max_chart_categories_trigger_appendix: int = 7
    max_chart_series: int = 2
    max_visible_table_columns: int = 12
    max_opportunities_executive: int = 10
    max_gl_accounts_executive: int = 12


LIMITS = DensityLimits()


@dataclass(frozen=True)
class DashboardVisualSpec:
    """Shared semantic definition for PPTX, Excel, and future dashboard widgets."""

    chart_type: str
    x_axis: str
    y_axis: str | None
    grouping: str | None
    filters: tuple[str, ...]
    drilldown_dimensions: tuple[str, ...]
    kpi_card_ids: tuple[str, ...]
    commentary_zone: str = "footer"


def assert_metric_source(metric_family: str, *, used_source: str) -> None:
    """Raise if a metric family is wired to a non-primary source (dev/test guard)."""
    allowed = SOURCE_HIERARCHY.get(metric_family)
    if not allowed:
        return
    key = used_source.lower().replace("-", "_")
    if not any(a in key for a in allowed):
        raise ValueError(
            f"Metric family '{metric_family}' must use primary source {allowed}; got '{used_source}'. "
            f"{FORBIDDEN_DERIVATIONS.get('pipeline_from_opportunities_only', '')}"
        )


def select_chart_kind(
    *,
    category_count: int,
    is_time_series: bool,
    movement_type: str | None = None,
    narrative_importance: str = "medium",
) -> ChartKind:
    """Chart selection intelligence — prefer executive-readable types."""
    if is_time_series or category_count >= 6:
        return "line"
    if movement_type in ("waterfall", "bridge", "arr_movement", "pipeline_movement"):
        return "waterfall"
    if movement_type == "funnel" or category_count <= 5:
        if movement_type == "funnel":
            return "funnel"
        return "column" if category_count <= 4 else "bar"
    if category_count > 7:
        return "bar"
    if narrative_importance == "relationship":
        return "scatter"
    if narrative_importance == "distribution":
        return "heatmap"
    return "column"


def chart_type_for_kind(kind: ChartKind) -> str:
    mapping: dict[ChartKind, str] = {
        "line": "line",
        "column": "column",
        "bar": "bar",
        "waterfall": "column",
        "funnel": "column",
        "scatter": "column",
        "heatmap": "column",
        "treemap": "column",
    }
    return mapping.get(kind, "column")


def should_escalate_to_appendix(slide: SlideContent) -> bool:
    """Executive deck summarizes; appendix holds detail."""
    if slide.table and len(slide.table.rows) > LIMITS.max_table_rows_trigger_appendix:
        return True
    if slide.table and len(slide.table.headers) > LIMITS.max_visible_table_columns:
        return True
    if slide.chart and len(slide.chart.categories) > LIMITS.max_chart_categories_trigger_appendix:
        return True
    if len(slide.bullets) > LIMITS.max_bullets:
        return True
    if slide.slide_id == "opportunity_drilldown" and slide.spotlight_cards:
        if len(slide.spotlight_cards) > LIMITS.max_opportunities_executive:
            return True
    if slide.slide_id == "department_spend" and slide.table:
        if len(slide.table.rows) > LIMITS.max_gl_accounts_executive:
            return True
    return False


def apply_density_governance(slide: SlideContent) -> SlideContent:
    """Enforce per-slide density caps before render."""
    chart = slide.chart
    table = slide.table
    secondary = slide.secondary_chart

    if chart and chart.chart_type in DISALLOWED_CHART_TYPES:
        chart = chart.model_copy(update={"chart_type": "column"})  # type: ignore[arg-type]

    if chart and len(chart.series) > LIMITS.max_chart_series:
        chart = chart.model_copy(
            update={"series": dict(list(chart.series.items())[: LIMITS.max_chart_series])}
        )

    if table and len(table.rows) > LIMITS.max_table_rows_executive:
        from app.services.reporting.export.board_chart_density import rank_table_top_movers

        table = rank_table_top_movers(
            table.headers,
            table.rows,
            max_rows=LIMITS.max_table_rows_executive,
        )

    bullets = slide.bullets[: LIMITS.max_bullets]

    if slide.layout in ("story_slide", "executive_ytd", "cash_trend") and chart and table:
        table = None
        secondary = None

    return slide.model_copy(
        update={
            "chart": chart,
            "table": table,
            "secondary_chart": secondary,
            "bullets": bullets,
            "kpi_cards": slide.kpi_cards[:4],
        }
    )


STORY_ARC_SECTIONS: tuple[str, ...] = (
    "gtm_performance",
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
)
