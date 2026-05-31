"""Executive flow dashboard API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.dashboard.executive_service import executive_flow
from app.services.dashboard.schemas import ExecutiveFlowResponse
from app.services.organizations import get_organization_or_404
from app.services.reporting.period_utils import to_period

dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def dashboard_params(
    scenario: str,
    start_period: str,
    end_period: str,
    period: str | None,
    quarter: str | None,
    fiscal_year: str | None,
    waterfall_type: str | None,
    marketing_channel: str | None,
    region: str | None,
    segment: str | None,
    owner: str | None,
) -> dict:
    start = to_period(period or start_period)
    end = to_period(period or end_period)
    if quarter and fiscal_year:
        q = int(quarter.upper().replace("Q", ""))
        start_month = (q - 1) * 3 + 1
        start = f"{int(fiscal_year):04d}-{start_month:02d}"
        end = f"{int(fiscal_year):04d}-{start_month + 2:02d}"
    elif fiscal_year:
        start = f"{int(fiscal_year):04d}-01"
        end = f"{int(fiscal_year):04d}-12"
    return {
        "scenario": scenario,
        "start_period": start,
        "end_period": end,
        "waterfall_type": waterfall_type,
        "marketing_channel": marketing_channel,
        "region": region,
        "segment": segment,
        "owner": owner,
    }


@dashboard_router.get("/executive-flow", response_model=ExecutiveFlowResponse)
def get_executive_flow(
    organization_id: uuid.UUID = Query(...),
    scenario: str = Query("Combined"),
    start_period: str = Query(...),
    end_period: str = Query(...),
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
    return executive_flow(
        db,
        organization_id,
        **dashboard_params(scenario, start_period, end_period, period, quarter, fiscal_year, waterfall_type, marketing_channel, region, segment, owner),
    )
