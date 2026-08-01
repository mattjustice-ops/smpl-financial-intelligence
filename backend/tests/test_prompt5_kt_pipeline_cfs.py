"""Prompt 5 KT seed, pipeline waterfall, and YTD CFS Actual wiring."""

from __future__ import annotations

from decimal import Decimal

from app.services.dashboard.schemas import ExecutiveFlowResponse, WaterfallSummaryRow
from app.services.reporting.export.board_platform_kt_seed import (
    KT_SEED_MARKER,
    build_seed_key_takeaways,
    format_kt_seed_block,
)
from app.services.reporting.export.board_platform_metrics import (
    build_pipeline_waterfall_chart,
    build_ytd_cash_flow_statement,
)
from app.services.reporting.export.prompt5_deck import (
    _refill_stripped_key_takeaways,
    build_prompt5_payload,
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


def _pipe_row(period: str, wtype: str, amount: Decimal) -> WaterfallSummaryRow:
    return WaterfallSummaryRow(
        organization_id="test-org",
        scenario="Actual",
        period=period,
        waterfall_name="pipeline",
        waterfall_type=wtype,
        line_item=wtype,
        line_item_order=0,
        amount=amount,
        source_table="test",
    )


def test_pipeline_waterfall_includes_beginning_and_end_totals():
    rows = [
        _pipe_row("2026-05", "ending_pipeline", Decimal("180770000")),
        _pipe_row("2026-06", "beginning_pipeline", Decimal("180770000")),
        _pipe_row("2026-06", "pipeline_created", Decimal("5400000")),
        _pipe_row("2026-06", "closed_won", Decimal("1800000")),
        _pipe_row("2026-06", "closed_lost", Decimal("7910000")),
        _pipe_row("2026-06", "slipped_pipeline", Decimal("9870000")),
        _pipe_row("2026-06", "ending_pipeline", Decimal("166590000")),
    ]
    wf = build_pipeline_waterfall_chart(
        _minimal_bundle(comparison_waterfalls={"pipeline": rows})
    )
    assert wf["labels"][0] == "Begin Pipeline"
    assert wf["labels"][-1] == "End Pipeline"
    assert wf["steps"][0]["kind"] == "total"
    assert wf["steps"][-1]["kind"] == "total"
    assert wf["beginning_pipeline_raw"] == 180770000.0
    assert abs(wf["signed_m"][0] - 180.77) < 0.02
    assert abs(wf["signed_m"][-1] - 166.59) < 0.02
    assert len(wf["shape_bars"]) == 6
    assert all("category_y" in b for b in wf["shape_bars"])
    assert wf["category_label_placement"] == "x_axis_below_chart"


def test_ytd_cfs_actual_not_forecast_and_keeps_zeros():
    ts_data = {
        "Actual": {
            "cfs": {
                "2026-01": {
                    "beginning_cash": 45_300_000,
                    "net_income": 400_000,
                    "da": 100_000,
                    "sbc": 0,
                    "chg_ar": 500_000,
                    "cfo": 1_000_000,
                    "capex": -50_000,
                    "cfi": -50_000,
                    "net_change": 950_000,
                    "ending_cash": 46_250_000,
                },
                "2026-06": {
                    "net_income": 409_000,
                    "da": 98_000,
                    "sbc": 0,
                    "chg_ar": 200_000,
                    "cfo": 700_000,
                    "capex": -55_000,
                    "cfi": -55_000,
                    "net_change": 645_000,
                    "ending_cash": 50_260_000,
                },
            }
        },
        "Forecast": {
            "cfs": {
                "2026-06": {
                    "net_income": 999_999_999,
                    "ending_cash": 1,
                }
            }
        },
        "Budget": {
            "cfs": {
                "2026-01": {
                    "beginning_cash": 46_770_000,
                    "net_income": 390_000,
                    "ending_cash": 47_000_000,
                },
                "2026-06": {
                    "net_income": 393_000,
                    "ending_cash": 48_170_000,
                },
            }
        },
    }
    cfs = build_ytd_cash_flow_statement(_minimal_bundle(), ts_data=ts_data)
    assert "never Forecast" in cfs["scenario_policy"]
    assert cfs["actual"]["scenario"] == "Actual"
    assert cfs["actual"]["net_income"] != "n/a"
    # True zero SBC preserved (not collapsed to n/a).
    assert cfs["actual"]["stock_based_compensation"] == "$0.00"
    assert "variance" in cfs
    # Forecast giant NI must not leak into Actual.
    assert "999" not in cfs["actual"]["net_income"]


def test_kt_seed_and_refill_wiped_slots():
    payload = build_prompt5_payload(_minimal_bundle())
    assert "key_takeaways_by_slide" in payload
    seeds = payload["key_takeaways_by_slide"]
    assert len(seeds["slide_2_executive"]) >= 4
    assert KT_SEED_MARKER in format_kt_seed_block(payload)

    script = (
        "const bullets2 = [\n"
        '  "1. Keep me",\n'
        '  "—",\n'
        '  "—",\n'
        '  "4. Keep four",\n'
        "];\n"
    )
    out = _refill_stripped_key_takeaways(script, payload)
    assert '"—"' not in out or out.count('"—"') < 2
    assert "1. Keep me" in out
    # Slot 2 refilled from seed.
    assert seeds["slide_2_executive"][1].split(",")[0] in out or "2." in out


def test_prompt5_payload_wires_beginning_pipeline_and_kt_seed():
    rows = [
        _pipe_row("2026-05", "ending_pipeline", Decimal("180000000")),
        _pipe_row("2026-06", "ending_pipeline", Decimal("166000000")),
        _pipe_row("2026-06", "pipeline_created", Decimal("5400000")),
        _pipe_row("2026-06", "closed_lost", Decimal("7910000")),
        _pipe_row("2026-06", "slipped_pipeline", Decimal("9870000")),
    ]
    payload = build_prompt5_payload(
        _minimal_bundle(comparison_waterfalls={"pipeline": rows})
    )
    gtm = payload["gtm_performance"]
    assert "beginning_pipeline" in gtm
    assert gtm["beginning_pipeline_raw"] == 180000000.0
    assert "pipeline_waterfall_chart" in gtm
    assert gtm["pipeline_waterfall_chart"]["render"] == "shape_rectangles"
    assert payload["key_takeaways_by_slide"]["slide_7_pipeline"]
