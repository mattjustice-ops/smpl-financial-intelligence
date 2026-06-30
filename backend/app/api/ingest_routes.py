"""Unified ingest — CSV upload and API batches (shared pipeline ledger)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.organizations import get_organization_or_404
from app.services.workspace.ingest_service import ingest_api_records, ingest_csv_bytes

ingest_router = APIRouter(prefix="/ingest", tags=["ingest"])


class ApiIngestBatchRequest(BaseModel):
    entity_type: str = Field(..., description="SMPL entity/table kind, e.g. mrr_waterfall")
    records: list[dict[str, Any]] = Field(default_factory=list)
    external_batch_id: str | None = None
    idempotency_key: str | None = None


@ingest_router.post("/csv")
async def ingest_csv_upload(
    organization_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
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
    return result
