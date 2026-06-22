"""Shared reporting outlook payload for Board Platform + Forecast Engine."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.organizations import get_organization_or_404
from app.services.reporting.three_statement_payload import build_shared_reporting_payload

reporting_outlook_router = APIRouter(prefix="/reporting", tags=["reporting-outlook"])


@reporting_outlook_router.get("/outlook")
def reporting_outlook_payload(
    organization_id: uuid.UUID,
    block_on_validation: bool = Query(False),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Single warehouse outlook payload — both board and forecast surfaces hydrate from this."""
    get_organization_or_404(db, organization_id)
    payload = build_shared_reporting_payload(
        db,
        organization_id,
        block_on_validation=block_on_validation,
    )
    return {
        "meta": payload["meta"],
        "TS_DATA": payload["TS_DATA"],
        "SRC": payload["SRC"],
        "ARR_WATERFALL": payload["ARR_WATERFALL"],
        "CASH_BRIDGE": payload.get("CASH_BRIDGE"),
        "baseline_engine": payload["baseline_engine"],
    }
