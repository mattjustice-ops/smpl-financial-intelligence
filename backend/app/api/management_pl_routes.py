"""Management P&L dashboard API."""

from __future__ import annotations

import uuid
from datetime import date

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.db.session import get_db
from app.services.management_pl.schemas import ManagementPlDashboardResponse
from app.services.management_pl.service import build_management_pl_dashboard
from app.services.organizations import get_organization_or_404

management_pl_router = APIRouter(prefix="/management-pl", tags=["management-pl"])


@management_pl_router.get("/ping")
def management_pl_ping() -> dict[str, str]:
    """Lightweight route to verify this router is mounted (use after restarting uvicorn)."""
    return {"status": "ok", "module": "management_pl"}


@management_pl_router.get("/dashboard", response_model=ManagementPlDashboardResponse)
def management_pl_dashboard(
    organization_id: uuid.UUID = Query(...),
    start_period: date = Query(...),
    end_period: date = Query(...),
    as_of_period: date | None = Query(None),
    period_mode: str = Query("fy", description="month | qtd | ytd | fy"),
    view_mode: str = Query("management"),
    department: str = Query("Total Company"),
    db: Session = Depends(get_db),
) -> ManagementPlDashboardResponse:
    get_organization_or_404(db, organization_id)
    if end_period < start_period:
        raise HTTPException(status_code=400, detail="end_period must be >= start_period")
    if period_mode not in ("month", "qtd", "ytd", "fy"):
        raise HTTPException(status_code=400, detail="period_mode must be month, qtd, ytd, or fy")
    try:
        return build_management_pl_dashboard(
            db,
            organization_id,
            start_period=start_period,
            end_period=end_period,
            as_of_period=as_of_period,
            period_mode=period_mode,
            view_mode=view_mode,
            department=department,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("management_pl_dashboard failed org=%s", organization_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
