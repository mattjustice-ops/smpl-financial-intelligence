"""Fiscal year period helpers for board + forecast horizons."""

from __future__ import annotations

from app.services.reporting.period_utils import next_period, period_range, to_period


def fiscal_year_end_period(as_of_period: str, *, fiscal_year_end_month: int = 12) -> str:
    """Last period (YYYY-MM) of the fiscal year containing as_of_period."""
    as_of = to_period(as_of_period)
    year = int(as_of[:4])
    month = int(as_of[5:7])
    fy_end = max(1, min(12, fiscal_year_end_month))
    if fy_end == 12:
        return f"{year:04d}-12"
    if month > fy_end:
        return f"{year + 1:04d}-{fy_end:02d}"
    return f"{year:04d}-{fy_end:02d}"


def fiscal_year_start_period(as_of_period: str, *, fiscal_year_end_month: int = 12) -> str:
    """First period (YYYY-MM) of the fiscal year containing as_of_period."""
    end = fiscal_year_end_period(as_of_period, fiscal_year_end_month=fiscal_year_end_month)
    end_year = int(end[:4])
    fy_end = max(1, min(12, fiscal_year_end_month))
    if fy_end == 12:
        return f"{end_year:04d}-01"
    start_month = fy_end + 1
    if start_month > 12:
        start_month = 1
    return f"{end_year - 1:04d}-{start_month:02d}"


def forecast_open_periods(close_period: str, *, fiscal_year_end_month: int = 12) -> list[str]:
    """Every forecast month after a close.

    Open months run from the month after the close through the end of that fiscal
    year. When the close is the fiscal year end, the forecast is the following
    fiscal year, every month of it.
    """
    close = to_period(close_period)
    fy_end = fiscal_year_end_period(close, fiscal_year_end_month=fiscal_year_end_month)
    if close < fy_end:
        return period_range(next_period(close), fy_end)
    start = next_period(fy_end)
    return period_range(start, fiscal_year_end_period(start, fiscal_year_end_month=fiscal_year_end_month))


def forecast_periods_after_close(close_period: str, window_end: str) -> list[str]:
    """Open forecast months for a reporting window that ends on the fiscal year end.

    A window that still has months after the close keeps those months. A close on
    the window end opens the next fiscal year, using the window end's month as the
    fiscal year end.
    """
    close = to_period(close_period)
    end = to_period(window_end)
    if close < end:
        return period_range(next_period(close), end)
    return forecast_open_periods(close, fiscal_year_end_month=int(end[5:7]))
