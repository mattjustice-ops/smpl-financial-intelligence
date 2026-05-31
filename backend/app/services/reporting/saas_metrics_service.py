"""Shared SaaS metric formulas."""

from __future__ import annotations

from decimal import Decimal


def calculate_arr(mrr: Decimal) -> Decimal:
    return mrr * Decimal("12")


def calculate_mrr(arr: Decimal) -> Decimal:
    return arr / Decimal("12") if arr else Decimal("0")
