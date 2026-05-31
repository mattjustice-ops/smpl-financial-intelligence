"""Export validation — summary, dimensional, and cross-source checks."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.dashboard.schemas import ExecutiveFlowResponse, WaterfallSummaryRow
from app.services.financial_statements.financial_statement_service import SummaryResponse
from app.services.reporting.export.schemas import ExportValidationSummary, ReportingBundle
from app.services.reporting.period_utils import prior_period, to_period
from app.services.reporting.validation_service import ValidationCheck, compare_values, warning

TOLERANCE = Decimal("1.00")
MARKETING_TABLE_MARKERS = ("marketing_pipeline", "actual_marketing_pipeline", "budget_marketing_pipeline")


def _fs_to_validation_checks(summary: SummaryResponse | None) -> list[ValidationCheck]:
    if summary is None:
        return []
    return [
        ValidationCheck(
            scenario=item.scenario,
            period=str(item.period)[:7] if item.period else "",
            validation_name=item.validation_name,
            status=item.status,
            expected_value=item.expected_value,
            actual_value=item.actual_value,
            variance=item.variance,
            source_tables_used=item.source_tables_used,
        )
        for item in summary.validation
    ]


def _filter_pipeline_checks(checks: list[ValidationCheck]) -> list[ValidationCheck]:
    """Pipeline waterfall must not be validated against marketing_pipeline."""
    filtered: list[ValidationCheck] = []
    for check in checks:
        sources = [s.lower() for s in (check.source_tables_used or [])]
        if check.validation_name.startswith("pipeline") and any(m in " ".join(sources) for m in MARKETING_TABLE_MARKERS):
            continue
        if "marketing_pipeline" in check.validation_name:
            continue
        filtered.append(check)
    return filtered


def _amount_for(
    rows: list[WaterfallSummaryRow],
    period: str,
    scenario: str,
    waterfall_type: str,
) -> Decimal:
    total = Decimal("0")
    for row in rows:
        if row.period == period and row.scenario == scenario and row.waterfall_type == waterfall_type:
            total += row.amount
    return total


def _cross_source_checks(bundle: ReportingBundle) -> list[ValidationCheck]:
    checks: list[ValidationCheck] = []
    as_of = bundle.as_of_period
    arr = bundle.comparison_waterfalls.get("arr", [])
    pipeline = bundle.comparison_waterfalls.get("pipeline", [])
    cash = bundle.comparison_waterfalls.get("cash_flow", [])
    deferred = bundle.comparison_waterfalls.get("deferred_revenue", [])

    if arr and pipeline:
        new_arr = _amount_for(arr, as_of, "Actual", "new_arr") or _amount_for(arr, as_of, "Actual", "new_business")
        closed_won = _amount_for(pipeline, as_of, "Actual", "closed_won")
        if new_arr or closed_won:
            checks.append(
                compare_values(
                    scenario="Actual",
                    period=as_of,
                    validation_name="closed_won_arr_ties_mrr_new_business_arr",
                    expected_value=new_arr,
                    actual_value=closed_won,
                    source_tables_used=["arr_waterfall", "pipeline_waterfall"],
                    tolerance=TOLERANCE,
                )
            )

    fs = bundle.comparison_financial_statements
    if cash and fs and fs.balance_sheet.rows:
        ending_cash = _amount_for(cash, as_of, "Actual", "ending_cash")
        bs_cash = Decimal("0")
        for row in fs.balance_sheet.rows:
            if to_period(str(row.period)) == as_of and row.scenario == "Actual" and row.line_item.lower() == "cash":
                bs_cash = row.amount
        if ending_cash or bs_cash:
            checks.append(
                compare_values(
                    scenario="Actual",
                    period=as_of,
                    validation_name="cash_bridge_ending_cash_ties_balance_sheet_cash",
                    expected_value=bs_cash,
                    actual_value=ending_cash,
                    source_tables_used=["cash_flow_bridge", "balance_sheet"],
                    tolerance=TOLERANCE,
                )
            )

    if arr and len(arr) > 0:
        prior = prior_period(as_of)
        for scenario in ("Actual", "Forecast"):
            ending_prior = _amount_for(arr, prior, scenario, "ending_arr") or _amount_for(arr, prior, scenario, "ending")
            beginning = _amount_for(arr, as_of, scenario, "beginning_arr") or _amount_for(arr, as_of, scenario, "beginning")
            if ending_prior or beginning:
                checks.append(
                    compare_values(
                        scenario=scenario,
                        period=as_of,
                        validation_name="actual_ending_balance_rolls_to_forecast_beginning",
                        expected_value=ending_prior,
                        actual_value=beginning,
                        source_tables_used=["mrr_waterfall"],
                        tolerance=TOLERANCE,
                    )
                )

    if deferred:
        for period in {row.period for row in deferred}:
            beginning = _amount_for(deferred, period, "Actual", "beginning_deferred_revenue")
            billings = _amount_for(deferred, period, "Actual", "new_billings")
            recognized = _amount_for(deferred, period, "Actual", "revenue_recognized")
            ending = _amount_for(deferred, period, "Actual", "ending_deferred_revenue")
            if beginning or billings or recognized or ending:
                expected = beginning + billings + recognized
                checks.append(
                    compare_values(
                        scenario="Actual",
                        period=period,
                        validation_name="deferred_revenue_waterfall_ties",
                        expected_value=expected,
                        actual_value=ending,
                        source_tables_used=["deferred_revenue_waterfall"],
                        tolerance=TOLERANCE,
                    )
                )

    return checks


def run_export_validation_bundle(bundle: ReportingBundle) -> ExportValidationSummary:
    executive = bundle.executive_flow
    checks: list[ValidationCheck] = _filter_pipeline_checks(list(executive.validation))
    checks.extend(_filter_pipeline_checks(_fs_to_validation_checks(bundle.comparison_financial_statements)))
    checks.extend(_cross_source_checks(bundle))

    if not checks:
        checks.append(
            warning(
                scenario=executive.scenario,
                period=executive.end_period,
                validation_name="export_validation_no_checks",
                source_tables_used=["export"],
            )
        )

    failed = sum(1 for c in checks if c.status == "fail")
    warns = sum(1 for c in checks if c.status == "warning")
    passed = sum(1 for c in checks if c.status == "pass")
    status = "fail" if failed else ("warning" if warns else "pass")

    return ExportValidationSummary(
        status=status,
        failed_count=failed,
        warning_count=warns,
        passed_count=passed,
        checks=checks,
    )


def run_export_validation(
    executive: ExecutiveFlowResponse,
    financial_statements: SummaryResponse | None,
    bundle: ReportingBundle | None = None,
) -> ExportValidationSummary:
    if bundle is not None:
        return run_export_validation_bundle(bundle)
    checks = _filter_pipeline_checks(list(executive.validation))
    checks.extend(_fs_to_validation_checks(financial_statements))
    failed = sum(1 for c in checks if c.status == "fail")
    warns = sum(1 for c in checks if c.status == "warning")
    passed = sum(1 for c in checks if c.status == "pass")
    return ExportValidationSummary(
        status="fail" if failed else ("warning" if warns else "pass"),
        failed_count=failed,
        warning_count=warns,
        passed_count=passed,
        checks=checks,
    )
