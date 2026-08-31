"""Tests for Prompt 5 MD&A slide payload blocks (GTM, headcount, dept updates)."""

from __future__ import annotations

from decimal import Decimal

from app.services.dashboard.schemas import ExecutiveFlowResponse
from app.services.marketing.schemas import ActualBudgetForecastResponse, MarketingMetricRow
from app.services.reporting.export.prompt5_deck import build_prompt5_payload
from app.services.reporting.export.prompt5_mda_slides import (
    build_deck_slide_order,
    build_gtm_channel_metrics_table,
    build_projected_headcount_block,
    enrich_mda_deck_slides,
)
from app.services.reporting.export.schemas import ExportValidationSummary, HeadcountRow, ReportingBundle


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


def _mkt_row(channel: str, spend: int, mqls: int, pipe: int, won: int) -> MarketingMetricRow:
    return MarketingMetricRow(
        organization_id="test-org",
        scenario="Actual",
        period="2026-06",
        marketing_channel=channel,
        marketing_spend=Decimal(spend),
        mqls=Decimal(mqls),
        sqls=Decimal(mqls // 2),
        opportunities_created=Decimal(max(mqls // 3, 1)),
        pipeline_arr_created=Decimal(pipe),
        closed_won_arr=Decimal(won),
        win_rate_on_pipeline_created=Decimal("0.12"),
        source_table="test",
    )


def test_gtm_channel_metrics_table_from_marketing_data():
    mkt = ActualBudgetForecastResponse(
        organization_id="test-org",
        start_period="2026-01",
        end_period="2026-12",
        actual=[_mkt_row("Outbound", 5000, 12, 484000, 180000)],
        budget=[_mkt_row("Outbound", 8000, 10, 400000, 150000)],
    )
    bundle = _minimal_bundle(marketing_channel_comparison=mkt)
    table = build_gtm_channel_metrics_table(bundle, "2026-06")
    assert table["available"] is True
    assert len(table["rows"]) == 1
    row = table["rows"][0]
    assert row["channel"] == "Outbound"
    assert row["mqls"] == 12
    assert row["efficiency_x"] > 0


def test_projected_headcount_block_department_stack():
    hc_rows = [
        HeadcountRow(scenario="Actual", period="2026-06", department="Engineering", headcount=Decimal("8")),
        HeadcountRow(scenario="Budget", period="2026-06", department="Engineering", headcount=Decimal("10")),
        HeadcountRow(scenario="Actual", period="2026-06", department="Sales", headcount=Decimal("4")),
        HeadcountRow(scenario="Budget", period="2026-06", department="Sales", headcount=Decimal("5")),
        HeadcountRow(scenario="Actual", period="2026-01", department="Engineering", headcount=Decimal("6")),
        HeadcountRow(scenario="Budget", period="2026-01", department="Engineering", headcount=Decimal("7")),
    ]
    bundle = _minimal_bundle(headcount=hc_rows)
    block = build_projected_headcount_block(bundle)
    assert block["available"] is True
    assert block["include_slide"] is True
    assert block["kpis"]["total_hc_actual"] == 12
    assert len(block["departments"]) == 2
    assert block["stacked_bars"][0]["actual"] == 8
    assert block["tenure"]["available"] is False


def test_projected_headcount_omits_slide_when_empty():
    bundle = _minimal_bundle(headcount=[])
    block = build_projected_headcount_block(bundle)
    assert block["include_slide"] is False


def test_deck_slide_order_skips_headcount_when_unavailable():
    payload = {"projected_headcount": {"include_slide": False}, "gtm_channel_metrics": {"available": True}}
    order = build_deck_slide_order(payload)
    assert order["include_projected_headcount"] is False
    assert order["total_slides"] == 13
    keys = [s["key"] for s in order["slides"]]
    assert "projected_headcount" not in keys
    assert "dept_funnel_efficiency" in keys
    assert order["slides"][-1]["key"] == "appendix_cfs"


def test_deck_slide_order_includes_headcount_when_available():
    payload = {"projected_headcount": {"include_slide": True}, "gtm_channel_metrics": {"available": True}}
    order = build_deck_slide_order(payload)
    assert order["total_slides"] == 14
    keys = [s["key"] for s in order["slides"]]
    assert keys.index("projected_headcount") < keys.index("board_actions")


def test_prompt5_payload_includes_mda_blocks():
    mkt = ActualBudgetForecastResponse(
        organization_id="test-org",
        start_period="2026-01",
        end_period="2026-12",
        actual=[_mkt_row("Organic Search", 5000, 13, 443000, 120000)],
        budget=[],
    )
    hc = [
        HeadcountRow(scenario="Actual", period="2026-06", department="G&A", headcount=Decimal("3")),
        HeadcountRow(scenario="Budget", period="2026-06", department="G&A", headcount=Decimal("4")),
    ]
    bundle = _minimal_bundle(marketing_channel_comparison=mkt, headcount=hc)
    payload = build_prompt5_payload(bundle)
    assert "deck_slide_order" in payload
    assert payload["gtm_channel_metrics"]["available"] is True
    assert payload["projected_headcount"]["include_slide"] is True
    assert "funnel_efficiency" in payload["department_updates"]
    assert payload["deck_slide_order"]["gtm_slide_6"]["primary_layout"] == "channel_metrics_table"


def test_enrich_mda_wires_gtm_performance_layout():
    payload = {"gtm_performance": {}}
    bundle = _minimal_bundle(
        marketing_channel_comparison=ActualBudgetForecastResponse(
            organization_id="test-org",
            start_period="2026-01",
            end_period="2026-12",
            actual=[_mkt_row("Paid Search", 8000, 19, 508000, 90000)],
            budget=[],
        )
    )
    out = enrich_mda_deck_slides(payload, bundle)
    assert out["gtm_performance"]["primary_layout"] == "channel_metrics_table"
    assert "layout_hint" in out["gtm_performance"]
