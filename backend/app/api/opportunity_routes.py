"""Opportunity drilldown APIs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.reporting_params import enrich_reporting_params
from app.api.waterfall_routes import route_params
from app.db.session import get_db
from app.services.dashboard.opportunity_attribution_service import closed_by_month, remaining_pipeline, stage_summary
from app.services.dashboard.schemas import OpportunityResponse
from app.services.organizations import get_organization_or_404

opportunity_router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def _with_params(
    db: Session,
    organization_id: uuid.UUID,
    params: dict,
    *,
    as_of_period: str | None,
) -> dict:
    get_organization_or_404(db, organization_id)
    return enrich_reporting_params(db, organization_id, params, as_of_period=as_of_period)


@opportunity_router.get("/stage-summary", response_model=OpportunityResponse)
def stage_summary_endpoint(
    organization_id: uuid.UUID = Query(...),
    as_of_period: str | None = Query(None, description="Close month for Combined (YYYY-MM)"),
    params: dict = Depends(route_params),
    db: Session = Depends(get_db),
) -> OpportunityResponse:
    params = _with_params(db, organization_id, params, as_of_period=as_of_period)
    return stage_summary(db, organization_id, **params)


@opportunity_router.get("/closed-by-month", response_model=OpportunityResponse)
def closed_by_month_endpoint(
    organization_id: uuid.UUID = Query(...),
    as_of_period: str | None = Query(None),
    params: dict = Depends(route_params),
    db: Session = Depends(get_db),
) -> OpportunityResponse:
    params = _with_params(db, organization_id, params, as_of_period=as_of_period)
    return closed_by_month(db, organization_id, **params)


@opportunity_router.get("/remaining-pipeline", response_model=OpportunityResponse)
def remaining_pipeline_endpoint(
    organization_id: uuid.UUID = Query(...),
    as_of_period: str | None = Query(None),
    params: dict = Depends(route_params),
    db: Session = Depends(get_db),
) -> OpportunityResponse:
    params = _with_params(db, organization_id, params, as_of_period=as_of_period)
    return remaining_pipeline(db, organization_id, **params)
