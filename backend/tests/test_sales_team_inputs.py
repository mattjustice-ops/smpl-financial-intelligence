"""Sales team the Budget Engine opens from: Forecast HRIS at the year end, quota types, ramp curves, attainment."""

from __future__ import annotations

import uuid

from app.services.readiness.sales_team_inputs import ramp_pct, sales_team

ORG = "8571e520-0687-4516-bdee-379f37c58c1f"
EMPLOYEE_COLUMNS = ("employee_id", "employee_name", "department", "sub_department", "role", "level", "region",
                    "hire_date", "termination_date", "quota_carrying", "annual_quota_arr", "productivity_ramp_months",
                    "base_salary", "commission_target")
EMPLOYEES = (
    ("E1", "Ann", "Sales", "Enterprise Sales", "Account Executive", "L4", "East", "2025-03-01", "", "Yes", "800000", "3",
     "125000", "80000"),
    ("E2", "Bob", "Sales", "Enterprise Sales", "Senior Account Executive", "L5", "West", "2026-11-01", "", "Yes", "1100000",
     "3", "150000", "110000"),
    ("E3", "Sid", "Sales", "Mid-Market Sales", "Sales Development Rep", "L2", "East", "2024-01-01", "", "Yes", "300000", "2",
     "70000", "25000"),
    ("E4", "Cara", "Customer Success", "Customer Success", "Customer Success Manager", "L3", "East", "2024-01-01", "", "No",
     "450000", "3", "95000", "0"),
    ("E5", "Gone", "Sales", "Enterprise Sales", "Account Executive", "L4", "East", "2024-01-01", "2026-06-30", "Yes",
     "800000", "3", "125000", "80000"),
    ("E6", "Late", "Sales", "Enterprise Sales", "Account Executive", "L4", "East", "2027-02-01", "", "Yes", "800000", "3",
     "125000", "80000"),
    ("E7", "Eve", "R&D", "Engineering", "Software Engineer", "L4", "East", "2024-01-01", "", "No", "0", "2", "160000", "0"),
)
CURVES = (("3", 0, "0.25"), ("3", 1, "0.6"), ("3", 2, "1.0"), ("2", 0, "0.5"), ("2", 1, "1.0"))


def _db(employees=EMPLOYEES, curves=CURVES, stale=False, bob_month_1="0.25"):
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    s = Session(create_engine("sqlite://"))
    s.execute(text("create table forecast_employees (organization_id text, " + ", ".join(f"{c} text" for c in EMPLOYEE_COLUMNS) + ")"))
    for row in employees:
        s.execute(text("insert into forecast_employees values (:o, " + ", ".join(f":c{i}" for i in range(len(row))) + ")"),
                  {"o": ORG, **{f"c{i}": v for i, v in enumerate(row)}})
    s.execute(text("create table workforce_hiring_ramp_assumptions (organization_id text, version text, department text, "
                   "role text, level text, month_offset integer, productivity_pct text)"))
    rows = [("Forecast", "*", "*", n, k, pct) for n, k, pct in curves]
    if stale:
        rows.append(("Forecast", "Sales", "Account Executive", "L3", 0, "0.25"))
    for row in rows:
        s.execute(text("insert into workforce_hiring_ramp_assumptions values (:o, :v, :d, :r, :l, :k, :p)"),
                  dict(zip(("o", "v", "d", "r", "l", "k", "p"), (ORG, *row))))
    s.execute(text("create table actual_sales_quotas (organization_id text, period text, employee_id text, rep_name text, "
                   "role text, quota_type text, hire_period text, productivity_ramp_months text, ramp_pct text)"))
    for row in (("2026-11", "E2", "Bob", "Senior Account Executive", "Bookings ARR", "2026-11", "3", bob_month_1),
                ("2026-12", "E2", "Bob", "Senior Account Executive", "Bookings ARR", "2026-11", "3", "0.6"),
                ("2026-01", "E1", "Ann", "Account Executive", "Bookings ARR", "2025-03", "3", "1.0"),
                ("2026-01", "E3", "Sid", "Sales Development Rep", "Pipeline ARR", "2024-01", "2", "1.0"),
                ("2026-01", "E9", "Ops", "Sales Operations Analyst", "Non-Quota", "2024-01", "2", "1.0")):
        s.execute(text("insert into actual_sales_quotas values (:o, :p, :e, :n, :r, :t, :h, :m, :pct)"),
                  dict(zip(("o", "p", "e", "n", "r", "t", "h", "m", "pct"), (ORG, *row))))
    return s


