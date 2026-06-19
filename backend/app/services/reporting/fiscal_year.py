"""Fiscal year period helpers for board + forecast horizons."""

from __future__ import annotations

from app.services.reporting.period_utils import to_period


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
