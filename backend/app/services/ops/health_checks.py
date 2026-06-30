"""Scheduled / on-demand platform health checks for SMPL Ops alerts."""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.usage_event import UsageEvent
from app.services.ops.storage_snapshot import maybe_collect_storage_snapshot
from app.services.ops.usage_tracking import record_usage_event
from app.services.ops.warehouse_health import warehouse_health_check_row
from app.services.reporting.export.export_jobs import list_export_jobs_snapshot


def _check(name: str, ok: bool, *, detail: str = "", latency_ms: int | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {"name": name, "ok": ok, "detail": detail}
    if latency_ms is not None:
        row["latency_ms"] = latency_ms
    return row


def run_platform_health_checks(db: Session, *, collect_storage: bool = True) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    started = time.perf_counter()
    try:
        db.execute(text("SELECT 1"))
        checks.append(
            _check(
                "database_query",
                True,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
        )
    except Exception as exc:
        checks.append(_check("database_query", False, detail=str(exc)))

    api_base = os.environ.get("SFI_PUBLIC_API_URL", "").strip().rstrip("/")
    if api_base:
        try:
            started = time.perf_counter()
            with httpx.Client(timeout=15.0) as client:
                res = client.get(f"{api_base}/health")
            ok = res.status_code == 200 and res.json().get("status") == "ok"
            checks.append(
                _check(
                    "api_health",
                    ok,
                    detail=f"HTTP {res.status_code}",
                    latency_ms=int((time.perf_counter() - started) * 1000),
                )
            )
        except Exception as exc:
            checks.append(_check("api_health", False, detail=str(exc)))
    else:
        checks.append(_check("api_health", True, detail="skipped (SFI_PUBLIC_API_URL unset)"))

    warehouse_summary: dict[str, Any] | None = None
    try:
        wh = warehouse_health_check_row(db)
        checks.append(_check(wh["name"], wh["ok"], detail=wh["detail"]))
        warehouse_summary = wh.get("warehouse")
    except Exception as exc:
        checks.append(_check("customer_warehouse_board", False, detail=str(exc)))

    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    failed_exports = db.scalar(
        select(func.count())
        .select_from(UsageEvent)
        .where(
            UsageEvent.created_at >= since_24h,
            UsageEvent.event_type == "export_failed",
        )
    )
    export_failures = int(failed_exports or 0)
    checks.append(
        _check(
            "export_failures_24h",
            export_failures == 0,
            detail=f"{export_failures} failed export(s) in last 24h",
        )
    )

    active_jobs = list_export_jobs_snapshot()
    stuck_jobs = [
        job
        for job in active_jobs
        if job.get("status") in ("running", "queued")
        and (job.get("running_seconds") or job.get("age_seconds") or 0) > 900
    ]
    checks.append(
        _check(
            "export_job_queue",
            len(stuck_jobs) == 0,
            detail=f"{len(active_jobs)} active job(s), {len(stuck_jobs)} over 15 min",
        )
    )

    storage_payload: dict[str, Any] | None = None
    if collect_storage:
        try:
            storage_payload = maybe_collect_storage_snapshot(db, force=False)
        except Exception as exc:
            checks.append(_check("storage_snapshot", False, detail=str(exc)))
        else:
            checks.append(_check("storage_snapshot", True, detail="captured or fresh within 20h"))

    all_ok = all(check["ok"] for check in checks)
    payload = {
        "status": "ok" if all_ok else "degraded",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "active_export_jobs": len(active_jobs),
        "storage": storage_payload,
        "warehouse": warehouse_summary,
    }
    record_usage_event(
        event_type="health_check",
        feature="ops_alerts",
        metadata=payload,
        db=db,
    )
    return payload
