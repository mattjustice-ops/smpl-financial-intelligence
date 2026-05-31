"""Marketing performance reporting API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.marketing import service
from app.services.marketing.schemas import ActualBudgetForecastResponse, MarketingResponse
from app.services.dashboard.marketing_attribution_service import channel_drilldown as channel_drilldown_service
from app.services.organizations import get_organization_or_404
from app.services.reporting.period_utils import to_period

marketing_router = APIRouter(prefix="/marketing", tags=["marketing"])


def _params(start_period: str, end_period: str) -> tuple[str, str]:
    start = to_period(start_period)
    end = to_period(end_period)
    if end < start:
        raise HTTPException(status_code=400, detail="end_period must be >= start_period")
    return start, end


@marketing_router.get("/performance-summary", response_model=MarketingResponse)
def performance_summary(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Combined"),
    start_period: str = Query(...),
    end_period: str = Query(...),
    marketing_channel: str | None = Query(None),
    db: Session = Depends(get_db),
) -> MarketingResponse:
    get_organization_or_404(db, organization_id)
    start, end = _params(start_period, end_period)
    return service.performance_summary(db, organization_id, scenario=scenario, start_period=start, end_period=end, marketing_channel=marketing_channel)


@marketing_router.get("/channel-performance", response_model=MarketingResponse)
def channel_performance(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Combined"),
    start_period: str = Query(...),
    end_period: str = Query(...),
    marketing_channel: str | None = Query(None),
    db: Session = Depends(get_db),
) -> MarketingResponse:
    get_organization_or_404(db, organization_id)
    start, end = _params(start_period, end_period)
    return service.channel_performance(db, organization_id, scenario=scenario, start_period=start, end_period=end, marketing_channel=marketing_channel)


@marketing_router.get("/pipeline-waterfall", response_model=MarketingResponse)
def pipeline_waterfall(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Combined"),
    start_period: str = Query(...),
    end_period: str = Query(...),
    marketing_channel: str | None = Query(None),
    db: Session = Depends(get_db),
) -> MarketingResponse:
    get_organization_or_404(db, organization_id)
    start, end = _params(start_period, end_period)
    return service.pipeline_waterfall(db, organization_id, scenario=scenario, start_period=start, end_period=end, marketing_channel=marketing_channel)


@marketing_router.get("/funnel-conversion", response_model=MarketingResponse)
def funnel_conversion(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Combined"),
    start_period: str = Query(...),
    end_period: str = Query(...),
    marketing_channel: str | None = Query(None),
    db: Session = Depends(get_db),
) -> MarketingResponse:
    get_organization_or_404(db, organization_id)
    start, end = _params(start_period, end_period)
    return service.funnel_conversion(db, organization_id, scenario=scenario, start_period=start, end_period=end, marketing_channel=marketing_channel)


@marketing_router.get("/spend-efficiency", response_model=MarketingResponse)
def spend_efficiency(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Combined"),
    start_period: str = Query(...),
    end_period: str = Query(...),
    marketing_channel: str | None = Query(None),
    db: Session = Depends(get_db),
) -> MarketingResponse:
    get_organization_or_404(db, organization_id)
    start, end = _params(start_period, end_period)
    return service.spend_efficiency(db, organization_id, scenario=scenario, start_period=start, end_period=end, marketing_channel=marketing_channel)


@marketing_router.get("/actual-budget-forecast", response_model=ActualBudgetForecastResponse)
def actual_budget_forecast(
    organization_id: uuid.UUID = Query(...),
    start_period: str = Query(...),
    end_period: str = Query(...),
    marketing_channel: str | None = Query(None),
    db: Session = Depends(get_db),
) -> ActualBudgetForecastResponse:
    get_organization_or_404(db, organization_id)
    start, end = _params(start_period, end_period)
    return service.actual_budget_forecast(db, organization_id, start_period=start, end_period=end, marketing_channel=marketing_channel)


@marketing_router.get("/channel-drilldown", response_model=MarketingResponse)
def channel_drilldown(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Combined"),
    start_period: str = Query(...),
    end_period: str = Query(...),
    marketing_channel: str | None = Query(None),
    db: Session = Depends(get_db),
) -> MarketingResponse:
    get_organization_or_404(db, organization_id)
    start, end = _params(start_period, end_period)
    return channel_drilldown_service(db, organization_id, scenario=scenario, start_period=start, end_period=end, marketing_channel=marketing_channel)
