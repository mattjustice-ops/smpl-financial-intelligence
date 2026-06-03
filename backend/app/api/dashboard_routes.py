"""Executive flow dashboard API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.reporting_params import dashboard_params, enrich_reporting_params
from app.db.session import get_db
from app.services.dashboard.executive_service import executive_flow
from app.services.dashboard.schemas import ExecutiveFlowResponse
from app.services.organizations import get_organization_or_404
from app.services.reporting.as_of_period import infer_as_of_period, resolve_as_of_period

dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@dashboard_router.get("/as-of-period")
def get_as_of_period(
    organization_id: uuid.UUID = Query(...),
    as_of_period: str | None = Query(None, description="Override close month (YYYY-MM)"),
    end_period: str | None = Query(None, description="Fallback when Actual rows are missing"),
    db: Session = Depends(get_db),
) -> dict[str, str | bool | None]:
    get_organization_or_404(db, organization_id)
    inferred = infer_as_of_period(db, organization_id)
    resolved = resolve_as_of_period(
        db,
        organization_id,
        as_of_period=as_of_period,
        end_period=end_period,
    )
    return {
        "organization_id": str(organization_id),
        "as_of_period": resolved,
        "inferred_from_actuals": inferred,
        "override_applied": bool(as_of_period),
    }


@dashboard_router.get("/executive-flow", response_model=ExecutiveFlowResponse)
def get_executive_flow(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Combined"),
    start_period: str = Query(...),
    end_period: str = Query(...),
    as_of_period: str | None = Query(None, description="Close month for Combined (YYYY-MM)"),
    period: str | None = Query(None),
    quarter: str | None = Query(None),
    fiscal_year: str | None = Query(None),
    waterfall_type: str | None = Query(None),
    marketing_channel: str | None = Query(None),
    region: str | None = Query(None),
    segment: str | None = Query(None),
    owner: str | None = Query(None),
    db: Session = Depends(get_db),
) -> ExecutiveFlowResponse:
    get_organization_or_404(db, organization_id)
    params = enrich_reporting_params(
        db,
        organization_id,
        dashboard_params(
            scenario,
            start_period,
            end_period,
            period,
            quarter,
            fiscal_year,
            waterfall_type,
            marketing_channel,
            region,
            segment,
            owner,
        ),
        as_of_period=as_of_period,
    )
    return executive_flow(db, organization_id, **params)
