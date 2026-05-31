"""Cash forecast workforce payroll integration."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.demo_finance import ForecastCashCollections, ForecastHeadcountPlan, ForecastIncomeStatement
from app.models.organization import Organization
from app.models.workforce import (
    WorkforceCompensationBand,
    WorkforceDepartmentAllocationRule,
    WorkforceEmployee,
    WorkforceHiringRampAssumption,
    WorkforceOpenRequisition,
)
from app.services.driver_forecast.forecast_cash_flow_engine import build_cash_flow_forecast
from app.services.workforce.integration import resolve_payroll_cash_out


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
            ForecastCashCollections.__table__,
            ForecastHeadcountPlan.__table__,
            ForecastIncomeStatement.__table__,
        ],
    )
    factory = sessionmaker(bind=engine)
    session = factory()
    org_id = uuid.uuid4()
    session.add(Organization(id=org_id, name="Test Co"))
    session.commit()
    yield session, org_id
    session.close()


def _seed_workforce(session, org_id) -> None:
    session.add(
        WorkforceEmployee(
            organization_id=org_id,
            version="Forecast",
            employee_id="E1",
            department="Sales",
            role="AE",
            level="L3",
            region="US",
            hire_date=date(2025, 1, 1),
            employment_status="Active",
            salary_annual=Decimal("120000"),
            benefits_load_pct=Decimal("0.25"),
        )
    )
    session.add(
        WorkforceCompensationBand(
            organization_id=org_id,
            version="Forecast",
            department="Sales",
            role="AE",
            level="L3",
            region="US",
            base_salary_annual=Decimal("120000"),
            benefits_load_pct=Decimal("0.25"),
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


def test_resolve_payroll_falls_back_to_manual_csv(db_session) -> None:
    session, org_id = db_session
    session.add(
        ForecastCashCollections(
            organization_id=org_id,
            version="Forecast",
            period=date(2026, 6, 1),
            payroll_cash_out=Decimal("45000"),
        )
    )
    session.commit()
    amount, source = resolve_payroll_cash_out(
        session,
        org_id,
        period=date(2026, 6, 1),
        manual_value=Decimal("45000"),
    )
    assert source == "forecast_cash_collections"
    assert amount == Decimal("45000.00")


def test_cash_flow_forecast_uses_workforce_payroll(db_session) -> None:
    session, org_id = db_session
    _seed_workforce(session, org_id)
    rows = build_cash_flow_forecast(
        session,
        org_id,
        start_period=date(2026, 6, 1),
        end_period=date(2026, 6, 30),
        assumptions={},
    )
    assert len(rows) == 1
    assert rows[0]["payroll_source"] == "workforce_derived"
    assert abs(rows[0]["payroll_cash_out"]) > Decimal("0")
