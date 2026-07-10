"""Customer workspace — usage, storage, close ledger."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.organizations import get_organization_or_404
from app.services.workspace.import_trace import org_mrr_data_trace, trace_batch
from app.services.workspace.pipeline_ledger import (
    close_ledger_summary,
    get_batch,
    list_batch_events,
    list_batches,
)
from app.services.workspace.workspace_summary import workspace_summary

workspace_router = APIRouter(prefix="/workspace", tags=["workspace"])


@workspace_router.get("/summary")
def get_workspace_summary(
    organization_id: uuid.UUID = Query(...),
    month: str | None = Query(None, description="Calendar month YYYY-MM"),
    days: int | None = Query(None, ge=1, le=90),
    db: Session = Depends(get_db),
) -> dict:
    org = get_organization_or_404(db, organization_id)
    return workspace_summary(db, org, month=month, days=days)


@workspace_router.get("/close-ledger")
def get_close_ledger(
    organization_id: uuid.UUID = Query(...),
    month: str | None = Query(None),
    days: int | None = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
) -> dict:
    get_organization_or_404(db, organization_id)
    return close_ledger_summary(db, organization_id=organization_id, month=month, days=days)


@workspace_router.get("/batches")
def get_ingest_batches(
    organization_id: uuid.UUID = Query(...),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    get_organization_or_404(db, organization_id)
    return {
        "organization_id": str(organization_id),
        "batches": list_batches(db, organization_id=organization_id, limit=limit),
    }


@workspace_router.get("/batches/{batch_id}")
def get_ingest_batch_detail(
    batch_id: uuid.UUID,
    organization_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    get_organization_or_404(db, organization_id)
    batch = get_batch(db, organization_id=organization_id, batch_id=batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    from app.services.workspace.pipeline_ledger import batch_to_payload

    return {
        "batch": batch_to_payload(batch),
        "events": list_batch_events(db, organization_id=organization_id, batch_id=batch_id),
    }


@workspace_router.get("/batches/{batch_id}/trace")
def get_ingest_batch_trace(
    batch_id: uuid.UUID,
    organization_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    """Live DB row counts for a batch's destination table (verify Neon vs Railway prod)."""
    get_organization_or_404(db, organization_id)
    payload = trace_batch(db, organization_id=organization_id, batch_id=batch_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    return payload


@workspace_router.get("/data-trace")
def get_org_data_trace(
    organization_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    """MRR physical table row counts + periods — confirms which Neon branch Railway uses."""
    get_organization_or_404(db, organization_id)
    return org_mrr_data_trace(db, organization_id)
