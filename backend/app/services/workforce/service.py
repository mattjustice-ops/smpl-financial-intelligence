"""Workforce operating intelligence service."""

from __future__ import annotations

import logging
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.demo_finance import ForecastIncomeStatement
from app.models.workforce import WorkforceOpenRequisition, WorkforcePeriodSummary
from app.services.workforce.constants import APPROVED_REQ_STATUSES, WORKFORCE_DEPARTMENTS
from app.services.workforce.engine import WorkforcePlanningEngine, month_start, period_range, q_fte, q_money
from app.services.workforce.legacy_headcount import (
    legacy_headcount_present,
    load_legacy_headcount_rows,
    merge_legacy_headcount,
)
from app.services.workforce.schemas import (
    WorkforceCapacityRow,
    WorkforceOperatingMetrics,
    WorkforcePeriodDepartmentRow,
    WorkforcePlanResponse,
    WorkforcePnlAllocationRow,
    WorkforceValidationRow,
)

logger = logging.getLogger(__name__)


def _normalize_scenario(scenario: str) -> str:
    s = scenario.strip()
    if s.lower() == "forecast":
        return "Forecast"
    if s.lower() == "budget":
        return "Budget"
    if s.lower() == "actual":
        return "Actual"
    return s


def build_workforce_plan(
    session: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: date,
    end_period: date,
    persist: bool = True,
    revenue_by_period: dict[date, Decimal] | None = None,
    arr_by_period: dict[date, Decimal] | None = None,
) -> WorkforcePlanResponse:
    version = _normalize_scenario(scenario)
    engine = WorkforcePlanningEngine(session, organization_id, version=version)
    result = engine.build(start_period, end_period)

    legacy_rows: list = []
    using_legacy_headcount = False
    try:
        legacy_rows = load_legacy_headcount_rows(
            session,
            organization_id,
            scenario=version,
            start_period=start_period,
            end_period=end_period,
        )
        using_legacy_headcount = bool(legacy_rows)
    except Exception:
        logger.exception("legacy headcount overlay failed for org=%s scenario=%s", organization_id, version)
        legacy_rows = []
        using_legacy_headcount = False

    merged_period_rows = merge_legacy_headcount(result.period_rows, legacy_rows)

    if persist:
        from app.services.workforce.engine import WorkforceEngineResult

        engine.persist_summary(
            WorkforceEngineResult(
                period_rows=merged_period_rows,
                pnl_allocations=result.pnl_allocations,
                gtm_capacity=result.gtm_capacity,
                validations=result.validations,
            )
        )

    revenue_by_period = revenue_by_period or _load_revenue(session, organization_id, version, start_period, end_period)
    arr_by_period = arr_by_period or {}

    period_summary: list[WorkforcePeriodDepartmentRow] = []
    for row in merged_period_rows:
        try:
            period_summary.append(WorkforcePeriodDepartmentRow(**row))
        except Exception as exc:
            raise ValueError(f"Invalid workforce period row for {row.get('department')} @ {row.get('period')}: {exc}") from exc
    pnl_allocations = [WorkforcePnlAllocationRow(**row, departments=[]) for row in result.pnl_allocations]
    gtm_capacity = [WorkforceCapacityRow(**row) for row in result.gtm_capacity]

    operating_metrics: list[WorkforceOperatingMetrics] = []
    filled_by_period: dict[date, Decimal] = {}
    planned_by_period: dict[date, Decimal] = {}
    hc_by_period: dict[date, Decimal] = {}
    cost_by_period: dict[date, Decimal] = {}
    new_hires_by_period: dict[date, Decimal] = {}
    for row in period_summary:
        filled_by_period[row.period] = filled_by_period.get(row.period, Decimal("0")) + row.filled_headcount
        planned_by_period[row.period] = planned_by_period.get(row.period, Decimal("0")) + row.planned_hire_headcount
        hc_by_period[row.period] = hc_by_period.get(row.period, Decimal("0")) + row.total_headcount_fte
        cost_by_period[row.period] = cost_by_period.get(row.period, Decimal("0")) + row.total_people_cost_monthly
        new_hires_by_period[row.period] = new_hires_by_period.get(row.period, Decimal("0")) + row.new_hires_fte

    planned_starts: dict[date, Decimal] = {}
    if using_legacy_headcount and new_hires_by_period:
        planned_starts = new_hires_by_period
    else:
        try:
            planned_starts = _planned_starts_by_period(
                session, organization_id, version=version, start_period=start_period, end_period=end_period
            )
        except Exception:
            planned_starts = {}

    for period in period_range(start_period, end_period):
        filled = filled_by_period.get(period, Decimal("0"))
        planned = planned_by_period.get(period, Decimal("0"))
        hc = hc_by_period.get(period, Decimal("0"))
        cost = cost_by_period.get(period, Decimal("0"))
        rev = revenue_by_period.get(period)
        arr = arr_by_period.get(period)
        operating_metrics.append(
            WorkforceOperatingMetrics(
                period=period,
                revenue=rev,
                arr=arr,
                filled_headcount_fte=q_fte(filled),
                planned_hire_headcount_fte=q_fte(planned),
                planned_starts_fte=q_fte(planned_starts.get(period, Decimal("0"))),
                total_headcount_fte=q_fte(hc),
                revenue_per_employee=q_money(rev / hc) if rev is not None and hc > 0 else None,
                arr_per_employee=q_money(arr / hc) if arr is not None and hc > 0 else None,
                total_people_cost_monthly=q_money(cost),
                burn_multiple=q_money(cost / rev) if rev and rev > 0 else None,
            )
        )

    validations: list[WorkforceValidationRow] = []
    for item in result.validations:
        if using_legacy_headcount and item.get("validation_name") == "workforce_source_data_missing":
            continue
        payload = dict(item)
        payload["scenario"] = version
        validations.append(WorkforceValidationRow(**payload))
    if using_legacy_headcount:
        validations.append(
            WorkforceValidationRow(
                scenario=version,
                period=start_period,
                validation_name="legacy_headcount_plan_in_use",
                status="pass",
                message="Filled FTE sourced from headcount plan (beginning + hires − attrition = ending).",
            )
        )

    departments = sorted({d for d in WORKFORCE_DEPARTMENTS} | {r.department for r in period_summary})

    response = WorkforcePlanResponse(
        organization_id=str(organization_id),
        scenario=version,
        start_period=start_period,
        end_period=end_period,
        departments=departments,
        period_summary=period_summary,
        pnl_allocations=pnl_allocations,
        gtm_capacity=gtm_capacity,
        operating_metrics=operating_metrics,
        validations=validations,
        data_sources=[
            "workforce_employees",
            "workforce_open_requisitions",
            "workforce_hiring_ramp_assumptions",
            "workforce_compensation_bands",
            "workforce_department_allocation_rules",
            *(["headcount_plan", "forecast_headcount_plan"] if using_legacy_headcount else []),
        ],
    )
    try:
        WorkforcePlanResponse.model_validate(response.model_dump(mode="json"))
    except Exception as exc:
        raise ValueError(f"Workforce plan response validation failed: {exc}") from exc
    return response


