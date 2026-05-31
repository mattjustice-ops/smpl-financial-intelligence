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

forecast_router = APIRouter(prefix="/forecast", tags=["forecast"])


def _validate_periods(start_period: date, end_period: date) -> None:
    if end_period < start_period:
        raise HTTPException(status_code=400, detail="end_period must be >= start_period")


@forecast_router.get("/cash-flow", response_model=ForecastScheduleResponse)
def forecast_cash_flow(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Forecast"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
) -> ForecastScheduleResponse:
    get_organization_or_404(db, organization_id)
    _validate_periods(start_period, end_period)
    return service.cash_flow_schedule(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)


@forecast_router.get("/deferred-revenue-waterfall", response_model=ForecastScheduleResponse)
def forecast_deferred_revenue_waterfall(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Forecast"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
) -> ForecastScheduleResponse:
    get_organization_or_404(db, organization_id)
    _validate_periods(start_period, end_period)
    return service.deferred_revenue_schedule(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)


@forecast_router.get("/working-capital", response_model=ForecastScheduleResponse)
def forecast_working_capital(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Forecast"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
) -> ForecastScheduleResponse:
    get_organization_or_404(db, organization_id)
    _validate_periods(start_period, end_period)
    return service.working_capital_schedule(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)


@forecast_router.get("/operating-cash-bridge", response_model=ForecastScheduleResponse)
def forecast_operating_cash_bridge(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Forecast"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
) -> ForecastScheduleResponse:
    get_organization_or_404(db, organization_id)
    _validate_periods(start_period, end_period)
    return service.operating_cash_bridge_schedule(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)


@forecast_router.get("/balance-sheet", response_model=ForecastScheduleResponse)
def forecast_balance_sheet(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Forecast"),
    start_period: date = Query(...),
    end_period: date = Query(...),
    db: Session = Depends(get_db),
) -> ForecastScheduleResponse:
    get_organization_or_404(db, organization_id)
    _validate_periods(start_period, end_period)
    return service.balance_sheet_schedule(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)


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
    return service.assumptions_schedule(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)


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
    return service.driver_summary(db, organization_id, scenario=scenario, start_period=start_period, end_period=end_period)
