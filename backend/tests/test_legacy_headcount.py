"""Tests for legacy headcount_plan overlay on workforce plan."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.demo_finance import ForecastHeadcountPlan, HeadcountPlan
from app.models.organization import Organization
from app.models.workforce import WorkforceEmployee
from app.services.workforce import service
from app.services.workforce.legacy_headcount import merge_legacy_headcount, _snapshot_from_mapping
from app.services.workforce.validation_service import run_workforce_validations


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Organization.__table__,
            WorkforceEmployee.__table__,
            HeadcountPlan.__table__,
            ForecastHeadcountPlan.__table__,
        ],
    )
    factory = sessionmaker(bind=engine)
    session = factory()
    org_id = uuid.uuid4()
    session.add(Organization(id=org_id, name="Test Co"))
    session.commit()
    yield session, org_id
    session.close()


@pytest.fixture()
def db_session_with_physical(db_session):
    session, org_id = db_session
    session.execute(
        text(
            """
            CREATE TABLE actual_headcount_plan (
                organization_id TEXT NOT NULL,
                source_row_number INTEGER NOT NULL,
                period TEXT,
                department TEXT,
                headcount_beginning TEXT,
                new_hires TEXT,
                attrition TEXT,
                headcount_ending TEXT,
                open_requisitions TEXT,
                monthly_gaap_payroll_cost TEXT,
                monthly_sbc TEXT,
                quota_capacity_arr TEXT,
                ramped_quota_capacity_arr TEXT,
                PRIMARY KEY (organization_id, source_row_number)
            )
            """
        )
    )
    session.commit()
    return session, org_id


def test_parse_headcount_flow_from_actual_csv_shape() -> None:
    snap = _snapshot_from_mapping(
        {
            "period": "2026-05",
            "department": "R&D",
            "headcount_beginning": "35",
            "new_hires": "1",
            "attrition": "0",
            "headcount_ending": "36",
            "open_requisitions": "0",
            "monthly_gaap_payroll_cost": "694313.33",
            "monthly_sbc": "86416.67",
            "ramped_quota_capacity_arr": "0",
        }
    )
    assert snap is not None
    assert snap.department == "R&D"
    assert snap.headcount_beginning == Decimal("35.0000")
    assert snap.new_hires == Decimal("1.0000")
    assert snap.attrition == Decimal("0.0000")
    assert snap.headcount_ending == Decimal("36.0000")
    assert snap.people_cost == Decimal("694313.33")


def test_legacy_headcount_plan_fills_actual_when_no_employees(db_session) -> None:
    session, org_id = db_session
    session.add(
        HeadcountPlan(
            organization_id=org_id,
            version="Actual",
            period=date(2026, 5, 1),
            department="Sales",
            headcount=Decimal("28"),
            monthly_payroll_cost=Decimal("437508.33"),
        )
    )
    session.commit()

    plan = service.build_workforce_plan(
        session,
        org_id,
        scenario="Actual",
        start_period=date(2026, 5, 1),
        end_period=date(2026, 5, 1),
        persist=False,
    )
    assert len(plan.period_summary) == 1
    row = plan.period_summary[0]
    assert row.filled_headcount == Decimal("28.0000")
    assert row.headcount_ending_fte == Decimal("28.0000")
    assert row.total_headcount_fte == Decimal("28.0000")
    assert any(v.validation_name == "legacy_headcount_plan_in_use" for v in plan.validations)


def test_physical_actual_headcount_plan_table_is_used(db_session_with_physical) -> None:
    session, org_id = db_session_with_physical
    session.execute(
        text(
            """
            INSERT INTO actual_headcount_plan
            (organization_id, source_row_number, period, department,
             headcount_beginning, new_hires, attrition, headcount_ending,
             open_requisitions, monthly_gaap_payroll_cost, monthly_sbc,
             quota_capacity_arr, ramped_quota_capacity_arr)
            VALUES (:org, 1, '2026-05', 'Sales', '28', '0', '0', '28', '0',
                    '437508.33', '25000', '16600000', '16400000')
            """
        ),
        {"org": str(org_id)},
    )
    session.commit()

    plan = service.build_workforce_plan(
        session,
        org_id,
        scenario="Actual",
        start_period=date(2026, 5, 1),
        end_period=date(2026, 5, 1),
        persist=False,
    )
    assert len(plan.period_summary) == 1
    row = plan.period_summary[0]
    assert row.department == "Sales"
    assert row.headcount_beginning_fte == Decimal("28.0000")
    assert row.filled_headcount == Decimal("28.0000")
    assert row.total_people_cost_monthly == Decimal("437508.33")


def test_legacy_plan_replaces_engine_departments_for_covered_periods() -> None:
    engine_rows = [
        {
            "period": date(2026, 5, 1),
            "department": "Engineering",
            "filled_headcount": Decimal("111"),
            "planned_hire_headcount": Decimal("0"),
            "total_headcount_fte": Decimal("111"),
            "base_payroll_monthly": Decimal("0"),
            "bonus_monthly": Decimal("0"),
            "commission_monthly": Decimal("0"),
            "equity_sbc_monthly": Decimal("0"),
            "benefits_load_monthly": Decimal("0"),
            "total_people_cost_monthly": Decimal("0"),
            "quota_capacity_arr": Decimal("0"),
            "productive_quota_capacity_arr": Decimal("0"),
        }
    ]
    snap = _snapshot_from_mapping(
        {
            "period": "2026-05",
            "department": "R&D",
            "headcount_beginning": "35",
            "new_hires": "1",
            "attrition": "0",
            "headcount_ending": "36",
        }
    )
    assert snap is not None
    merged = merge_legacy_headcount(engine_rows, [snap])
    assert len(merged) == 1
    assert merged[0]["department"] == "R&D"
    assert merged[0]["filled_headcount"] == Decimal("36.0000")


def test_legacy_headcount_overlays_employee_row_count(db_session) -> None:
    session, org_id = db_session
    session.add(
        WorkforceEmployee(
            organization_id=org_id,
            version="Forecast",
            employee_id="E1",
            department="Sales",
            role="AE",
            employment_status="Active",
            hire_date=date(2025, 1, 1),
            salary_annual=Decimal("120000"),
        )
    )
    session.add(
        ForecastHeadcountPlan(
            organization_id=org_id,
            version="Forecast",
            period=date(2026, 5, 1),
            department="Sales",
            headcount=Decimal("45"),
            monthly_payroll_cost=Decimal("450000"),
        )
    )
    session.commit()

    plan = service.build_workforce_plan(
        session,
        org_id,
        scenario="Forecast",
        start_period=date(2026, 5, 1),
        end_period=date(2026, 5, 1),
        persist=False,
    )
    sales = next(r for r in plan.period_summary if r.department == "Sales")
    assert sales.filled_headcount == Decimal("45.0000")
    assert sales.total_headcount_fte == Decimal("45.0000")


def test_validation_passes_when_legacy_headcount_present(db_session) -> None:
    session, org_id = db_session
    session.add(
        HeadcountPlan(
            organization_id=org_id,
            version="Actual",
            period=date(2026, 5, 1),
            department="Sales",
            headcount=Decimal("28"),
        )
    )
    session.commit()

    result = run_workforce_validations(
        session,
        org_id,
        scenario="Actual",
        start_period=date(2026, 5, 1),
        end_period=date(2026, 5, 1),
    )
    assert not any(c.validation_name == "workforce_source_data_missing" for c in result.checks)