def _req_approved(status: str | None) -> bool:
    return (status or "").strip().lower() in APPROVED_REQ_STATUSES


def _planned_starts_by_period(
    session: Session,
    organization_id: uuid.UUID,
    *,
    version: str,
    start_period: date,
    end_period: date,
) -> dict[date, Decimal]:
    """Approved requisitions whose planned start falls in each period (monthly flow)."""
    counts: dict[date, Decimal] = {}
    rows = session.scalars(
        select(WorkforceOpenRequisition).where(
            WorkforceOpenRequisition.organization_id == organization_id,
            WorkforceOpenRequisition.version == version,
        )
    )
    start = month_start(start_period)
    end = month_start(end_period)
    for req in rows:
        if not _req_approved(req.approved_status):
            continue
        hire_start = req.planned_start_date or req.target_hire_date
        if hire_start is None:
            continue
        period = month_start(hire_start)
        if period < start or period > end:
            continue
        counts[period] = counts.get(period, Decimal("0")) + Decimal("1")
    return counts


def _load_revenue(
    session: Session,
    organization_id: uuid.UUID,
    version: str,
    start_period: date,
    end_period: date,
) -> dict[date, Decimal]:
    if version != "Forecast":
        return {}
    rows = session.scalars(
        select(ForecastIncomeStatement).where(
            ForecastIncomeStatement.organization_id == organization_id,
            ForecastIncomeStatement.version == version,
            ForecastIncomeStatement.period >= start_period.replace(day=1),
            ForecastIncomeStatement.period <= end_period.replace(day=1),
        )
    )
    return {row.period.replace(day=1): q_money(row.revenue or 0) for row in rows}


def load_persisted_summary(
    session: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start_period: date,
    end_period: date,
) -> list[WorkforcePeriodSummary]:
    version = _normalize_scenario(scenario)
    return list(
        session.scalars(
            select(WorkforcePeriodSummary).where(
                WorkforcePeriodSummary.organization_id == organization_id,
                WorkforcePeriodSummary.version == version,
                WorkforcePeriodSummary.period >= start_period.replace(day=1),
                WorkforcePeriodSummary.period <= end_period.replace(day=1),
            )
        )
    )
