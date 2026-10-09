"""Workforce plans: loaded roster for heads, GL for payroll dollars, roster cost vs GL as a check."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.demo_finance import ForecastHeadcountPlan, ForecastIncomeStatement
from app.models.organization import Organization
from app.models.workforce import (
    WorkforceCompensationBand,
    WorkforceDepartmentAllocationRule,
    WorkforceEmployee,
    WorkforceHiringRampAssumption,
    WorkforceOpenRequisition,
    WorkforcePeriodSummary,
)
from app.services.workforce import gl_payroll, roster, service
from app.services.workforce.engine import WorkforcePlanningEngine


def _employee(employee_id: str, department: str, status: str = "Active", hire: str = "2025-01-01", **extra) -> dict:
    row = {
        "employee_id": employee_id,
        "department": department,
        "role": "Account Executive",
        "level": "L4",
        "region": "East",
        "employment_status": status,
        "hire_date": hire,
        "termination_date": None,
        "base_salary": "120000",
        "variable_comp": "60000",
        "commission_target": "60000",
        "equity_sbc_annual": "12000",
        "benefits_load_pct": "0.20",
        "fully_loaded_cash_cost": "216000.0",
        "annual_quota_arr": "800000",
        "productivity_ramp_months": "4",
    }
    row.update(extra)
    return row


def _gl(
    period: str,
    expense_type: str,
    amount: float,
    department: str,
    statement: str = "Income Statement",
    category: str = "Operating Expense",
) -> dict:
    return {
        "period": period,
        "statement": statement,
        "statement_category": category,
        "account_group": "Labor",
        "expense_type": expense_type,
        "account_name": expense_type,
        "department": department,
        "amount": amount,
    }


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Organization.__table__,
            WorkforceEmployee.__table__,
            WorkforceOpenRequisition.__table__,
            WorkforceHiringRampAssumption.__table__,
            WorkforceCompensationBand.__table__,
            WorkforceDepartmentAllocationRule.__table__,
            WorkforcePeriodSummary.__table__,
            ForecastHeadcountPlan.__table__,
            ForecastIncomeStatement.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    org_id = uuid.uuid4()
    session.add(Organization(id=org_id, name="Test Co"))
    session.commit()
    yield session, org_id
    session.close()


def test_loaded_row_mapping_does_not_add_commission_twice() -> None:
    emp = roster.employee_from_loaded_row(_employee("E1", "Sales"))
    assert emp.salary_annual == Decimal("120000")
    assert emp.bonus_annual == Decimal("60000")
    assert emp.commission_annual == Decimal("0")
    assert emp.annual_cash_cost == Decimal("216000.0")
    assert emp.quota_capacity_arr == Decimal("800000")
    assert emp.months_to_full_productivity == 4
    assert not emp.planned
    assert roster.employee_from_loaded_row(_employee("E2", "Sales", status="Planned")).planned


def test_build_gl_payroll_takes_payroll_types_only() -> None:
    payroll = gl_payroll.build_gl_payroll(
        [
            _gl("2026-06", "Salaries and Wages", 100, "Sales"),
            _gl("2026-06", "Benefits", 10, "Sales"),
            _gl("2026-06", "Payroll Taxes", 5, "Sales"),
            _gl("2026-06", "Commissions", 20, "Sales"),
            _gl("2026-06", "Software", 999, "Sales"),
            _gl("2026-06", "Equity", -50, "Sales", statement="Balance Sheet"),
            _gl("2026-06", "Salaries and Wages", 70, "Engineering"),
        ]
    )
    sales = payroll.by_department[(date(2026, 6, 1), "Sales")]
    assert (sales.wages, sales.benefits, sales.commissions, sales.total) == (
        Decimal("100"),
        Decimal("15"),
        Decimal("20"),
        Decimal("135"),
    )
    assert payroll.by_pnl_line[(date(2026, 6, 1), "sales_and_marketing")] == Decimal("135")
    assert payroll.by_pnl_line[(date(2026, 6, 1), "research_and_development")] == Decimal("70")


def test_build_gl_payroll_counts_bonus_retirement_severance_and_cogs_labor() -> None:
    payroll = gl_payroll.build_gl_payroll(
        [
            _gl("2026-06", "Salaries and Wages", 100, "Finance"),
            _gl("2026-06", "Bonus", 12, "Finance"),
            _gl("2026-06", "Retirement Match", 4, "Finance"),
            _gl("2026-06", "Severance", 30, "Finance"),
            _gl("2026-06", "Labor", 500, "Support", category="Cost of Revenue"),
        ]
    )
    period = date(2026, 6, 1)
    finance = payroll.by_department[(period, "Finance")]
    assert (finance.wages, finance.bonus, finance.benefits, finance.total) == (
        Decimal("130"),
        Decimal("12"),
        Decimal("4"),
        Decimal("146"),
    )
    assert payroll.by_department[(period, "Support")].wages == Decimal("500")
    assert payroll.by_pnl_line[(period, "cost_of_revenue")] == Decimal("500")
    assert payroll.by_pnl_line[(period, "general_and_administrative")] == Decimal("146")

    rows = [
        {
            "period": period,
            "department": "Finance",
            "filled_headcount": Decimal("1"),
            "planned_hire_headcount": Decimal("0"),
            "total_headcount_fte": Decimal("1"),
            "quota_capacity_arr": Decimal("0"),
            "productive_quota_capacity_arr": Decimal("0"),
        }
    ]
    out = {r["department"]: r for r in gl_payroll.apply_gl_payroll(rows, payroll, [period])}
    assert out["Finance"]["bonus_monthly"] == Decimal("12.00")
    assert out["Finance"]["total_people_cost_monthly"] == Decimal("146.00")


def test_leavers_count_by_date_at_month_end() -> None:
    leaver = roster.employee_from_loaded_row(
        _employee("E9", "Sales", status="Terminated", hire="2025-01-15", termination_date="2026-03-31")
    )
    assert leaver.counted
    assert roster.on_roster(leaver, date(2025, 1, 1))
    assert roster.on_roster(leaver, date(2026, 2, 1))
    assert not roster.on_roster(leaver, date(2026, 3, 1))
    undated = roster.employee_from_loaded_row(_employee("E10", "Sales", status="Terminated"))
    assert not undated.counted


def test_engine_counts_leavers_until_their_exit_month(db_session, monkeypatch) -> None:
    session, org_id = db_session
    loaded = [
        _employee("E1", "Sales"),
        _employee("E2", "Sales", status="Terminated", termination_date="2026-02-10"),
    ]
    monkeypatch.setattr(roster, "_loaded_rows", lambda s, o, v: loaded if v == "Actual" else [])
    engine = WorkforcePlanningEngine(session, org_id, version="Actual")
    result = engine.build(date(2026, 1, 1), date(2026, 2, 1))
    sales = {r["period"]: r for r in result.period_rows if r["department"] == "Sales"}
    assert sales[date(2026, 1, 1)]["filled_headcount"] == Decimal("2")
    assert sales[date(2026, 2, 1)]["filled_headcount"] == Decimal("1")


def test_forecast_payroll_uses_actual_gl_for_months_without_forecast_gl(db_session, monkeypatch) -> None:
    session, org_id = db_session
    rows = {
        "Actual": [_gl("2026-06", "Salaries and Wages", 100, "Sales"), _gl("2026-07", "Salaries and Wages", 1, "Sales")],
        "Forecast": [_gl("2026-07", "Salaries and Wages", 200, "Sales")],
    }
    monkeypatch.setattr(gl_payroll, "fetch_gl_pl_rows", lambda db, org, version: rows.get(version, []))
    by_period = gl_payroll.gl_payroll_by_period(session, org_id, "Forecast")
    assert by_period == {date(2026, 6, 1): Decimal("100"), date(2026, 7, 1): Decimal("200")}


def test_apply_gl_payroll_replaces_cost_and_adds_gl_only_teams() -> None:
    period = date(2026, 6, 1)
    rows = [
        {
            "period": period,
            "department": "R&D",
            "filled_headcount": Decimal("36"),
            "planned_hire_headcount": Decimal("0"),
            "total_headcount_fte": Decimal("36"),
            "base_payroll_monthly": Decimal("500000"),
            "bonus_monthly": Decimal("1"),
            "commission_monthly": Decimal("1"),
            "equity_sbc_monthly": Decimal("1"),
            "benefits_load_monthly": Decimal("1"),
            "total_people_cost_monthly": Decimal("500004"),
            "quota_capacity_arr": Decimal("0"),
            "productive_quota_capacity_arr": Decimal("0"),
        }
    ]
    payroll = gl_payroll.build_gl_payroll([_gl("2026-06", "Salaries and Wages", 800000, "Engineering")])
    out = {r["department"]: r for r in gl_payroll.apply_gl_payroll(rows, payroll, [period])}
    assert out["R&D"]["total_people_cost_monthly"] == Decimal("0.00")
    assert out["R&D"]["total_headcount_fte"] == Decimal("36")
    assert out["Engineering"]["total_people_cost_monthly"] == Decimal("800000.00")
    assert out["Engineering"]["total_headcount_fte"] == Decimal("0")


def test_payroll_checks_compare_roster_cost_with_gl_by_team() -> None:
    periods = [date(2026, 6, 1), date(2026, 7, 1)]
    payroll = gl_payroll.build_gl_payroll(
        [_gl("2026-06", "Salaries and Wages", 30000, "Sales"), _gl("2026-06", "Salaries and Wages", 9000, "Engineering")]
    )
    roster_cost = {(date(2026, 6, 1), "Sales"): Decimal("18000"), (date(2026, 6, 1), "R&D"): Decimal("8000")}
    rows = [
        {"period": date(2026, 6, 1), "total_headcount_fte": Decimal("2")},
        {"period": date(2026, 7, 1), "total_headcount_fte": Decimal("2")},
    ]
    checks = gl_payroll.payroll_checks(rows, roster_cost, payroll, periods)
    missing = [c for c in checks if c["validation_name"] == "gl_payroll_missing"]
    assert len(missing) == 1 and "2026-07" in missing[0]["message"]
    by_team = {c["message"].split(":")[0]: c for c in checks if c["validation_name"] == "roster_cost_vs_gl_payroll"}
    assert set(by_team) == {"All teams", "Engineering", "R&D", "Sales"}
    assert by_team["All teams"]["expected_value"] == Decimal("39000.00")
    assert by_team["All teams"]["actual_value"] == Decimal("26000.00")
    assert by_team["Sales"]["variance"] == Decimal("-12000.00")
    assert by_team["R&D"]["expected_value"] == Decimal("0.00")
    assert all(c["status"] == "warning" for c in by_team.values())


def test_engine_reads_loaded_roster_and_counts_planned_rows_as_hires(db_session, monkeypatch) -> None:
    session, org_id = db_session
    session.add(
        WorkforceOpenRequisition(
            organization_id=org_id,
            version="Forecast",
            req_id="OLD-1",
            role="AE",
            department="Sales",
            planned_start_date=date(2026, 1, 1),
            approved_status="Approved",
        )
    )
    session.commit()
    loaded = [
        _employee("E1", "Sales"),
        _employee("E2", "Marketing"),
        _employee("P1", "Sales", status="Planned", hire="2026-03-01"),
    ]
    monkeypatch.setattr(roster, "_loaded_rows", lambda s, o, v: loaded if v == "Forecast" else [])
    engine = WorkforcePlanningEngine(session, org_id, version="Forecast")
    assert engine.roster_source == "forecast_employees"
    assert engine.requisitions == []
    result = engine.build(date(2026, 2, 1), date(2026, 3, 1))
    sales = {r["period"]: r for r in result.period_rows if r["department"] == "Sales"}
    assert sales[date(2026, 2, 1)]["filled_headcount"] == Decimal("1")
    assert sales[date(2026, 2, 1)]["planned_hire_headcount"] == Decimal("0")
    assert sales[date(2026, 3, 1)]["planned_hire_headcount"] == Decimal("1")


def test_plan_takes_payroll_from_gl_not_roster(db_session, monkeypatch) -> None:
    session, org_id = db_session
    monkeypatch.setattr(roster, "_loaded_rows", lambda s, o, v: [_employee("E1", "Sales")] if v == "Forecast" else [])
    monkeypatch.setattr(
        gl_payroll,
        "fetch_gl_pl_rows",
        lambda db, org, version: [_gl("2026-07", "Salaries and Wages", 25000, "Sales")] if version == "Forecast" else [],
    )
    plan = service.build_workforce_plan(
        session, org_id, scenario="Forecast", start_period=date(2026, 7, 1), end_period=date(2026, 7, 31), persist=False
    )
    sales = next(r for r in plan.period_summary if r.department == "Sales")
    assert sales.total_headcount_fte == Decimal("1")
    assert sales.total_people_cost_monthly == Decimal("25000.00")
    assert plan.operating_metrics[0].total_people_cost_monthly == Decimal("25000.00")
    assert "forecast_employees" in plan.data_sources and "gl_actuals" in plan.data_sources
    check = next(
        v for v in plan.validations if v.validation_name == "roster_cost_vs_gl_payroll" and v.message.startswith("Sales")
    )
    assert check.expected_value == Decimal("25000.00")
    assert check.actual_value == Decimal("18000.00")
    assert check.status == "warning"
