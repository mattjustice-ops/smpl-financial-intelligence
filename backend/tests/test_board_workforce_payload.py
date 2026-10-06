"""Board Workforce tab payload: roster heads, GL-only payroll, plan quota, open reqs, ramp curves."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.reporting.board_workforce import workforce_board_payload
from app.services.workforce.gl_payroll import build_gl_payroll
from app.services.workforce.legacy_headcount import LegacyHeadcountSnapshot
from app.services.workforce.roster import employee_from_loaded_row


def _emp(emp_id: str, dept: str, hire: str, status: str = "Active", **extra) -> object:
    return employee_from_loaded_row(
        {
            "employee_id": emp_id,
            "department": dept,
            "role": extra.get("role", "Role"),
            "employment_status": status,
            "hire_date": hire,
            "base_salary": extra.get("base", "120000"),
            "variable_comp": extra.get("variable", "0"),
            "benefits_load_pct": "0",
            "annual_quota_arr": extra.get("quota", "0"),
        }
    )


def _gl(period: str, dept: str, expense_type: str, amount: str, category: str = "Operating Expenses") -> dict:
    return {
        "period": period,
        "statement": "Income Statement",
        "statement_category": category,
        "account_group": "Labor" if expense_type != "Commissions" else "Sales Expense",
        "expense_type": expense_type,
        "department": dept,
        "amount": amount,
    }


def _plan(period: str, dept: str, heads: int, quota: str = "0", ramped: str = "0") -> LegacyHeadcountSnapshot:
    return LegacyHeadcountSnapshot(
        period=date.fromisoformat(period + "-01"),
        department=dept,
        headcount_beginning=Decimal(heads),
        new_hires=Decimal(0),
        attrition=Decimal(0),
        headcount_ending=Decimal(heads),
        quota_capacity_arr=Decimal(quota),
        productive_quota_capacity_arr=Decimal(ramped),
    )


def _payload(**overrides):
    args = dict(
        as_of_period="2026-06",
        roster=[
            _emp("E1", "Sales", "2025-03-01", quota="900000", variable="60000"),
            _emp("E2", "R&D", "2026-04-01"),
            _emp("P1", "Sales", "2026-06-01", status="Planned"),
            _emp("P2", "R&D", "2026-09-01", status="Planned"),
            _emp("T1", "Sales", "2026-01-01", status="Terminated"),
        ],
        budget_roster=[_emp("B1", "Sales", "2025-01-01"), _emp("B2", "Sales", "2025-01-01")],
        plan=[_plan("2026-01", "Sales", 1, "900000", "800000"), _plan("2026-07", "Sales", 2, "1800000", "1000000")],
        budget_plan=[],
        payroll=build_gl_payroll(
            [
                _gl("2026-01", "Sales", "Salaries and Wages", "10000"),
                _gl("2026-01", "Sales", "Payroll Taxes", "800"),
                _gl("2026-01", "Sales", "Commissions", "1200"),
                _gl("2026-06", "Engineering", "Salaries and Wages", "20000"),
                _gl("2026-06", "Engineering", "Benefits", "2000"),
                _gl("2026-06", "Engineering", "Cloud Infrastructure", "9999"),
            ]
        ),
        reqs=[
            {"req_id": "R1", "department": "Sales", "role": "AE", "level": "L4", "status": "Open",
             "approved_flag": "Yes", "priority": "high", "planned_start_date": "2026-06-01"},
            {"req_id": "R2", "department": "R&D", "role": "SWE", "level": "L4", "status": "Open",
             "approved_flag": "Yes", "priority": "Medium", "planned_start_date": "2026-09-01"},
            {"req_id": "R3", "department": "G&A", "role": "Counsel", "status": "Cancelled",
             "approved_flag": "Yes", "planned_start_date": "2026-10-01"},
            {"req_id": "R4", "department": "G&A", "role": "Analyst", "status": "Open",
             "approved_flag": "No", "planned_start_date": "2026-10-01"},
        ],
        ramp=[
            {"ramp_months": "2", "month": "1", "pct": "0.5"},
            {"ramp_months": "2", "month": "2", "pct": "1.0"},
            {"ramp_months": "4", "month": "1", "pct": "0"},
        ],
        roster_source="forecast_employees",
    )
    args.update(overrides)
    return workforce_board_payload(**args)


def test_heads_come_from_roster_including_started_planned_hires() -> None:
    p = _payload()
    assert p["heads_source"] == "forecast_employees"
    assert p["departments"] == ["Sales", "R&D"]
    assert p["heads"]["Sales"][:6] == [1, 1, 1, 1, 1, 2]
    assert p["heads"]["R&D"][2:4] == [0, 1] and p["heads"]["R&D"][8] == 2
    assert p["heads_total"][5] == 3 and p["heads_total"][11] == 4
    assert p["heads_budget_total"] == [2] * 12
    assert p["summary"]["close_hc"] == 3 and p["summary"]["budget_close_hc"] == 2
    assert [r["id"] for r in p["roster"]] == ["E1", "P1", "E2"]


def test_payroll_is_gl_only_by_gl_team_with_gaps_left_empty() -> None:
    p = _payload()
    assert p["payroll_source"] == "gl_actuals"
    assert p["payroll"][0] == 12000.0 and p["payroll"][5] == 22000.0
    assert p["payroll"][1] is None, "months without GL payroll stay empty, never zero or roster cost"
    assert set(p["payroll_by_team"]) == {"Sales", "Engineering"}
    assert p["payroll_parts"]["commissions"][0] == 1200.0
    assert p["payroll_parts"]["benefits"][0] == 800.0


def test_quota_comes_from_headcount_plan() -> None:
    p = _payload()
    assert p["quota_source"] == "headcount_plan"
    assert p["quota"][0] == 900000.0 and p["quota_ramped"][6] == 1000000.0
    assert p["quota"][1] is None


def test_open_reqs_after_close_that_are_approved() -> None:
    p = _payload()
    assert [r["id"] for r in p["reqs"]] == ["R2"]
    assert p["reqs"][0]["pri"] == "Medium" and p["summary"]["open_reqs"] == 1


def test_ramp_curves_from_assumptions() -> None:
    assert _payload()["ramp"] == {"2": [50.0, 100.0], "4": [0.0]}


def test_payroll_check_compares_roster_cost_with_gl_by_team() -> None:
    check = _payload()["payroll_check"]
    assert check["span"] == "2026-01 to 2026-06"
    rows = {r["team"]: r for r in check["rows"]}
    assert rows["Sales"]["gl"] == 12000.0
    assert rows["Engineering"]["roster"] == 0.0 and rows["Engineering"]["gl"] == 22000.0
    assert rows["R&D"]["gl"] == 0.0 and rows["R&D"]["roster"] > 0


def test_headcount_plan_supplies_heads_when_no_roster() -> None:
    p = _payload(roster=[], roster_source="workforce_employees")
    assert p["heads_source"] == "headcount_plan"
    assert p["heads"]["Sales"][0] == 1 and p["heads"]["Sales"][6] == 2
    assert p["roster"] == [] and p["payroll_check"]["rows"] == []


def test_nothing_loaded_gives_empty_payload() -> None:
    p = workforce_board_payload(
        as_of_period="2026-06", roster=[], budget_roster=[], plan=[], budget_plan=[],
        payroll=build_gl_payroll([]), reqs=[], ramp=[], roster_source=None,
    )
    assert p["heads"] == {} and p["heads_source"] is None
    assert p["payroll"] == [None] * 12 and p["summary"]["close_hc"] is None
