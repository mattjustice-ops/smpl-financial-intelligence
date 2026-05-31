"""Workforce finance integration helpers."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.demo_finance import (
    ForecastCashCollections,
    ForecastHeadcountPlan,
    ForecastIncomeStatement,
    ForecastQuotaCapacity,
)
from app.models.organization import Organization
from app.models.workforce import (
    WorkforceCompensationBand,
    WorkforceDepartmentAllocationRule,
    WorkforceEmployee,
    WorkforceHiringRampAssumption,
    WorkforceOpenRequisition,
    WorkforcePeriodSummary,
)
from app.services.management_pl.gl_hierarchy import GlEntry
from app.services.workforce import integration


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
            ForecastCashCollections.__table__,
            ForecastHeadcountPlan.__table__,
            ForecastIncomeStatement.__table__,
            ForecastQuotaCapacity.__table__,
        ],
    )
    factory = sessionmaker(bind=engine)
    session = factory()
    org_id = uuid.uuid4()
    session.add(Organization(id=org_id, name="Test Co"))
    session.commit()
    yield session, org_id
    session.close()


def _seed_workforce(session: Session, org_id: uuid.UUID) -> None:
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
            bonus_annual=Decimal("12000"),
            commission_annual=Decimal("50000"),
            equity_sbc_annual=Decimal("10000"),
            benefits_load_pct=Decimal("0.25"),
            quota_capacity_arr=Decimal("800000"),
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
            bonus_target_pct=Decimal("0.10"),
            commission_annual=Decimal("50000"),
            equity_sbc_annual=Decimal("10000"),
            benefits_load_pct=Decimal("0.25"),
            default_quota_capacity_arr=Decimal("800000"),
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


def test_pnl_overlay_and_payroll_gl_filter(db_session) -> None:
    session, org_id = db_session
    _seed_workforce(session, org_id)
    overlay = integration.pnl_overlay_by_period(
        session, org_id, scenario="Forecast", start_period=date(2026, 1, 1), end_period=date(2026, 1, 1)
    )
    assert overlay["2026-01"]["sales_and_marketing"] > Decimal("10000")

    entry = GlEntry(
        period="2026-06",
        version="Forecast",
        account_number="6100",
        account_name="Sales Payroll",
        account_group="Payroll",
        section_key="sales_and_marketing",
        department="Sales & Marketing",
        source_department="Sales",
        expense_type="Payroll",
        amount=Decimal("-50000"),
    )
    assert integration.is_payroll_gl_entry(entry)
    filtered = integration.exclude_payroll_gl_entries([entry], {"2026-06"})
    assert filtered == []


def test_resolve_payroll_cash_out_prefers_workforce(db_session) -> None:
    session, org_id = db_session
    _seed_workforce(session, org_id)
    amount, source = integration.resolve_payroll_cash_out(
        session,
        org_id,
        period=date(2026, 1, 1),
        manual_value=Decimal("999"),
    )
    assert source == "workforce_derived"
    assert amount > Decimal("10000")
    assert amount != Decimal("999")


def test_gtm_capacity_falls_back_to_forecast_quota(db_session) -> None:
    session, org_id = db_session
    session.add(
        ForecastQuotaCapacity(
            organization_id=org_id,
            version="Forecast",
            period=date(2026, 3, 1),
            region="US",
            quota_carrying_reps=Decimal("5"),
            quota_capacity_arr=Decimal("2500000"),
            expected_bookings_arr=Decimal("2000000"),
        )
    )
    session.commit()
    rows = integration.load_gtm_quota_capacity(
        session,
        org_id,
        scenario="Forecast",
        start_period=date(2026, 1, 1),
        end_period=date(2026, 12, 31),
    )
    assert rows
    assert rows[0]["source"] == "forecast_quota_capacity"
    assert rows[0]["quota_capacity_arr"] == Decimal("2500000")


def test_load_headcount_from_workforce_summary(db_session) -> None:
    session, org_id = db_session
    session.add(
        WorkforcePeriodSummary(
            organization_id=org_id,
            version="Forecast",
            period=date(2026, 5, 1),
            department="Sales",
            filled_headcount=Decimal("10"),
            planned_hire_headcount=Decimal("2"),
            total_headcount_fte=Decimal("12"),
            base_payroll_monthly=Decimal("100000"),
            bonus_monthly=Decimal("10000"),
            commission_monthly=Decimal("50000"),
            equity_sbc_monthly=Decimal("5000"),
            benefits_load_monthly=Decimal("25000"),
            total_people_cost_monthly=Decimal("190000"),
            quota_capacity_arr=Decimal("8000000"),
            productive_quota_capacity_arr=Decimal("7200000"),
        )
    )
    session.commit()
    rows = integration.load_headcount_from_workforce_summary(session, org_id, "2026-01", "2026-12")
    assert len(rows) == 1
    assert rows[0]["headcount"] == Decimal("12")
    assert rows[0]["source_table"] == "workforce_period_summary"
