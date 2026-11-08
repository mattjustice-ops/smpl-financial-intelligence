"""Export preflight arithmetic / completeness gates."""

from __future__ import annotations

from decimal import Decimal

from app.services.dashboard.schemas import ExecutiveFlowResponse, WaterfallSummaryRow
from app.services.reporting.export.export_preflight import run_export_preflight_checks
from app.services.reporting.export.schemas import ExportValidationSummary, HeadcountRow, ReportingBundle


def _wf(
    period: str,
    wtype: str,
    amount: Decimal,
    *,
    waterfall: str = "arr",
    scenario: str = "Actual",
) -> WaterfallSummaryRow:
    return WaterfallSummaryRow(
        organization_id="test-org",
        scenario=scenario,
        period=period,
        waterfall_name=waterfall,
        waterfall_type=wtype,
        line_item=wtype,
        line_item_order=0,
        amount=amount,
        source_table="test",
    )


def _base_bundle(**kwargs) -> ReportingBundle:
    as_of = "2026-06"
    arr = kwargs.pop("arr", None)
    if arr is None:
        arr = [
            _wf(as_of, "beginning_arr", Decimal("83450000")),
            _wf(as_of, "new_business", Decimal("1680000")),
            _wf(as_of, "expansion", Decimal("869100")),
            _wf(as_of, "reactivation", Decimal("142900")),
            _wf(as_of, "contraction", Decimal("313700")),
            _wf(as_of, "churn", Decimal("520200")),
            _wf(as_of, "ending_arr", Decimal("85308100")),  # ties
        ]
    cash = kwargs.pop("cash", [])
    headcount = kwargs.pop("headcount", [])
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
        comparison_waterfalls={"arr": arr, "cash_flow": cash},
        headcount=headcount,
        validation=ExportValidationSummary(
            status="pass", failed_count=0, warning_count=0, passed_count=0, checks=[]
        ),
        **kwargs,
    )


def test_arr_bridge_identity_pass() -> None:
    checks = run_export_preflight_checks(_base_bundle())
    arr = next(c for c in checks if c.validation_name == "export_preflight_arr_bridge_identity")
    assert arr.status == "pass"


def test_arr_bridge_identity_fail() -> None:
    as_of = "2026-06"
    arr = [
        _wf(as_of, "beginning_arr", Decimal("83450000")),
        _wf(as_of, "new_business", Decimal("1680000")),
        _wf(as_of, "expansion", Decimal("869100")),
        _wf(as_of, "reactivation", Decimal("142900")),
        _wf(as_of, "contraction", Decimal("313700")),
        _wf(as_of, "churn", Decimal("520200")),
        _wf(as_of, "ending_arr", Decimal("90000000")),  # broken
    ]
    checks = run_export_preflight_checks(_base_bundle(arr=arr))
    arr_check = next(c for c in checks if c.validation_name == "export_preflight_arr_bridge_identity")
    assert arr_check.status == "fail"


def test_headcount_missing_fails_when_arr_present() -> None:
    checks = run_export_preflight_checks(_base_bundle(headcount=[]))
    hc = next(c for c in checks if c.validation_name == "export_preflight_headcount_missing")
    assert hc.status == "fail"


def test_headcount_present_uses_the_loaded_roster_when_actual_is_empty() -> None:
    rows = [
        HeadcountRow(
            scenario="Forecast",
            period="2026-06",
            department="Engineering",
            headcount=Decimal("247"),
            source_table="forecast_employees",
        )
    ]
    checks = run_export_preflight_checks(_base_bundle(headcount=rows))
    hc = next(c for c in checks if c.validation_name == "export_preflight_headcount_present")
    assert hc.status == "pass"
    assert hc.actual_value == Decimal("247")
    assert hc.scenario == "Forecast"


def test_cash_preflight_includes_tax_interest_and_other() -> None:
    cash = [
        _wf("2026-06", "beginning_cash", Decimal("100"), waterfall="cash_flow"),
        _wf("2026-06", "cash_collections", Decimal("50"), waterfall="cash_flow"),
        _wf("2026-06", "payroll_cash_out", Decimal("-20"), waterfall="cash_flow"),
        _wf("2026-06", "tax_cash_out", Decimal("-5"), waterfall="cash_flow"),
        _wf("2026-06", "interest_cash_out", Decimal("-3"), waterfall="cash_flow"),
        _wf("2026-06", "other_operating_cash_out", Decimal("-2"), waterfall="cash_flow"),
        _wf("2026-06", "capex", Decimal("-10"), waterfall="cash_flow"),
        _wf("2026-06", "ending_cash", Decimal("110"), waterfall="cash_flow"),
    ]
    checks = run_export_preflight_checks(_base_bundle(cash=cash))
    cash_check = next(c for c in checks if c.validation_name == "export_preflight_cash_bridge_identity")
    assert cash_check.status == "pass"
    assert cash_check.expected_value == Decimal("110")
