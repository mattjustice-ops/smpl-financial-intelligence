"""Canonical Net New ARR must never equal New Business alone."""

from __future__ import annotations

from decimal import Decimal

from app.services.dashboard.schemas import ExecutiveFlowResponse, WaterfallSummaryRow
from app.services.reporting.export.metric_registry import (
    NET_NEW_FORMULA_ID,
    compute_net_new_arr,
    compute_new_business_arr,
)
from app.services.reporting.export.board_metrics_snapshot import build_metrics_snapshot
from app.services.reporting.export.schemas import ExportValidationSummary, ReportingBundle


def _wf(
    period: str,
    wtype: str,
    amount: Decimal,
    scenario: str = "Actual",
) -> WaterfallSummaryRow:
    return WaterfallSummaryRow(
        organization_id="test-org",
        scenario=scenario,
        period=period,
        waterfall_name="arr",
        waterfall_type=wtype,
        line_item=wtype,
        line_item_order=0,
        amount=amount,
        source_table="test",
    )


def _bundle() -> ReportingBundle:
    as_of = "2026-06"
    rows = [
        _wf(as_of, "beginning_arr", Decimal("83450000")),
        _wf(as_of, "new_business", Decimal("1680000")),
        _wf(as_of, "new_arr", Decimal("1680000")),  # alias — must NOT become Net New alone
        _wf(as_of, "expansion", Decimal("869100")),
        _wf(as_of, "reactivation", Decimal("142900")),
        _wf(as_of, "contraction", Decimal("313700")),
        _wf(as_of, "churn", Decimal("520200")),
        _wf(as_of, "ending_arr", Decimal("85308000")),
    ]
    return ReportingBundle(
        organization_id="test-org",
        organization_name="Test Co",
        scenario="Combined",
        period_label="June 2026",
        as_of_period=as_of,
        start_period="2026-01",
        end_period="2026-12",
        currency="USD",
        executive_flow=ExecutiveFlowResponse(
            organization_id="test-org",
            scenario="Combined",
            start_period="2026-01",
            end_period="2026-12",
            as_of_period=as_of,
        ),
        comparison_waterfalls={"arr": rows},
        validation=ExportValidationSummary(
            status="pass", failed_count=0, warning_count=0, passed_count=0, checks=[]
        ),
    )


def test_net_new_formula_id() -> None:
    assert "nb+exp+react" in NET_NEW_FORMULA_ID


def test_compute_net_new_not_new_business() -> None:
    bundle = _bundle()
    nb = compute_new_business_arr(bundle, "2026-06")
    nn = compute_net_new_arr(bundle, "2026-06")
    assert nb == Decimal("1680000")
    # 1.68 + 0.8691 + 0.1429 − 0.3137 − 0.5202 = 1.8581M
    assert nn == Decimal("1858100")
    assert nn != nb


def test_snapshot_separates_net_new_and_new_business() -> None:
    snap = build_metrics_snapshot(_bundle())
    assert snap.new_arr_actual == Decimal("1680000")
    assert snap.net_new_arr == Decimal("1858100")
    assert snap.net_new_arr != snap.new_arr_actual
