"""Hard arithmetic / completeness gates for customer PPTX + MDA exports.

These checks extend ``run_export_validation_bundle`` so existing
``block_on_failure=True`` customer packs 409 before shipping a deck whose
numbers cannot tie to the board SoT.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.services.reporting.export.metric_registry import (
    arr_bridge_identity_expected,
    compute_ending_arr,
)
from app.services.reporting.export.schemas import ReportingBundle
from app.services.reporting.export.validation_precheck import TOLERANCE
from app.services.reporting.period_utils import to_period
from app.services.reporting.validation_service import ValidationCheck, compare_values

ZERO = Decimal("0")


def _mql_sum_marketing_comparison(bundle: ReportingBundle, period: str) -> Decimal:
    total = ZERO
    if not bundle.marketing_comparison:
        return total
    for row in bundle.marketing_comparison.actual:
        if row.period == period:
            total += Decimal(str(row.mqls or 0))
    return total


def _mql_sum_channel_comparison(bundle: ReportingBundle, period: str) -> Decimal:
    total = ZERO
    mkt = bundle.marketing_channel_comparison
    if not mkt:
        return total
    for row in mkt.actual:
        if row.period == period:
            total += Decimal(str(row.mqls or 0))
    return total


def _cash_bridge_identity(
    bundle: ReportingBundle,
    cash_bridge_data: dict[str, Any] | None,
) -> ValidationCheck | None:
    """Beginning + inflows − outflows ≈ ending cash (Actual close month)."""
    from app.services.reporting.export.board_platform_metrics import (
        _cash_bridge_table_amount,
        _cash_wf_amount,
    )
    from app.services.reporting.export.is_line_resolver import ending_cash_at
    from app.services.reporting.period_utils import prior_period

    as_of = bundle.as_of_period
    prior = prior_period(as_of)
    beginning = ending_cash_at(bundle, prior, "Actual")
    ending = ending_cash_at(bundle, as_of, "Actual")
    if not beginning and not ending:
        return None

    def _line(bridge_field: str | None, *wf_types: str, abs_out: bool = False) -> Decimal:
        if bridge_field:
            table_val = _cash_bridge_table_amount(
                cash_bridge_data, "Actual", as_of, bridge_field, abs_out=abs_out
            )
            if table_val is not None and table_val != ZERO:
                return table_val
        return _cash_wf_amount(bundle, as_of, "Actual", *wf_types, abs_out=abs_out)

    collections = _line(None, "cash_collections", "collections")
    payroll = _line("payroll", "payroll_cash_out", "payroll", abs_out=True)
    vendor = _line(
        "vendor",
        "vendor_cash_out",
        "vendor_cash_out_n30",
        "vendor_payments",
        "vendor",
        abs_out=True,
    )
    commissions = _line(
        "commission", "commission_cash_out", "commissions", "commission", abs_out=True
    )
    capex = _line("capex", "capex", abs_out=True)

    # Skip when middle lines are empty — no bridge to reconcile yet.
    if not (collections or payroll or vendor or commissions or capex):
        return None

    expected = beginning + collections - payroll - vendor - commissions - capex
    return compare_values(
        scenario="Actual",
        period=as_of,
        validation_name="export_preflight_cash_bridge_identity",
        expected_value=expected,
        actual_value=ending,
        source_tables_used=["cash_flow_bridge", "balance_sheet", "export_preflight"],
        tolerance=TOLERANCE,
    )


def _arr_bridge_identity(bundle: ReportingBundle) -> ValidationCheck | None:
    as_of = bundle.as_of_period
    if not bundle.comparison_waterfalls.get("arr"):
        return None
    ending = compute_ending_arr(bundle, as_of, "Actual")
    if not ending:
        return None
    expected, actual = arr_bridge_identity_expected(bundle, as_of, "Actual")
    if expected == ZERO and actual == ZERO:
        return None
    return compare_values(
        scenario="Actual",
        period=as_of,
        validation_name="export_preflight_arr_bridge_identity",
        expected_value=expected,
        actual_value=actual,
        source_tables_used=["arr_waterfall", "export_preflight"],
        tolerance=TOLERANCE,
    )


def _dual_mql_sot(bundle: ReportingBundle) -> ValidationCheck | None:
    """Fail when marketing_comparison MQL total ≠ marketing_channel_comparison total."""
    as_of = bundle.as_of_period
    header = _mql_sum_marketing_comparison(bundle, as_of)
    channels = _mql_sum_channel_comparison(bundle, as_of)
    if header == ZERO or channels == ZERO:
        return None
    return compare_values(
        scenario="Actual",
        period=as_of,
        validation_name="export_preflight_dual_mql_sot",
        expected_value=header,
        actual_value=channels,
        source_tables_used=[
            "marketing_comparison",
            "marketing_channel_comparison",
            "export_preflight",
        ],
        tolerance=TOLERANCE,
    )


def _headcount_missing(bundle: ReportingBundle) -> ValidationCheck | None:
    """Fail when ARR is present but Actual headcount for close month is zero."""
    as_of = bundle.as_of_period
    ending = compute_ending_arr(bundle, as_of, "Actual")
    if not ending:
        return None
    hc = sum(
        int(Decimal(str(r.headcount or 0)))
        for r in bundle.headcount
        if to_period(str(r.period)) == to_period(as_of) and r.scenario == "Actual"
    )
    if hc > 0:
        return ValidationCheck(
            scenario="Actual",
            period=as_of,
            validation_name="export_preflight_headcount_present",
            status="pass",
            actual_value=Decimal(hc),
            source_tables_used=["workforce_period_summary", "export_preflight"],
        )
    return ValidationCheck(
        scenario="Actual",
        period=as_of,
        validation_name="export_preflight_headcount_missing",
        status="fail",
        expected_value=Decimal("1"),
        actual_value=Decimal(hc),
        variance=Decimal(hc) - Decimal("1"),
        source_tables_used=["workforce_period_summary", "export_preflight"],
    )


def run_export_preflight_checks(
    bundle: ReportingBundle,
    *,
    cash_bridge_data: dict[str, Any] | None = None,
) -> list[ValidationCheck]:
    """Return arithmetic / completeness checks to merge into export validation."""
    checks: list[ValidationCheck] = []
    arr = _arr_bridge_identity(bundle)
    if arr is not None:
        checks.append(arr)
    cash = _cash_bridge_identity(bundle, cash_bridge_data)
    if cash is not None:
        checks.append(cash)
    mql = _dual_mql_sot(bundle)
    if mql is not None:
        checks.append(mql)
    hc = _headcount_missing(bundle)
    if hc is not None:
        checks.append(hc)
    return checks
