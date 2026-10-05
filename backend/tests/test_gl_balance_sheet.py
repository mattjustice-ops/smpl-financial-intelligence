"""Balance sheet and cash flow from GL activity (financial_dashboard_cf_re_logic.md worked example)."""

from __future__ import annotations

import pytest

from app.services.reporting.gl_balance_sheet import (
    build_balance_sheet_and_cash_flow,
    chain_rows,
    classify_bs_line,
)

BSA = "Balance Sheet Activity"


def bs(period, expense_type, amount, *, name="", department="", source="Demo Model"):
    return {
        "period": period,
        "statement": "Balance Sheet",
        "expense_type": expense_type,
        "account_group": expense_type,
        "account_name": name or expense_type,
        "department": department,
        "source_system": source,
        "amount": amount,
    }


def pl(period, category, amount, *, group="", department=""):
    return {
        "period": period,
        "statement": "Income Statement",
        "statement_category": category,
        "account_group": group,
        "account_name": category,
        "department": department,
        "amount": amount,
    }


def worked_example():
    opening = [
        bs("2022-10", "Cash", 500, source="Opening Balance"),
        bs("2022-10", "Prepaids", 100, source="Opening Balance"),
        bs("2022-10", "Accounts Payable", -50, source="Opening Balance"),
        bs("2022-10", "Equity", -1000, name="APIC - Common", source="Opening Balance"),
        bs("2022-10", "Equity", 450, name="Retained Earnings", source="Opening Balance"),
    ]
    activity = [
        bs("2022-11", "Cash", 200 - 150),
        bs("2022-11", "Prepaids", -10, department=BSA),
        bs("2022-11", "Equity", -20, name="APIC - Stock Comp", department=BSA),
        bs("2022-12", "Cash", 300 - 180),
        bs("2022-12", "Accounts Payable", -40),
        bs("2022-12", "Prepaids", -10, department=BSA),
        bs("2022-12", "Equity", -20, name="APIC - Stock Comp", department=BSA),
    ]
    income = [
        pl("2022-11", "Revenue", -200),
        pl("2022-11", "Operating Expense", 150, group="G&A"),
        pl("2022-11", "Operating Expense", 20, group="G&A"),
        pl("2022-11", "D&A", 10),
        pl("2022-12", "Revenue", -300),
        pl("2022-12", "Operating Expense", 180 + 40, group="G&A"),
        pl("2022-12", "Operating Expense", 20, group="G&A"),
        pl("2022-12", "D&A", 10),
    ]
    return opening + activity, income


def test_worked_example_balance_sheet_rolls_from_opening_balances():
    balance, _ = build_balance_sheet_and_cash_flow(*worked_example())
    nov, dec = balance["2022-11"], balance["2022-12"]
    assert nov["cash"] == 550 and nov["prepaids_and_other_current_assets"] == 90
    assert nov["retained_earnings"] == -450 and nov["current_period_net_income"] == 20
    assert nov["apic_stock_compensation"] == 20 and nov["paid_in_capital"] == 1000
    assert nov["total_assets"] == 640 and nov["balance_check"] == 0
    assert dec["cash"] == 670 and dec["accounts_payable"] == 90
    assert dec["retained_earnings"] == -430 and dec["current_period_net_income"] == 50
    assert dec["total_liabilities_and_equity"] == 750 and dec["balance_check"] == 0


def test_worked_example_cash_flow_passes_the_four_checks():
    _, cash_flow = build_balance_sheet_and_cash_flow(*worked_example())
    nov, dec = cash_flow["2022-11"], cash_flow["2022-12"]
    assert nov["net_income"] == 20
    assert nov["depreciation_and_amortization"] == 10
    assert nov["stock_based_compensation"] == 20
    assert nov["other_non_cash"] == 0
    assert nov["change_in_prepaids"] == 0
    assert nov["net_cash_from_operating_activities"] == 50
    assert (nov["beginning_cash"], nov["ending_cash"], nov["cash_check"]) == (500, 550, 0)
    assert dec["change_in_accounts_payable"] == 40
    assert dec["net_cash_from_operating_activities"] == 120
    assert (dec["ending_cash"], dec["cash_check"]) == (670, 0)
    for month in (nov, dec):
        assert month["net_cash_from_operating_activities"] == pytest.approx(
            month["net_income"] + month["non_cash_total"] + month["working_capital_total"]
        )
        assert month["net_change_in_cash"] == pytest.approx(
            month["net_cash_from_operating_activities"]
            + month["net_cash_from_investing_activities"]
            + month["net_cash_from_financing_activities"]
        )


