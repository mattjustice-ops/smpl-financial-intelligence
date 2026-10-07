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


def deferred_commission_rows():
    """Dec 2022: pay 60 of commissions (capitalized), amortize 1, reclass 1 to current."""

    def dc(period, expense_type, amount, source="Demo Model"):
        return {**bs(period, expense_type, amount, source=source), "account_group": "Deferred Commissions"}

    rows, income = worked_example()
    rows += [
        dc("2022-10", "Deferred Commissions", 12, source="Opening Balance"),
        dc("2022-10", "Deferred Commissions Noncurrent", 48, source="Opening Balance"),
        bs("2022-10", "Equity", -60, name="APIC - Common", source="Opening Balance"),
        bs("2022-12", "Cash", -60),
        dc("2022-12", "Deferred Commissions Noncurrent", 60),
        dc("2022-12", "Deferred Commissions", -1),
        dc("2022-12", "Deferred Commissions", 1),
        dc("2022-12", "Deferred Commissions Noncurrent", -1),
    ]
    income.append(pl("2022-12", "Operating Expense", 1, group="G&A"))
    return rows, income


def test_deferred_commissions_are_assets_and_operating_working_capital():
    balance, cash_flow = build_balance_sheet_and_cash_flow(*deferred_commission_rows())
    nov, dec = balance["2022-11"], balance["2022-12"]
    assert (nov["deferred_commissions_current"], nov["deferred_commissions_noncurrent"]) == (12, 48)
    assert (dec["deferred_commissions_current"], dec["deferred_commissions_noncurrent"]) == (12, 107)
    assert dec["total_assets"] == 670 - 60 + 80 + 12 + 107
    assert dec["balance_check"] == 0 and "unmapped" not in dec
    cf = cash_flow["2022-12"]
    assert cf["change_in_deferred_commissions"] == -59
    assert cf["unclassified"] == 0
    assert cf["net_cash_from_operating_activities"] == 120 - 1 - 59
    assert cf["net_cash_from_investing_activities"] == 0
    assert cf["cash_check"] == 0


def test_statement_validations_include_deferred_commissions(monkeypatch: pytest.MonkeyPatch):
    from datetime import date

    from app.services.financial_statements import financial_statement_service as fs
    from app.services.financial_statements.financial_statement_validation_service import validate_financial_statements

    built = build_balance_sheet_and_cash_flow(*deferred_commission_rows())
    monkeypatch.setattr(fs, "gl_balance_sheet_and_cash_flow_by_period", lambda _db, _org, _scenario: built)
    monkeypatch.setattr(fs, "gl_income_statement_by_period", lambda _db, _org, _scenario: {})
    kwargs = dict(scenario="Actual", start_period=date(2022, 12, 1), end_period=date(2022, 12, 1))
    balance = fs.statement(None, None, statement_type="balance_sheet", **kwargs)
    cash = fs.statement(None, None, statement_type="cash_flow", **kwargs)
    income = fs.statement(None, None, statement_type="income_statement", **kwargs)
    lines = {r.line_item: r.amount for r in balance.rows} | {r.line_item: r.amount for r in cash.rows}
    assert lines["Deferred Commissions - Noncurrent"] == 107
    assert lines["Change in Deferred Commissions"] == -59
    results = {r.validation_name: r.status for r in validate_financial_statements(income, balance, cash)}
    assert results["balance_sheet_total_assets"] == "pass"
    assert results["cash_flow_operating_cash_flow"] == "pass"


def test_opening_month_has_no_cash_flow_and_its_cash_is_checked_next_month(monkeypatch: pytest.MonkeyPatch):
    from datetime import date

    from app.services.financial_statements import financial_statement_service as fs
    from app.services.financial_statements.financial_statement_validation_service import validate_financial_statements

    built = build_balance_sheet_and_cash_flow(*deferred_commission_rows())
    monkeypatch.setattr(fs, "gl_balance_sheet_and_cash_flow_by_period", lambda _db, _org, _scenario: built)
    monkeypatch.setattr(fs, "gl_income_statement_by_period", lambda _db, _org, _scenario: {})
    kwargs = dict(scenario="Actual", start_period=date(2022, 10, 1), end_period=date(2022, 12, 1))
    balance = fs.statement(None, None, statement_type="balance_sheet", **kwargs)
    cash = fs.statement(None, None, statement_type="cash_flow", **kwargs)
    income = fs.statement(None, None, statement_type="income_statement", **kwargs)
    oct_, nov, dec = date(2022, 10, 1), date(2022, 11, 1), date(2022, 12, 1)
    assert oct_ not in {r.period for r in cash.rows}

    results = validate_financial_statements(income, balance, cash)
    assert not [(r.validation_name, r.period) for r in results if r.status == "fail"]
    assert not [r for r in results if r.period == oct_ and r.validation_name.startswith("cash_flow")]
    beginning = {r.period: r for r in results if r.validation_name == "cash_flow_beginning_cash_equals_prior_balance_sheet_cash"}
    assert set(beginning) == {nov, dec} and beginning[nov].status == "pass"

    # A month after the opening without a cash flow still fails.
    missing = cash.model_copy(update={"rows": [r for r in cash.rows if r.period != nov]})
    failed = {(r.validation_name, r.period) for r in validate_financial_statements(income, balance, missing) if r.status == "fail"}
    assert ("cash_flow_ending_cash_equals_balance_sheet_cash", nov) in failed

    # Beginning cash that does not pick up the prior month's balance sheet cash fails.
    off = cash.model_copy(update={"rows": [
        r.model_copy(update={"amount": r.amount + 5}) if (r.period, r.line_item) == (dec, "Beginning Cash Balance") else r
        for r in cash.rows
    ]})
    failed = {(r.validation_name, r.period) for r in validate_financial_statements(income, balance, off) if r.status == "fail"}
    assert ("cash_flow_beginning_cash_equals_prior_balance_sheet_cash", dec) in failed


def test_unclassified_gl_balance_sheet_account_fails_validation(monkeypatch: pytest.MonkeyPatch):
    from datetime import date

    from app.services.financial_statements import financial_statement_service as fs

    rows, income = worked_example()
    rows += [bs("2022-12", "Mystery Asset", 25), bs("2022-12", "Cash", -25)]
    built = build_balance_sheet_and_cash_flow(rows, income)
    monkeypatch.setattr(fs, "gl_balance_sheet_and_cash_flow_by_period", lambda _db, _org, _scenario: built)
    monkeypatch.setattr(fs, "fetch_rows", lambda *_args: [])
    results = fs.source_reconciliation_validations(
        None, None, scenario="Actual", start_period=date(2022, 11, 1), end_period=date(2022, 12, 1)
    )
    failed = {(r.validation_name, r.period) for r in results if r.status == "fail"}
    assert ("gl_balance_sheet_accounts_classified", date(2022, 12, 1)) in failed
    assert ("gl_cash_flow_activity_classified", date(2022, 12, 1)) in failed
    assert not {name for name, period in failed if period == date(2022, 11, 1)}


def test_unknown_balance_sheet_account_is_reported_not_assigned():
    assert classify_bs_line({"statement": "Balance Sheet", "expense_type": "Mystery", "account_group": ""}) == "unmapped"
    assert classify_bs_line({"statement": "Income Statement", "expense_type": "Cash"}) is None
