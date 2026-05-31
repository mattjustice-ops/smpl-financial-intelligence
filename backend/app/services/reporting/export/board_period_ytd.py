"""CM / QTD / YTD / FY outlook rollups for board visuals (Actual + Forecast logic)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.services.reporting.export.effective_periods import export_fiscal_periods, is_closed_period
from app.services.reporting.export.period_views import qtd_periods, ytd_periods
from app.services.reporting.export.schemas import ReportingBundle
from app.services.reporting.period_utils import to_period

ZERO = Decimal("0")


@dataclass
class PeriodRollup:
    current_month: Decimal
    qtd: Decimal
    ytd: Decimal
    fy_outlook: Decimal
    budget_cm: Decimal
    budget_ytd: Decimal
    budget_fy: Decimal


def _wf_by_period(
    bundle: ReportingBundle,
    key: str,
    wtype: str,
    scenario: str,
) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for row in bundle.comparison_waterfalls.get(key) or []:
        if row.waterfall_type == wtype and row.scenario == scenario:
            out[to_period(row.period)] = row.amount
    return out


def _fs_by_period(
    bundle: ReportingBundle,
    line_match: str,
    scenario: str,
) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if not fs:
        return out
    needle = line_match.lower()
    for row in fs.income_statement.rows:
        if row.scenario != scenario:
            continue
        if needle in row.line_item.lower() and "deferred" not in row.line_item.lower():
            out[to_period(str(row.period)[:7])] = row.amount
    return out


def _sum_periods(values: dict[str, Decimal], periods: list[str]) -> Decimal:
    return sum(values.get(p, ZERO) for p in periods)


def _outlook_series(
    bundle: ReportingBundle,
    actual: dict[str, Decimal],
    forecast: dict[str, Decimal],
) -> dict[str, Decimal]:
    """Actual for closed months; Forecast for open months in fiscal window."""
    as_of = bundle.as_of_period
    outlook: dict[str, Decimal] = {}
    for period in export_fiscal_periods(bundle.start_period, bundle.end_period):
        p = to_period(period)
        has_a = p in actual and actual[p] != ZERO
        closed = is_closed_period(p, as_of, has_actual_rows=has_a)
        if closed:
            outlook[p] = actual.get(p, ZERO)
        else:
            outlook[p] = forecast.get(p, ZERO) if forecast.get(p, ZERO) != ZERO else ZERO
    return outlook


def rollup_waterfall_metric(
    bundle: ReportingBundle,
    key: str,
    wtype: str,
    *,
    flow: bool = False,
) -> PeriodRollup:
    """Sum or point-in-time rollup for a waterfall type across periods."""
    as_of = to_period(bundle.as_of_period)
    actual = _wf_by_period(bundle, key, wtype, "Actual")
    forecast = _wf_by_period(bundle, key, wtype, "Forecast")
    budget = _wf_by_period(bundle, key, wtype, "Budget")
    outlook = _outlook_series(bundle, actual, forecast)

    if flow:
        cm = actual.get(as_of, ZERO)
        qtd = _sum_periods(actual, qtd_periods(as_of))
        ytd = _sum_periods(actual, ytd_periods(as_of))
        fy = _sum_periods(outlook, export_fiscal_periods(bundle.start_period, bundle.end_period))
    else:
        cm = actual.get(as_of, ZERO) or outlook.get(as_of, ZERO)
        qtd = _sum_periods(outlook, qtd_periods(as_of))
        ytd = _sum_periods(outlook, ytd_periods(as_of))
        fy = outlook.get(as_of, ZERO) or _sum_periods(outlook, export_fiscal_periods(bundle.start_period, bundle.end_period))

    return PeriodRollup(
        current_month=cm,
        qtd=qtd,
        ytd=ytd,
        fy_outlook=fy,
        budget_cm=budget.get(as_of, ZERO),
        budget_ytd=_sum_periods(budget, ytd_periods(as_of)),
        budget_fy=_sum_periods(budget, export_fiscal_periods(bundle.start_period, bundle.end_period)),
    )


def rollup_ending_arr(bundle: ReportingBundle) -> PeriodRollup:
    for wtype in ("ending_arr", "ending"):
        if _wf_by_period(bundle, "arr", wtype, "Actual"):
            return rollup_waterfall_metric(bundle, "arr", wtype, flow=False)
    return PeriodRollup(ZERO, ZERO, ZERO, ZERO, ZERO, ZERO, ZERO)


def rollup_revenue(bundle: ReportingBundle) -> PeriodRollup:
    as_of = to_period(bundle.as_of_period)
    actual = _fs_by_period(bundle, "revenue", "Actual")
    forecast = _fs_by_period(bundle, "revenue", "Forecast")
    budget = _fs_by_period(bundle, "revenue", "Budget")
    outlook = _outlook_series(bundle, actual, forecast)
    return PeriodRollup(
        current_month=actual.get(as_of, ZERO),
        qtd=_sum_periods(outlook, qtd_periods(as_of)),
        ytd=_sum_periods(outlook, ytd_periods(as_of)),
        fy_outlook=_sum_periods(outlook, export_fiscal_periods(bundle.start_period, bundle.end_period)),
        budget_cm=budget.get(as_of, ZERO),
        budget_ytd=_sum_periods(budget, ytd_periods(as_of)),
        budget_fy=_sum_periods(budget, export_fiscal_periods(bundle.start_period, bundle.end_period)),
    )


def rollup_ebitda(bundle: ReportingBundle) -> PeriodRollup:
    as_of = to_period(bundle.as_of_period)
    actual = _fs_by_period(bundle, "ebitda", "Actual")
    forecast = _fs_by_period(bundle, "ebitda", "Forecast")
    budget = _fs_by_period(bundle, "ebitda", "Budget")
    outlook = _outlook_series(bundle, actual, forecast)
    return PeriodRollup(
        current_month=actual.get(as_of, ZERO),
        qtd=_sum_periods(outlook, qtd_periods(as_of)),
        ytd=_sum_periods(outlook, ytd_periods(as_of)),
        fy_outlook=_sum_periods(outlook, export_fiscal_periods(bundle.start_period, bundle.end_period)),
        budget_cm=budget.get(as_of, ZERO),
        budget_ytd=_sum_periods(budget, ytd_periods(as_of)),
        budget_fy=_sum_periods(budget, export_fiscal_periods(bundle.start_period, bundle.end_period)),
    )


def rollup_cash(bundle: ReportingBundle) -> PeriodRollup:
    return rollup_waterfall_metric(bundle, "cash_flow", "ending_cash", flow=False)


def rollup_pipeline_created(bundle: ReportingBundle) -> PeriodRollup:
    return rollup_waterfall_metric(bundle, "pipeline", "pipeline_created", flow=True)


def monthly_ending_arr_series(bundle: ReportingBundle) -> tuple[list[str], list[float], list[float], list[float]]:
    """Month labels + Actual path + Outlook path + Budget for trend chart."""
    as_of = to_period(bundle.as_of_period)
    actual = _wf_by_period(bundle, "arr", "ending_arr", "Actual") or _wf_by_period(bundle, "arr", "ending", "Actual")
    forecast = _wf_by_period(bundle, "arr", "ending_arr", "Forecast") or _wf_by_period(bundle, "arr", "ending", "Forecast")
    budget = _wf_by_period(bundle, "arr", "ending_arr", "Budget") or _wf_by_period(bundle, "arr", "ending", "Budget")
    outlook = _outlook_series(bundle, actual, forecast)

    periods = export_fiscal_periods(bundle.start_period, bundle.end_period)
    labels: list[str] = []
    act_line: list[float] = []
    out_line: list[float] = []
    bud_line: list[float] = []

    last_a = 0.0
    for period in periods:
        p = to_period(period)
        labels.append(p[5:7])
        a = float(actual.get(p, ZERO))
        o = float(outlook.get(p, ZERO))
        b = float(budget.get(p, ZERO))
        if is_closed_period(p, as_of, has_actual_rows=a != 0):
            last_a = a if a else last_a
            act_line.append(a if a else last_a)
            out_line.append(a if a else last_a)
        else:
            act_line.append(last_a)
            out_line.append(o if o else last_a)
        bud_line.append(b)
    return labels, act_line, out_line, bud_line


def monthly_flow_series(
    bundle: ReportingBundle,
    key: str,
    wtype: str,
) -> tuple[list[str], list[float], list[float]]:
    """Monthly flow metric (pipeline created, etc.) — Actual months + Outlook for open."""
    as_of = to_period(bundle.as_of_period)
    actual = _wf_by_period(bundle, key, wtype, "Actual")
    forecast = _wf_by_period(bundle, key, wtype, "Forecast")
    outlook = _outlook_series(bundle, actual, forecast)
    periods = export_fiscal_periods(bundle.start_period, bundle.end_period)
    labels: list[str] = []
    act_vals: list[float] = []
    out_vals: list[float] = []
    for period in periods:
        p = to_period(period)
        labels.append(p[5:7])
        a = float(actual.get(p, ZERO))
        o = float(outlook.get(p, ZERO))
        if is_closed_period(p, as_of, has_actual_rows=a != 0):
            act_vals.append(a)
            out_vals.append(a)
        else:
            act_vals.append(0.0)
            out_vals.append(o)
    return labels, act_vals, out_vals
