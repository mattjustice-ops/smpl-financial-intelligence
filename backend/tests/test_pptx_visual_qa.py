"""Tests for presentation QA and orchestration."""

from __future__ import annotations

from app.services.board_package.pptx_presentation_orchestrator import enforce_executive_layout
from app.services.board_package.pptx_visual_qa import audit_slide_content, remediate_slide_content
from app.services.board_package.schemas import ChartSpec, SlideContent, TableSpec
from app.services.reporting.export.board_appendix_engine import split_slide_overflow


def test_remediate_drops_stacked_chart_table():
    slide = SlideContent(
        slide_id="gtm_performance",
        title="GTM",
        layout="story_slide",
        chart=ChartSpec(title="Trend", categories=["A"], series={"x": [1.0]}),
        table=TableSpec(headers=["H"], rows=[["1"]]),
    )
    fixed = remediate_slide_content(slide)
    assert fixed.chart is not None
    assert fixed.table is None


def test_appendix_split_on_large_table():
    rows = [[str(i), str(i * 10)] for i in range(12)]
    slide = SlideContent(
        slide_id="marketing_channels",
        title="Channels",
        layout="story_slide",
        table=TableSpec(headers=["Ch", "Val"], rows=rows),
    )
    exec_slide, appendix = split_slide_overflow(slide)
    assert exec_slide.table is not None
    assert len(exec_slide.table.rows) <= 5
    assert appendix is not None
    assert appendix.slide_id == "appendix_marketing_channels"


def test_enforce_story_layout_for_gtm():
    slide = SlideContent(slide_id="gtm_performance", title="GTM", layout="chart_primary")
    out = enforce_executive_layout(slide)
    assert out.layout == "story_slide"


def test_audit_flags_sparse_story():
    slide = SlideContent(slide_id="x", title="Empty", layout="story_slide")
    result = audit_slide_content(slide)
    assert not result.ok
