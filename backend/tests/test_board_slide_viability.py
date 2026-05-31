"""Slide viability filter tests."""

from __future__ import annotations

from app.services.board_package.schemas import ChartSpec, SlideContent, TableSpec
from app.services.reporting.export.board_slide_viability import (
    _table_has_rows,
    chart_has_decision_value,
    filter_board_slides,
    is_viable,
    prune_slide_content,
)


def test_empty_chart_not_viable():
    spec = ChartSpec(title="T", categories=["A"], series={"S": [0.0, 0.0]})
    assert not chart_has_decision_value(spec)


def test_table_has_rows_accepts_table_spec():
    assert not _table_has_rows(None)
    assert _table_has_rows(TableSpec(headers=["A"], rows=[["1"]]))


def test_prune_drops_table_when_chart_present():
    slide = SlideContent(
        slide_id="gtm_performance",
        title="GTM",
        layout="story_slide",
        chart=ChartSpec(title="C", categories=["Jan"], series={"X": [100.0]}),
        table=TableSpec(headers=["H"], rows=[["a", "b"]]),
    )
    out = prune_slide_content(slide)
    assert out.chart is not None
    assert out.table is None


def test_filter_drops_sparse_slide():
    slides = [
        SlideContent(slide_id="executive_summary", title="Exec", layout="executive_ytd"),
        SlideContent(slide_id="marketing_channels", title="Ch", layout="story_slide"),
    ]
    out = filter_board_slides(slides)
    assert any(s.slide_id == "executive_summary" for s in out)
    assert not any(s.slide_id == "marketing_channels" for s in out)
