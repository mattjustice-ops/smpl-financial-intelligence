"""Governance rules from executive reporting platform spec."""

from __future__ import annotations

from app.services.board_package.schemas import ChartSpec, SlideContent, TableSpec
from app.services.reporting.export.executive_reporting_governance import (
    FORBIDDEN_DERIVATIONS,
    LIMITS,
    apply_density_governance,
    chart_type_for_kind,
    select_chart_kind,
    should_escalate_to_appendix,
)


def test_select_chart_time_series_is_line():
    assert select_chart_kind(category_count=12, is_time_series=True) == "line"


def test_select_chart_movement_is_waterfall():
    assert select_chart_kind(category_count=5, is_time_series=False, movement_type="pipeline_movement") == "waterfall"


def test_should_escalate_large_table():
    rows = [[str(i), str(i)] for i in range(12)]
    slide = SlideContent(
        slide_id="marketing_channels",
        title="Channels",
        table=TableSpec(headers=["A", "B"], rows=rows),
    )
    assert should_escalate_to_appendix(slide)


def test_apply_density_drops_table_when_chart_on_story():
    slide = SlideContent(
        slide_id="gtm_performance",
        title="GTM",
        layout="story_slide",
        chart=ChartSpec(title="T", categories=["A"], series={"s": [1.0]}),
        table=TableSpec(headers=["H"], rows=[["1"]]),
    )
    out = apply_density_governance(slide)
    assert out.chart is not None
    assert out.table is None


def test_forbidden_derivations_documented():
    assert "arr_from_revenue" in FORBIDDEN_DERIVATIONS
    assert LIMITS.max_chart_categories_executive == 7
