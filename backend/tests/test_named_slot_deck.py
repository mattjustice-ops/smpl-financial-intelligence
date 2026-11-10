"""The MD&A deck fills named slots from the close. Prompt 5 is only the fallback."""

from __future__ import annotations

import zipfile
from datetime import date
from decimal import Decimal
from io import BytesIO

from lxml import etree

from app.services.dashboard.schemas import ExecutiveFlowResponse, WaterfallAttributionRow, WaterfallSummaryRow
from app.services.marketing.schemas import ActualBudgetForecastResponse, MarketingMetricRow
from app.services.financial_statements.financial_statement_service import (
    NormalizedStatementLine,
    NormalizedStatementResponse,
    SummaryResponse,
)
from app.services.reporting.export.board_export_service import build_mda_deck_pptx_bytes
from app.services.reporting.export.board_review.from_bundle import review_input
from app.services.reporting.export.schemas import ExportValidationSummary, ReportingBundle

ORG = "00000000-0000-0000-0000-000000000001"
LINES = (
    (1, "Revenue", "1000"),
    (2, "Cost of revenue", "200"),
    (3, "Gross profit", "800"),
    (4, "Sales and marketing", "100"),
    (5, "Research and development", "80"),
    (6, "General and administrative", "50"),
    (7, "EBITDA", "570"),
    (8, "Net income", "400"),
)


def _line(scenario: str, month: int, order: int, name: str, amount: str) -> NormalizedStatementLine:
    return NormalizedStatementLine(
        organization_id=ORG,
        scenario=scenario,
        period=date(2026, month, 1),
        line_item=name,
        line_item_order=order,
        section="income",
        amount=Decimal(amount),
        source_table="test",
        source_column="amount",
    )


def _empty(kind: str) -> NormalizedStatementResponse:
    return NormalizedStatementResponse(
        organization_id=ORG,
        scenario="Actual",
        start_period=date(2026, 1, 1),
        end_period=date(2026, 5, 1),
        statement_type=kind,
    )


def _wf(scenario: str, name: str, wtype: str, amount: str) -> WaterfallSummaryRow:
    return WaterfallSummaryRow(
        organization_id=ORG,
        scenario=scenario,
        period="2026-05",
        waterfall_name=name,
        waterfall_type=wtype,
        line_item=wtype,
        line_item_order=1,
        amount=Decimal(amount),
        source_table="test",
    )


def _bundle() -> ReportingBundle:
    rows = [
        _line(scenario, month, order, name, amount)
        for month in range(1, 6)
        for scenario in ("Actual", "Budget")
        for order, name, amount in LINES
    ]
    income = NormalizedStatementResponse(
        organization_id=ORG,
        scenario="Actual",
        start_period=date(2026, 1, 1),
        end_period=date(2026, 5, 1),
        statement_type="income_statement",
        rows=rows,
    )
    summary = SummaryResponse(
        organization_id=ORG,
        scenario="Actual",
        start_period=date(2026, 1, 1),
        end_period=date(2026, 5, 1),
        income_statement=income,
        balance_sheet=_empty("balance_sheet"),
        cash_flow=_empty("cash_flow"),
        validation=[],
    )
    arr = [
        _wf("Actual", "arr", "beginning_arr", "1000"),
        _wf("Actual", "arr", "new_business", "100"),
        _wf("Actual", "arr", "expansion_arr", "50"),
        _wf("Actual", "arr", "contraction_arr", "20"),
        _wf("Actual", "arr", "churn_arr", "-10"),
        _wf("Actual", "arr", "ending_arr", "1120"),
        _wf("Budget", "arr", "beginning_arr", "1000"),
        _wf("Budget", "arr", "new_business", "80"),
        _wf("Budget", "arr", "ending_arr", "1080"),
    ]
    cash = [
        _wf("Actual", "cash_flow", "beginning_cash", "500"),
        _wf("Actual", "cash_flow", "cash_collections", "200"),
        _wf("Actual", "cash_flow", "payroll_cash_out", "30"),
        _wf("Actual", "cash_flow", "ending_cash", "670"),
        _wf("Budget", "cash_flow", "beginning_cash", "480"),
        _wf("Budget", "cash_flow", "cash_collections", "190"),
        _wf("Budget", "cash_flow", "payroll_cash_out", "-25"),
        _wf("Budget", "cash_flow", "ending_cash", "645"),
    ]
    return ReportingBundle(
        organization_id=ORG,
        organization_name="Test Co",
        scenario="Combined",
        period_label="May 2026",
        as_of_period="2026-05",
        start_period="2026-01",
        end_period="2026-12",
        currency="USD",
        executive_flow=ExecutiveFlowResponse(
            organization_id=ORG,
            scenario="Combined",
            start_period="2026-01",
            end_period="2026-12",
            as_of_period="2026-05",
        ),
        financial_statements=summary,
        comparison_waterfalls={"arr": arr, "cash_flow": cash},
        validation=ExportValidationSummary(status="pass", failed_count=0, warning_count=0, passed_count=1),
    )


def _metric(scenario: str, period: str, *, channel: str | None, kind: str, spend: str, mqls: str, created: str) -> MarketingMetricRow:
    return MarketingMetricRow(
        organization_id=ORG,
        scenario=scenario,
        period=period,
        marketing_channel=channel,
        marketing_spend=Decimal(spend),
        mqls=Decimal(mqls),
        opportunities_created=Decimal("4"),
        pipeline_arr_created=Decimal(created),
        closed_won_arr=Decimal("100"),
        closed_lost_arr=Decimal("40"),
        slipped_pipeline_arr=Decimal("10"),
        beginning_pipeline_arr=Decimal("500"),
        ending_pipeline_arr=Decimal("650"),
        source_table="test",
        row_kind=kind,
    )


