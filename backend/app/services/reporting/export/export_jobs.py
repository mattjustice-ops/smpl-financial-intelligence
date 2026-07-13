"""Durable background export jobs — status + artifact survive Railway restart.

In-process ThreadPoolExecutor still runs work; Postgres holds the source of truth
so a restart does not silently erase queued/running/complete jobs.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Literal

from sqlalchemy import select

logger = logging.getLogger(__name__)

ExportJobKind = Literal["mda_package", "mda_deck"]
ExportJobStatus = Literal["queued", "running", "complete", "failed"]

_JOB_TTL_SECONDS = 3600
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="export-job")
_lock = threading.Lock()
_jobs: dict[str, ExportJob] = {}
_interrupted_marked = False


class ExportJobConflictError(Exception):
    """Raised when an org already has a heavy export queued or running."""

    def __init__(self, organization_id: uuid.UUID, active_job_id: str) -> None:
        self.organization_id = organization_id
        self.active_job_id = active_job_id
        super().__init__(
            f"Organization already has an active export job ({active_job_id}). "
            "Wait for it to finish or fail before starting another."
        )


@dataclass
class ExportJob:
    job_id: str
    kind: ExportJobKind
    organization_id: uuid.UUID | None = None
    status: ExportJobStatus = "queued"
    message: str = "Queued"
    filename: str = ""
    content_type: str = ""
    content: bytes | None = None
    headers_extra: dict[str, str] = field(default_factory=dict)
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _session():
    from app.db.session import SessionLocal

    return SessionLocal()


def _record_to_job(row: Any) -> ExportJob:
    created = row.created_at.timestamp() if row.created_at else time.time()
    updated = row.updated_at.timestamp() if row.updated_at else created
    headers = row.headers_extra if isinstance(row.headers_extra, dict) else {}
    return ExportJob(
        job_id=str(row.id),
        kind=row.kind,  # type: ignore[arg-type]
        organization_id=row.organization_id,
        status=row.status,  # type: ignore[arg-type]
        message=row.message or "",
        filename=row.filename or "",
        content_type=row.content_type or "",
        content=bytes(row.content) if row.content is not None else None,
        headers_extra={str(k): str(v) for k, v in headers.items()},
        error=row.error,
        created_at=created,
        updated_at=updated,
    )


def _db_insert(job: ExportJob) -> None:
    try:
        from app.models.export_job import ExportJobRecord

        db = _session()
        try:
            expires = _utcnow() + timedelta(seconds=_JOB_TTL_SECONDS)
            db.add(
                ExportJobRecord(
                    id=uuid.UUID(job.job_id),
                    organization_id=job.organization_id,
                    kind=job.kind,
                    status=job.status,
                    message=job.message,
                    filename=job.filename,
                    content_type=job.content_type,
                    error=job.error,
                    headers_extra=job.headers_extra or None,
                    expires_at=expires,
                )
            )
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to persist export job %s to database", job.job_id)


def _db_update(job_id: str, **fields: Any) -> None:
    try:
        from app.models.export_job import ExportJobRecord

        db = _session()
        try:
            row = db.get(ExportJobRecord, uuid.UUID(job_id))
            if row is None:
                return
            for key, value in fields.items():
                setattr(row, key, value)
            row.updated_at = _utcnow()
            if fields.get("status") in ("complete", "failed") and row.completed_at is None:
                row.completed_at = _utcnow()
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to update export job %s in database", job_id)


def _db_get(job_id: str) -> ExportJob | None:
    try:
        from app.models.export_job import ExportJobRecord

        db = _session()
        try:
            row = db.get(ExportJobRecord, uuid.UUID(job_id))
            if row is None:
                return None
            return _record_to_job(row)
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to load export job %s from database", job_id)
        return None


def _db_find_active_for_org(organization_id: uuid.UUID) -> str | None:
    try:
        from app.models.export_job import ExportJobRecord

        db = _session()
        try:
            row = db.scalars(
                select(ExportJobRecord)
                .where(
                    ExportJobRecord.organization_id == organization_id,
                    ExportJobRecord.status.in_(("queued", "running")),
                )
                .order_by(ExportJobRecord.created_at.desc())
                .limit(1)
            ).first()
            return str(row.id) if row else None
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to check active export jobs for org %s", organization_id)
        return None


def _db_purge_expired() -> None:
    try:
        from app.models.export_job import ExportJobRecord

        db = _session()
        try:
            now = _utcnow()
            expired = db.scalars(
                select(ExportJobRecord).where(
                    ExportJobRecord.expires_at.is_not(None),
                    ExportJobRecord.expires_at < now,
                )
            ).all()
            for row in expired:
                db.delete(row)
            if expired:
                db.commit()
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to purge expired export jobs")


def _mark_interrupted_running_jobs() -> None:
    """On worker boot, fail any jobs left in running/queued from a prior process."""
    global _interrupted_marked
    if _interrupted_marked:
        return
    _interrupted_marked = True
    try:
        from app.models.export_job import ExportJobRecord

        db = _session()
        try:
            rows = db.scalars(
                select(ExportJobRecord).where(ExportJobRecord.status.in_(("queued", "running")))
            ).all()
            if not rows:
                return
            for row in rows:
                row.status = "failed"
                row.error = "Worker restarted before this export finished — please regenerate."
                row.message = "Interrupted by restart"
                row.completed_at = _utcnow()
                row.updated_at = _utcnow()
            db.commit()
            logger.warning("Marked %s interrupted export job(s) as failed after restart", len(rows))
        finally:
            db.close()
    except Exception:
        # Table may not exist yet (pre-migration); safe to ignore.
        logger.debug("Could not mark interrupted export jobs (table may be missing)", exc_info=True)


def _record_export_pipeline_safe(
    *,
    organization_id: uuid.UUID | None,
    event_type: str,
    export_kind: str,
    job_id: str | None = None,
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    if organization_id is None:
        return
    try:
        from app.db.session import SessionLocal
        from app.services.workspace.ingest_service import record_export_pipeline_event

        db = SessionLocal()
        try:
            record_export_pipeline_event(
                db,
                organization_id=organization_id,
                event_type=event_type,
                export_kind=export_kind,
                job_id=job_id,
                error=error,
                metadata=metadata,
            )
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to record export pipeline event %s", event_type)


def _purge_stale_memory() -> None:
    cutoff = time.time() - _JOB_TTL_SECONDS
    stale = [job_id for job_id, job in _jobs.items() if job.updated_at < cutoff]
    for job_id in stale:
        _jobs.pop(job_id, None)


def _update(job_id: str, **fields: Any) -> ExportJob:
    with _lock:
        job = _jobs[job_id]
        for key, value in fields.items():
            setattr(job, key, value)
        job.updated_at = time.time()
        snapshot = ExportJob(
            job_id=job.job_id,
            kind=job.kind,
            organization_id=job.organization_id,
            status=job.status,
            message=job.message,
            filename=job.filename,
            content_type=job.content_type,
            content=job.content,
            headers_extra=dict(job.headers_extra),
            error=job.error,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    db_fields: dict[str, Any] = {}
    for key in ("status", "message", "error", "filename", "content_type"):
        if key in fields:
            db_fields[key] = fields[key]
    if "content" in fields:
        db_fields["content"] = fields["content"]
    if "headers_extra" in fields:
        db_fields["headers_extra"] = fields["headers_extra"]
    if db_fields:
        _db_update(job_id, **db_fields)
    return snapshot


def _memory_active_for_org(organization_id: uuid.UUID) -> str | None:
    with _lock:
        for job in _jobs.values():
            if job.organization_id == organization_id and job.status in ("queued", "running"):
                return job.job_id
    return None


def submit_export_job(
    kind: ExportJobKind,
    runner: Callable[[str], None],
    *,
    filename: str,
    content_type: str,
    organization_id: uuid.UUID | None = None,
) -> ExportJob:
    from app.services.ops.usage_tracking import record_export_event

    _mark_interrupted_running_jobs()
    _purge_stale_memory()
    _db_purge_expired()

    if organization_id is not None:
        active = _memory_active_for_org(organization_id) or _db_find_active_for_org(organization_id)
        if active:
            raise ExportJobConflictError(organization_id, active)

    job_id = str(uuid.uuid4())
    job = ExportJob(
        job_id=job_id,
        kind=kind,
        organization_id=organization_id,
        filename=filename,
        content_type=content_type,
    )
    with _lock:
        _jobs[job_id] = job
    _db_insert(job)

    record_export_event("queued", kind=kind, organization_id=organization_id, job_id=job_id)
    _record_export_pipeline_safe(
        organization_id=organization_id,
        event_type="export_queued",
        export_kind=kind,
        job_id=job_id,
    )

    def _wrapped() -> None:
        started_at = time.time()
        try:
            _update(job_id, status="running", message="Starting export…")
            runner(job_id)
            with _lock:
                finished = _jobs.get(job_id)
            if finished and finished.status == "complete":
                duration_ms = int((time.time() - started_at) * 1000)
                record_export_event(
                    "complete",
                    kind=kind,
                    organization_id=organization_id,
                    job_id=job_id,
                    duration_ms=duration_ms,
                )
                _record_export_pipeline_safe(
                    organization_id=organization_id,
                    event_type="export_complete",
                    export_kind=kind,
                    job_id=job_id,
                    metadata={"duration_ms": duration_ms},
                )
        except Exception as exc:
            logger.exception("Export job %s failed", job_id)
            _update(job_id, status="failed", error=f"{type(exc).__name__}: {exc}", message="Export failed")
            duration_ms = int((time.time() - started_at) * 1000)
            record_export_event(
                "failed",
                kind=kind,
                organization_id=organization_id,
                job_id=job_id,
                duration_ms=duration_ms,
                error=f"{type(exc).__name__}: {exc}",
            )
            _record_export_pipeline_safe(
                organization_id=organization_id,
                event_type="export_failed",
                export_kind=kind,
                job_id=job_id,
                error=f"{type(exc).__name__}: {exc}",
                metadata={"duration_ms": duration_ms},
            )

    _executor.submit(_wrapped)
    return job


def get_export_job(job_id: str) -> ExportJob | None:
    with _lock:
        cached = _jobs.get(job_id)
        if cached is not None:
            return cached
    return _db_get(job_id)


def update_export_job_message(job_id: str, message: str) -> None:
    if job_id in _jobs:
        _update(job_id, message=message)
    else:
        _db_update(job_id, message=message)


def complete_export_job(
    job_id: str,
    content: bytes,
    *,
    message: str = "Complete",
    headers_extra: dict[str, str] | None = None,
) -> None:
    if not content:
        raise ValueError("Export job returned empty content")
    payload = {
        "status": "complete",
        "message": message,
        "content": content,
        "headers_extra": headers_extra or {},
        "error": None,
    }
    if job_id in _jobs:
        _update(job_id, **payload)
    else:
        _db_update(job_id, **payload)


def progress_stages_for_job(job: ExportJob) -> list[dict[str, Any]]:
    """Customer-facing checklist stages for export progress UI (Rev 4 §4A)."""
    message = (job.message or "").lower()
    status = job.status

    stages = [
        {"id": "queued", "label": "Export queued", "done": False, "current": False},
        {"id": "validated", "label": "Validation complete", "done": False, "current": False},
        {"id": "intelligence", "label": "Financial context ready", "done": False, "current": False},
        {
            "id": "narrative",
            "label": "Building package" if job.kind == "mda_package" else "Building PowerPoint",
            "done": False,
            "current": False,
        },
        {"id": "complete", "label": "Ready to download", "done": False, "current": False},
    ]

    def mark(up_to: int) -> None:
        for i, stage in enumerate(stages):
            stage["done"] = i < up_to or (status == "complete" and i <= up_to)
            stage["current"] = i == up_to and status not in ("complete", "failed")

    if status == "complete" or ("ready" in message and status != "failed"):
        for stage in stages:
            stage["done"] = True
            stage["current"] = False
        return stages

    # Infer how far we got from the last status message (including failures mid-flight).
    if "generating" in message or "prompt" in message or "building" in message or "export failed" in message:
        cursor = 3
    elif "three-statement" in message or "cash bridge" in message or "loading" in message:
        cursor = 2
    elif "collecting" in message or "starting" in message:
        cursor = 1
    elif status == "queued" or message in ("", "queued") or message.startswith("queued"):
        cursor = 0
    else:
        cursor = 1

    mark(cursor)

    if status == "failed":
        for stage in stages:
            stage["current"] = False
        # Drop unfinished "Ready to download"; surface an explicit retry stage.
        stages = [stage for stage in stages if stage["id"] != "complete" or stage["done"]]
        stages.append(
            {
                "id": "failed",
                "label": "Export failed — please try again",
                "done": False,
                "current": True,
                "failed": True,
            }
        )

    return stages


def estimated_remaining_seconds(job: ExportJob) -> int | None:
    if job.status in ("complete", "failed"):
        return 0 if job.status == "complete" else None
    elapsed = max(0, time.time() - job.created_at)
    # Conservative close-week ETA: decks often 3–8 minutes
    target = 420.0 if job.kind == "mda_deck" else 300.0
    remaining = int(max(30, target - elapsed))
    return remaining


def job_status_payload(job: ExportJob) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "kind": job.kind,
        "status": job.status,
        "message": job.message,
        "filename": job.filename,
        "error": job.error,
        "organization_id": str(job.organization_id) if job.organization_id else None,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "durable": True,
        "progress": progress_stages_for_job(job),
        "eta_seconds": estimated_remaining_seconds(job),
    }


def list_export_jobs_snapshot() -> list[dict[str, Any]]:
    """Job snapshot for SMPL Ops — prefers durable DB rows, falls back to memory."""
    _mark_interrupted_running_jobs()
    _purge_stale_memory()
    _db_purge_expired()

    rows: list[dict[str, Any]] = []
    try:
        from app.models.export_job import ExportJobRecord

        db = _session()
        try:
            cutoff = _utcnow() - timedelta(seconds=_JOB_TTL_SECONDS)
            records = db.scalars(
                select(ExportJobRecord)
                .where(ExportJobRecord.created_at >= cutoff)
                .order_by(ExportJobRecord.created_at.desc())
                .limit(20)
            ).all()
            now = time.time()
            for row in records:
                created = row.created_at.timestamp() if row.created_at else now
                updated = row.updated_at.timestamp() if row.updated_at else created
                rows.append(
                    {
                        "job_id": str(row.id),
                        "kind": row.kind,
                        "status": row.status,
                        "message": row.message or "",
                        "organization_id": str(row.organization_id) if row.organization_id else None,
                        "error": row.error,
                        "age_seconds": int(max(0, now - created)),
                        "running_seconds": int(max(0, now - updated))
                        if row.status in ("running", "queued")
                        else None,
                        "durable": True,
                    }
                )
        finally:
            db.close()
    except Exception:
        logger.debug("Export job DB snapshot unavailable; using memory", exc_info=True)

    if rows:
        return rows

    with _lock:
        jobs = list(_jobs.values())
    jobs.sort(key=lambda job: job.created_at, reverse=True)
    return [
        {
            "job_id": job.job_id,
            "kind": job.kind,
            "status": job.status,
            "message": job.message,
            "organization_id": str(job.organization_id) if job.organization_id else None,
            "error": job.error,
            "age_seconds": int(max(0, time.time() - job.created_at)),
            "running_seconds": int(max(0, time.time() - job.updated_at))
            if job.status in ("running", "queued")
            else None,
            "durable": False,
        }
        for job in jobs[:20]
    ]


def queue_depth_summary() -> dict[str, Any]:
    """Ops-facing queue counters (Must Ship: basic queue visibility)."""
    snapshot = list_export_jobs_snapshot()
    queued = sum(1 for j in snapshot if j["status"] == "queued")
    running = sum(1 for j in snapshot if j["status"] == "running")
    failed = sum(1 for j in snapshot if j["status"] == "failed")
    complete = sum(1 for j in snapshot if j["status"] == "complete")
    wait_ages = [j["age_seconds"] for j in snapshot if j["status"] == "queued"]
    return {
        "queued": queued,
        "running": running,
        "failed": failed,
        "complete": complete,
        "active_count": queued + running,
        "oldest_queued_seconds": max(wait_ages) if wait_ages else None,
        "jobs": snapshot,
    }
