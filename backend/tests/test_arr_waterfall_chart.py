"""ARR waterfall chart block — matches board platform boardWaterfallMonthM."""

import pytest
from decimal import Decimal

from app.services.dashboard.schemas import ExecutiveFlowResponse, WaterfallSummaryRow
from app.services.reporting.export.board_platform_metrics import build_arr_waterfall_chart
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


def test_waterfall_chart_structure():
    wf = build_arr_waterfall_chart(_minimal_bundle())
    assert wf["labels"] == [
        "Begin ARR",
        "New Business",
        "Expansion",
        "Reactivation",
        "Contraction",
        "Churn",
        "End ARR",
    ]
    assert len(wf["offsets_m"]) == 7
    assert wf["offsets_m"][0] == 0
    assert wf["offsets_m"][-1] == 0
    assert wf["scenario"] == "Actual"
    assert wf["colors"]["total"] == "00d4aa"
    assert wf["bar_colors"][0] == "00d4aa"
    assert wf["bar_colors"][1] == "166534"
    assert wf["bar_colors"][4] == "991b1b"
    assert wf["render"] == "shape_rectangles"
    assert len(wf["shape_bars"]) == 7


def test_waterfall_offsets_match_board_platform_formula():
    """Mirror board-data.js boardWaterfallMonthM stacking math."""
    bop, nb, exp, react, con, churn = 83.44, 1.68, 0.87, 0.14, -0.31, -0.52
    after_nb = bop + nb
    after_exp = after_nb + exp
    after_react = after_exp + react
    after_con = after_react + con
    after_churn = after_con + churn

    expected_offsets = [0, bop, after_nb, after_exp, after_con, after_churn, 0]
    expected_heights = [bop, nb, exp, react, abs(con), abs(churn), after_churn]

    rows = [
        ("2026-05", "ending_arr", Decimal("83440000")),
        ("2026-06", "new_business", Decimal("1680000")),
        ("2026-06", "expansion", Decimal("870000")),
        ("2026-06", "reactivation", Decimal("140000")),
        ("2026-06", "contraction", Decimal("-310000")),
        ("2026-06", "churn", Decimal("-520000")),
        ("2026-06", "ending_arr", Decimal("85310000")),
    ]

    def _wf_row(period: str, wtype: str, amount: Decimal) -> WaterfallSummaryRow:
        return WaterfallSummaryRow(
            organization_id="test-org",
            scenario="Actual",
            period=period,
            waterfall_name="arr",
            waterfall_type=wtype,
            line_item=wtype,
            line_item_order=0,
            amount=amount,
            source_table="test",
        )

    bundle = _minimal_bundle(
        comparison_waterfalls={"arr": [_wf_row(p, w, a) for p, w, a in rows]},
    )
    wf = build_arr_waterfall_chart(bundle)
    assert wf["offsets_m"] == pytest.approx(expected_offsets, abs=0.01)
    assert wf["heights_m"] == pytest.approx(expected_heights, abs=0.01)
    assert wf["steps"][1]["display"] == "+$1.68M"
    assert wf["steps"][0]["display"] == "$83.44M"
