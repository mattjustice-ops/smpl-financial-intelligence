"""
Downstream feed adapters — workforce operating model → finance surfaces.

Payroll dollars in every feed are GL payroll (``gl_payroll``); head counts and quota come
from the roster and headcount plan.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.services.workforce.constants import PNL_LINE_MAP
from app.services.workforce.engine import month_start, q_money
from app.services.workforce.gl_payroll import GL_PAYROLL_SOURCE, gl_payroll_by_period
from app.services.workforce import service as workforce_service


def _normalize_scenario(scenario: str) -> str:
    s = scenario.strip()
    if s.lower() == "forecast":
        return "Forecast"
    if s.lower() == "budget":
        return "Budget"
    if s.lower() == "actual":
        return "Actual"
    return s


def payroll_by_department(
    session: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: date,
    end_period: date,
) -> list[dict[str, Any]]:
    """Monthly GL payroll and roster head count by department."""
    plan = workforce_service.build_workforce_plan(
        session, organization_id, scenario=scenario, start_period=start_period, end_period=end_period, persist=False
    )
    return [
        {
            "period": row.period,
            "department": row.department,
            "headcount_fte": row.total_headcount_fte,
            "monthly_payroll_cost": row.total_people_cost_monthly,
            "total_people_cost": row.total_people_cost_monthly,
            "source": GL_PAYROLL_SOURCE,
        }
        for row in plan.period_summary
    ]


def pnl_people_cost_lines(
    session: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: date,
    end_period: date,
) -> list[dict[str, Any]]:
    """GL payroll by income statement line."""
    plan = workforce_service.build_workforce_plan(
        session, organization_id, scenario=scenario, start_period=start_period, end_period=end_period, persist=False
    )
    out: list[dict[str, Any]] = []
    for row in plan.pnl_allocations:
        key = row.pnl_line.strip().lower().replace(" ", "_")
        out.append(
            {
                "period": row.period,
                "pnl_line": PNL_LINE_MAP.get(key, row.pnl_line),
                "amount": row.amount,
                "source": GL_PAYROLL_SOURCE,
            }
        )
    return out


def cash_payroll_outflow(
    session: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: date,
    end_period: date,
    payroll_timing_days: int = 0,
) -> list[dict[str, Any]]:
    """
    Cash payroll outflow schedule from GL payroll, excluding commissions (their own cash line).
    Timing shift is a simple month lag placeholder until payroll calendar rules exist.
    """
    start, end = month_start(start_period), month_start(end_period)
    by_period = {
        period: q_money(amount)
        for period, amount in gl_payroll_by_period(
            session, organization_id, _normalize_scenario(scenario), include_commissions=False
        ).items()
        if start <= period <= end
    }
    return [
        {
            "period": period,
            "payroll_cash_out": amount,
            "source": GL_PAYROLL_SOURCE,
            "payroll_timing_days": payroll_timing_days,
        }
        for period, amount in sorted(by_period.items())
    ]


def gtm_quota_capacity_feed(
    session: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: date,
    end_period: date,
) -> list[dict[str, Any]]:
    """Sales/Marketing productive quota capacity from workforce model."""
    plan = workforce_service.build_workforce_plan(
        session, organization_id, scenario=scenario, start_period=start_period, end_period=end_period, persist=False
    )
    return [
        {
            "period": row.period,
            "region": "All",
            "quota_carrying_reps": row.quota_carrying_reps_fte,
            "quota_capacity_arr": row.quota_capacity_arr,
            "productive_quota_capacity_arr": row.productive_quota_capacity_arr,
            "source": "workforce_derived",
        }
        for row in plan.gtm_capacity
    ]


def sync_legacy_headcount_plan(
    session: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: date,
    end_period: date,
) -> int:
    """
    Write derived payroll into typed headcount_plan / forecast_headcount_plan for
    backward-compatible reporting until all consumers use workforce APIs.
    """
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from app.models.demo_finance import ForecastHeadcountPlan, HeadcountPlan

    version = _normalize_scenario(scenario)
    rows = payroll_by_department(session, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)
    if not rows:
        return 0
    model = ForecastHeadcountPlan if version == "Forecast" else HeadcountPlan
    count = 0
    for row in rows:
        payload = {
            "organization_id": organization_id,
            "version": version,
            "period": row["period"],
            "department": row["department"],
            "headcount": row["headcount_fte"],
            "monthly_payroll_cost": row["monthly_payroll_cost"],
            "total_people_cost": row["total_people_cost"],
        }
        stmt = pg_insert(model).values(**payload)
        if version == "Forecast":
            stmt = stmt.on_conflict_do_update(
                index_elements=["organization_id", "version", "period", "department"],
                set_={
                    "headcount": payload["headcount"],
                    "monthly_payroll_cost": payload["monthly_payroll_cost"],
                    "total_people_cost": payload["total_people_cost"],
                },
            )
        else:
            stmt = stmt.on_conflict_do_update(
                index_elements=["organization_id", "version", "period", "department"],
                set_={
                    "headcount": payload["headcount"],
                    "monthly_payroll_cost": payload["monthly_payroll_cost"],
                    "total_people_cost": payload["total_people_cost"],
                },
            )
        session.execute(stmt)
        count += 1
    session.flush()
    return count
