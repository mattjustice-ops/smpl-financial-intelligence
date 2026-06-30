"""Append-only pipeline ledger for CSV + API ingest and close tracking."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.pipeline import IngestBatch, PipelineEvent
from app.services.ops.ops_period import parse_calendar_month


def create_ingest_batch(
    db: Session,
    *,
    organization_id: uuid.UUID,
    source: str,
    entity_type: str | None = None,
    filename: str | None = None,
    external_batch_id: str | None = None,
    idempotency_key: str | None = None,
    period: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> IngestBatch:
    batch = IngestBatch(
        organization_id=organization_id,
        source=source,
        status="received",
        entity_type=entity_type,
        filename=filename,
        external_batch_id=external_batch_id,
        idempotency_key=idempotency_key,
        period=period,
        metadata_json=metadata,
    )
    db.add(batch)
    db.flush()
    record_pipeline_event(
        db,
        organization_id=organization_id,
        batch_id=batch.id,
        event_type="batch_received",
        source=source,
        entity_type=entity_type,
        period=period,
        metadata={
            "filename": filename,
            "external_batch_id": external_batch_id,
        },
    )
    return batch


def find_batch_by_idempotency(
    db: Session,
    *,
    organization_id: uuid.UUID,
    idempotency_key: str,
) -> IngestBatch | None:
    return db.scalars(
        select(IngestBatch).where(
            IngestBatch.organization_id == organization_id,
            IngestBatch.idempotency_key == idempotency_key,
        )
    ).first()


def update_batch_counts(
    db: Session,
    batch: IngestBatch,
    *,
    status: str,
    rows_staged: int | None = None,
    rows_imported: int | None = None,
    rows_rejected: int | None = None,
    metadata: dict[str, Any] | None = None,
    complete: bool = False,
) -> IngestBatch:
    batch.status = status
    if rows_staged is not None:
        batch.rows_staged = rows_staged
    if rows_imported is not None:
        batch.rows_imported = rows_imported
    if rows_rejected is not None:
        batch.rows_rejected = rows_rejected
    if metadata:
        merged = dict(batch.metadata_json or {})
        merged.update(metadata)
        batch.metadata_json = merged
    batch.updated_at = datetime.now(timezone.utc)
    if complete:
        batch.completed_at = datetime.now(timezone.utc)
    db.flush()
    return batch


def record_pipeline_event(
    db: Session,
    *,
    organization_id: uuid.UUID,
    event_type: str,
    source: str,
    batch_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    period: str | None = None,
    row_number: int | None = None,
    external_id: str | None = None,
    field_name: str | None = None,
    error_code: str | None = None,
    message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> PipelineEvent:
    event = PipelineEvent(
        organization_id=organization_id,
        batch_id=batch_id,
        event_type=event_type,
        source=source,
        entity_type=entity_type,
        period=period,
        row_number=row_number,
        external_id=external_id,
        field_name=field_name,
        error_code=error_code,
        message=message,
        metadata_json=metadata,
    )
    db.add(event)
    db.flush()
    return event


def record_row_validation_errors(
    db: Session,
    *,
    organization_id: uuid.UUID,
    batch_id: uuid.UUID,
    source: str,
    entity_type: str | None,
    validation_errors: list[dict[str, Any]],
) -> None:
    for err in validation_errors:
        row_index = err.get("row_index")
        external_id = err.get("external_id")
        if isinstance(err.get("errors"), list) and err["errors"]:
            first = err["errors"][0]
            field_name = ".".join(str(part) for part in first.get("loc", ()))
            error_code = str(first.get("type") or "validation_error")
            message = str(first.get("msg") or "Validation failed")
        else:
            field_name = err.get("field")
            error_code = str(err.get("code") or "validation_error")
            message = str(err.get("message") or err)

        record_pipeline_event(
            db,
            organization_id=organization_id,
            batch_id=batch_id,
            event_type="row_error",
            source=source,
            entity_type=entity_type,
            row_number=int(row_index) if row_index is not None else None,
            external_id=str(external_id) if external_id is not None else None,
            field_name=str(field_name) if field_name else None,
            error_code=error_code,
            message=message,
            metadata={"raw": err},
        )


def batch_to_payload(batch: IngestBatch) -> dict[str, Any]:
    return {
        "batch_id": str(batch.id),
        "organization_id": str(batch.organization_id),
        "source": batch.source,
        "status": batch.status,
        "entity_type": batch.entity_type,
        "filename": batch.filename,
        "external_batch_id": batch.external_batch_id,
        "period": batch.period,
        "rows_staged": batch.rows_staged,
        "rows_imported": batch.rows_imported,
        "rows_rejected": batch.rows_rejected,
        "metadata": batch.metadata_json,
        "created_at": batch.created_at.isoformat(),
        "updated_at": batch.updated_at.isoformat(),
        "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
    }


def event_to_payload(event: PipelineEvent) -> dict[str, Any]:
    return {
        "event_id": str(event.id),
        "batch_id": str(event.batch_id) if event.batch_id else None,
        "event_type": event.event_type,
        "source": event.source,
        "entity_type": event.entity_type,
        "period": event.period,
        "row_number": event.row_number,
        "external_id": event.external_id,
        "field_name": event.field_name,
        "error_code": event.error_code,
        "message": event.message,
        "metadata": event.metadata_json,
        "created_at": event.created_at.isoformat(),
    }


def list_batches(
    db: Session,
    *,
    organization_id: uuid.UUID,
    limit: int = 50,
) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(IngestBatch)
        .where(IngestBatch.organization_id == organization_id)
        .order_by(IngestBatch.created_at.desc())
        .limit(max(1, min(limit, 200)))
    ).all()
    return [batch_to_payload(row) for row in rows]


def get_batch(
    db: Session,
    *,
    organization_id: uuid.UUID,
    batch_id: uuid.UUID,
) -> IngestBatch | None:
    return db.scalars(
        select(IngestBatch).where(
            IngestBatch.id == batch_id,
            IngestBatch.organization_id == organization_id,
        )
    ).first()


def list_batch_events(
    db: Session,
    *,
    organization_id: uuid.UUID,
    batch_id: uuid.UUID,
    limit: int = 500,
) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(PipelineEvent)
        .where(
            PipelineEvent.organization_id == organization_id,
            PipelineEvent.batch_id == batch_id,
        )
        .order_by(PipelineEvent.created_at.asc())
        .limit(max(1, min(limit, 2000)))
    ).all()
    return [event_to_payload(row) for row in rows]


def close_ledger_summary(
    db: Session,
    *,
    organization_id: uuid.UUID,
    month: str | None = None,
    days: int | None = None,
) -> dict[str, Any]:
    if month:
        start, end = parse_calendar_month(month)
        period = {"kind": "calendar_month", "month": month}
    else:
        from datetime import timedelta

        bounded = max(1, min(days or 30, 90))
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=bounded)
        period = {"kind": "rolling_days", "days": bounded}

    try:
        batch_rows = db.scalars(
            select(IngestBatch).where(
                IngestBatch.organization_id == organization_id,
                IngestBatch.created_at >= start,
                IngestBatch.created_at < end,
            )
        ).all()
    except Exception:
        db.rollback()
        return {
            "period": period,
            "ingest_by_source": {},
            "event_totals": {},
            "recent_row_errors": [],
            "recent_batches": [],
            "ledger_available": False,
        }

    by_source: dict[str, dict[str, int]] = {}
    for batch in batch_rows:
        bucket = by_source.setdefault(
            batch.source,
            {"batches": 0, "rows_staged": 0, "rows_imported": 0, "rows_rejected": 0},
        )
        bucket["batches"] += 1
        bucket["rows_staged"] += batch.rows_staged
        bucket["rows_imported"] += batch.rows_imported
        bucket["rows_rejected"] += batch.rows_rejected

    event_counts = db.execute(
        select(PipelineEvent.event_type, func.count())
        .where(
            PipelineEvent.organization_id == organization_id,
            PipelineEvent.created_at >= start,
            PipelineEvent.created_at < end,
        )
        .group_by(PipelineEvent.event_type)
    ).all()

    row_errors = db.scalars(
        select(PipelineEvent)
        .where(
            PipelineEvent.organization_id == organization_id,
            PipelineEvent.created_at >= start,
            PipelineEvent.created_at < end,
            PipelineEvent.event_type == "row_error",
        )
        .order_by(PipelineEvent.created_at.desc())
        .limit(25)
    ).all()

    return {
        "period": period,
        "ingest_by_source": by_source,
        "event_totals": {event_type: int(count) for event_type, count in event_counts},
        "recent_row_errors": [event_to_payload(event) for event in row_errors],
        "recent_batches": [batch_to_payload(batch) for batch in batch_rows[:12]],
        "ledger_available": True,
    }
