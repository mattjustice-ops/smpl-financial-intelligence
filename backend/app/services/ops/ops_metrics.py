"""Aggregate queries for SMPL Ops dashboard."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.usage_event import UsageEvent
from app.core.config import get_settings
from app.services.ops.ops_period import format_calendar_month, parse_calendar_month, recent_calendar_months
from app.services.ops.storage_snapshot import (
    maybe_collect_storage_snapshot,
    storage_snapshot_history,
)
from app.services.ops.usage_limits import DEFAULT_USAGE_LIMITS, limits_for_plan
from app.services.ops.warehouse_health import assess_all_customer_warehouses
from app.services.reporting.export.export_jobs import queue_depth_summary


def _usage_percent(used: float | int, cap: int | float | None) -> float | None:
    if cap is None or cap == 0:
        return None
    return round(min(100.0, (float(used) / float(cap)) * 100.0), 1)


def _usage_window(
    *,
    days: int | None = None,
    month: str | None = None,
) -> tuple[datetime, datetime, dict[str, Any]]:
    if month:
        start, end = parse_calendar_month(month)
        period = {
            "kind": "calendar_month",
            "month": format_calendar_month(start),
            "start": start.isoformat(),
            "end": end.isoformat(),
        }
        return start, end, period

    bounded_days = max(1, min(days or 30, 90))
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=bounded_days)
    period = {
        "kind": "rolling_days",
        "days": bounded_days,
        "start": start.isoformat(),
        "end": end.isoformat(),
    }
    return start, end, period


def _merge_customer_rows(
    db: Session,
    *,
    llm_rows: list[Any],
    export_rows: list[Any],
    org_footprint: dict[str, dict[str, Any]],
    include_plan_limits: bool = False,
) -> list[dict[str, Any]]:
    org_ids: set[uuid.UUID | None] = set()
    org_ids.update(row.organization_id for row in llm_rows)
    org_ids.update(row.organization_id for row in export_rows)
    org_ids.update(uuid.UUID(org_id) for org_id in org_footprint.keys())

    org_map: dict[uuid.UUID, Organization] = {}
    real_ids = [org_id for org_id in org_ids if org_id is not None]
    if real_ids:
        orgs = db.scalars(select(Organization).where(Organization.id.in_(real_ids))).all()
        org_map = {org.id: org for org in orgs}

    llm_by_org = {row.organization_id: row for row in llm_rows}
    export_by_org = {row.organization_id: row for row in export_rows}

    customers: list[dict[str, Any]] = []
    for org_id in sorted(org_ids, key=lambda value: str(value)):
        org = org_map.get(org_id) if org_id else None
        llm = llm_by_org.get(org_id)
        exports = export_by_org.get(org_id)
        footprint = org_footprint.get(str(org_id)) if org_id else None
        ai_cost = float(llm.ai_cost_usd) if llm and llm.ai_cost_usd is not None else 0.0
        warehouse_rows = int(footprint["warehouse_rows"]) if footprint else 0
        storage_mb = float(footprint["estimated_storage_mb"]) if footprint else 0.0
        row: dict[str, Any] = {
            "organization_id": str(org_id) if org_id else None,
            "organization_name": org.name if org else "Unknown",
            "plan": org.plan if org else None,
            "status": org.status if org else None,
            "ai_cost_usd": round(ai_cost, 4),
            "input_tokens": int(llm.input_tokens) if llm else 0,
            "output_tokens": int(llm.output_tokens) if llm else 0,
            "llm_calls": int(llm.llm_calls) if llm else 0,
            "exports_complete": int(exports.exports) if exports else 0,
            "warehouse_rows": warehouse_rows,
            "estimated_storage_mb": storage_mb,
        }
        if include_plan_limits:
            limits = limits_for_plan(org.plan if org else None)
            row["limits"] = limits
            row["percent_used"] = {
                "ai_cost_usd_monthly": _usage_percent(ai_cost, limits.get("ai_cost_usd_monthly")),
                "exports_monthly": _usage_percent(
                    row["exports_complete"],
                    limits.get("exports_monthly"),
                ),
                "llm_calls_monthly": _usage_percent(row["llm_calls"], limits.get("llm_calls_monthly")),
            }
        customers.append(row)

    customers.sort(
        key=lambda row: (row["ai_cost_usd"], row["estimated_storage_mb"]),
        reverse=True,
    )
    return customers


def customer_usage_summary(
    db: Session,
    *,
    days: int | None = 30,
    month: str | None = None,
) -> dict[str, Any]:
    start, end, period = _usage_window(days=days, month=month)
    storage = maybe_collect_storage_snapshot(db, force=False) or {}
    org_footprint = storage.get("org_footprint") or {}

    llm_rows = db.execute(
        select(
            UsageEvent.organization_id,
            func.coalesce(func.sum(UsageEvent.estimated_cost_usd), 0).label("ai_cost_usd"),
            func.coalesce(func.sum(UsageEvent.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(UsageEvent.output_tokens), 0).label("output_tokens"),
            func.count().label("llm_calls"),
        )
        .where(
            UsageEvent.created_at >= start,
            UsageEvent.created_at < end,
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
            UsageEvent.created_at >= start,
            UsageEvent.created_at < end,
            UsageEvent.event_type == "export_complete",
        )
        .group_by(UsageEvent.organization_id)
    ).all()

    customers = _merge_customer_rows(
        db,
        llm_rows=llm_rows,
        export_rows=export_rows,
        org_footprint=org_footprint,
        include_plan_limits=period.get("kind") == "calendar_month",
    )

    totals = db.execute(
        select(
            func.coalesce(func.sum(UsageEvent.estimated_cost_usd), 0),
            func.coalesce(func.sum(UsageEvent.input_tokens), 0),
            func.coalesce(func.sum(UsageEvent.output_tokens), 0),
            func.count(),
        ).where(
            UsageEvent.created_at >= start,
            UsageEvent.created_at < end,
            UsageEvent.event_type == "llm_call",
        )
    ).one()

    export_total = db.scalar(
        select(func.count())
        .select_from(UsageEvent)
        .where(
            UsageEvent.created_at >= start,
            UsageEvent.created_at < end,
            UsageEvent.event_type == "export_complete",
        )
    )

    return {
        "period": period,
        "available_months": recent_calendar_months(count=12),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "plan_limits": dict(DEFAULT_USAGE_LIMITS),
        "limits_enabled": period.get("kind") == "calendar_month",
        "totals": {
            "ai_cost_usd": round(float(totals[0] or 0), 4),
            "input_tokens": int(totals[1] or 0),
            "output_tokens": int(totals[2] or 0),
            "llm_calls": int(totals[3] or 0),
            "exports_complete": int(export_total or 0),
            "active_organizations": len(customers),
            "estimated_storage_mb": round(
                sum(row["estimated_storage_mb"] for row in customers),
                3,
            ),
            "database_gb": storage.get("database_gb"),
        },
        "customers": customers,
    }


def platform_health_summary(db: Session) -> dict[str, Any]:
    now = time.time()
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)

    export_queue = queue_depth_summary()
    storage = maybe_collect_storage_snapshot(db, force=False) or {}
    storage_history = storage_snapshot_history(db, days=90)

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
        .where(UsageEvent.event_type.in_(("export_failed", "platform_check", "health_check")))
        .order_by(UsageEvent.created_at.desc())
        .limit(12)
    ).all()

    latest_health_check = db.scalars(
        select(UsageEvent)
        .where(UsageEvent.event_type == "health_check")
        .order_by(UsageEvent.created_at.desc())
        .limit(1)
    ).first()

    db_ok = True
    db_latency_ms: int | None = None
    try:
        started = time.perf_counter()
        db.execute(text("SELECT 1"))
        db_latency_ms = int((time.perf_counter() - started) * 1000)
    except Exception:
        db_ok = False

    alert_status = "unknown"
    alert_checks: list[dict[str, Any]] = []
    if latest_health_check and latest_health_check.metadata_json:
        alert_status = latest_health_check.metadata_json.get("status", "unknown")
        alert_checks = list(latest_health_check.metadata_json.get("checks", []) or [])

    settings = get_settings()
    fail_threshold = int(getattr(settings, "smpl_close_export_fail_alert_24h", 2) or 2)
    depth_threshold = int(getattr(settings, "smpl_close_queue_alert_depth", 4) or 4)
    oldest_threshold = int(getattr(settings, "smpl_close_queue_alert_oldest_seconds", 600) or 600)
    export_failures_n = int(failed_exports_24h or 0)
    oldest_queued = int(export_queue.get("oldest_queued_seconds") or 0)
    active_count = int(export_queue.get("active_count") or 0)
    live_checks = [
        {
            "name": "close_week_export_failures",
            "ok": export_failures_n < fail_threshold,
            "detail": f"{export_failures_n} failed export(s) in last 24h (alert at ≥{fail_threshold})",
        },
        {
            "name": "close_week_queue_depth",
            "ok": active_count < depth_threshold and oldest_queued < oldest_threshold,
            "detail": (
                f"{active_count} active jobs (alert at ≥{depth_threshold}), "
                f"oldest queued {oldest_queued}s (alert at ≥{oldest_threshold}s)"
            ),
        },
    ]
    # Prefer live close-week signals on the dashboard even before a stored health check runs.
    for live in live_checks:
        alert_checks = [c for c in alert_checks if c.get("name") != live["name"]]
        alert_checks.append(live)
    if any(not c.get("ok") for c in live_checks):
        alert_status = "degraded"

    warehouse = assess_all_customer_warehouses(db)
    warehouse_ok = bool(warehouse.get("ok"))

    from app.services.ops.close_workflow_alerts import assess_close_workflow_alerts

    close_workflow = assess_close_workflow_alerts(db)
    for live in close_workflow.get("checks") or []:
        alert_checks = [c for c in alert_checks if c.get("name") != live["name"]]
        alert_checks.append(live)
    if not close_workflow.get("ok"):
        alert_status = "degraded"

    effective_status = "ok"
    if not db_ok or not warehouse_ok:
        effective_status = "degraded"
    elif alert_status == "degraded" or not close_workflow.get("ok"):
        effective_status = "degraded"
    elif alert_status == "unknown" and not alert_checks:
        effective_status = "unknown"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database": {
            "ok": db_ok,
            "latency_ms": db_latency_ms,
        },
        "warehouse": warehouse,
        "storage": {
            "database_gb": storage.get("database_gb"),
            "tenant_table_gb": storage.get("tenant_table_gb"),
            "captured_at": storage.get("captured_at"),
            "top_tables": storage.get("top_tables") or [],
            "history": storage_history,
        },
        "alerts": {
            "status": effective_status,
            "stored_status": alert_status,
            "last_check_at": latest_health_check.created_at.isoformat()
            if latest_health_check
            else None,
            "checks": alert_checks,
        },
        "export_jobs": {
            "active_count": export_queue["active_count"],
            "queued": export_queue["queued"],
            "running": export_queue["running"],
            "failed": export_queue["failed"],
            "complete": export_queue["complete"],
            "oldest_queued_seconds": export_queue["oldest_queued_seconds"],
            "durable": True,
            "jobs": export_queue["jobs"],
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
        "deploy_freeze": {
            "active": bool(getattr(settings, "smpl_deploy_freeze", False)),
            "note": getattr(settings, "smpl_deploy_freeze_note", "") or "",
            "until": getattr(settings, "smpl_deploy_freeze_until", None),
        },
        "close_workflow": close_workflow,
    }
