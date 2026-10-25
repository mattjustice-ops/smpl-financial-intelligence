"""Shared reporting outlook payload for Board Platform + Forecast Engine."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.organizations import get_organization_or_404
from app.services.reporting.org_reporting_settings import resolve_org_close_month
from app.services.reporting.source_trace import build_source_trace
from app.services.reporting.three_statement_payload import (
    build_outlook_api_payload,
    build_shared_reporting_payload,
)

reporting_outlook_router = APIRouter(prefix="/reporting", tags=["reporting-outlook"])


@reporting_outlook_router.get("/outlook")
def reporting_outlook_payload(
    organization_id: uuid.UUID,
    block_on_validation: bool = Query(False),
    as_of_period: str | None = Query(None, min_length=7, max_length=7),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Single warehouse outlook payload — both board and forecast surfaces hydrate from this."""
    get_organization_or_404(db, organization_id)
    try:
        if block_on_validation:
            return build_shared_reporting_payload(
                db,
                organization_id,
                block_on_validation=True,
                include_reporting_bundle=True,
                as_of_period=as_of_period,
            )
        return build_outlook_api_payload(db, organization_id, as_of_period=as_of_period)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@reporting_outlook_router.get("/trace")
def reporting_source_trace(
    organization_id: uuid.UUID,
    period: str = Query(min_length=7, max_length=10),
    grain: str = Query("account"),
    account_number: str = Query(""),
    account_name: str = Query(""),
    include_entries: bool = Query(False),
    offset: int = Query(0, ge=0),
    deal_type: str = Query(""),
    deal_offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """The records that add up to one number for one month."""
    org = get_organization_or_404(db, organization_id)
    try:
        close = resolve_org_close_month(db, org)
        return build_source_trace(
            db,
            organization_id,
            period=period,
            close=close,
            grain=grain,
            account_number=account_number,
            account_name=account_name,
            include_entries=include_entries,
            offset=offset,
            deal_type=deal_type,
            deal_offset=deal_offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
