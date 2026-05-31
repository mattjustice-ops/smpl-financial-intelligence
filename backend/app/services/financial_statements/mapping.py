"""Normalize gl_actuals statement/category labels into canonical buckets."""

from __future__ import annotations

from typing import Optional

# Canonical statement types stored in gl_actuals.statement (flexible input).
INCOME_STATEMENT = "income_statement"
BALANCE_SHEET = "balance_sheet"
CASH_FLOW = "cash_flow"
UNKNOWN = "unknown"

# Income statement roll-up buckets (from category / account_name).
IS_REVENUE = "revenue"
IS_COGS = "cogs"
IS_OPEX = "operating_expense"
IS_OTHER_INCOME = "other_income"
IS_OTHER_EXPENSE = "other_expense"

# Balance sheet buckets.
BS_ASSET = "asset"
BS_LIABILITY = "liability"
BS_EQUITY = "equity"

# Cash flow buckets (when tagged directly in GL).
CF_OPERATING = "operating"
CF_INVESTING = "investing"
CF_FINANCING = "financing"


def normalize_statement(value: Optional[str]) -> str:
    s = (value or "").strip().lower().replace("_", " ").replace("-", " ")
    if not s:
        return UNKNOWN
    if "cash" in s and "flow" in s:
        return CASH_FLOW
    if "balance" in s:
        return BALANCE_SHEET
    if "income" in s or "p&l" in s or "p l" in s or "profit and loss" in s or s == "opex":
        return INCOME_STATEMENT
    if s in {"income", "operating", "opex"}:
        return INCOME_STATEMENT
    return UNKNOWN


def normalize_is_bucket(category: Optional[str], account_name: Optional[str] = None) -> str:
    c = (category or "").strip().lower()
    name = (account_name or "").strip().lower()
    if c in {"revenue", "sales", "income"} or "revenue" in name:
        return IS_REVENUE
    if (
        c in {"cogs", "cost of goods", "cost of sales", "cost of revenue", "cos"}
        or "cogs" in name
        or "cost of revenue" in c
    ):
        return IS_COGS
    if c in {
        "operating expense",
        "opex",
        "operating",
        "sales & marketing",
        "s&m",
        "sm",
        "research & development",
        "r&d",
        "general & administrative",
        "g&a",
    } or any(
        t in c or t in name
        for t in ("operating", "marketing", "research", "administrative", "sales &")
    ):
        return IS_OPEX
    if "other income" in c:
        return IS_OTHER_INCOME
    if "other expense" in c:
        return IS_OTHER_EXPENSE
    # Default signed-amount P&L rows without category → operating
    return IS_OPEX


def normalize_bs_bucket(category: Optional[str], account_name: Optional[str] = None) -> str:
    c = (category or "").strip().lower()
    name = (account_name or "").strip().lower()
    if c in {"asset", "assets"} or "receivable" in name or name == "cash":
        return BS_ASSET
    if c in {"liability", "liabilities"} or "payable" in name or "deferred revenue" in name:
        return BS_LIABILITY
    if c in {"equity", "equities"} or "equity" in name:
        return BS_EQUITY
    return BS_ASSET


def normalize_cf_bucket(category: Optional[str], account_name: Optional[str] = None) -> str:
    c = (category or "").strip().lower()
    name = (account_name or "").strip().lower()
    if "invest" in c or "capex" in c or "invest" in name:
        return CF_INVESTING
    if "financ" in c or "debt" in c or "equity" in c or "dividend" in name:
        return CF_FINANCING
    return CF_OPERATING
