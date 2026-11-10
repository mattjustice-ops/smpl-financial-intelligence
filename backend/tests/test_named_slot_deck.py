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
from app.services.reporting.export.board_review.deck import build_named_slot_deck
from app.services.reporting.export.board_review.from_bundle import review_input
from app.services.reporting.export.schemas import ExportValidationSummary, HeadcountRow, ReportingBundle

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
    for row in bundle.marketing_comparison.budget:
        row.closed_lost_arr = Decimal("0")
        row.slipped_pipeline_arr = Decimal("0")
    raw, source = build_named_slot_deck(bundle)
    assert source == "named_slots"
    assert raw[:2] == b"PK"
    for row in bundle.marketing_comparison.budget:
        row.pipeline_arr_created = Decimal("0")
    raw, source = build_named_slot_deck(bundle)
    assert source == "named_slots"


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


def test_review_input_uses_loaded_pipeline_spend_customers_people_and_last_year():
    bundle = _bundle()
    bundle.comparison_waterfalls["pipeline"] = [
        _wf("Actual", "pipeline", "beginning_pipeline", "2800000"),
        _wf("Actual", "pipeline", "pipeline_created", "900000"),
        _wf("Actual", "pipeline", "closed_won", "-400000"),
        _wf("Actual", "pipeline", "closed_lost", "-700000"),
        _wf("Actual", "pipeline", "slipped_pipeline", "-200000"),
        _wf("Actual", "pipeline", "ending_pipeline", "2400000"),
        _wf("Budget", "pipeline", "beginning_pipeline", "3000000"),
        _wf("Budget", "pipeline", "pipeline_created", "1500000"),
        _wf("Budget", "pipeline", "closed_won", "-800000"),
        _wf("Budget", "pipeline", "closed_lost", "-500000"),
        _wf("Budget", "pipeline", "slipped_pipeline", "-250000"),
        _wf("Budget", "pipeline", "ending_pipeline", "2950000"),
    ]
    bundle.marketing_channel_comparison = ActualBudgetForecastResponse(
        organization_id=ORG,
        start_period="2026-01",
        end_period="2026-12",
        actual=[
            _metric("Actual", "2026-05", channel="Paid Search", kind="channel", spend="0", mqls="10", created="1"),
            _metric("Actual", "2026-05", channel="GL: Paid search", kind="gl_account", spend="120000", mqls="0", created="0"),
        ],
        budget=[
            _metric("Budget", "2026-05", channel="Paid Search", kind="channel", spend="0", mqls="12", created="2"),
            _metric("Budget", "2026-05", channel="GL: Paid search", kind="gl_account", spend="100000", mqls="0", created="0"),
        ],
    )
    bundle.marketing_comparison = ActualBudgetForecastResponse(
        organization_id=ORG,
        start_period="2026-01",
        end_period="2026-12",
        actual=[_metric("Actual", "2026-05", channel=None, kind="total", spend="0", mqls="10", created="1")],
        budget=[_metric("Budget", "2026-05", channel=None, kind="total", spend="0", mqls="12", created="2")],
    )
    bundle.arr_customers = [
        WaterfallAttributionRow(
            organization_id=ORG,
            scenario="Actual",
            period="2026-05",
            waterfall_type="expansion",
            customer_name=None,
            arr_impact=Decimal("25000"),
            amount=Decimal("25000"),
            source_table="test",
            raw={"account_name": "Harbor"},
        )
    ]
    bundle.pipeline_drilldown = {
        "closed_won": {"opportunities": [{"customer_name": "Northwind", "arr_impact": "50000"}]},
        "slipped_pipeline": {"opportunities": [{"customer_name": "BlueRiver", "arr_impact": "10000"}]},
    }
    bundle.headcount = [
        HeadcountRow(
            scenario="Actual", period="2026-05", department="Sales", headcount=Decimal("11"),
            heads_open=Decimal("10"), hires=Decimal("2"), departures=Decimal("1"),
            salaries=Decimal("100"), taxes_benefits=Decimal("10"), variable_pay=Decimal("5"), stock_comp=Decimal("1"),
            source_table="test",
        ),
        HeadcountRow(
            scenario="Budget", period="2026-05", department="Sales", headcount=Decimal("12"),
            salaries=Decimal("120"), taxes_benefits=Decimal("10"), variable_pay=Decimal("5"), stock_comp=Decimal("1"),
            source_table="test",
        ),
        HeadcountRow(scenario="Budget", period="2026-12", department="Sales", headcount=Decimal("14"), source_table="test"),
    ]
    for month in range(1, 6):
        for order, name, amount in LINES:
            bundle.financial_statements.income_statement.rows.append(
                NormalizedStatementLine(
                    organization_id=ORG, scenario="Actual", period=date(2025, month, 1),
                    line_item=name, line_item_order=order, section="income",
                    amount=Decimal(amount), source_table="test", source_column="amount",
                )
            )
    bundle.comparison_waterfalls["arr"].extend([
        _wf("Actual", "arr", "beginning_arr", "700"),
        _wf("Actual", "arr", "ending_arr", "800"),
    ])
    for row in bundle.comparison_waterfalls["arr"][-2:]:
        row.period = "2025-05"
    bundle.comparison_waterfalls["cash_flow"].extend([
        _wf("Actual", "cash_flow", "beginning_cash", "400"),
        _wf("Actual", "cash_flow", "ending_cash", "450"),
    ])
    for row in bundle.comparison_waterfalls["cash_flow"][-2:]:
        row.period = "2025-05"

    months = [f"2026-{m:02d}" for m in range(1, 6)]
    ts = {"Actual": {"cfs": {m: {"net_income": 40, "cfo": 30, "ending_cash": 450} for m in months}}}
    ts["Actual"]["cfs"]["2026-01"]["beginning_cash"] = 400
    ts["Budget"] = {"cfs": {m: {"net_income": 50, "cfo": 35, "ending_cash": 500} for m in months}}
    ts["Budget"]["cfs"]["2026-01"]["beginning_cash"] = 380

    payload = review_input(bundle, ts_data=ts)
    assert payload is not None
    assert payload["pipeline"]["actual"]["beginning"] == 2800000
    assert payload["pipeline"]["actual"]["closed_lost"] == -700000
    assert payload["pipeline"]["plan"]["ending"] == 2950000
    assert payload["pipeline"]["plan"]["closed_lost"] == -500000
    assert payload["gtm"]["channels"][0]["name"] == "Paid search"
    assert payload["gtm"]["channels"][0]["spend"] == 120000
    assert payload["gtm"]["channels"][0]["plan"] == 100000
    assert payload["gtm"]["funnel"]["plan"]["opp"] == 4
    names = {row["name"] for row in payload["customers"]["closed_won"]}
    assert "Northwind" in names
    assert payload["customers"]["expansion"][0]["name"] == "Harbor"
    assert payload["customers"]["slipped"][0]["name"] == "BlueRiver"
    assert payload["people"]["departments"][0]["hires"] == 2
    assert payload["people"]["departments"][0]["heads_close"] == 11
    assert payload["people"]["year_end"]["plan"] == 14
    assert payload["pnl"]["month"]["last_year"]["revenue"] == 1000
    assert payload["pnl"]["ytd"]["last_year"]["revenue"] == 5000
    assert payload["arr"]["last_year_ending"] == 800
    assert payload["cash"]["last_year_ending"] == 450
    assert payload["cf_ytd"]["actual"]["net_income"] == 200
    assert payload["cf_ytd"]["actual"]["beginning"] == 400
    assert payload["cf_ytd"]["plan"]["cfo"] == 175

    raw, source = build_named_slot_deck(bundle, ts_data=ts)
    assert source == "named_slots"
    assert raw[:2] == b"PK"
