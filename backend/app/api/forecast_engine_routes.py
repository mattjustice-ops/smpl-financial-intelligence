"""Forecast Engine live payload route."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.organizations import get_organization_or_404
from app.services.reporting.three_statement_payload import build_shared_reporting_payload

forecast_engine_router = APIRouter(prefix="/forecast-engine", tags=["forecast-engine"])


@forecast_engine_router.get("/payload")
def forecast_engine_payload(
    organization_id: uuid.UUID,
    block_on_validation: bool = Query(False),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    get_organization_or_404(db, organization_id, module="forecast_engine")
    return build_shared_reporting_payload(
        db, organization_id, block_on_validation=block_on_validation
    )
