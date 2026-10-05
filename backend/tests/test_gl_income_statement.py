"""Income statement built from GL rows (debit-positive)."""

from __future__ import annotations

import pytest

from app.services.reporting.gl_income_statement import build_income_statement_rows, classify_gl_line


def _row(amount, *, category="Operating Expense", statement="Income Statement", group="", dept="", name="", period="2026-01"):
    return {
        "period": period,
        "statement": statement,
        "statement_category": category,
        "category": category,
        "account_group": group,
        "account_name": name,
        "department": dept,
        "amount": amount,
    }


def test_revenue_credit_shows_positive_and_expenses_as_posted() -> None:
    is_row = build_income_statement_rows(
        [
            _row(-1_000.0, category="Revenue", name="Subscription Revenue"),
            _row(200.0, category="Cost of Revenue"),
            _row(150.0, dept="Sales"),
            _row(50.0, dept="Marketing"),
            _row(100.0, dept="Engineering"),
            _row(80.0, dept="Finance"),
        ]
    )["2026-01"]

    assert is_row["revenue"] == 1_000.0
    assert is_row["cogs"] == 200.0
    assert is_row["gross_profit"] == 800.0
    assert is_row["sm"] == 200.0
    assert is_row["rd"] == 100.0
    assert is_row["ga"] == 80.0
    assert is_row["total_opex"] == 380.0
    assert is_row["ebitda"] == 420.0
    assert is_row["gm_pct"] == pytest.approx(0.8)


def test_sm_is_sales_plus_marketing_only() -> None:
    is_row = build_income_statement_rows(
        [
            _row(150.0, dept="Sales"),
            _row(50.0, dept="Marketing"),
            _row(30.0, dept="Customer Success"),
            _row(20.0, dept="Support"),
        ]
    )["2026-01"]

    assert is_row["sm"] == 200.0
    assert is_row["ga"] == 50.0


def test_function_named_in_category_or_account_group() -> None:
    rows = [
        _row(10.0, category="Sales and Marketing", statement="Sales and Marketing"),
        _row(20.0, group="S&M"),
        _row(5.0, group="R&D"),
        _row(4.0, group="D&A"),
        _row(3.0, category="Other", group="Interest"),
    ]
    is_row = build_income_statement_rows(rows)["2026-01"]

    assert is_row["sm"] == 30.0
    assert is_row["rd"] == 5.0
    assert is_row["da"] == 4.0
    assert is_row["interest"] == 3.0


def test_balance_sheet_rows_are_ignored() -> None:
    assert classify_gl_line(_row(1.0, statement="Balance Sheet", category="Assets")) is None
    assert build_income_statement_rows([_row(1.0, statement="Balance Sheet", category="Assets")]) == {}


def test_unknown_department_is_visible_not_hidden() -> None:
    is_row = build_income_statement_rows([_row(40.0, dept="Mystery Team")])["2026-01"]

    assert is_row["unmapped"] == 40.0
    assert is_row["total_opex"] == 40.0
    assert is_row["ga"] == 0.0


def test_below_ebitda_lines_and_net_income() -> None:
    is_row = build_income_statement_rows(
        [
            _row(-1_000.0, category="Revenue"),
            _row(300.0, dept="Sales"),
            _row(50.0, category="D&A"),
            _row(20.0, category="Interest"),
            _row(30.0, category="Taxes"),
        ]
    )["2026-01"]

    assert is_row["ebitda"] == 700.0
    assert is_row["op_income"] == 650.0
    assert is_row["pretax"] == 630.0
    assert is_row["net_income"] == 600.0


def test_services_revenue_split_comes_from_accounts() -> None:
    is_row = build_income_statement_rows(
        [
            _row(-900.0, category="Revenue", name="Subscription Revenue"),
            _row(-100.0, category="Revenue", name="Professional Services Revenue"),
        ]
    )["2026-01"]

    assert is_row["sub_rev"] == 900.0
    assert is_row["svc_rev"] == 100.0
