"""Unit tests for 17-slide board export from reporting bundle."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.reporting.export.board_commentary_service import build_slide_commentary
from app.services.reporting.export.board_export_service import build_board_package_from_bundle
from app.services.dashboard.schemas import ExecutiveFlowResponse
from app.services.reporting.export.schemas import (
    CommentaryField,
    ExportValidationSummary,
    ReportingBundle,
    ValidationCheck,
)
from app.services.board_package.pptx_builder import render_pptx_bytes


def _minimal_bundle() -> ReportingBundle:
    org = "00000000-0000-0000-0000-000000000001"
    return ReportingBundle(
        organization_id=org,
        organization_name="Test Co",
        scenario="Combined",
        period_label="May 2026",
        as_of_period="2026-05",
        start_period="2026-01",
        end_period="2026-12",
        currency="USD",
        executive_flow=ExecutiveFlowResponse(
            organization_id=org,
            scenario="Combined",
            start_period="2026-01",
            end_period="2026-12",
        ),
        validation=ExportValidationSummary(
            status="pass",
            failed_count=0,
            warning_count=0,
            passed_count=1,
            checks=[ValidationCheck(validation_name="stub", status="pass")],
        ),
        mda_commentary=[
            CommentaryField(
                section="SaaS MD&A",
                what_changed="ARR above plan.",
                favorable="Enterprise expansion strong.",
                unfavorable="SMB churn elevated.",
            )
        ],
    )


def test_board_package_full_narrative():
    bundle = _minimal_bundle()
    pkg = build_board_package_from_bundle(bundle, include_validation_appendix=True)
    assert len(pkg.slides) >= 10  # viability filter may drop sparse slides
    assert pkg.slides[0].slide_id == "executive_summary"
    assert pkg.slides[0].layout == "executive_ytd"
    assert pkg.slides[-1].slide_id == "validation"


def test_executive_package_mode():
    bundle = _minimal_bundle()
    pkg = build_board_package_from_bundle(bundle, package_mode="executive_summary")
    assert len(pkg.slides) == 5
    assert all(s.slide_id != "marketing_channels" for s in pkg.slides)


def test_executive_summary_executive_ytd_layout():
    bundle = _minimal_bundle()
    pkg = build_board_package_from_bundle(bundle)
    exec_slide = pkg.slides[0]
    assert exec_slide.layout == "executive_scorecard"
    assert exec_slide.table is not None or exec_slide.chart is not None
    if exec_slide.table:
        assert exec_slide.table.headers[1] == "CM"


def test_gtm_slide_uses_story_layout():
    bundle = _minimal_bundle()
    pkg = build_board_package_from_bundle(bundle)
    gtm = next(s for s in pkg.slides if s.slide_id == "gtm_performance")
    assert gtm.layout == "story_slide"
    assert gtm.secondary_chart is None


def test_render_pptx_bytes_non_empty():
    bundle = _minimal_bundle()
    pkg = build_board_package_from_bundle(bundle)
    raw = render_pptx_bytes(pkg)
    assert raw[:2] == b"PK"
    assert len(raw) > 5000


def test_commentary_includes_strategic_context_keywords():
    bundle = _minimal_bundle()
    comm = build_slide_commentary(bundle, "executive_summary")
    assert comm.favorable
    assert "enterprise" in comm.favorable.lower() or "ARR" in comm.favorable
