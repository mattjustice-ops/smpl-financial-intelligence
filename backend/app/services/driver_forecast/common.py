"""Shared primitives for driver-based SaaS forecasting."""

from __future__ import annotations

import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable

MONEY = Decimal("0.01")
ZERO = Decimal("0")


def q_money(value: Decimal | int | str | None) -> Decimal:
    if value is None:
        value = ZERO
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def month_start(value: date) -> date:
    return value.replace(day=1)


def month_end(value: date) -> date:
    last = calendar.monthrange(value.year, value.month)[1]
    return value.replace(day=last)


def add_months(value: date, months: int) -> date:
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    return date(year, month, 1)


def month_range(start_period: date, end_period: date) -> list[date]:
    current = month_start(start_period)
    end = month_start(end_period)
    out: list[date] = []
    while current <= end:
        out.append(current)
        current = add_months(current, 1)
    return out


def period_type(period: date, actual_cutoff: date = date(2026, 5, 1)) -> str:
    return "actual" if month_start(period) <= actual_cutoff else "forecast"


def sum_decimal(values: Iterable[Decimal | None]) -> Decimal:
    return q_money(sum((v or ZERO for v in values), ZERO))
