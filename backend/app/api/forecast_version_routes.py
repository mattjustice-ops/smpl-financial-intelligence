"""Forecast version lifecycle routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.forecast_version import ForecastDraftCreate, ForecastPromoteResponse, ForecastVersionOut
from app.services.forecast_version_service import (
    list_forecast_versions,
    promote_forecast_version,
    save_forecast_draft,
)

forecast_versions_router = APIRouter(prefix="/forecast/versions", tags=["forecast-versions"])


@forecast_versions_router.get("", response_model=list[ForecastVersionOut])
def get_forecast_versions(
    organization_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[ForecastVersionOut]:
    versions = list_forecast_versions(db, organization_id)
    return [ForecastVersionOut.model_validate(v) for v in versions]


@forecast_versions_router.post("/draft", response_model=ForecastVersionOut)
def create_or_update_forecast_draft(
    organization_id: uuid.UUID,
    body: ForecastDraftCreate,
    db: Session = Depends(get_db),
) -> ForecastVersionOut:
    version = save_forecast_draft(
        db,
        organization_id,
        version_name=body.version_name,
        as_of_period=body.as_of_period,
        horizon=body.horizon,
        levers=body.levers,
        req_active=body.req_active,
        results=body.results,
        tables=body.tables,
        version_id=body.version_id,
    )
    return ForecastVersionOut.model_validate(version)


@forecast_versions_router.post("/{version_id}/promote", response_model=ForecastPromoteResponse)
def promote_version(
    organization_id: uuid.UUID,
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ForecastPromoteResponse:
    version = promote_forecast_version(db, organization_id, version_id)
    return ForecastPromoteResponse(version=ForecastVersionOut.model_validate(version))
