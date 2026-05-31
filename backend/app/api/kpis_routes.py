"""HTTP routes for the SaaS KPI calculation engine."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.kpis.service import run_kpis
from app.services.organizations import get_organization_or_404

kpis_router = APIRouter(prefix="/kpis", tags=["kpis"])


class KpiSnapshot(BaseModel):
    period_start: date
    period_end: date

    arr: Decimal
    mrr: Decimal
    beginning_arr: Decimal
    ending_arr: Decimal

    nrr: Optional[Decimal] = None
    grr: Optional[Decimal] = None
    logo_churn_rate: Optional[Decimal] = None
    gross_mrr_churn_rate: Optional[Decimal] = None
    net_mrr_churn_rate: Optional[Decimal] = None

    arpa: Optional[Decimal] = None
    cac: Optional[Decimal] = None
    cac_payback_months: Optional[Decimal] = None
    ltv: Optional[Decimal] = None
    ltv_to_cac: Optional[Decimal] = None

    revenue_growth_rate: Optional[Decimal] = None
    operating_margin: Optional[Decimal] = None
    rule_of_40: Optional[Decimal] = None
    magic_number: Optional[Decimal] = None
    sales_efficiency: Optional[Decimal] = None
    pipeline_coverage: Optional[Decimal] = None
    burn_multiple: Optional[Decimal] = None


class KpiRunResponse(BaseModel):
    snapshot: KpiSnapshot
    inputs_used: dict


@kpis_router.post("/run", response_model=KpiRunResponse)
def run_kpis_endpoint(
    organization_id: uuid.UUID = Query(..., description="Tenant organization UUID"),
    period_start: date = Query(..., description="Inclusive start date"),
    period_end: date = Query(..., description="Inclusive end date"),
    target_bookings: Optional[Decimal] = Query(None, description="Target ARR bookings for pipeline coverage"),
    gross_margin: Decimal = Query(Decimal("0.7"), ge=Decimal("0"), le=Decimal("1")),
    net_burn: Optional[Decimal] = Query(None, description="Net burn for the period; positive = burning cash"),
    prior_period_revenue: Optional[Decimal] = Query(None),
    prior_period_sales_marketing_expense: Optional[Decimal] = Query(None),
    db: Session = Depends(get_db),
) -> KpiRunResponse:
    """Compute every SaaS KPI for one window using stored MRR / bookings / GL data.

    The MRR waterfall must already be persisted for the `period_start` month
    (call `POST /api/v1/mrr/run` first).
    """
    get_organization_or_404(db, organization_id)
    if period_end < period_start:
        raise HTTPException(status_code=400, detail="period_end must be >= period_start")
    try:
        result = run_kpis(
            db,
            organization_id,
            period_start=period_start,
            period_end=period_end,
            target_bookings=target_bookings,
            gross_margin=gross_margin,
            net_burn=net_burn,
            prior_period_revenue=prior_period_revenue,
            prior_period_sales_marketing_expense=prior_period_sales_marketing_expense,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    payload = result.as_dict()
    inputs_used = payload.pop("inputs_used")
    return KpiRunResponse(snapshot=KpiSnapshot(**payload), inputs_used=inputs_used)


@kpis_router.get("/preview", response_model=KpiRunResponse)
def preview_kpis(
    organization_id: uuid.UUID = Query(...),
    period_start: date = Query(...),
    period_end: date = Query(...),
    target_bookings: Optional[Decimal] = Query(None),
    gross_margin: Decimal = Query(Decimal("0.7")),
    net_burn: Optional[Decimal] = Query(None),
    db: Session = Depends(get_db),
) -> KpiRunResponse:
    """Convenience alias of /run for dashboards (same behavior, GET-friendly)."""
    return run_kpis_endpoint(
        organization_id=organization_id,
        period_start=period_start,
        period_end=period_end,
        target_bookings=target_bookings,
        gross_margin=gross_margin,
        net_burn=net_burn,
        db=db,
    )
