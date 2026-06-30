"""SMPL Ops internal API — customer usage and platform health."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import require_internal_auth_key
from app.db.session import get_db
from app.services.ops.ops_metrics import customer_usage_summary, platform_health_summary
from app.services.ops.usage_tracking import record_usage_event

ops_router = APIRouter(prefix="/ops", tags=["ops"])


@ops_router.get("/customer-usage")
def get_customer_usage(
    days: int = 30,
    db: Session = Depends(get_db),
    _: None = Depends(require_internal_auth_key),
) -> dict:
    bounded_days = max(1, min(days, 90))
    return customer_usage_summary(db, days=bounded_days)


@ops_router.get("/platform-health")
def get_platform_health(
    db: Session = Depends(get_db),
    _: None = Depends(require_internal_auth_key),
) -> dict:
    payload = platform_health_summary(db)
    record_usage_event(event_type="platform_check", feature="ops_dashboard")
    return payload
