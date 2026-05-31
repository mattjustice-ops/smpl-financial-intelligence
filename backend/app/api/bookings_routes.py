"""HTTP routes for the bookings forecast engine."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.bookings.engine import ForecastMethod, ScenarioFactors, WinRates
from app.services.bookings.service import run_bookings_forecast
from app.services.organizations import get_organization_or_404

bookings_router = APIRouter(prefix="/bookings", tags=["bookings"])


class ForecastRequest(BaseModel):
    period_start: date
    period_end: date
    method: ForecastMethod = ForecastMethod.WEIGHTED
    target_bookings: Optional[Decimal] = None

    scenario_conservative: Decimal = Decimal("0.8")
    scenario_base: Decimal = Decimal("1.0")
    scenario_upside: Decimal = Decimal("1.2")

    win_rates_by_stage: Optional[dict[str, Decimal]] = Field(
        None, description="Optional override; defaults to history derived from DB."
    )
    win_rates_by_segment: Optional[dict[str, Decimal]] = None
    win_rates_overall: Optional[Decimal] = None


class OpportunityForecastOut(BaseModel):
    opportunity_id: str
    customer_id: str
    rep_id: Optional[str]
    segment: Optional[str]
    stage: str
    amount: Decimal
    probability: Decimal
    expected_close_date: date
    forecast_value: Decimal
    method: str


class BookingsForecastOut(BaseModel):
    method: str
    period_start: date
    period_end: date
    total_pipeline: Decimal
    total_forecast: Decimal
    by_month: dict[str, Decimal]
    by_quarter: dict[str, Decimal]
    by_rep: dict[str, Decimal]
    by_segment: dict[str, Decimal]
    by_customer: dict[str, Decimal]
    scenarios: dict[str, Decimal]
    opportunity_forecasts: list[OpportunityForecastOut]


class ConfidenceOut(BaseModel):
    score: Decimal
    avg_probability: Decimal
    stage_maturity_score: Decimal
    sample_size: int
    band: str


class WinRatesOut(BaseModel):
    by_stage: dict[str, Decimal]
    by_segment: dict[str, Decimal]
    overall: Decimal


class ForecastResponse(BaseModel):
    forecast: BookingsForecastOut
    confidence: ConfidenceOut
    coverage_ratio: Optional[Decimal]
    win_rates_used: WinRatesOut


@bookings_router.post("/run", response_model=ForecastResponse)
def run_forecast(
    organization_id: uuid.UUID = Query(..., description="Tenant organization UUID"),
    body: ForecastRequest = Body(...),
    db: Session = Depends(get_db),
) -> ForecastResponse:
    get_organization_or_404(db, organization_id)

    win_rates_override: Optional[WinRates] = None
    if body.win_rates_overall is not None:
        win_rates_override = WinRates(
            by_stage=dict(body.win_rates_by_stage or {}),
            by_segment=dict(body.win_rates_by_segment or {}),
            overall=body.win_rates_overall,
        )

    try:
        result = run_bookings_forecast(
            db,
            organization_id,
            period_start=body.period_start,
            period_end=body.period_end,
            method=body.method,
            scenario_factors=ScenarioFactors(
                conservative=body.scenario_conservative,
                base=body.scenario_base,
                upside=body.scenario_upside,
            ),
            target_bookings=body.target_bookings,
            win_rates_override=win_rates_override,
            win_rates_by_stage_override=body.win_rates_by_stage if win_rates_override is None else None,
            win_rates_by_segment_override=body.win_rates_by_segment if win_rates_override is None else None,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    f = result.forecast
    return ForecastResponse(
        forecast=BookingsForecastOut(
            method=f.method.value,
            period_start=f.period_start,
            period_end=f.period_end,
            total_pipeline=f.total_pipeline,
            total_forecast=f.total_forecast,
            by_month={k.isoformat(): v for k, v in f.by_month.items()},
            by_quarter=dict(f.by_quarter),
            by_rep=dict(f.by_rep),
            by_segment=dict(f.by_segment),
            by_customer=dict(f.by_customer),
            scenarios=dict(f.scenarios),
            opportunity_forecasts=[OpportunityForecastOut(**r.as_dict()) for r in f.opportunity_forecasts],
        ),
        confidence=ConfidenceOut(**result.confidence.as_dict()),
        coverage_ratio=result.coverage_ratio,
        win_rates_used=WinRatesOut(
            by_stage=dict(result.win_rates_used.by_stage),
            by_segment=dict(result.win_rates_used.by_segment),
            overall=result.win_rates_used.overall,
        ),
    )