def test_review_input_passes_loaded_gtm_customers_and_forecast():
    bundle = _bundle()
    bundle.as_of_period = "2026-06"
    extra = []
    for month in range(1, 13):
        scenarios = ("Budget",) if month > 6 else ("Actual", "Budget")
        for scenario in scenarios:
            for order, name, amount in LINES:
                extra.append(_line(scenario, month, order, name, amount))
        if month > 6:
            for order, name, amount in LINES:
                extra.append(_line("Forecast", month, order, name, amount))
    bundle.financial_statements.income_statement.rows.extend(extra)
    bundle.financial_statements.balance_sheet.rows.extend(
        [
            _line("Forecast", 12, 1, "Cash", "900000"),
            _line("Budget", 12, 1, "Cash", "800000"),
        ]
    )
    bundle.comparison_waterfalls["arr"].extend(
        [
            _wf("Forecast", "arr", "ending_arr", "1200000"),
            _wf("Budget", "arr", "ending_arr", "1300000"),
        ]
    )
    for row in bundle.comparison_waterfalls["arr"][-2:]:
        row.period = "2026-12"
    bundle.marketing_comparison = ActualBudgetForecastResponse(
        organization_id=ORG,
        start_period="2026-01",
        end_period="2026-12",
        actual=[_metric("Actual", "2026-06", channel=None, kind="total", spend="329300", mqls="707", created="3680000")],
        budget=[_metric("Budget", "2026-06", channel=None, kind="total", spend="290700", mqls="838", created="8420000")],
    )
    bundle.marketing_channel_comparison = ActualBudgetForecastResponse(
        organization_id=ORG,
        start_period="2026-01",
        end_period="2026-12",
        actual=[_metric("Actual", "2026-06", channel="Paid Search", kind="channel", spend="329300", mqls="707", created="3680000")],
        budget=[_metric("Budget", "2026-06", channel="Paid Search", kind="channel", spend="290700", mqls="838", created="8420000")],
    )
    bundle.arr_customers = [
        WaterfallAttributionRow(
            organization_id=ORG,
            scenario="Actual",
            period="2026-06",
            waterfall_type="new_logo",
            customer_name="Brightmere Analytics",
            arr_impact=Decimal("212000"),
            amount=Decimal("212000"),
            source_table="test",
        )
    ]
    bundle.pipeline_drilldown = {
        "slipped_pipeline": {
            "opportunities": [{"customer_name": "Ironwharf Capital", "arr_impact": "215000"}]
        }
    }
    payload = review_input(bundle)
    assert payload is not None
    assert payload["gtm"]["channels"][0]["name"] == "Paid Search"
    assert payload["gtm"]["channels"][0]["spend"] == 329300
    assert payload["gtm"]["funnel"]["actual"]["mql"] == 707
    assert payload["pipeline"]["actual"]["closed_won"] == -100
    assert payload["customers"]["new_business"][0]["name"] == "Brightmere Analytics"
    assert payload["customers"]["slipped"][0]["name"] == "Ironwharf Capital"
    assert payload["outlook"]["fy"]["revenue"] == 6000 + 6000
    assert payload["outlook"]["fy"]["ending_arr"] == 1200000
    assert payload["outlook"]["fy"]["ending_cash"] == 900000
    assert payload["outlook"]["plan_fy"]["ending_arr"] == 1300000
    assert "people" not in payload


def test_review_input_keeps_arr_losses_negative_and_cash_outflows_negative():
    payload = review_input(_bundle())
    assert payload is not None and payload["status"] == "draft"
    approved = review_input(_bundle(), finalized=True)
    assert approved is not None and approved["status"] == "approved"
    assert payload is not None
    actual = payload["arr"]["actual"]
    assert actual["contraction"] == -20
    assert actual["churn"] == -10
    assert actual["ending"] == 1120
    assert payload["cash"]["actual"]["payroll"] == -30
    assert payload["cash"]["plan"]["payroll"] == -25
    assert "people" not in payload
    assert "outlook" not in payload


def test_mda_deck_fills_named_slots_and_does_not_call_the_model(monkeypatch):
    def _fail(*_args, **_kwargs):
        raise AssertionError("Prompt 5 should not run when the close month is loaded")

    monkeypatch.setattr(
        "app.services.reporting.export.prompt5_deck.build_claude_deck_pptx_bytes",
        _fail,
    )
    raw, source = build_mda_deck_pptx_bytes(_bundle(), use_ai_commentary=False)
    assert source == "named_slots"
    assert raw[:2] == b"PK"
    root = etree.fromstring(zipfile.ZipFile(BytesIO(raw)).read("ppt/charts/chart1.xml"))
    ns = {"c": "http://schemas.openxmlformats.org/drawingml/2006/chart", "a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    texts = ["".join(t.text or "" for t in node.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}t")) for node in root.findall(".//c:dLbl", ns)]
    assert texts
    assert all("\u2212" not in t and "\u2060" not in t for t in texts)
    rpr = root.find(".//c:dLbl//a:rPr", ns)
    assert rpr.get("sz") == "900"
    assert rpr.find("a:latin", ns).get("typeface") == "Calibri"
    line = root.find(".//c:scatterChart//a:ln", ns)
    assert line.get("w") == "6350"
    assert root.find(".//c:scatterStyle", ns).get("val") == "line"
