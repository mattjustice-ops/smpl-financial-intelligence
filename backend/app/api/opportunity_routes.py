"""Opportunity drilldown APIs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.waterfall_routes import route_params
from app.db.session import get_db
from app.services.dashboard.opportunity_attribution_service import closed_by_month, remaining_pipeline, stage_summary
from app.services.dashboard.schemas import OpportunityResponse
from app.services.organizations import get_organization_or_404

opportunity_router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@opportunity_router.get("/stage-summary", response_model=OpportunityResponse)
def stage_summary_endpoint(organization_id: uuid.UUID = Query(...), params: dict = Depends(route_params), db: Session = Depends(get_db)) -> OpportunityResponse:
    get_organization_or_404(db, organization_id)
    return stage_summary(db, organization_id, **params)


@opportunity_router.get("/closed-by-month", response_model=OpportunityResponse)
def closed_by_month_endpoint(organization_id: uuid.UUID = Query(...), params: dict = Depends(route_params), db: Session = Depends(get_db)) -> OpportunityResponse:
    get_organization_or_404(db, organization_id)
    return closed_by_month(db, organization_id, **params)


@opportunity_router.get("/remaining-pipeline", response_model=OpportunityResponse)
def remaining_pipeline_endpoint(organization_id: uuid.UUID = Query(...), params: dict = Depends(route_params), db: Session = Depends(get_db)) -> OpportunityResponse:
    get_organization_or_404(db, organization_id)
    return remaining_pipeline(db, organization_id, **params)
