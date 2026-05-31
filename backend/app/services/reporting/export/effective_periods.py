"""Actual + Forecast period logic: closed months use Actual; open months use Forecast outlook."""

from __future__ import annotations

from decimal import Decimal

from app.services.reporting.period_utils import period_range, prior_period, to_period

ZERO = Decimal("0")
BLANK = None  # write empty cell, not zero


def is_closed_period(period: str, as_of_period: str, *, has_actual_rows: bool) -> bool:
    """Month is closed when period <= as-of and Actual data exists in warehouse."""
    return has_actual_rows and to_period(period) <= to_period(as_of_period)


def export_fiscal_periods(start_period: str, end_period: str) -> list[str]:
    """Full reporting window (e.g. Jan–Dec), not capped at as-of."""
    return period_range(start_period, end_period)


def outlook_amount(actual: Decimal, budget: Decimal, forecast: Decimal, *, closed: bool) -> Decimal | None:
    """Combined / full-year outlook: Actual when closed, Forecast when open — never $0 placeholder."""
    if closed:
        return actual if actual != ZERO else BLANK
    if forecast != ZERO:
        return forecast
    return BLANK


def period_display_values(
    actual: Decimal,
    budget: Decimal,
    forecast: Decimal,
    *,
    period: str,
    as_of_period: str,
    has_actual_rows: bool,
    has_budget_rows: bool,
    has_forecast_rows: bool,
) -> dict[str, Decimal | None]:
    """Values to render in Excel; omit misleading zero forecast on closed months."""
    closed = is_closed_period(period, as_of_period, has_actual_rows=has_actual_rows)
    as_of = to_period(as_of_period)
    p = to_period(period)

    out: dict[str, Decimal | None] = {
        "actual": BLANK,
        "budget": BLANK,
        "forecast": BLANK,
        "outlook": BLANK,
    }

    if closed:
        out["actual"] = actual if has_actual_rows else BLANK
        out["budget"] = budget if has_budget_rows else BLANK
        out["outlook"] = outlook_amount(actual, budget, forecast, closed=True)
        if has_forecast_rows and p == as_of:
            out["forecast"] = forecast
    else:
        out["budget"] = budget if has_budget_rows else BLANK
        out["forecast"] = forecast if has_forecast_rows else BLANK
        out["outlook"] = outlook_amount(actual, budget, forecast, closed=False)

    return out


def include_forecast_column(period: str, as_of_period: str, *, has_actual_rows: bool, has_forecast_rows: bool) -> bool:
    if not has_forecast_rows:
        return False
    closed = is_closed_period(period, as_of_period, has_actual_rows=has_actual_rows)
    if not closed:
        return True
    return to_period(period) == to_period(as_of_period)
