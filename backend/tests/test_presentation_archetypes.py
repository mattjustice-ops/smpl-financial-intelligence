"""Deterministic presentation template catalog."""

from __future__ import annotations

from app.presentation.templates.archetypes import (
    DEPRECATED_LAYOUTS,
    SLIDE_TEMPLATE_REGISTRY,
    apply_template_to_slide,
    resolve_template,
)
from app.presentation.visual_qa.rules import validate_slide_template
from app.services.board_package.schemas import SlideContent
from app.services.reporting.export.board_semantic_mappings import NARRATIVE_SLIDE_ORDER


def test_every_narrative_slide_has_template():
    for slide_id in NARRATIVE_SLIDE_ORDER:
        assert resolve_template(slide_id) is not None, slide_id


def test_apply_template_forces_canonical_layout():
    slide = SlideContent(
        slide_id="gtm_performance",
        title="GTM",
        layout="chart_primary",
        chart=None,
    )
    fixed = apply_template_to_slide(slide)
    assert fixed.layout == "story_slide"
    assert fixed.secondary_chart is None


def test_deprecated_layouts_remap():
    slide = SlideContent(slide_id="unknown_x", title="X", layout="dual_metric")
    fixed = apply_template_to_slide(slide)
    assert fixed.layout == DEPRECATED_LAYOUTS["dual_metric"]


def test_executive_summary_template():
    spec = resolve_template("executive_summary")
    assert spec is not None
    assert spec.layout == "executive_scorecard"
    assert spec.chart_primitive == "executive_kpi_trend"


def test_validate_rejects_secondary_chart():
    from app.services.board_package.schemas import ChartSpec

    slide = SlideContent(
        slide_id="arr_waterfall",
        title="ARR",
        layout="story_slide",
        secondary_chart=ChartSpec(title="x", categories=["a"], series={"s": [1.0]}),
    )
    issues = validate_slide_template(slide)
    assert any("secondary_chart" in i for i in issues)


def test_registry_covers_all_standard_slides():
    assert len(SLIDE_TEMPLATE_REGISTRY) >= 15
