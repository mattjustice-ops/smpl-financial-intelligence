"""In-memory background export jobs — avoids Railway 502 on long-running deck/package builds."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Literal
import uuid

logger = logging.getLogger(__name__)

ExportJobKind = Literal["mda_package", "mda_deck"]
ExportJobStatus = Literal["queued", "running", "complete", "failed"]

_JOB_TTL_SECONDS = 3600
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="export-job")
_lock = threading.Lock()
_jobs: dict[str, ExportJob] = {}


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


def _purge_stale_jobs() -> None:
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
        return job


def submit_export_job(
    kind: ExportJobKind,
    runner: Callable[[str], None],
    *,
    filename: str,
    content_type: str,
    organization_id: uuid.UUID | None = None,
) -> ExportJob:
    from app.services.ops.usage_tracking import record_export_event

    _purge_stale_jobs()
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
        return _jobs.get(job_id)


def update_export_job_message(job_id: str, message: str) -> None:
    _update(job_id, message=message)


def complete_export_job(
    job_id: str,
    content: bytes,
    *,
    message: str = "Complete",
    headers_extra: dict[str, str] | None = None,
) -> None:
    if not content:
        raise ValueError("Export job returned empty content")
    _update(
        job_id,
        status="complete",
        message=message,
        content=content,
        headers_extra=headers_extra or {},
        error=None,
    )


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
    }


def list_export_jobs_snapshot() -> list[dict[str, Any]]:
    """Non-sensitive in-memory job snapshot for SMPL Ops."""
    _purge_stale_jobs()
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
        }
        for job in jobs[:20]
    ]
