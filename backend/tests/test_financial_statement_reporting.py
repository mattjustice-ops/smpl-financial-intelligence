"""Normalized financial statement reporting formula tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.financial_statements.financial_statement_service import (
    ensure_balance_formulas,
    ensure_cash_flow_formulas,
    ensure_income_formulas,
)


def test_income_statement_formulas_calculate_correctly() -> None:
    row = ensure_income_formulas(
        {
            "period": date(2026, 6, 1),
            "revenue": Decimal("1000"),
            "cost_of_revenue": Decimal("250"),
            "sales_and_marketing": Decimal("100"),
            "research_and_development": Decimal("150"),
            "general_and_administrative": Decimal("50"),
            "depreciation_and_amortization": Decimal("25"),
            "interest_expense": Decimal("10"),
            "tax_expense": Decimal("5"),
        }
    )
    assert row["gross_profit"] == Decimal("750.00")
    assert row["total_operating_expenses"] == Decimal("300.00")
    assert row["ebitda"] == Decimal("450.00")
    assert row["operating_income"] == Decimal("425.00")
    assert row["net_income"] == Decimal("410.00")


def test_balance_sheet_balances_when_components_tie() -> None:
    row = ensure_balance_formulas(
        {
            "period": date(2026, 6, 1),
            "cash": Decimal("100"),
            "accounts_receivable": Decimal("50"),
            "prepaids_and_other_current_assets": Decimal("25"),
            "property_and_equipment_net": Decimal("75"),
            "accounts_payable": Decimal("30"),
            "deferred_revenue": Decimal("70"),
            "debt": Decimal("50"),
            "equity": Decimal("100"),
        }
    )
    assert row["total_assets"] == Decimal("250.00")
    assert row["total_liabilities"] == Decimal("150.00")
    assert row["total_liabilities_and_equity"] == Decimal("250.00")
    assert row["balance_check"] == Decimal("0.00")


def test_balance_sheet_uses_prepaids_ppe_and_debt_aliases() -> None:
    row = ensure_balance_formulas(
        {
            "period": date(2026, 6, 1),
            "cash": Decimal("100"),
            "accounts_receivable": Decimal("50"),
            "prepaids": Decimal("25"),
            "fixed_assets": Decimal("75"),
            "accounts_payable": Decimal("30"),
            "deferred_revenue": Decimal("70"),
            "debt_balance": Decimal("50"),
            "equity": Decimal("100"),
        }
    )
    assert row["prepaids_and_other_current_assets"] == Decimal("25.00")
    assert row["property_and_equipment_net"] == Decimal("75.00")
    assert row["debt"] == Decimal("50.00")
    assert row["balance_check"] == Decimal("0.00")


def test_forecast_june_beginning_cash_equals_actual_may_ending_cash() -> None:
    rows = ensure_cash_flow_formulas(
        [
            {
                "period": date(2026, 6, 1),
                "net_income": Decimal("10"),
                "depreciation_and_amortization": Decimal("1"),
                "change_in_accounts_receivable": Decimal("-2"),
                "change_in_deferred_revenue": Decimal("3"),
                "change_in_accounts_payable": Decimal("4"),
                "capital_expenditures": Decimal("-5"),
                "debt_issuance_repayment": Decimal("0"),
            }
        ],
        {("Actual", date(2026, 5, 1)): Decimal("500")},
        "Forecast",
    )
    assert rows[0]["beginning_cash"] == Decimal("500")
    assert rows[0]["ending_cash"] == Decimal("511.00")
