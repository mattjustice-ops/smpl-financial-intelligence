"""Tests for background export job registry."""

from app.services.reporting.export.export_jobs import (
    complete_export_job,
    get_export_job,
    job_status_payload,
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
    import time

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
