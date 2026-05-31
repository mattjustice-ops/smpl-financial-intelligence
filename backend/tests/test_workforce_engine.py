"""Workforce operating model engine tests."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.organization import Organization
from app.models.workforce import (
    WorkforceCompensationBand,
    WorkforceDepartmentAllocationRule,
    WorkforceEmployee,
    WorkforceHiringRampAssumption,
    WorkforceOpenRequisition,
)
from app.services.workforce.engine import WorkforcePlanningEngine, q_money


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
        ],
    )
    factory = sessionmaker(bind=engine)
    session = factory()
    org_id = uuid.uuid4()
    session.add(Organization(id=org_id, name="Test Co"))
    session.commit()
    yield session, org_id
    session.close()


def _seed_minimal(session: Session, org_id: uuid.UUID) -> None:
    session.add(
        WorkforceEmployee(
            organization_id=org_id,
            version="Forecast",
            employee_id="E1",
            department="Sales",
            role="Account Executive",
            level="L3",
            region="US",
            hire_date=date(2025, 1, 1),
            employment_status="Active",
            salary_annual=Decimal("120000"),
            bonus_annual=Decimal("18000"),
            commission_annual=Decimal("80000"),
            equity_sbc_annual=Decimal("12000"),
            benefits_load_pct=Decimal("0.25"),
            quota_capacity_arr=Decimal("900000"),
        )
    )
    session.add(
        WorkforceCompensationBand(
            organization_id=org_id,
            version="Forecast",
            department="Sales",
            role="Account Executive",
            level="L3",
            region="US",
            base_salary_annual=Decimal("125000"),
            bonus_target_pct=Decimal("0.15"),
            commission_annual=Decimal("90000"),
            equity_sbc_annual=Decimal("15000"),
            benefits_load_pct=Decimal("0.25"),
            default_quota_capacity_arr=Decimal("900000"),
        )
    )
    session.add(
        WorkforceDepartmentAllocationRule(
            organization_id=org_id,
            version="Forecast",
            rule_id="R1",
            department="Sales",
            pnl_line="sales_and_marketing",
            allocation_pct=Decimal("1"),
        )
    )
    session.commit()


def test_derived_payroll_not_zero(db_session) -> None:
    session, org_id = db_session
    _seed_minimal(session, org_id)
    engine = WorkforcePlanningEngine(session, org_id, version="Forecast")
    result = engine.build(date(2026, 1, 1), date(2026, 1, 1))
    sales = [r for r in result.period_rows if r["department"] == "Sales"]
    assert len(sales) == 1
    assert sales[0]["total_people_cost_monthly"] > Decimal("10000")
    assert sales[0]["filled_headcount"] == Decimal("1.0000")


def test_open_req_adds_planned_hire_fte(db_session) -> None:
    session, org_id = db_session
    _seed_minimal(session, org_id)
    session.add(
        WorkforceOpenRequisition(
            organization_id=org_id,
            version="Forecast",
            req_id="REQ1",
            role="Account Executive",
            department="Sales",
            planned_start_date=date(2026, 6, 1),
            approved_status="Approved",
            requisition_type="new",
            level="L3",
            region="US",
        )
    )
    session.commit()
    engine = WorkforcePlanningEngine(session, org_id, version="Forecast")
    result = engine.build(date(2026, 5, 1), date(2026, 6, 1))
    may = next(r for r in result.period_rows if r["period"] == date(2026, 5, 1) and r["department"] == "Sales")
    june = next(r for r in result.period_rows if r["period"] == date(2026, 6, 1) and r["department"] == "Sales")
    assert may["planned_hire_headcount"] == Decimal("0")
    assert june["planned_hire_headcount"] == Decimal("1.0000")
    assert june["total_headcount_fte"] == Decimal("2.0000")


def test_operating_metrics_include_planned_starts(db_session) -> None:
    session, org_id = db_session
    _seed_minimal(session, org_id)
    session.add(
        WorkforceOpenRequisition(
            organization_id=org_id,
            version="Forecast",
            req_id="REQ1",
            role="Account Executive",
            department="Sales",
            planned_start_date=date(2026, 3, 1),
            approved_status="Approved",
            requisition_type="new",
            level="L3",
            region="US",
        )
    )
    session.commit()
    from app.services.workforce import service

    plan = service.build_workforce_plan(
        session,
        org_id,
        scenario="Forecast",
        start_period=date(2026, 1, 1),
        end_period=date(2026, 5, 1),
        persist=False,
    )
    march = next(m for m in plan.operating_metrics if m.period == date(2026, 3, 1))
    may = next(m for m in plan.operating_metrics if m.period == date(2026, 5, 1))
    assert march.planned_starts_fte == Decimal("1.0000")
    assert may.planned_hire_headcount_fte == Decimal("1.0000")
    assert may.total_headcount_fte == Decimal("2.0000")


def test_ramp_reduces_early_month_payroll(db_session) -> None:
    session, org_id = db_session
    session.add(
        WorkforceOpenRequisition(
            organization_id=org_id,
            version="Forecast",
            req_id="REQ1",
            role="Account Executive",
            department="Sales",
            planned_start_date=date(2026, 6, 1),
            approved_status="Approved",
            requisition_type="new",
            level="L3",
            region="US",
        )
    )
    session.add(
        WorkforceHiringRampAssumption(
            organization_id=org_id,
            version="Forecast",
            department="Sales",
            role="Account Executive",
            level="L3",
            month_offset=0,
            productivity_pct=Decimal("0.25"),
        )
    )
    session.add(
        WorkforceCompensationBand(
            organization_id=org_id,
            version="Forecast",
            department="Sales",
            role="Account Executive",
            level="L3",
            region="US",
            base_salary_annual=Decimal("120000"),
            bonus_target_pct=Decimal("0"),
            commission_annual=Decimal("0"),
            equity_sbc_annual=Decimal("0"),
            benefits_load_pct=Decimal("0"),
            default_quota_capacity_arr=Decimal("0"),
        )
    )
    session.commit()
    engine = WorkforcePlanningEngine(session, org_id, version="Forecast")
    result = engine.build(date(2026, 6, 1), date(2026, 7, 1))
    june = next(r for r in result.period_rows if r["period"] == date(2026, 6, 1))
    july = next(r for r in result.period_rows if r["period"] == date(2026, 7, 1))
    assert june["total_people_cost_monthly"] < july["total_people_cost_monthly"]


def test_pnl_allocation_uses_rules(db_session) -> None:
    session, org_id = db_session
    _seed_minimal(session, org_id)
    engine = WorkforcePlanningEngine(session, org_id, version="Forecast")
    result = engine.build(date(2026, 1, 1), date(2026, 1, 1))
    assert any(a["pnl_line"] == "sales_and_marketing" for a in result.pnl_allocations)
    sm = next(a for a in result.pnl_allocations if a["pnl_line"] == "sales_and_marketing")
    sales_cost = next(r["total_people_cost_monthly"] for r in result.period_rows if r["department"] == "Sales")
    assert sm["amount"] == q_money(sales_cost)
