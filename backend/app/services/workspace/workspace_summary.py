"""Customer workspace summary — usage, storage, and close ledger."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.services.ops.ops_period import recent_calendar_months
from app.services.ops.storage_snapshot import maybe_collect_storage_snapshot
from app.services.ops.usage_limits import DEFAULT_USAGE_LIMITS, monthly_usage_status_payload
from app.services.workspace.load_domains import build_load_domain_status
from app.services.workspace.pipeline_ledger import close_ledger_summary
from app.services.reporting.org_reporting_settings import resolve_org_reporting_window


def workspace_summary(
    db: Session,
    org: Organization,
    *,
    month: str | None = None,
    days: int | None = None,
) -> dict[str, Any]:
    usage = monthly_usage_status_payload(db, org)
    storage = maybe_collect_storage_snapshot(db, force=False) or {}
    org_footprint = (storage.get("org_footprint") or {}).get(str(org.id)) or {}
    ledger = close_ledger_summary(db, organization_id=org.id, month=month, days=days)
    as_of, _, _ = resolve_org_reporting_window(db, org)
    load_domains = build_load_domain_status(db, org.id, as_of_period=as_of)

    return {
        "organization_id": str(org.id),
        "organization_name": org.name,
        "plan": org.plan,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "available_months": recent_calendar_months(count=12),
        "plan_limits": dict(DEFAULT_USAGE_LIMITS),
        "usage": usage,
        "storage": {
            "warehouse_rows": int(org_footprint.get("warehouse_rows") or 0),
            "estimated_storage_mb": float(org_footprint.get("estimated_storage_mb") or 0),
            "captured_at": storage.get("captured_at"),
        },
        "close_ledger": ledger,
        "load_domains": load_domains,
    }
