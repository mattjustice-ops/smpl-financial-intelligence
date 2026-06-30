"""Aggregate queries for SMPL Ops dashboard."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.usage_event import UsageEvent
from app.services.reporting.export.export_jobs import list_export_jobs_snapshot


def _since(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def customer_usage_summary(db: Session, *, days: int = 30) -> dict[str, Any]:
    since = _since(days)

    llm_rows = db.execute(
        select(
            UsageEvent.organization_id,
            func.coalesce(func.sum(UsageEvent.estimated_cost_usd), 0).label("ai_cost_usd"),
            func.coalesce(func.sum(UsageEvent.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(UsageEvent.output_tokens), 0).label("output_tokens"),
            func.count().label("llm_calls"),
        )
        .where(
            UsageEvent.created_at >= since,
            UsageEvent.event_type == "llm_call",
        )
        .group_by(UsageEvent.organization_id)
    ).all()

    export_rows = db.execute(
        select(
            UsageEvent.organization_id,
            func.count().label("exports"),
        )
        .where(
            UsageEvent.created_at >= since,
            UsageEvent.event_type == "export_complete",
        )
        .group_by(UsageEvent.organization_id)
    ).all()

    org_ids = {row.organization_id for row in llm_rows if row.organization_id}
    org_ids.update(row.organization_id for row in export_rows if row.organization_id)

    org_map: dict[uuid.UUID, Organization] = {}
    if org_ids:
        orgs = db.scalars(select(Organization).where(Organization.id.in_(org_ids))).all()
        org_map = {org.id: org for org in orgs}

    llm_by_org = {row.organization_id: row for row in llm_rows}
    export_by_org = {row.organization_id: row for row in export_rows}

    customers: list[dict[str, Any]] = []
    for org_id in org_ids:
        org = org_map.get(org_id) if org_id else None
        llm = llm_by_org.get(org_id)
        exports = export_by_org.get(org_id)
        ai_cost = float(llm.ai_cost_usd) if llm and llm.ai_cost_usd is not None else 0.0
        customers.append(
            {
                "organization_id": str(org_id) if org_id else None,
                "organization_name": org.name if org else "Unknown",
                "plan": org.plan if org else None,
                "status": org.status if org else None,
                "ai_cost_usd": round(ai_cost, 4),
                "input_tokens": int(llm.input_tokens) if llm else 0,
                "output_tokens": int(llm.output_tokens) if llm else 0,
                "llm_calls": int(llm.llm_calls) if llm else 0,
                "exports_complete": int(exports.exports) if exports else 0,
            }
        )

    customers.sort(key=lambda row: row["ai_cost_usd"], reverse=True)

    totals = db.execute(
        select(
            func.coalesce(func.sum(UsageEvent.estimated_cost_usd), 0),
            func.coalesce(func.sum(UsageEvent.input_tokens), 0),
            func.coalesce(func.sum(UsageEvent.output_tokens), 0),
            func.count(),
        ).where(
            UsageEvent.created_at >= since,
            UsageEvent.event_type == "llm_call",
        )
    ).one()

    export_total = db.scalar(
        select(func.count())
        .select_from(UsageEvent)
        .where(
            UsageEvent.created_at >= since,
            UsageEvent.event_type == "export_complete",
        )
    )

    return {
        "period_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "totals": {
            "ai_cost_usd": round(float(totals[0] or 0), 4),
            "input_tokens": int(totals[1] or 0),
            "output_tokens": int(totals[2] or 0),
            "llm_calls": int(totals[3] or 0),
            "exports_complete": int(export_total or 0),
            "active_organizations": len(customers),
        },
        "customers": customers,
    }


def platform_health_summary(db: Session) -> dict[str, Any]:
    now = time.time()
    since_24h = _since(1)

    active_jobs = list_export_jobs_snapshot()

    failed_exports_24h = db.scalar(
        select(func.count())
        .select_from(UsageEvent)
        .where(
            UsageEvent.created_at >= since_24h,
            UsageEvent.event_type == "export_failed",
        )
    )

    llm_calls_24h = db.scalar(
        select(func.count())
        .select_from(UsageEvent)
        .where(
            UsageEvent.created_at >= since_24h,
            UsageEvent.event_type == "llm_call",
        )
    )

    ai_cost_24h = db.scalar(
        select(func.coalesce(func.sum(UsageEvent.estimated_cost_usd), 0))
        .select_from(UsageEvent)
        .where(
            UsageEvent.created_at >= since_24h,
            UsageEvent.event_type == "llm_call",
        )
    )

    recent_failures = db.scalars(
        select(UsageEvent)
        .where(UsageEvent.event_type.in_(("export_failed", "platform_check")))
        .order_by(UsageEvent.created_at.desc())
        .limit(10)
    ).all()

    db_ok = True
    db_latency_ms: int | None = None
    try:
        started = time.perf_counter()
        db.execute(text("SELECT 1"))
        db_latency_ms = int((time.perf_counter() - started) * 1000)
    except Exception:
        db_ok = False

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database": {
            "ok": db_ok,
            "latency_ms": db_latency_ms,
        },
        "export_jobs": {
            "active_count": len(active_jobs),
            "jobs": active_jobs,
        },
        "last_24h": {
            "llm_calls": int(llm_calls_24h or 0),
            "ai_cost_usd": round(float(ai_cost_24h or 0), 4),
            "export_failures": int(failed_exports_24h or 0),
        },
        "recent_events": [
            {
                "event_type": event.event_type,
                "feature": event.feature,
                "organization_id": str(event.organization_id) if event.organization_id else None,
                "created_at": event.created_at.isoformat(),
                "metadata": event.metadata_json,
            }
            for event in recent_failures
        ],
        "checked_at_epoch": now,
    }