def test_retained_earnings_ignores_gl_activity_on_the_retained_earnings_account():
    rows, income = worked_example()
    rows.append(bs("2022-12", "Equity", -999, name="Retained Earnings"))
    balance, _ = build_balance_sheet_and_cash_flow(rows, income)
    assert balance["2022-12"]["retained_earnings"] == -430


def test_equity_raise_is_financing_not_operating():
    rows, income = worked_example()
    rows += [bs("2022-12", "Equity", -400, name="APIC - Common"), bs("2022-12", "Cash", 400)]
    balance, cash_flow = build_balance_sheet_and_cash_flow(rows, income)
    assert cash_flow["2022-12"]["equity_issuance"] == 400
    assert cash_flow["2022-12"]["net_cash_from_financing_activities"] == 400
    assert cash_flow["2022-12"]["cash_check"] == 0
    assert balance["2022-12"]["paid_in_capital"] == 1400


def test_budget_continues_from_actual_balances():
    actual_bs, actual_pl = worked_example()
    budget_bs = [bs("2022-12", "Cash", 70)]
    budget_pl = [pl("2022-12", "Revenue", -70), pl("2022-11", "Revenue", -999)]
    rows, income, start = chain_rows("Budget", actual_bs, actual_pl, budget_bs, budget_pl)
    assert start == "2022-12"
    balance, cash_flow = build_balance_sheet_and_cash_flow(rows, income)
    assert balance["2022-12"]["cash"] == 620
    assert balance["2022-12"]["retained_earnings"] == -430
    assert cash_flow["2022-12"]["cash_check"] == 0


def test_financial_statements_balance_sheet_and_cash_flow_come_from_gl(monkeypatch: pytest.MonkeyPatch):
    from datetime import date
    from decimal import Decimal

    from app.services.financial_statements import financial_statement_service as fs

    built = build_balance_sheet_and_cash_flow(*worked_example())
    monkeypatch.setattr(fs, "gl_balance_sheet_and_cash_flow_by_period", lambda _db, _org, _scenario: built)
    kwargs = dict(scenario="Actual", start_period=date(2022, 11, 1), end_period=date(2022, 12, 1))

    balance = fs.statement(None, None, statement_type="balance_sheet", **kwargs)
    by_line = {(r.period, r.line_item): r for r in balance.rows}
    dec = date(2022, 12, 1)
    assert by_line[(dec, "Cash")].amount == Decimal("670.00")
    assert by_line[(dec, "Retained Earnings")].amount == Decimal("-430.00")
    assert by_line[(dec, "Total Equity")].amount == Decimal("660.00")
    assert by_line[(dec, "Balance Check")].amount == Decimal("0.00")
    assert {r.source_table for r in balance.rows} == {"gl_actuals"}

    cash = fs.statement(None, None, statement_type="cash_flow", **kwargs)
    cf = {(r.period, r.line_item): r.amount for r in cash.rows}
    assert cf[(dec, "Beginning Cash Balance")] == Decimal("550.00")
    assert cf[(dec, "Stock-Based Compensation")] == Decimal("20.00")
    assert cf[(dec, "Ending Cash Balance")] == Decimal("670.00")

    rows = fs.gl_balance_rows(None, None, "Actual", date(2022, 12, 1), date(2022, 12, 1))
    assert rows[0]["prepaids_and_other_current"] == rows[0]["prepaids_and_other_current_assets"] == Decimal("80.00")


def test_unknown_balance_sheet_account_is_reported_not_assigned():
    assert classify_bs_line({"statement": "Balance Sheet", "expense_type": "Mystery", "account_group": ""}) == "unmapped"
    assert classify_bs_line({"statement": "Income Statement", "expense_type": "Cash"}) is None
