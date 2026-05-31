"""Shared financial metric formulas."""

from __future__ import annotations

from decimal import Decimal


def calculate_gross_profit(revenue: Decimal, cost_of_revenue: Decimal) -> Decimal:
    return revenue - cost_of_revenue


def calculate_ebitda(gross_profit: Decimal, operating_expenses: Decimal) -> Decimal:
    return gross_profit - operating_expenses


def calculate_deferred_revenue_rollforward(beginning_deferred_revenue: Decimal, billings: Decimal, revenue_recognized: Decimal) -> Decimal:
    return beginning_deferred_revenue + billings - revenue_recognized


def calculate_cash_collections(beginning_accounts_receivable: Decimal, billings: Decimal, ending_accounts_receivable: Decimal) -> Decimal:
    return beginning_accounts_receivable + billings - ending_accounts_receivable
