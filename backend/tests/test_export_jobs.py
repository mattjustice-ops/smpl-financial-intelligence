"""Tests for background export job registry."""

from __future__ import annotations

import threading
import time
import uuid

import pytest

from app.services.reporting.export.export_jobs import (
    ExportJobConflictError,
    complete_export_job,
    get_export_job,
    job_status_payload,
    queue_depth_summary,
    submit_export_job,
    update_export_job_message,
)


def test_export_job_lifecycle() -> None:
    seen: list[str] = []

    def runner(job_id: str) -> None:
        seen.append(job_id)
        update_export_job_message(job_id, "working")
        complete_export_job(job_id, b"file-bytes", message="done")

    job = submit_export_job("mda_package", runner, filename="test.xlsx", content_type="application/xlsx")

    deadline = time.time() + 5.0
    status = "queued"
    while time.time() < deadline:
        current = get_export_job(job.job_id)
        assert current is not None
        status = current.status
        if status == "complete":
            break
        time.sleep(0.05)

    assert seen == [job.job_id]
    final = get_export_job(job.job_id)
    assert final is not None
    assert final.status == "complete"
    assert final.content == b"file-bytes"
    payload = job_status_payload(final)
    assert payload["job_id"] == job.job_id
    assert payload["status"] == "complete"
    assert payload["durable"] is True


def test_per_org_concurrency_lock() -> None:
    org_id = uuid.uuid4()
    release = threading.Event()

    def blocker(job_id: str) -> None:
        release.wait(timeout=5.0)
        complete_export_job(job_id, b"ok", message="done")

    first = submit_export_job(
        "mda_deck",
        blocker,
        filename="a.pptx",
        content_type="application/pptx",
        organization_id=org_id,
    )
    with pytest.raises(ExportJobConflictError) as exc_info:
        submit_export_job(
            "mda_deck",
            blocker,
            filename="b.pptx",
            content_type="application/pptx",
            organization_id=org_id,
        )
    assert exc_info.value.active_job_id == first.job_id
    release.set()

    deadline = time.time() + 5.0
    while time.time() < deadline:
        current = get_export_job(first.job_id)
        if current and current.status == "complete":
            break
        time.sleep(0.05)


def test_queue_depth_summary_shape() -> None:
    summary = queue_depth_summary()
    assert "queued" in summary
    assert "running" in summary
    assert "failed" in summary
    assert "active_count" in summary
    assert "jobs" in summary


def test_progress_stages_advance_with_message() -> None:
    from app.services.reporting.export.export_jobs import ExportJob, job_status_payload

    job = ExportJob(
        job_id="progress-test",
        kind="mda_deck",
        status="running",
        message="Generating MD&A deck (Prompt 5)…",
    )
    payload = job_status_payload(job)
    assert "progress" in payload
    assert payload["eta_seconds"] is not None
    stages = payload["progress"]
    assert stages[0]["done"] is True
    assert stages[3]["current"] is True
    assert stages[3]["label"] == "Building PowerPoint"


def test_progress_stages_show_failure_retry() -> None:
    from app.services.reporting.export.export_jobs import ExportJob, job_status_payload

    job = ExportJob(
        job_id="fail-test",
        kind="mda_deck",
        status="failed",
        message="Export failed",
        error="IdleInTransactionSessionTimeout",
    )
    payload = job_status_payload(job)
    assert payload["eta_seconds"] is None
    stages = payload["progress"]
    assert stages[-1]["id"] == "failed"
    assert stages[-1]["failed"] is True
    assert "try again" in stages[-1]["label"].lower()


def test_progress_stages_include_validation_check_counts() -> None:
    from app.services.reporting.export.export_jobs import ExportJob, job_status_payload

    job = ExportJob(
        job_id="checks-test",
        kind="mda_deck",
        status="running",
        message="Validation complete (9/12 checks)…",
        metadata={"validation_passed": 9, "validation_total": 12},
    )
    stages = job_status_payload(job)["progress"]
    assert stages[1]["label"] == "Validation complete (9/12 checks)"
    assert stages[1]["done"] is True or stages[1]["current"] is True

    """Regression: Neon IdleInTransactionSessionTimeout when SessionLocal stays open through Claude."""
    import inspect

    from app.api import export_routes

    for fn_name, gen_marker in (
        ("_run_mda_deck_job", "build_pptx_mda_deck("),
        ("_run_mda_package_job", "build_mda_package_xlsx_bytes("),
    ):
        src = inspect.getsource(getattr(export_routes, fn_name))
        close_at = src.find("db.close()")
        gen_at = src.find(gen_marker)
        assert close_at != -1, f"{fn_name} must close the DB session"
        assert gen_at != -1, f"{fn_name} must call {gen_marker}"
        assert close_at < gen_at, f"{fn_name} must close DB before {gen_marker}"
