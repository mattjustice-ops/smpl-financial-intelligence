"""HTTP routes for the MRR waterfall engine."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.mrr.service import run_period_waterfall
from app.services.organizations import get_organization_or_404

mrr_router = APIRouter(prefix="/mrr", tags=["mrr"])


class CustomerRowOut(BaseModel):
    customer_id: str
    period: date
    beginning_mrr: Decimal
    new_mrr: Decimal
    expansion_mrr: Decimal
    contraction_mrr: Decimal
    churn_mrr: Decimal
    reactivation_mrr: Decimal
    ending_mrr: Decimal
    movement_type: str


class SummaryOut(BaseModel):
    period: date
    beginning_mrr: Decimal
    new_mrr: Decimal
    expansion_mrr: Decimal
    contraction_mrr: Decimal
    churn_mrr: Decimal
    reactivation_mrr: Decimal
    ending_mrr: Decimal
    active_customers_beginning: int
    active_customers_ending: int
    new_customers: int
    churned_customers: int
    reactivated_customers: int


class ArrBridgeOut(BaseModel):
    period: date
    beginning_arr: Decimal
    new_arr: Decimal
    expansion_arr: Decimal
    contraction_arr: Decimal
    churn_arr: Decimal
    reactivation_arr: Decimal
    ending_arr: Decimal


class MetricsOut(BaseModel):
    period: date
    nrr: Optional[Decimal]
    grr: Optional[Decimal]
    gross_mrr_churn_rate: Optional[Decimal]
    expansion_rate: Optional[Decimal]
    logo_churn_rate: Optional[Decimal]
    net_new_mrr: Decimal


class WaterfallResponse(BaseModel):
    period: date
    persisted_rows: int
    customer_rows: list[CustomerRowOut]
    summary: SummaryOut
    arr_bridge: ArrBridgeOut
    metrics: MetricsOut


@mrr_router.post("/run", response_model=WaterfallResponse)
def run_waterfall(
    organization_id: uuid.UUID = Query(..., description="Tenant organization UUID"),
    period: date = Query(..., description="Target month (normalized to first of month)"),
    prior_period: Optional[date] = Query(None, description="Override prior month start"),
    persist: bool = Query(True, description="Write rows to mrr_waterfall"),
    db: Session = Depends(get_db),
) -> WaterfallResponse:
    get_organization_or_404(db, organization_id)
    try:
        result = run_period_waterfall(
            db,
            organization_id,
            period,
            prior_period=prior_period,
            persist=persist,
        )
    except Exception as e:  # surface engine errors as 400 for clarity
        raise HTTPException(status_code=400, detail=str(e)) from e
    return WaterfallResponse(
        period=result.period,
        persisted_rows=result.persisted_rows,
        customer_rows=[CustomerRowOut(**r.as_dict()) for r in result.customer_rows],
        summary=SummaryOut(**result.summary.as_dict()),
        arr_bridge=ArrBridgeOut(**result.arr_bridge.as_dict()),
        metrics=MetricsOut(**result.metrics.as_dict()),
    )


@mrr_router.get("/preview", response_model=WaterfallResponse)
def preview_waterfall(
    organization_id: uuid.UUID = Query(...),
    period: date = Query(...),
    prior_period: Optional[date] = Query(None),
    db: Session = Depends(get_db),
) -> WaterfallResponse:
    """Same as /run but never writes — for dashboards and what-if checks."""
    return run_waterfall(
        organization_id=organization_id,
        period=period,
        prior_period=prior_period,
        persist=False,
        db=db,
    )
