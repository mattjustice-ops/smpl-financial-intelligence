"""Shared reporting outlook payload for Board Platform + Forecast Engine."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.organizations import get_organization_or_404
from app.services.reporting.org_reporting_settings import (
    ensure_org_reporting_defaults,
    resolve_org_close_month,
)
from app.services.reporting.period_utils import to_period
from app.services.reporting.source_trace import build_source_trace
from app.services.reporting.outlook_cache import get_or_build
from app.services.reporting.read_cache import outlook_read_scope
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
    compile: bool = Query(
        False,
        description="Table Update: drop the outlook cache and rebuild schedules for this close.",
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Single warehouse outlook payload — both board and forecast surfaces hydrate from this."""
    org = get_organization_or_404(db, organization_id)
    try:
        if block_on_validation:
            with outlook_read_scope():
                return build_shared_reporting_payload(
                    db,
                    organization_id,
                    block_on_validation=True,
                    include_reporting_bundle=True,
                    as_of_period=as_of_period,
                )
        ensure_org_reporting_defaults(db, org)
        viewed = to_period(as_of_period) if as_of_period else to_period(org.close_month or "")
        from app.services.forecast_version_service import get_active_forecast_version
        from app.services.reporting.outlook_cache import forget_outlook

        if compile:
            # Close Engine "Build the statements" must recompile grain/flux, not serve TTL cache.
            forget_outlook(organization_id)

        active = get_active_forecast_version(db, org)
        key = (str(organization_id), viewed, str(active.id) if active else "")

        def build() -> dict[str, Any]:
            with outlook_read_scope():
                return build_outlook_api_payload(db, organization_id, as_of_period=as_of_period)

        return get_or_build(key, build)
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
