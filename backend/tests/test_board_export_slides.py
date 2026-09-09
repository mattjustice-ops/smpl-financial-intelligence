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
            as_of_period="2026-05",
        ),
        validation=ExportValidationSummary(
            status="pass",
            failed_count=0,
            warning_count=0,
            passed_count=1,
            checks=[
                ValidationCheck(
                    scenario="Combined",
                    period="2026-05",
                    validation_name="stub",
                    status="pass",
                )
            ],
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
    # Content slides are preceded by section_transition dividers, so assert on
    # slide ids rather than positions.
    ids = [s.slide_id for s in pkg.slides]
    assert "executive_summary" in ids
    assert ids[-1] == "validation"
    assert ids.index("section_executive_summary") < ids.index("executive_summary")


def test_executive_package_mode():
    bundle = _minimal_bundle()
    pkg = build_board_package_from_bundle(bundle, package_mode="executive_summary")
    ids = [s.slide_id for s in pkg.slides]
    # Executive mode drops the section dividers and any slide the viability
    # filter finds too sparse to stand on its own.
    assert ids == ["executive_summary", "mda_summary", "cash_forecast", "risks_opportunities"]
    assert "marketing_channels" not in ids


def test_executive_summary_executive_ytd_layout():
    bundle = _minimal_bundle()
    pkg = build_board_package_from_bundle(bundle)
    exec_slide = next(s for s in pkg.slides if s.slide_id == "executive_summary")
    assert exec_slide.layout == "executive_scorecard"
    assert exec_slide.table is not None or exec_slide.chart is not None
    if exec_slide.table:
        assert exec_slide.table.headers[1] == "CM"


def test_story_slide_layout_has_no_secondary_chart():
    bundle = _minimal_bundle()
    pkg = build_board_package_from_bundle(bundle)
    story = [s for s in pkg.slides if s.layout == "story_slide"]
    assert story, "expected at least one story_slide in the deck"
    assert all(s.secondary_chart is None for s in story)


def test_viability_filter_drops_slides_without_data():
    # The minimal bundle carries no GTM rows; the slide must not be emitted
    # rather than rendering as an empty frame in front of a board.
    pkg = build_board_package_from_bundle(_minimal_bundle())
    assert "gtm_performance" not in [s.slide_id for s in pkg.slides]


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
