"""Pydantic models for financial statement API responses."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field


class StatementLine(BaseModel):
    """One displayed row on a financial statement."""

    line_id: str
    label: str
    amount: Decimal
    account_number: Optional[str] = None
    category: Optional[str] = None
    is_subtotal: bool = False
    indent_level: int = 0


class StatementSection(BaseModel):
    section_id: str
    title: str
    lines: list[StatementLine] = Field(default_factory=list)
    subtotal: Optional[Decimal] = None


class IncomeStatement(BaseModel):
    statement_type: Literal["income_statement"] = "income_statement"
    period_start: date
    period_end: date
    currency: str = "USD"
    sections: list[StatementSection] = Field(default_factory=list)
    total_revenue: Decimal = Decimal("0")
    total_cogs: Decimal = Decimal("0")
    gross_profit: Decimal = Decimal("0")
    total_operating_expense: Decimal = Decimal("0")
    operating_income: Decimal = Decimal("0")
    net_income: Decimal = Decimal("0")


class BalanceSheet(BaseModel):
    statement_type: Literal["balance_sheet"] = "balance_sheet"
    as_of: date
    currency: str = "USD"
    sections: list[StatementSection] = Field(default_factory=list)
    total_assets: Decimal = Decimal("0")
    total_liabilities: Decimal = Decimal("0")
    total_equity: Decimal = Decimal("0")
    total_liabilities_and_equity: Decimal = Decimal("0")
  # assets - (liabilities + equity); should be ~0 when balanced
    check: Decimal = Decimal("0")


class CashFlowStatement(BaseModel):
    statement_type: Literal["cash_flow_statement"] = "cash_flow_statement"
    period_start: date
    period_end: date
    currency: str = "USD"
    method: Literal["indirect", "direct"] = "indirect"
    sections: list[StatementSection] = Field(default_factory=list)
    net_income: Decimal = Decimal("0")
    cash_from_operations: Decimal = Decimal("0")
    cash_from_investing: Decimal = Decimal("0")
    cash_from_financing: Decimal = Decimal("0")
    net_change_in_cash: Decimal = Decimal("0")
    cash_beginning: Decimal = Decimal("0")
    cash_ending: Decimal = Decimal("0")
    reconciliation_delta: Decimal = Decimal("0")


class FinancialStatementsPackage(BaseModel):
    organization_id: str
    period_start: date
    period_end: date
    currency: str = "USD"
    income_statement: IncomeStatement
    balance_sheet: BalanceSheet
    cash_flow_statement: CashFlowStatement
    source_row_count: int = 0
