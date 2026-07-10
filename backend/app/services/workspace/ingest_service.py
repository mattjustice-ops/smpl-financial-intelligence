"""Unified CSV + API ingest with pipeline ledger."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.services.demo_csv.loader import LoadResult, load_demo_csv_core, load_entity_records, parse_csv
from app.services.workspace.import_trace import enrich_ingest_result, resolve_csv_destination
from app.services.workspace.pipeline_ledger import (
    batch_to_payload,
    create_ingest_batch,
    find_batch_by_idempotency,
    get_batch,
    record_pipeline_event,
    record_row_validation_errors,
    update_batch_counts,
)


def _finalize_batch(
    db: Session,
    batch_id: uuid.UUID,
    organization_id: uuid.UUID,
    res: LoadResult,
    *,
    rows_staged: int,
) -> dict[str, Any]:
    batch = get_batch(db, organization_id=organization_id, batch_id=batch_id)
    if batch is None:
        raise RuntimeError("ingest batch missing after load")

    source = batch.source

    if res.header_error:
        update_batch_counts(
            db,
            batch,
            status="failed",
            rows_staged=rows_staged,
            rows_rejected=rows_staged,
            metadata={"header_error": res.header_error},
            complete=True,
        )
        record_pipeline_event(
            db,
            organization_id=organization_id,
            batch_id=batch.id,
            event_type="batch_failed",
            source=source,
            entity_type=res.csv_kind,
            message=str(res.header_error.get("message") or "header_error"),
            metadata=res.header_error,
        )
        db.commit()
        return {"batch": batch_to_payload(batch), "header_error": res.header_error}

    if res.integrity_error:
        update_batch_counts(
            db,
            batch,
            status="failed",
            rows_staged=rows_staged,
            rows_rejected=max(rows_staged - res.rows_upserted, 0),
            metadata={"integrity_error": res.integrity_error},
            complete=True,
        )
        record_pipeline_event(
            db,
            organization_id=organization_id,
            batch_id=batch.id,
            event_type="batch_failed",
            source=source,
            entity_type=res.csv_kind,
            message=res.integrity_error,
        )
        db.commit()
        return {"batch": batch_to_payload(batch), "integrity_error": res.integrity_error}

    rejected = len(res.validation_errors)
    imported = res.rows_upserted if res.did_upsert else 0
    status = "complete" if res.did_upsert and not rejected else ("partial" if imported else "failed")

    destination = resolve_csv_destination(batch.filename)
    batch.entity_type = res.csv_kind
    batch_metadata = {
        "csv_kind": res.csv_kind,
        "warnings": res.warnings,
        "destination_kind": destination.get("destination_kind"),
        "destination_table": destination.get("destination_table"),
        "reporting_table": destination.get("reporting_table"),
        "reporting_reads_this_table": destination.get("reporting_reads_this_table"),
        "replace_all_org_rows": destination.get("replace_all_org_rows"),
    }

    update_batch_counts(
        db,
        batch,
        status=status,
        rows_staged=rows_staged,
        rows_imported=imported,
        rows_rejected=rejected,
        metadata=batch_metadata,
        complete=True,
    )

    record_pipeline_event(
        db,
        organization_id=organization_id,
        batch_id=batch.id,
        event_type="rows_staged",
        source=source,
        entity_type=res.csv_kind,
        metadata={"rows_staged": rows_staged},
    )

    if res.validation_errors:
        record_row_validation_errors(
            db,
            organization_id=organization_id,
            batch_id=batch.id,
            source=source,
            entity_type=res.csv_kind,
            validation_errors=res.validation_errors,
        )
        record_pipeline_event(
            db,
            organization_id=organization_id,
            batch_id=batch.id,
            event_type="rows_rejected",
            source=source,
            entity_type=res.csv_kind,
            metadata={"rows_rejected": rejected},
        )

    if imported:
        record_pipeline_event(
            db,
            organization_id=organization_id,
            batch_id=batch.id,
            event_type="rows_imported",
            source=source,
            entity_type=res.csv_kind,
            metadata={"rows_imported": imported},
        )

    db.commit()
    return enrich_ingest_result(
        db,
        organization_id,
        {
            "batch": batch_to_payload(batch),
            "csv_kind": res.csv_kind,
            "entity_type": res.csv_kind,
            "rows_upserted": imported,
            "validation_errors": res.validation_errors,
            "warnings": res.warnings,
        },
        filename=batch.filename,
    )


def ingest_csv_bytes(
    db: Session,
    organization_id: uuid.UUID,
    content: bytes,
    *,
    filename: str | None = None,
) -> dict[str, Any]:
    _, raw_rows = parse_csv(content)
    rows_staged = len(raw_rows)

    batch = create_ingest_batch(
        db,
        organization_id=organization_id,
        source="csv_upload",
        filename=filename,
        metadata={"rows_staged_hint": rows_staged},
    )
    update_batch_counts(db, batch, status="staging", rows_staged=rows_staged)
    db.commit()

    res = load_demo_csv_core(db, organization_id, content, filename=filename)
    if res.did_upsert:
        db.commit()
    else:
        db.rollback()

    return _finalize_batch(db, batch.id, organization_id, res, rows_staged=rows_staged)


def ingest_api_records(
    db: Session,
    organization_id: uuid.UUID,
    *,
    entity_type: str,
    records: list[dict[str, Any]],
    external_batch_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    if idempotency_key:
        existing = find_batch_by_idempotency(
            db,
            organization_id=organization_id,
            idempotency_key=idempotency_key,
        )
        if existing:
            return {"batch": batch_to_payload(existing), "deduplicated": True}

    batch = create_ingest_batch(
        db,
        organization_id=organization_id,
        source="api",
        entity_type=entity_type,
        external_batch_id=external_batch_id,
        idempotency_key=idempotency_key,
        metadata={"record_count": len(records)},
    )
    rows_staged = len(records)
    update_batch_counts(db, batch, status="staging", rows_staged=rows_staged)
    db.commit()

    res = load_entity_records(db, organization_id, entity_type, records)
    if res.did_upsert:
        db.commit()
    else:
        db.rollback()

    return _finalize_batch(db, batch.id, organization_id, res, rows_staged=rows_staged)


def record_export_pipeline_event(
    db: Session,
    *,
    organization_id: uuid.UUID,
    event_type: str,
    export_kind: str,
    job_id: str | None = None,
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    merged = dict(metadata or {})
    if job_id:
        merged["job_id"] = job_id
    record_pipeline_event(
        db,
        organization_id=organization_id,
        event_type=event_type,
        source="system",
        entity_type=export_kind,
        message=error,
        metadata=merged,
    )
    db.commit()
