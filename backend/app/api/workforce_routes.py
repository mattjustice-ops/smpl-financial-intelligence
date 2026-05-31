"""Workforce operating model API."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.organizations import get_organization_or_404
from app.services.workforce import feeds, service
from app.services.workforce.schemas import WorkforcePlanResponse, WorkforceValidationResponse
from app.services.workforce import validation_service as workforce_validation_service

workforce_router = APIRouter(prefix="/workforce", tags=["workforce"])


def _validate_periods(start_period: date, end_period: date) -> None:
    if end_period < start_period:
        raise HTTPException(status_code=400, detail="end_period must be >= start_period")


@workforce_router.get("/plan", response_model=WorkforcePlanResponse)
def workforce_plan(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Forecast"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    persist: bool = Query(True, description="Write derived rows to workforce_period_summary"),
    db: Session = Depends(get_db),
) -> WorkforcePlanResponse:
    get_organization_or_404(db, organization_id)
    _validate_periods(start_period, end_period)
    try:
        plan = service.build_workforce_plan(
            db,
            organization_id,
            scenario=scenario,
            start_period=start_period,
            end_period=end_period,
            persist=persist,
        )
        return plan.model_dump(mode="json")
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "workforce_plan_failed",
                "error": str(exc),
                "hint": "Restart the API after pulling latest changes, then run scripts/diagnose_workforce_headcount.py.",
            },
        ) from exc


@workforce_router.post("/recompute")
def workforce_recompute(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Forecast"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    sync_legacy_headcount: bool = Query(
        True,
        description="Push derived payroll into headcount_plan tables for legacy reporting",
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    get_organization_or_404(db, organization_id)
    _validate_periods(start_period, end_period)
    try:
        plan = service.build_workforce_plan(
            db,
            organization_id,
            scenario=scenario,
            start_period=start_period,
            end_period=end_period,
            persist=True,
        )
        legacy_rows = 0
        if sync_legacy_headcount:
            legacy_rows = feeds.sync_legacy_headcount_plan(
                db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period
            )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "message": "workforce_recompute_failed",
                "error": str(exc),
                "hint": "Run `python -m alembic upgrade head` and upload workforce CSVs first.",
            },
        ) from exc
    return {
        "status": "ok",
        "periods_computed": len(plan.period_summary),
        "legacy_headcount_rows_synced": legacy_rows,
        "validations": [v.model_dump(mode="json") for v in plan.validations],
    }


@workforce_router.get("/feeds/payroll")
def workforce_feed_payroll(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Forecast"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    get_organization_or_404(db, organization_id)
    _validate_periods(start_period, end_period)
    return feeds.payroll_by_department(
        db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period
    )


@workforce_router.get("/feeds/cash-payroll")
def workforce_feed_cash_payroll(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Forecast"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    get_organization_or_404(db, organization_id)
    _validate_periods(start_period, end_period)
    return feeds.cash_payroll_outflow(
        db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period
    )


@workforce_router.get("/feeds/gtm-capacity")
def workforce_feed_gtm_capacity(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Forecast"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    get_organization_or_404(db, organization_id)
    _validate_periods(start_period, end_period)
    return feeds.gtm_quota_capacity_feed(
        db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period
    )


@workforce_router.get("/departments")
def workforce_departments() -> dict[str, list[str]]:
    from app.services.workforce.constants import WORKFORCE_DEPARTMENTS

    return {"departments": list(WORKFORCE_DEPARTMENTS)}


@workforce_router.get("/validation", response_model=WorkforceValidationResponse)
def workforce_validation(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Forecast"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
) -> WorkforceValidationResponse:
    get_organization_or_404(db, organization_id)
    _validate_periods(start_period, end_period)
    return workforce_validation_service.run_workforce_validations(
        db,
        organization_id,
        scenario=scenario,
        start_period=start_period,
        end_period=end_period,
    )
