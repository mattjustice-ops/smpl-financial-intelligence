"""Canonical period handling for reporting modules."""

from __future__ import annotations

from datetime import date
from typing import Iterable


def to_period(value: date | str) -> str:
    if isinstance(value, date):
        return f"{value.year:04d}-{value.month:02d}"
    s = str(value).strip()
    if len(s) >= 7 and s[4] == "-":
        return s[:7]
    if len(s) == 6 and s.isdigit():
        return f"{s[:4]}-{s[4:]}"
    parsed = date.fromisoformat(s[:10])
    return f"{parsed.year:04d}-{parsed.month:02d}"


def period_to_date(period: str) -> date:
    p = to_period(period)
    return date(int(p[:4]), int(p[5:7]), 1)


def sort_periods(periods: Iterable[str]) -> list[str]:
    return sorted({to_period(p) for p in periods})


def period_range(start_period: str | date, end_period: str | date) -> list[str]:
    current = period_to_date(to_period(start_period))
    end = period_to_date(to_period(end_period))
    out: list[str] = []
    while current <= end:
        out.append(to_period(current))
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return out


def prior_period(period: str) -> str:
    current = period_to_date(period)
    if current.month == 1:
        return f"{current.year - 1:04d}-12"
    return f"{current.year:04d}-{current.month - 1:02d}"


def combined_scenario_for_period(period: str) -> str:
    return "Actual" if to_period(period) <= "2026-05" else "Forecast"


def scenario_periods(scenario: str, start_period: str | date, end_period: str | date) -> list[tuple[str, str]]:
    periods = period_range(start_period, end_period)
    if scenario.lower() == "combined":
        return [(combined_scenario_for_period(period), period) for period in periods]
    normalized = "Actual" if scenario.lower() == "actual" else "Budget" if scenario.lower() == "budget" else "Forecast"
    return [(normalized, period) for period in periods]
