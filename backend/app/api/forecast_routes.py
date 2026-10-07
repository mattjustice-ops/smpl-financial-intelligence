"""Driver-based SaaS forecast API endpoints."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.driver_forecast import service
from app.services.driver_forecast.schemas import DriverSummaryResponse, ForecastScheduleResponse
from app.services.organizations import get_organization_or_404
from app.services.reporting.as_of_period import bind_as_of_period, infer_as_of_period, reset_as_of_period

forecast_router = APIRouter(prefix="/forecast", tags=["forecast"])


def _validate_periods(start_period: date, end_period: date) -> None:
    if end_period < start_period:
        raise HTTPException(status_code=400, detail="end_period must be >= start_period")


def _with_loaded_close(db: Session, organization_id: uuid.UUID, build):
    """Split actual vs forecast months at the last closed Actual month in the warehouse."""
    as_of = infer_as_of_period(db, organization_id)
    token = bind_as_of_period(as_of) if as_of else None
    try:
        return build()
    finally:
        if token is not None:
            reset_as_of_period(token)


@forecast_router.get("/cash-flow", response_model=ForecastScheduleResponse)
def forecast_cash_flow(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Forecast"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
) -> ForecastScheduleResponse:
    get_organization_or_404(db, organization_id, module="cash")
    _validate_periods(start_period, end_period)
    return _with_loaded_close(
        db, organization_id, lambda: service.cash_flow_schedule(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)
    )


@forecast_router.get("/deferred-revenue-waterfall", response_model=ForecastScheduleResponse)
def forecast_deferred_revenue_waterfall(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Forecast"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
) -> ForecastScheduleResponse:
    get_organization_or_404(db, organization_id, module="revenue")
    _validate_periods(start_period, end_period)
    return _with_loaded_close(
        db, organization_id, lambda: service.deferred_revenue_schedule(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)
    )


@forecast_router.get("/working-capital", response_model=ForecastScheduleResponse)
def forecast_working_capital(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Forecast"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
) -> ForecastScheduleResponse:
    get_organization_or_404(db, organization_id, module="cash")
    _validate_periods(start_period, end_period)
    return _with_loaded_close(
        db, organization_id, lambda: service.working_capital_schedule(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)
    )


@forecast_router.get("/operating-cash-bridge", response_model=ForecastScheduleResponse)
def forecast_operating_cash_bridge(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Forecast"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
) -> ForecastScheduleResponse:
    get_organization_or_404(db, organization_id, module="cash")
    _validate_periods(start_period, end_period)
    return _with_loaded_close(
        db, organization_id, lambda: service.operating_cash_bridge_schedule(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)
    )


@forecast_router.get("/balance-sheet", response_model=ForecastScheduleResponse)
def forecast_balance_sheet(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Forecast"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
) -> ForecastScheduleResponse:
    get_organization_or_404(db, organization_id, module="cash")
    _validate_periods(start_period, end_period)
    return _with_loaded_close(
        db, organization_id, lambda: service.balance_sheet_schedule(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)
    )


@forecast_router.get("/assumptions", response_model=ForecastScheduleResponse)
def forecast_assumptions(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Forecast"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
) -> ForecastScheduleResponse:
    get_organization_or_404(db, organization_id)
    _validate_periods(start_period, end_period)
    return _with_loaded_close(
        db, organization_id, lambda: service.assumptions_schedule(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)
    )


@forecast_router.get("/driver-summary", response_model=DriverSummaryResponse)
def forecast_driver_summary(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Forecast"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
) -> DriverSummaryResponse:
    get_organization_or_404(db, organization_id)
    _validate_periods(start_period, end_period)
    return _with_loaded_close(
        db, organization_id, lambda: service.driver_summary(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)
    )
