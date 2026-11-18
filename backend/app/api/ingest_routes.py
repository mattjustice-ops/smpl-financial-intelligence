"""Unified ingest — CSV upload and API batches (shared pipeline ledger)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.organizations import get_organization_or_404
from app.services.close_context.named_load_remove import (
    list_period_loads,
    remove_csv_load,
    remove_named_load,
    stamp_csv_period_load,
)
from app.services.reporting.outlook_cache import forget_outlook
from app.services.workspace.ingest_service import ingest_api_records, ingest_csv_bytes

ingest_router = APIRouter(prefix="/ingest", tags=["ingest"])


class ApiIngestBatchRequest(BaseModel):
    entity_type: str = Field(..., description="SMPL entity/table kind, e.g. mrr_waterfall")
    records: list[dict[str, Any]] = Field(default_factory=list)
    external_batch_id: str | None = None
    idempotency_key: str | None = None
    source_system: str | None = Field(
        default=None,
        max_length=128,
        description="Customer system label, e.g. Salesforce, NetSuite, Stripe",
    )


class RemoveLoadRequest(BaseModel):
    system: str = Field(..., max_length=128)
    dataset: str = Field(..., max_length=256)
    as_of_period: str = Field(..., min_length=7, max_length=7)


@ingest_router.get("/loads")
def list_loads(
    organization_id: uuid.UUID = Query(...),
    as_of_period: str = Query(..., min_length=7, max_length=7),
    db: Session = Depends(get_db),
) -> dict:
    get_organization_or_404(db, organization_id)
    try:
        loads = list_period_loads(db, organization_id, as_of_period)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"as_of_period": as_of_period, "loads": loads}


@ingest_router.post("/loads/remove")
def remove_load(
    body: RemoveLoadRequest,
    organization_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    """Delete one named load for that period. The close month stays where it is."""
    get_organization_or_404(db, organization_id)
    system = body.system.strip()
    try:
        if system == "Campfire":
            from app.services.campfire.sandbox_import import remove_sandbox_load

            removed = remove_sandbox_load(
                db,
                dataset=body.dataset,
                as_of_period=body.as_of_period,
                scope="name",
            )
            forget_outlook()
            return removed
        if system == "CSV":
            removed = remove_csv_load(
                db,
                organization_id,
                dataset=body.dataset,
                as_of_period=body.as_of_period,
            )
            forget_outlook(organization_id)
            return removed
        removed = remove_named_load(
            db,
            organization_id,
            system=system,
            dataset=body.dataset,
            as_of_period=body.as_of_period,
            scope="name",
        )
        forget_outlook(organization_id)
        return removed
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@ingest_router.post("/csv")
async def ingest_csv_upload(
    organization_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    as_of_period: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> dict:
    get_organization_or_404(db, organization_id)
    raw = await file.read()
    result = ingest_csv_bytes(db, organization_id, raw, filename=file.filename)
    if result.get("header_error"):
        raise HTTPException(status_code=400, detail=result["header_error"])
    if result.get("integrity_error"):
        raise HTTPException(
            status_code=409,
            detail={
                "message": "database_integrity_error",
                "detail": result["integrity_error"],
            },
        )
    period = (as_of_period or "").strip()
    if period:
        try:
            stamped = stamp_csv_period_load(
                db,
                organization_id,
                filename=file.filename,
                as_of_period=period,
                csv_kind=result.get("csv_kind") or result.get("entity_type"),
                applied=int(result.get("rows_upserted") or 0),
                rejected=len(result.get("validation_errors") or []),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if stamped.get("load_name"):
            result["load_name"] = stamped["load_name"]
    forget_outlook(organization_id)
    return result


@ingest_router.post("/batches")
def ingest_api_batch(
    organization_id: uuid.UUID = Query(...),
    body: ApiIngestBatchRequest = ...,
    db: Session = Depends(get_db),
) -> dict:
    get_organization_or_404(db, organization_id)
    if not body.records:
        raise HTTPException(status_code=400, detail="records must not be empty")
    result = ingest_api_records(
        db,
        organization_id,
        entity_type=body.entity_type,
        records=body.records,
        external_batch_id=body.external_batch_id,
        idempotency_key=body.idempotency_key,
        source_system=body.source_system,
    )
    if result.get("header_error"):
        raise HTTPException(status_code=400, detail=result["header_error"])
    if result.get("integrity_error"):
        raise HTTPException(
            status_code=409,
            detail={
                "message": "database_integrity_error",
                "detail": result["integrity_error"],
            },
        )
    forget_outlook(organization_id)
    return result
