"""Engine statement rows become the ledger the Board reads."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.reporting.engine_ledger import ledger_rows
from app.services.reporting.gl_balance_sheet import build_balance_sheet_and_cash_flow


def _open(expense_type: str, amount: float, *, name: str = "") -> dict:
    return {
        "period": "2026-12",
        "statement": "Balance Sheet",
        "expense_type": expense_type,
        "account_group": expense_type,
        "account_name": name or expense_type,
        "department": "",
        "source_system": "Opening Balance",
        "amount": amount,
    }


def test_promoted_journals_match_the_engine_and_use_the_capex_debit():
    prior = {
        "cash": Decimal("1000"), "ar": Decimal("100"), "prepaids": Decimal("50"),
        "dc_current": Decimal("0"), "dc_noncurrent": Decimal("0"), "ppe": Decimal("200"),
        "other_assets": Decimal("0"), "ap": Decimal("80"), "dr": Decimal("60"),
        "debt": Decimal("500"), "other_liabilities": Decimal("40"), "accrued": Decimal("0"),
        "equity": Decimal("670"),
    }
    income = {"2027-01": {
        "revenue": "300", "cost_of_revenue": "80", "sales_and_marketing": "43",
        "research_and_development": "20", "general_and_administrative": "10",
        "depreciation_and_amortization": "5", "interest_expense": "4", "tax_expense": "0",
        "net_income": "138",
    }}
    balance = {"2027-01": {
        "cash": "1137", "accounts_receivable": "110", "prepaids_and_other_current": "48",
        "deferred_commissions_current": "15", "ppe_net": "207", "accounts_payable": "90",
        "deferred_revenue": "70", "debt": "500", "other_liabilities": "40",
        "accrued_commissions": "6", "equity": "811",
    }}
    cash_flow = {"2027-01": {"capital_expenditures": "-12", "stock_based_compensation": "3"}}
    activity = ledger_rows("Budget", ["2027-01"], income, balance, cash_flow, prior)
    capex = [r for r in activity if r["source_record_id"].endswith("-capex") and r["account_number"] == "1500"]
    interest = [r for r in activity if r["source_record_id"].endswith("-interest_paid")]
    assert capex[0]["amount"] == Decimal("12.00")
    assert interest[0]["amount"] == Decimal("-4.00")
    assert any(r["source_record_id"].endswith("-depreciation") and r["department"] == "Balance Sheet Activity" for r in activity)

    opening = [
        _open("Cash", 1000),
        _open("Accounts Receivable", 100),
        _open("Prepaids", 50),
        _open("Fixed Assets", 200),
        _open("Accounts Payable", -80),
        _open("Deferred Revenue", -60),
        _open("Debt", -500),
        _open("Other Liabilities", -40),
        _open("Equity", -670, name="APIC - Common"),
    ]
    bs_rows = opening + [r for r in activity if "balance" in r["statement"].lower()]
    pl_rows = [r for r in activity if "balance" not in r["statement"].lower()]
    built, flow = build_balance_sheet_and_cash_flow(bs_rows, pl_rows)
    jan = built["2027-01"]
    cf = flow["2027-01"]
    assert jan["cash"] == pytest.approx(1137)
    assert jan["property_and_equipment_net"] == pytest.approx(207)
    assert jan["debt"] == pytest.approx(500)
    assert jan["equity"] == pytest.approx(811)
    assert jan["balance_check"] == pytest.approx(0)
    assert cf["capital_expenditures"] == pytest.approx(-12)
    assert cf["depreciation_and_amortization"] == pytest.approx(5)
    assert cf["cash_check"] == pytest.approx(0)
