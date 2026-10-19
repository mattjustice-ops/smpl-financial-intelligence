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
            "level": extra.get("level") or "",
            "region": extra.get("region") or "",
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


def test_payroll_total_and_parts_include_bonus_and_foot_to_the_teams() -> None:
    rows = [
        _gl("2026-01", "Sales", "Salaries and Wages", "10000"),
        _gl("2026-01", "Sales", "Bonus", "1500"),
        _gl("2026-01", "Engineering", "Bonus", "700"),
        _gl("2026-01", "Engineering", "Payroll Taxes", "300"),
        _gl("2026-01", "Sales", "Commissions", "1200"),
    ]
    p = _payload(payroll=build_gl_payroll(rows))
    assert p["payroll"][0] == 13700.0
    assert p["payroll_parts"]["bonus"][0] == 2200.0
    assert sum(series[0] for series in p["payroll_parts"].values()) == p["payroll"][0]
    assert sum(series[0] for series in p["payroll_by_team"].values()) == p["payroll"][0]
    assert p["payroll_parts"]["bonus"][1] is None


def test_quota_comes_from_headcount_plan() -> None:
    p = _payload()
    assert p["quota_source"] == "headcount_plan"
    assert p["quota"][0] == 900000.0 and p["quota_ramped"][6] == 1000000.0
    assert p["quota"][1] is None


def test_open_reqs_after_close_that_are_approved() -> None:
    p = _payload()
    assert [r["id"] for r in p["reqs"]] == ["R2"]
    assert p["reqs"][0]["pri"] == "Medium" and p["summary"]["open_reqs"] == 1
    assert p["reqs"][0]["region"] == ""


def test_open_req_region_comes_from_the_planned_hire() -> None:
    p = _payload(
        roster=[_emp("P9", "Sales", "2026-07-01", status="Planned", role="Account Executive", level="L4", region="South")],
        reqs=[{
            "req_id": "R9", "department": "Sales", "role": "Account Executive", "level": "L4",
            "status": "Open", "approved_flag": "Yes", "priority": "High", "planned_start_date": "2026-07-01",
            "source": "P9 planned start 2026-07-01",
        }],
    )
    assert p["reqs"][0]["region"] == "South"


def test_ramp_curves_from_assumptions() -> None:
    assert _payload()["ramp"] == {"2": [50.0, 100.0], "4": [0.0]}


def test_payroll_check_compares_roster_cost_with_gl_by_team() -> None:
    check = _payload()["payroll_check"]
    assert check["span"] == "2026-01 to 2026-06"
    rows = {r["team"]: r for r in check["rows"]}
    assert rows["Sales"]["gl"] == 12000.0
    assert rows["Engineering"]["roster"] == 0.0 and rows["Engineering"]["gl"] == 22000.0
    assert rows["R&D"]["gl"] == 0.0 and rows["R&D"]["roster"] > 0
    assert check["register_loaded"] is False and rows["Sales"]["register"] is None


def test_register_ties_to_the_gl_payroll_it_posted_by_team() -> None:
    def posted(*args: str) -> dict:
        return {**_gl(*args), "source_system": "Payroll"}

    gl = [
        posted("2026-01", "Sales", "Salaries and Wages", "10000"),
        posted("2026-01", "Sales", "Payroll Taxes", "800"),
        {**_gl("2026-01", "Sales", "Payroll Taxes", "90"), "source_system": "Commission build"},
        {**_gl("2026-01", "Sales", "Commissions", "1200"), "source_system": "Commission build"},
        posted("2026-06", "Engineering", "Salaries and Wages", "20000"),
        posted("2026-06", "Engineering", "Benefits", "2000"),
    ]
    register = [
        {"period": "2026-01-31", "department": "Sales", "total_payroll_cost": "10800"},
        {"period": "2026-06-30", "department": "Engineering", "total_payroll_cost": "21500"},
        {"period": "2026-09-30", "department": "Engineering", "total_payroll_cost": "99999"},
    ]
    check = _payload(payroll=build_gl_payroll(gl), register=register)["payroll_check"]
    rows = {r["team"]: r for r in check["rows"]}
    assert check["register_loaded"] is True
    assert rows["Sales"]["gl"] == 12090.0 and rows["Sales"]["gl_from_register"] == 10800.0
    assert rows["Sales"]["register"] == 10800.0 and rows["Sales"]["register_variance"] == 0.0
    assert rows["Engineering"]["register"] == 21500.0, "open months are outside the check"
    assert rows["Engineering"]["register_variance"] == -500.0


def test_unsplit_cost_of_revenue_labor_is_its_own_part() -> None:
    rows = [
        _gl("2026-01", "Support", "Labor", "5000", category="Cost of Revenue"),
        _gl("2026-01", "Support", "Salaries and Wages", "2000"),
    ]
    p = _payload(payroll=build_gl_payroll(rows))
    assert p["payroll_parts"]["labor"][0] == 5000.0 and p["payroll_parts"]["wages"][0] == 2000.0
    assert p["payroll"][0] == 7000.0


def test_year_end_roster_is_who_is_on_the_books_in_december_with_bonus_net_of_commission() -> None:
    p = _payload()
    assert p["year_end_month"] == "2026-12"
    assert [(r["dept"], r["id"]) for r in p["year_end_roster"]] == [("R&D", "E2"), ("R&D", "P2"), ("Sales", "E1"),
                                                                    ("Sales", "P1")]
    assert sum(r["base"] for r in p["year_end_roster"]) == 480000.0
    assert sum(series[-1] for series in p["heads"].values()) == len(p["year_end_roster"])

    ae = employee_from_loaded_row({"employee_id": "A1", "department": "Sales", "level": "L4", "employment_status": "Active",
                                   "hire_date": "2025-01-01", "base_salary": "120000", "variable_comp": "70000",
                                   "commission_target": "55000"})
    leaver = employee_from_loaded_row({"employee_id": "A2", "department": "Sales", "level": "L4",
                                       "employment_status": "Terminated", "hire_date": "2025-01-01",
                                       "termination_date": "2026-11-15", "base_salary": "90000"})
    rows = _payload(roster=[ae, leaver])["year_end_roster"]
    assert rows == [{"id": "A1", "dept": "Sales", "lvl": "L4", "base": 120000.0, "bonus": 15000.0, "hire": "2025-01-01"}]


def test_no_year_end_roster_without_a_loaded_roster() -> None:
    assert _payload(roster=[], roster_source="workforce_employees")["year_end_roster"] == []


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
    assert p["payroll_policies"] == {"version": None, "policies": [], "retirement_match_realized": None}
