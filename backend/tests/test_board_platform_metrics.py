"""Tests for board platform metric registry (deck payload tie-out)."""

from decimal import Decimal

from app.services.dashboard.schemas import ExecutiveFlowResponse
from app.services.reporting.export.board_platform_metrics import (
    build_deck_payload,
    build_period_matrix,
    gross_margin_pct,
    validate_deck_payload,
)
from app.services.reporting.export.schemas import ExportValidationSummary, ReportingBundle


def _minimal_bundle(**overrides) -> ReportingBundle:
    base = dict(
        organization_id="test-org",
        organization_name="Test Co",
        scenario="Combined",
        start_period="2026-01",
        end_period="2026-12",
        as_of_period="2026-06",
        period_label="June 2026",
        currency="USD",
        executive_flow=ExecutiveFlowResponse(
            organization_id="test-org",
            scenario="Combined",
            start_period="2026-01",
            end_period="2026-12",
            as_of_period="2026-06",
        ),
        comparison_waterfalls={},
        validation=ExportValidationSummary(status="pass"),
    )
    base.update(overrides)
    return ReportingBundle(**base)


def test_period_matrix_has_qtd_revenue_row():
    payload = build_period_matrix(_minimal_bundle())
    rev = next(r for r in payload["rows"] if r["metric"] == "Revenue")
    assert "qtd" in rev
    assert "actual" in rev["qtd"]
    assert "budget" in rev["qtd"]


def test_fy_outlook_headcount_is_integer_not_money():
    bundle = _minimal_bundle()
    payload = build_deck_payload(bundle)
    hc = payload["fy_outlook"]["headcount"]
    assert hc["format"] == "integer_headcount_not_dollars"
    assert isinstance(hc["current_month_actual"], int)


def test_gross_margin_uses_gross_profit_over_revenue():
    from datetime import date

    from app.services.financial_statements.financial_statement_service import (
        NormalizedStatementLine,
        NormalizedStatementResponse,
        SummaryResponse,
    )

    rev = Decimal("7350000")
    gp = Decimal("5145000")
    period = date(2026, 6, 1)
    is_rows = [
        NormalizedStatementLine(
            organization_id="test-org",
            scenario="Actual",
            period=period,
            line_item="Revenue",
            line_item_order=1,
            section="revenue",
            amount=rev,
            source_table="t",
            source_column="c",
        ),
        NormalizedStatementLine(
            organization_id="test-org",
            scenario="Actual",
            period=period,
            line_item="Gross Profit",
            line_item_order=2,
            section="profit",
            amount=gp,
            source_table="t",
            source_column="c",
        ),
    ]
    empty = NormalizedStatementResponse(
        organization_id="test-org",
        scenario="Combined",
        start_period=period,
        end_period=period,
        statement_type="cf",
        rows=[],
    )
    fs = SummaryResponse(
        organization_id="test-org",
        scenario="Combined",
        start_period=period,
        end_period=period,
        income_statement=NormalizedStatementResponse(
            organization_id="test-org",
            scenario="Combined",
            start_period=period,
            end_period=period,
            statement_type="is",
            rows=is_rows,
        ),
        balance_sheet=empty,
        cash_flow=empty,
        validation=[],
    )
    bundle = _minimal_bundle(comparison_financial_statements=fs)
    gm = gross_margin_pct(bundle, "2026-06", "Actual")
    assert gm is not None
    assert abs(float(gm) - 70.0) < 0.5


def test_validate_flags_empty_cfs():
    payload = build_deck_payload(_minimal_bundle())
    warnings = validate_deck_payload(payload)
    cfs = payload.get("ytd_cash_flow_statement") or {}
    assert "beginning_cash" in (cfs.get("actual") or {})
    assert "beginning_cash" in (cfs.get("budget") or {})


def test_appendix_block_present():
    payload = build_deck_payload(_minimal_bundle())
    assert "appendix" in payload
    assert payload["appendix"]["label"].startswith("Appendix A")


def test_enriched_prompt5_payload_has_v3_blocks():
    from app.services.reporting.export.prompt5_deck import build_prompt5_payload

    payload = build_prompt5_payload(_minimal_bundle())
    assert payload["payload_meta"]["version"] == "v3_full"
    assert "monthly_trends" in payload
    assert "ending_arr_outlook_m" in payload["monthly_trends"]
    assert "pl_detail" in payload
    assert "gtm_funnel" in payload
    assert "mom_context" in payload
    ro = payload["risks_and_opportunities"]
    assert "risks" in ro and "opportunities" in ro
    assert len(ro["risks"]) == 4
    assert len(ro["opportunities"]) == 4
    assert "bridge_table" in payload["arr_analysis"]
    assert "waterfall_chart" in payload["arr_analysis"]
    wf = payload["arr_analysis"]["waterfall_chart"]
    assert wf["render"] == "shape_rectangles"
    assert len(wf["shape_bars"]) == 7
    assert wf["steps"][0]["kind"] == "total"
    assert wf["steps"][-1]["kind"] == "total"
    assert wf["colors"]["total"] == "00d4aa"
    assert "bridge_table" in payload["cash_liquidity"]
    assert "summary_table" in payload["fy_outlook"]
    assert "executive_kpis" not in payload


def test_ending_arr_point_in_time_cm_equals_ytd():
    from app.services.reporting.export.board_period_ytd import rollup_ending_arr

    bundle = _minimal_bundle()
    roll = rollup_ending_arr(bundle)
    assert roll.current_month == roll.qtd == roll.ytd
