"""SMPL Ops internal API — customer usage and platform health."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps.auth import require_internal_auth_key
from app.db.session import get_db
from app.services.ops.health_checks import run_platform_health_checks
from app.services.ops.ops_metrics import customer_usage_summary, platform_health_summary
from app.services.ops.ops_period import parse_calendar_month
from app.services.ops.storage_snapshot import maybe_collect_storage_snapshot
from app.services.ops.usage_tracking import record_usage_event

ops_router = APIRouter(prefix="/ops", tags=["ops"])


@ops_router.get("/customer-usage")
def get_customer_usage(
    days: int | None = Query(default=None),
    month: str | None = Query(default=None, description="Calendar month YYYY-MM"),
    db: Session = Depends(get_db),
    _: None = Depends(require_internal_auth_key),
) -> dict:
    if month:
        try:
            parse_calendar_month(month)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return customer_usage_summary(db, month=month)
    return customer_usage_summary(db, days=days or 30)


@ops_router.get("/platform-health")
def get_platform_health(
    db: Session = Depends(get_db),
    _: None = Depends(require_internal_auth_key),
) -> dict:
    payload = platform_health_summary(db)
    record_usage_event(event_type="platform_check", feature="ops_dashboard", db=db)
    return payload


@ops_router.get("/close-readiness")
def get_close_readiness(
    month: str = Query(..., description="Close period YYYY-MM"),
    ensure_sessions: bool = Query(
        False,
        description="When true, create close_session rows for orgs that lack one",
    ),
    db: Session = Depends(get_db),
    _: None = Depends(require_internal_auth_key),
) -> dict:
    """Month-End Readiness Dashboard (§6) — one row per org for the close period."""
    from app.services.close_context.close_session_service import list_close_readiness
    from app.services.ops.ops_period import parse_calendar_month

    try:
        parse_calendar_month(month)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return list_close_readiness(db, as_of_period=month, ensure_sessions=ensure_sessions)


@ops_router.get("/close-sessions/{session_id}")
def get_close_session_detail(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: None = Depends(require_internal_auth_key),
) -> dict:
    """Support lineage lookup for a Close Session ID (§4E)."""
    from app.services.close_context.close_session_service import close_session_lineage

    payload = close_session_lineage(db, session_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Close session not found")
    return payload


@ops_router.post("/collect-storage-snapshot")
def post_collect_storage_snapshot(
    force: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: None = Depends(require_internal_auth_key),
) -> dict:
    payload = maybe_collect_storage_snapshot(db, force=force)
    if payload is None:
        raise HTTPException(status_code=500, detail="Storage snapshot failed")
    return {"ok": True, "snapshot": payload}


@ops_router.post("/run-health-check")
def post_run_health_check(
    collect_storage: bool = Query(default=True),
    db: Session = Depends(get_db),
    _: None = Depends(require_internal_auth_key),
) -> dict:
    return run_platform_health_checks(db, collect_storage=collect_storage)
