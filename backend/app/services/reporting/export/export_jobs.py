"""In-memory background export jobs — avoids Railway 502 on long-running deck/package builds."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

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
    status: ExportJobStatus = "queued"
    message: str = "Queued"
    filename: str = ""
    content_type: str = ""
    content: bytes | None = None
    headers_extra: dict[str, str] = field(default_factory=dict)
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


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
) -> ExportJob:
    _purge_stale_jobs()
    job_id = str(uuid.uuid4())
    job = ExportJob(
        job_id=job_id,
        kind=kind,
        filename=filename,
        content_type=content_type,
    )
    with _lock:
        _jobs[job_id] = job

    def _wrapped() -> None:
        try:
            _update(job_id, status="running", message="Starting export…")
            runner(job_id)
        except Exception as exc:
            logger.exception("Export job %s failed", job_id)
            _update(job_id, status="failed", error=f"{type(exc).__name__}: {exc}", message="Export failed")

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
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }
