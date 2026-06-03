"""Marketing performance reporting API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.reporting_params import enrich_reporting_params
from app.db.session import get_db
from app.services.dashboard.marketing_attribution_service import channel_drilldown as channel_drilldown_service
from app.services.marketing import service
from app.services.marketing.schemas import ActualBudgetForecastResponse, MarketingResponse
from app.services.organizations import get_organization_or_404
from app.services.reporting.period_utils import to_period

marketing_router = APIRouter(prefix="/marketing", tags=["marketing"])


def _params(start_period: str, end_period: str) -> tuple[str, str]:
    start = to_period(start_period)
    end = to_period(end_period)
    if end < start:
        raise HTTPException(status_code=400, detail="end_period must be >= start_period")
    return start, end


def _marketing_kwargs(
    db: Session,
    organization_id: uuid.UUID,
    *,
    scenario: str,
    start: str,
    end: str,
    as_of_period: str | None,
    marketing_channel: str | None,
) -> dict:
    params = enrich_reporting_params(
        db,
        organization_id,
        {"scenario": scenario, "start_period": start, "end_period": end, "marketing_channel": marketing_channel},
        as_of_period=as_of_period,
    )
    return {
        "scenario": params["scenario"],
        "start_period": params["start_period"],
        "end_period": params["end_period"],
        "marketing_channel": marketing_channel,
        "as_of_period": params["as_of_period"],
    }


@marketing_router.get("/performance-summary", response_model=MarketingResponse)
def performance_summary(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Combined"),
    start_period: str = Query(...),
    end_period: str = Query(...),
    as_of_period: str | None = Query(None, description="Close month for Combined (YYYY-MM)"),
    marketing_channel: str | None = Query(None),
    db: Session = Depends(get_db),
) -> MarketingResponse:
    get_organization_or_404(db, organization_id)
    start, end = _params(start_period, end_period)
    return service.performance_summary(
        db,
        organization_id,
        **_marketing_kwargs(
            db,
            organization_id,
            scenario=scenario,
            start=start,
            end=end,
            as_of_period=as_of_period,
            marketing_channel=marketing_channel,
        ),
    )


@marketing_router.get("/channel-performance", response_model=MarketingResponse)
def channel_performance(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Combined"),
    start_period: str = Query(...),
    end_period: str = Query(...),
    as_of_period: str | None = Query(None),
    marketing_channel: str | None = Query(None),
    db: Session = Depends(get_db),
) -> MarketingResponse:
    get_organization_or_404(db, organization_id)
    start, end = _params(start_period, end_period)
    return service.channel_performance(
        db,
        organization_id,
        **_marketing_kwargs(
            db,
            organization_id,
            scenario=scenario,
            start=start,
            end=end,
            as_of_period=as_of_period,
            marketing_channel=marketing_channel,
        ),
    )


@marketing_router.get("/actual-budget-forecast", response_model=ActualBudgetForecastResponse)
def actual_budget_forecast(
    organization_id: uuid.UUID = Query(...),
    start_period: str = Query(...),
    end_period: str = Query(...),
    as_of_period: str | None = Query(None),
    marketing_channel: str | None = Query(None),
    db: Session = Depends(get_db),
) -> ActualBudgetForecastResponse:
    get_organization_or_404(db, organization_id)
    start, end = _params(start_period, end_period)
    kwargs = _marketing_kwargs(
        db,
        organization_id,
        scenario="Combined",
        start=start,
        end=end,
        as_of_period=as_of_period,
        marketing_channel=marketing_channel,
    )
    return service.actual_budget_forecast(
        db,
        organization_id,
        start_period=start,
        end_period=end,
        marketing_channel=marketing_channel,
        as_of_period=kwargs["as_of_period"],
    )


@marketing_router.get("/channel-drilldown")
def channel_drilldown(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Combined"),
    period: str = Query(...),
    marketing_channel: str = Query(...),
    as_of_period: str | None = Query(None),
    db: Session = Depends(get_db),
) -> dict:
    get_organization_or_404(db, organization_id)
    enrich_reporting_params(
        db,
        organization_id,
        {"scenario": scenario, "start_period": period, "end_period": period},
        as_of_period=as_of_period,
    )
    return channel_drilldown_service(
        db,
        organization_id,
        scenario=scenario,
        period=to_period(period),
        marketing_channel=marketing_channel,
    ).model_dump(mode="json")
