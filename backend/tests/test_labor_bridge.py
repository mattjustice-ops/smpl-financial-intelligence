"""Saved compensation bridge: roster-priced hires and departures, GL reconciling plug."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.reporting.board_workforce import workforce_board_payload
from app.services.workforce.gl_payroll import GlPayrollSet, build_gl_payroll
from app.services.workforce.labor_bridge import build_labor_bridges, person_month_cost
from app.services.workforce.roster import employee_from_loaded_row


def _emp(emp_id: str, dept: str, hire: str, **extra) -> object:
    row = {
        "employee_id": emp_id,
        "department": dept,
        "role": "Role",
        "level": extra.get("level") or "",
        "employment_status": extra.get("status", "Active"),
        "hire_date": hire,
        "termination_date": extra.get("termination"),
        "base_salary": extra.get("base", "120000"),
        "variable_comp": extra.get("variable", "0"),
        "commission_target": extra.get("commission", "0"),
        "benefits_load_pct": extra.get("benefits", "0"),
    }
    return employee_from_loaded_row(row)


def _gl(period: str, dept: str, expense_type: str, amount: str) -> dict:
    return {
        "period": period,
        "statement": "Income Statement",
        "statement_category": "Operating Expenses",
        "account_group": "Labor",
        "expense_type": expense_type,
        "department": dept,
        "amount": amount,
    }


def _bridges(roster, actual_rows, budget_roster=None, budget_rows=None):
    return build_labor_bridges(
        close=date(2026, 6, 1),
        roster=roster,
        budget_roster=budget_roster or [],
        actual_payroll=build_gl_payroll(actual_rows),
        budget_payroll=build_gl_payroll(budget_rows) if budget_rows is not None else None,
    )


def _mom(bridges):
    return next(b for b in bridges if b["id"] == "mom")


def _bar(bridge, key):
    return next(bar["amount"] for bar in bridge["bars"] if bar["key"] == key)


def test_month_bridge_prices_a_hire_and_lands_on_gl():
    stayed = _emp("E1", "Engineering", "2025-01-01", base="120000")
    hired = _emp("E2", "Engineering", "2026-06-16", base="60000")
    may = person_month_cost(stayed)
    june_people = may + person_month_cost(hired)
    gl_june = june_people + Decimal("2500")
    bridge = _mom(
        _bridges(
            [stayed, hired],
            [
                _gl("2026-05", "Engineering", "Salaries and Wages", str(may)),
                _gl("2026-06", "Engineering", "Salaries and Wages", str(gl_june)),
                _gl("2026-06", "Engineering", "Commissions", "9000"),
            ],
        )
    )
    assert bridge["available"] is True
    assert bridge["ties"] is True
    assert _bar(bridge, "hires") == float(person_month_cost(hired).quantize(Decimal("0.01")))
    assert bridge["change"] == float((gl_june - may).quantize(Decimal("0.01")))
    assert _bar(bridge, "reconciling") == 2500
    assert "Commissions" not in bridge["commentary"]
    assert "Hires" in bridge["commentary"]
    cited = sum(bar["amount"] for bar in bridge["bars"])
    assert cited == bridge["change"]


def test_departure_is_a_negative_bar():
    leaver = _emp("E1", "Sales", "2024-01-01", base="120000", termination="2026-06-01")
    stayer = _emp("E2", "Sales", "2024-01-01", base="120000")
    pay = person_month_cost(stayer)
    bridge = _mom(
        _bridges(
            [leaver, stayer],
            [
                _gl("2026-05", "Sales", "Salaries and Wages", str(pay * 2)),
                _gl("2026-06", "Sales", "Salaries and Wages", str(pay)),
            ],
        )
    )
    assert _bar(bridge, "departures") == float((-pay).quantize(Decimal("0.01")))
    assert bridge["ties"] is True
    assert "reconciling" not in {bar["key"] for bar in bridge["bars"]}


def test_missing_prior_month_does_not_invent_a_zero():
    bridge = _mom(_bridges([_emp("E1", "Sales", "2025-01-01")], [_gl("2026-06", "Sales", "Salaries and Wages", "10000")]))
    assert bridge["available"] is False
    assert "2026-05" not in bridge["reason"]
    assert "May" in bridge["reason"]


def test_commissions_do_not_move_compensation():
    person = _emp("E1", "Sales", "2025-01-01", base="120000", commission="24000")
    bridge = _mom(
        _bridges(
            [person],
            [
                _gl("2026-05", "Sales", "Salaries and Wages", "10000"),
                _gl("2026-05", "Sales", "Commissions", "1000"),
                _gl("2026-06", "Sales", "Salaries and Wages", "10000"),
                _gl("2026-06", "Sales", "Commissions", "8000"),
            ],
        )
    )
    assert bridge["change"] == 0
    assert bridge["bars"] == []
    assert bridge["ties"] is True


def test_department_bars_add_to_the_company_before_the_plug():
    eng = _emp("E1", "Engineering", "2026-06-01", base="120000")
    sales = _emp("S1", "Sales", "2026-06-01", base="60000")
    bridge = _mom(
        _bridges(
            [eng, sales],
            [
                _gl("2026-05", "Engineering", "Salaries and Wages", "0"),
                _gl("2026-05", "Sales", "Benefits", "0"),
                _gl("2026-06", "Engineering", "Salaries and Wages", "20000"),
                _gl("2026-06", "Sales", "Bonus", "4000"),
            ],
        )
    )
    assert bridge["ties"] is True
    dept_hires = sum(_bar(row, "hires") for row in bridge["departments"])
    assert dept_hires == _bar(bridge, "hires")
    assert all(row["ties"] for row in bridge["departments"])


def test_budget_rate_uses_both_rosters_and_is_omitted_without_budget_gl():
    actual = _emp("E1", "Sales", "2025-01-01", base="144000")
    budget = _emp("E1", "Sales", "2025-01-01", base="120000")
    bridges = _bridges(
        [actual],
        [_gl("2026-05", "Sales", "Salaries and Wages", "10000"), _gl("2026-06", "Sales", "Salaries and Wages", "15000")],
        budget_roster=[budget],
        budget_rows=[_gl("2026-06", "Sales", "Salaries and Wages", "10000")],
    )
    versus = next(b for b in bridges if b["id"] == "budget")
    assert versus["ties"] is True
    assert _bar(versus, "rate") == float((person_month_cost(actual) - person_month_cost(budget)).quantize(Decimal("0.01")))
    assert "above budget" in versus["commentary"]
    without = _bridges(
        [actual],
        [_gl("2026-05", "Sales", "Salaries and Wages", "10000"), _gl("2026-06", "Sales", "Salaries and Wages", "15000")],
    )
    assert [b["id"] for b in without] == ["mom"]


def test_payload_carries_the_saved_bridge():
    payroll = build_gl_payroll(
        [
            _gl("2026-05", "Sales", "Salaries and Wages", "10000"),
            _gl("2026-06", "Sales", "Salaries and Wages", "11000"),
        ]
    )
    payload = workforce_board_payload(
        as_of_period="2026-06",
        roster=[_emp("E1", "Sales", "2025-01-01")],
        budget_roster=[],
        plan=[],
        budget_plan=[],
        payroll=GlPayrollSet(),
        actual_payroll=payroll,
        budget_payroll=None,
        reqs=[],
        ramp=[],
        roster_source="forecast_employees",
    )
    bridge = _mom(payload["labor_bridges"])
    assert bridge["available"] is True
    assert bridge["ties"] is True
    assert "rose $1,000.00" in bridge["commentary"]
    assert "GL reconciling $1,000.00" in bridge["commentary"]