def _run(db, answers=None, measured=None):
    return sales_team(db, uuid.UUID(ORG), answers if answers is not None else {"7.25": "80"}, "2026-12", measured)


def test_team_at_the_forecast_year_end() -> None:
    out = _run(_db(), measured={"closer_attainment": 1.12, "months": ["2026-01", "2026-12"]})
    assert [e["employee_id"] for e in out["employees"]] == ["E1", "E2", "E3", "E4"]
    bob = out["employees"][1]
    assert (bob["territory"], bob["tenure_months"], bob["quota_type"], bob["annual_quota_arr"], bob["commission_target"]) == \
        ("West", 2, "Bookings ARR", 1100000.0, 110000.0)
    assert out["heads"] == [
        {"department": "Customer Success", "role": "Customer Success Manager", "territory": "East", "quota_type": None,
         "heads": 1, "ramping": 0, "annual_quota_arr": 450000.0},
        {"department": "Sales", "role": "Account Executive", "territory": "East", "quota_type": "Bookings ARR",
         "heads": 1, "ramping": 0, "annual_quota_arr": 800000.0},
        {"department": "Sales", "role": "Sales Development Rep", "territory": "East", "quota_type": "Pipeline ARR",
         "heads": 1, "ramping": 0, "annual_quota_arr": 300000.0},
        {"department": "Sales", "role": "Senior Account Executive", "territory": "West", "quota_type": "Bookings ARR",
         "heads": 1, "ramping": 1, "annual_quota_arr": 1100000.0},
    ]
    assert out["ramp"] == {"version": "Forecast", "curves": {"2": [0.5, 1.0], "3": [0.25, 0.6, 1.0]}}
    assert out["attainment"] == {"expected": 0.8, "measured": 1.12, "measured_months": ["2026-01", "2026-12"]}
    assert out["checks"] == [{"id": "ramp_vs_quotas", "status": "pass",
                              "finding": "4 of 4 Actual quota rows apply the Forecast ramp curve"}]
    assert out["missing"] == []


def test_ramp_curve_holds_full_quota_after_it_ends() -> None:
    assert [ramp_pct([0.25, 0.6, 1.0], k) for k in (0, 1, 2, 3, 9)] == [0.0, 0.25, 0.6, 1.0, 1.0]


def test_stale_and_mismatched_ramp_is_flagged_not_used() -> None:
    employees = EMPLOYEES[:1] + (EMPLOYEES[1][:11] + ("4",) + EMPLOYEES[1][12:],) + EMPLOYEES[2:]
    out = _run(_db(employees=employees, stale=True, bob_month_1="0.33"))
    assert out["ramp"]["curves"] == {"2": [0.5, 1.0], "3": [0.25, 0.6, 1.0]}
    assert out["checks"][0]["status"] == "conflict"
    assert "Bob 2026-11 (3-month ramp, month 1): quota file 33%, curve 25%" in out["checks"][0]["finding"]
    assert any("not keyed by ramp length, not used: Sales / Account Executive / L3" in m for m in out["missing"])
    assert any("no 4-month ramp curve: E2 (Senior Account Executive)" in m for m in out["missing"])


def test_only_stale_ramp_rows_leave_every_closer_without_a_curve() -> None:
    out = _run(_db(curves=(), stale=True))
    assert out["ramp"]["curves"] == {} and out["checks"] == []
    assert any("no 3-month ramp curve: E1 (Account Executive), E2 (Senior Account Executive)" in m for m in out["missing"])
    assert any("no 2-month ramp curve: E3 (Sales Development Rep)" in m for m in out["missing"])


def test_nothing_loaded_is_reported_not_assumed() -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    out = _run(Session(create_engine("sqlite://")), answers={})
    assert out["employees"] == [] and out["heads"] == [] and out["ramp"] == {"version": None, "curves": {}}
    assert out["attainment"]["expected"] is None
    for table in ("forecast_employees", "actual_sales_quotas", "workforce_hiring_ramp_assumptions", "7.25"):
        assert any(table in m for m in out["missing"]), table
