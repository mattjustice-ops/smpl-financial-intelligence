"""Workforce validation service tests."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.demo_finance import ForecastHeadcountPlan, ForecastIncomeStatement, ForecastQuotaCapacity
from app.models.organization import Organization
from app.models.workforce import (
    WorkforceCompensationBand,
    WorkforceDepartmentAllocationRule,
    WorkforceEmployee,
    WorkforceHiringRampAssumption,
    WorkforceOpenRequisition,
)
from app.services.workforce import validation_service


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


def test_validation_warns_when_source_missing(db_session) -> None:
    session, org_id = db_session
    result = validation_service.run_workforce_validations(
        session,
        org_id,
        scenario="Forecast",
        start_period=date(2026, 1, 1),
        end_period=date(2026, 12, 31),
    )
    assert result.status in ("warning", "fail")
    assert any(c.validation_name == "workforce_source_data_missing" for c in result.checks)


def test_validation_passes_with_derived_payroll(db_session) -> None:
    session, org_id = db_session
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
    result = validation_service.run_workforce_validations(
        session,
        org_id,
        scenario="Forecast",
        start_period=date(2026, 1, 1),
        end_period=date(2026, 1, 31),
    )
    assert any(c.validation_name == "workforce_payroll_derived" and c.status == "pass" for c in result.checks)
    assert any(c.validation_name == "workforce_pnl_overlay_ready" for c in result.checks)
