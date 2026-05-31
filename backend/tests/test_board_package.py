"""Tests for the board reporting package generator.

Covers:
- canonical 10-slide structure (titles, ordering, graceful handling of missing inputs)
- pptx rendering produces a valid binary that python-pptx can re-open
- Google Slides batchUpdate JSON is a list of well-formed requests
- the FastAPI route returns a .pptx with the right content type
"""

from __future__ import annotations

import io
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from app.services.board_package.package import build_board_package, fmt_money, fmt_pct, fmt_ratio
from app.services.board_package.pptx_builder import render_pptx_bytes
from app.services.board_package.schemas import (
    ArrBridge,
    BoardPackageInputs,
    BookingsForecastSlide,
    CashForecastSlide,
    ChurnExpansionAnalysis,
    CompanyKpiSummary,
    MrrWaterfallSlide,
    QuotaAttainmentRow,
    RevenueForecastSlide,
    SalesEfficiencySlide,
)
from app.services.board_package.service import generate_board_package
from app.services.board_package.slides_structure import to_google_slides_requests
from app.services.commentary.schemas import (
    Citation,
    CommentaryOutput,
    CommentarySection,
    DataGap,
    FollowupQuestion,
    RiskOpportunity,
)

EXPECTED_SLIDE_ORDER = [
    ("executive_summary", "Executive Summary"),
    ("revenue_performance", "Revenue Performance"),
    ("mrr_waterfall", "MRR Waterfall"),
    ("arr_bridge", "ARR Bridge"),
    ("bookings_forecast", "Bookings Forecast"),
    ("pipeline_coverage", "Pipeline Coverage"),
    ("retention_churn_expansion", "Retention, Churn & Expansion"),
    ("cash_forecast", "Cash Forecast"),
    ("sales_efficiency", "Sales Efficiency & Quota Attainment"),
    ("risks_and_opportunities", "Key Risks & Opportunities"),
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _sample_commentary() -> CommentaryOutput:
    section = lambda title, narrative: CommentarySection(
        title=title,
        narrative=narrative,
        citations=[Citation(label="NRR", value="1.05")],
    )
    return CommentaryOutput(
        period_label="May 2026",
        executive_summary=section("Executive Summary", "Strong month. ARR up 10%."),
        revenue_commentary=section("Revenue", "Revenue grew 10% over prior month."),
        mrr_waterfall_commentary=section("MRR", "MRR closed at $110k with NRR 1.05."),
        bookings_forecast_commentary=section("Bookings", "Coverage at 3.0x supports the base case."),
        cash_forecast_commentary=section("Cash", "Cash position remains healthy."),
        risks_and_opportunities=[
            RiskOpportunity(
                type="risk",
                description="Gross churn 8% is above trailing average.",
                evidence="$8k of $100k beginning MRR.",
                severity="medium",
            ),
            RiskOpportunity(
                type="opportunity",
                description="Expansion outpacing churn in Enterprise.",
                evidence="$5k expansion vs $8k churn — but Enterprise segment is net positive.",
                severity="medium",
            ),
        ],
        followup_questions=[
            FollowupQuestion(question="Which segments drove churn?", rationale="Need to attribute root cause."),
        ],
        data_gaps=[
            DataGap(topic="Segment-level churn", data_needed="Per-segment downgrade reasons."),
        ],
    )


def _full_inputs() -> BoardPackageInputs:
    return BoardPackageInputs(
        period_label="May 2026",
        organization_name="Demo Org",
        currency="USD",
        prepared_for="Board of Directors",
        prepared_date=date(2026, 5, 31),
        kpi_summary=CompanyKpiSummary(
            period_label="May 2026",
            arr=Decimal("1320000"),
            mrr=Decimal("110000"),
            nrr=Decimal("1.05"),
            grr=Decimal("0.90"),
            rule_of_40=Decimal("0.24"),
            magic_number=Decimal("0.73"),
            cac=Decimal("3000"),
            cac_payback_months=Decimal("5.0"),
            ltv=Decimal("5365.90"),
            ltv_to_cac=Decimal("1.79"),
            burn_multiple=Decimal("0.25"),
            sales_efficiency=Decimal("3.0"),
            pipeline_coverage=Decimal("3.0"),
            gross_mrr_churn_rate=Decimal("0.08"),
            logo_churn_rate=Decimal("0.05"),
            net_mrr_churn_rate=Decimal("-0.05"),
        ),
        mrr_waterfall=MrrWaterfallSlide(
            period=date(2026, 5, 1),
            beginning_mrr=Decimal("100000"),
            new_mrr=Decimal("15000"),
            expansion_mrr=Decimal("5000"),
            contraction_mrr=Decimal("2000"),
            churn_mrr=Decimal("8000"),
            reactivation_mrr=Decimal("0"),
            ending_mrr=Decimal("110000"),
            nrr=Decimal("1.05"),
            grr=Decimal("0.90"),
        ),
        arr_bridge=ArrBridge(
            period=date(2026, 5, 1),
            beginning_arr=Decimal("1200000"),
            new_arr=Decimal("180000"),
            expansion_arr=Decimal("60000"),
            contraction_arr=Decimal("24000"),
            churn_arr=Decimal("96000"),
            reactivation_arr=Decimal("0"),
            ending_arr=Decimal("1320000"),
        ),
        bookings_forecast=BookingsForecastSlide(
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            total_forecast=Decimal("180000"),
            weighted_forecast=Decimal("160000"),
            stage_adjusted_forecast=Decimal("170000"),
            historical_forecast=Decimal("175000"),
            conservative=Decimal("150000"),
            base=Decimal("180000"),
            upside=Decimal("220000"),
            confidence_score=Decimal("0.72"),
            confidence_band="medium",
            coverage_ratio=Decimal("3.0"),
            target_bookings=Decimal("60000"),
            total_pipeline=Decimal("600000"),
        ),
        revenue_forecast=RevenueForecastSlide(
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            forecasted_revenue=Decimal("110000"),
            actual_revenue=Decimal("110000"),
            prior_period_revenue=Decimal("100000"),
            growth_rate=Decimal("0.10"),
        ),
        cash_forecast=CashForecastSlide(
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            forecasted_collections=Decimal("125000"),
            open_ar_balance=Decimal("80000"),
            expected_dso=Decimal("42"),
            cash_position=Decimal("4500000"),
            runway_months=Decimal("18"),
            aging_buckets={"0-30": Decimal("50000"), "31-60": Decimal("20000"), "60+": Decimal("10000")},
        ),
        sales_efficiency=SalesEfficiencySlide(
            new_bookings_arr=Decimal("180000"),
            sales_marketing_expense=Decimal("60000"),
            sales_efficiency=Decimal("3.0"),
            magic_number=Decimal("0.73"),
            cac=Decimal("3000"),
            cac_payback_months=Decimal("5.0"),
        ),
        quota_attainment=[
            QuotaAttainmentRow(
                rep_id="REP-001",
                rep_name="Alex Doe",
                segment="Enterprise",
                quota_arr=Decimal("400000"),
                closed_won_arr=Decimal("180000"),
                attainment_rate=Decimal("0.45"),
            ),
            QuotaAttainmentRow(
                rep_id="REP-002",
                rep_name="Jamie Smith",
                segment="SMB",
                quota_arr=Decimal("200000"),
                closed_won_arr=Decimal("220000"),
                attainment_rate=Decimal("1.10"),
            ),
        ],
        churn_expansion=ChurnExpansionAnalysis(
            period=date(2026, 5, 1),
            expansion_mrr=Decimal("5000"),
            contraction_mrr=Decimal("2000"),
            churn_mrr=Decimal("8000"),
            reactivation_mrr=Decimal("0"),
            new_customers=20,
            churned_customers=10,
            expanded_customers=4,
            contracted_customers=1,
            reactivated_customers=0,
            notable_movements=["CUST-007 churned ($2k MRR)", "CUST-014 expanded ($1.5k MRR)"],
        ),
        commentary=_sample_commentary(),
    )


# ---------------------------------------------------------------------------
# Canonical package builder
# ---------------------------------------------------------------------------


def test_build_board_package_produces_ten_slides_in_order() -> None:
    pkg = build_board_package(_full_inputs())
    assert pkg.period_label == "May 2026"
    assert pkg.organization_name == "Demo Org"
    assert len(pkg.slides) == 10
    for slide, (expected_id, expected_title) in zip(pkg.slides, EXPECTED_SLIDE_ORDER):
        assert slide.slide_id == expected_id
        assert slide.title == expected_title


def test_executive_summary_pulls_from_commentary_and_kpis() -> None:
    pkg = build_board_package(_full_inputs())
    exec_slide = pkg.slides[0]
    assert "ARR" in exec_slide.bullets[0]
    assert exec_slide.narrative == "Strong month. ARR up 10%."


def test_mrr_waterfall_slide_has_table_and_chart() -> None:
    pkg = build_board_package(_full_inputs())
    mrr_slide = next(s for s in pkg.slides if s.slide_id == "mrr_waterfall")
    assert mrr_slide.table is not None
    assert mrr_slide.chart is not None
    assert mrr_slide.chart.chart_type == "waterfall"
    # Beginning + new + expansion + reactivation + (-contraction) + (-churn) + ending
    assert len(mrr_slide.chart.categories) == 7


def test_quota_table_is_populated_when_reps_provided() -> None:
    pkg = build_board_package(_full_inputs())
    se_slide = next(s for s in pkg.slides if s.slide_id == "sales_efficiency")
    assert se_slide.table is not None
    assert len(se_slide.table.rows) == 2
    assert se_slide.table.headers[0] == "Rep ID"


def test_risks_slide_renders_commentary_items() -> None:
    pkg = build_board_package(_full_inputs())
    risks = next(s for s in pkg.slides if s.slide_id == "risks_and_opportunities")
    joined = "\n".join(risks.bullets)
    assert "RISK" in joined
    assert "OPPORTUNITY" in joined
    assert "Follow-up questions" in joined
    assert risks.footnote and "Data gaps" in risks.footnote


def test_missing_inputs_render_not_provided_message() -> None:
    sparse = BoardPackageInputs(period_label="May 2026", organization_name="Demo")
    pkg = build_board_package(sparse)
    assert len(pkg.slides) == 10
    for slide in pkg.slides:
        body = (slide.narrative or "") + " " + " ".join(slide.bullets)
        assert "Not provided" in body, f"Slide {slide.slide_id} did not flag missing data"


def test_formatters() -> None:
    assert fmt_money(Decimal("1500000")) == "$1.50M USD"
    assert fmt_money(Decimal("1500")) == "$1.5K USD"
    assert fmt_money(Decimal("250")) == "$250.00 USD"
    assert fmt_money(Decimal("-500")) == "-$500.00 USD"
    assert fmt_money(None) == "n/a"
    assert fmt_pct(Decimal("0.123")) == "12.3%"
    assert fmt_pct(None) == "n/a"
    assert fmt_ratio(Decimal("3.05")) == "3.05x"


# ---------------------------------------------------------------------------
# PPTX renderer
# ---------------------------------------------------------------------------


def test_render_pptx_produces_valid_zip_bytes() -> None:
    pptx = pytest.importorskip("pptx")
    pkg = build_board_package(_full_inputs())
    data = render_pptx_bytes(pkg)
    assert isinstance(data, bytes)
    # .pptx files are zip archives; first two bytes are always "PK".
    assert data[:2] == b"PK"
    # Re-open with python-pptx to verify it's a structurally valid presentation.
    prs = pptx.Presentation(io.BytesIO(data))
    # 1 cover slide + 10 content slides
    assert len(prs.slides) == 11


def test_render_pptx_with_sparse_inputs_still_succeeds() -> None:
    pytest.importorskip("pptx")
    sparse = BoardPackageInputs(period_label="May 2026", organization_name="Demo")
    pkg = build_board_package(sparse)
    data = render_pptx_bytes(pkg)
    assert data[:2] == b"PK"


# ---------------------------------------------------------------------------
# Google Slides structure
# ---------------------------------------------------------------------------


def test_to_google_slides_requests_returns_batch_update_shape() -> None:
    pkg = build_board_package(_full_inputs())
    payload = to_google_slides_requests(pkg)
    assert "presentation_title" in payload
    assert payload["presentation_title"].startswith("Demo Org")
    assert isinstance(payload["requests"], list)
    assert len(payload["requests"]) > 0
    # Every request item is a dict with exactly one operation key.
    for req in payload["requests"]:
        assert isinstance(req, dict)
        assert len(req) == 1


def test_google_slides_includes_one_createSlide_per_slide_plus_cover() -> None:
    pkg = build_board_package(_full_inputs())
    payload = to_google_slides_requests(pkg)
    create_slide_count = sum(1 for r in payload["requests"] if "createSlide" in r)
    assert create_slide_count == 11  # 1 cover + 10 content


def test_google_slides_renders_tables_for_known_slides() -> None:
    pkg = build_board_package(_full_inputs())
    payload = to_google_slides_requests(pkg)
    create_table_count = sum(1 for r in payload["requests"] if "createTable" in r)
    assert create_table_count >= 5  # most content slides include a table


# ---------------------------------------------------------------------------
# FastAPI route
# ---------------------------------------------------------------------------


def test_board_package_generate_route() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/v1/board-package/generate",
        json=_full_inputs().model_dump(mode="json"),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["slides"]) == 10
    assert body["slides"][0]["title"] == "Executive Summary"


def test_board_package_pptx_route_returns_binary() -> None:
    pytest.importorskip("pptx")
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/v1/board-package/pptx",
        json=_full_inputs().model_dump(mode="json"),
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.content[:2] == b"PK"


def test_board_package_slides_structure_route() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/v1/board-package/slides-structure",
        json=_full_inputs().model_dump(mode="json"),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "presentation_title" in body
    assert isinstance(body["requests"], list)
    assert any("createSlide" in r for r in body["requests"])
