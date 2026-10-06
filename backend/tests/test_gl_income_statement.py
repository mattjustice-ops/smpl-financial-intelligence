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


def test_customer_success_is_sales_and_support_is_ga() -> None:
    is_row = build_income_statement_rows(
        [
            _row(150.0, dept="Sales"),
            _row(50.0, dept="Marketing"),
            _row(30.0, dept="Customer Success"),
            _row(20.0, dept="Support"),
        ]
    )["2026-01"]

    assert is_row["sm"] == 230.0
    assert is_row["ga"] == 20.0


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


def test_implementation_revenue_is_its_own_line_and_saas_is_subscription() -> None:
    is_row = build_income_statement_rows(
        [
            _row(-900.0, category="Revenue", name="SaaS Revenue", group="Revenue"),
            _row(-35.0, category="Revenue", name="Implementation & Onboarding Revenue", group="Revenue"),
        ]
    )["2026-01"]

    assert is_row["revenue"] == 935.0
    assert is_row["sub_rev"] == 900.0
    assert is_row["svc_rev"] == 35.0
    assert is_row["impl_rev"] == 35.0
    assert is_row["rec_svc_rev"] == 0.0


def test_support_and_tam_are_recurring_services_and_implementation_is_not() -> None:
    is_row = build_income_statement_rows(
        [
            _row(-900.0, category="Revenue", name="Subscription Revenue", group="Revenue"),
            _row(-60.0, category="Revenue", name="Support & Services Revenue", group="Revenue"),
            _row(-15.0, category="Revenue", name="Technical Account Management", group="Revenue"),
            _row(-25.0, category="Revenue", name="Implementation & Onboarding Revenue", group="Revenue"),
        ]
    )["2026-01"]

    assert is_row["revenue"] == 1000.0
    assert is_row["sub_rev"] == 900.0
    assert is_row["rec_svc_rev"] == 75.0
    assert is_row["impl_rev"] == 25.0
    assert is_row["svc_rev"] == 100.0


def test_financial_statements_income_rows_come_from_gl(monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import date
    from decimal import Decimal

    from app.services.financial_statements import financial_statement_service as fs

    built = build_income_statement_rows(
        [
            _row(-1_000.0, category="Revenue", name="Subscription Revenue", period="2026-01"),
            _row(300.0, category="Cost of Revenue", period="2026-01"),
            _row(200.0, dept="Customer Success", period="2026-01"),
            _row(-1_100.0, category="Revenue", name="Subscription Revenue", period="2026-02"),
        ]
    )
    calls: list[str] = []

    def fake_gl(_db, _org, scenario):
        calls.append(scenario)
        return built

    monkeypatch.setattr(fs, "gl_income_statement_by_period", fake_gl)
    rows = fs.gl_income_rows(None, None, "Actual", date(2026, 1, 1), date(2026, 1, 1))

    assert calls == ["Actual"]
    assert [r["period"] for r in rows] == [date(2026, 1, 1)]
    jan = rows[0]
    assert jan["revenue"] == Decimal("1000.00")
    assert jan["cost_of_revenue"] == Decimal("300.00")
    assert jan["sales_and_marketing"] == Decimal("200.00")
    assert jan["ebitda"] == Decimal("500.00")


def test_readiness_source_can_name_a_gl_version() -> None:
    from app.services.readiness.evidence import _split_source
    from app.services.readiness.registry import OBJECTS

    assert _split_source("gl_actuals#Budget") == ("gl_actuals", "Budget")
    assert _split_source("actual_balance_sheet") == ("actual_balance_sheet", None)
    assert OBJECTS["income_statement"].tables == ("gl_actuals#Actual",)
