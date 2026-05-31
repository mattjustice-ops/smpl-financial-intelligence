"""Centralized reporting-period semantics: CM, QTD, YTD, FY outlook, Actual+Forecast."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from app.services.reporting.export.effective_periods import export_fiscal_periods, is_closed_period
from app.services.reporting.export.period_views import qtd_periods, ytd_periods
from app.services.reporting.export.schemas import ReportingBundle
from app.services.reporting.period_utils import prior_period, to_period

ZERO = Decimal("0")


class PeriodMode(str, Enum):
    CURRENT_MONTH = "current_month"
    PRIOR_MONTH = "prior_month"
    QTD = "qtd"
    PRIOR_QUARTER = "prior_quarter"
    YTD = "ytd"
    PRIOR_YTD = "prior_ytd"
    FY_OUTLOOK = "fy_outlook"
    FULL_YEAR = "full_year"


class ScenarioMode(str, Enum):
    ACTUAL = "Actual"
    BUDGET = "Budget"
    FORECAST = "Forecast"
    OUTLOOK = "outlook"  # Actual closed + Forecast open


@dataclass(frozen=True)
class ReportingPeriodContext:
    as_of: str
    prior_month: str
    fiscal_start: str
    fiscal_end: str
    ytd_periods: tuple[str, ...]
    qtd_periods: tuple[str, ...]
    fiscal_periods: tuple[str, ...]
    closed_periods: tuple[str, ...]
    open_periods: tuple[str, ...]


def _actual_presence_by_period(bundle: ReportingBundle, fiscal: list[str]) -> dict[str, bool]:
    """Periods that have at least one Actual row in waterfalls or income statement."""
    wanted = set(fiscal)
    presence = {p: False for p in fiscal}
    for rows in bundle.comparison_waterfalls.values():
        for row in rows or []:
            if str(getattr(row, "scenario", "")).strip() == "Actual":
                p = to_period(str(row.period))
                if p in wanted:
                    presence[p] = True
    for wf in bundle.executive_flow.waterfalls.values():
        for row in wf.rows:
            if str(getattr(row, "scenario", "")).strip() == "Actual":
                p = to_period(str(row.period))
                if p in wanted:
                    presence[p] = True
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if fs:
        for row in fs.income_statement.rows:
            if row.scenario == "Actual":
                p = to_period(str(row.period)[:7])
                if p in wanted:
                    presence[p] = True
    return presence


def build_period_context(bundle: ReportingBundle) -> ReportingPeriodContext:
    as_of = to_period(bundle.as_of_period)
    fiscal = list(export_fiscal_periods(bundle.start_period, bundle.end_period))
    presence = _actual_presence_by_period(bundle, fiscal)
    closed: list[str] = []
    open_: list[str] = []
    for p in fiscal:
        if is_closed_period(p, as_of, has_actual_rows=presence.get(p, False)):
            closed.append(p)
        else:
            open_.append(p)
    fiscal_t = tuple(fiscal)
    return ReportingPeriodContext(
        as_of=as_of,
        prior_month=prior_period(as_of),
        fiscal_start=fiscal[0] if fiscal else as_of,
        fiscal_end=fiscal[-1] if fiscal else as_of,
        ytd_periods=tuple(ytd_periods(as_of)),
        qtd_periods=tuple(qtd_periods(as_of)),
        fiscal_periods=fiscal_t,
        closed_periods=tuple(closed),
        open_periods=tuple(open_),
    )


def periods_for_mode(ctx: ReportingPeriodContext, mode: PeriodMode) -> list[str]:
    if mode == PeriodMode.CURRENT_MONTH:
        return [ctx.as_of]
    if mode == PeriodMode.PRIOR_MONTH:
        return [ctx.prior_month]
    if mode == PeriodMode.QTD:
        return list(ctx.qtd_periods)
    if mode == PeriodMode.YTD:
        return list(ctx.ytd_periods)
    if mode == PeriodMode.FY_OUTLOOK or mode == PeriodMode.FULL_YEAR:
        return list(ctx.fiscal_periods)
    if mode == PeriodMode.PRIOR_QUARTER:
        # prior quarter ending at start of current Q
        if not ctx.qtd_periods:
            return []
        q0 = ctx.qtd_periods[0]
        pm = prior_period(q0)
        return qtd_periods(pm)
    if mode == PeriodMode.PRIOR_YTD:
        py = str(int(ctx.as_of[:4]) - 1)
        return [f"{py}-{p[5:7]}" for p in ctx.ytd_periods]
    return [ctx.as_of]


def outlook_value(
    period: str,
    actual: dict[str, Decimal],
    forecast: dict[str, Decimal],
    ctx: ReportingPeriodContext,
) -> Decimal:
    """Actual for closed months; forecast for open months in fiscal window."""
    p = to_period(period)
    a = actual.get(p, ZERO)
    if p in ctx.closed_periods and a != ZERO:
        return a
    if p in ctx.closed_periods:
        return a
    f = forecast.get(p, ZERO)
    return f if f != ZERO else ZERO


def sum_for_mode(
    actual: dict[str, Decimal],
    forecast: dict[str, Decimal],
    ctx: ReportingPeriodContext,
    mode: PeriodMode,
    *,
    scenario: ScenarioMode = ScenarioMode.OUTLOOK,
    point_in_time: bool = False,
) -> Decimal:
    periods = periods_for_mode(ctx, mode)
    if not periods:
        return ZERO
    if point_in_time:
        p = periods[-1]
        if scenario == ScenarioMode.ACTUAL:
            return actual.get(p, ZERO)
        if scenario == ScenarioMode.FORECAST:
            return forecast.get(p, ZERO)
        return outlook_value(p, actual, forecast, ctx)
    total = ZERO
    for p in periods:
        if scenario == ScenarioMode.ACTUAL:
            total += actual.get(p, ZERO)
        elif scenario == ScenarioMode.FORECAST:
            total += forecast.get(p, ZERO)
        elif scenario == ScenarioMode.BUDGET:
            total += actual.get(p, ZERO)  # caller passes budget dict as actual slot
        else:
            total += outlook_value(p, actual, forecast, ctx)
    return total


def trend_axis_labels(periods: list[str], *, max_points: int = 8) -> list[str]:
    """Readable x-axis: quarterly when crowded, else month abbreviations."""
    if len(periods) <= max_points:
        return [_short_period(p) for p in periods]
    # aggregate to quarters
    buckets: dict[str, list[str]] = {}
    for p in periods:
        month = int(p[5:7])
        q = (month - 1) // 3 + 1
        key = f"Q{q}'{p[2:4]}"
        buckets.setdefault(key, []).append(p)
    return list(buckets.keys())[:max_points]


def _short_period(period: str) -> str:
    p = to_period(period)
    return p[5:7]  # MM
