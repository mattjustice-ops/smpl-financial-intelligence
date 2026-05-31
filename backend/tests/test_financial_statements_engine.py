"""Unit tests for financial statements engine (no database)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from app.services.financial_statements.engine import build_financial_statements
from app.services.financial_statements.repository import GlRow


ORG = uuid.UUID("8571e520-0687-4516-bdee-379f37c58c1f")
JAN = date(2026, 1, 1)
FEB = date(2026, 2, 1)
MAR = date(2026, 3, 1)


def _row(
    period: date,
    account_number: str,
    account_name: str,
    statement: str,
    category: str,
    amount: str,
) -> GlRow:
    return GlRow(
        period=period,
        account_number=account_number,
        account_name=account_name,
        statement=statement,
        category=category,
        amount=Decimal(amount),
        currency="USD",
        subsidiary="US Parent",
    )


def _sample_gl_rows() -> list[GlRow]:
    """Minimal GL set mirroring the user's chart of accounts."""
    is_stmt = "Income Statement"
    bs_stmt = "Balance Sheet"
    rows: list[GlRow] = []
    for period, rev, cash in [
        (JAN, "310000", "2500000"),
        (FEB, "350000", "2415000"),
        (MAR, "370000", "2330000"),
    ]:
        rows.extend(
            [
                _row(period, "4000", "Subscription Revenue", is_stmt, "Revenue", rev),
                _row(period, "4010", "Professional Services Revenue", is_stmt, "Revenue", "20000"),
                _row(period, "5000", "Cloud Hosting COGS", is_stmt, "COGS", "-43400"),
                _row(period, "6000", "Sales & Marketing", is_stmt, "Operating Expense", "-145000"),
                _row(period, "6100", "Research & Development", is_stmt, "Operating Expense", "-180000"),
                _row(period, "6200", "General & Administrative", is_stmt, "Operating Expense", "-95000"),
                _row(period, "1000", "Cash", bs_stmt, "Asset", cash),
                _row(period, "1100", "Accounts Receivable", bs_stmt, "Asset", "210000"),
                _row(period, "2000", "Accounts Payable", bs_stmt, "Liability", "-175000"),
                _row(period, "2100", "Deferred Revenue", bs_stmt, "Liability", "-900000"),
                _row(period, "3000", "Equity", bs_stmt, "Equity", "-1600000"),
            ]
        )
    return rows


def test_income_statement_q1_totals() -> None:
    pkg = build_financial_statements(
        _sample_gl_rows(),
        organization_id=ORG,
        period_start=JAN,
        period_end=MAR,
    )
    is_ = pkg.income_statement
    assert is_.total_revenue == Decimal("1090000.00")  # 330k + 370k + 390k per month
    assert is_.gross_profit == is_.total_revenue + is_.total_cogs
    assert is_.net_income == is_.operating_income


def test_balance_sheet_snapshot_march() -> None:
    pkg = build_financial_statements(
        _sample_gl_rows(),
        organization_id=ORG,
        period_start=JAN,
        period_end=MAR,
    )
    bs = pkg.balance_sheet
    assert bs.as_of == MAR
    assert bs.total_assets == Decimal("2540000.00")  # cash 2.33M + AR 210k (March snapshot)
    assert bs.sections[0].section_id == "assets"


def test_cash_flow_indirect_reconciles() -> None:
    pkg = build_financial_statements(
        _sample_gl_rows(),
        organization_id=ORG,
        period_start=JAN,
        period_end=MAR,
    )
    cf = pkg.cash_flow_statement
    assert cf.method == "indirect"
    assert cf.cash_beginning == Decimal("2500000.00")
    assert cf.cash_ending == Decimal("2330000.00")
    assert cf.net_change_in_cash == Decimal("-170000.00")
    assert cf.net_income == pkg.income_statement.net_income


def test_empty_gl_returns_zero_statements() -> None:
    pkg = build_financial_statements(
        [],
        organization_id=ORG,
        period_start=JAN,
        period_end=JAN,
    )
    assert pkg.income_statement.net_income == Decimal("0.00")
    assert pkg.balance_sheet.total_assets == Decimal("0.00")
    assert pkg.source_row_count == 0
