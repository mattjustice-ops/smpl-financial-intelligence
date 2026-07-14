"""Customer Close Workflow API — status, lock, reopen, receipts, unload."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.organizations import get_organization_or_404

close_workflow_router = APIRouter(prefix="/close-workflow", tags=["close-workflow"])


class LockRequest(BaseModel):
    locked_by: str | None = Field(default=None, max_length=256)
    run_freeze: bool = True


class ReopenRequest(BaseModel):
    locked_by: str | None = Field(default=None, max_length=256)


class UnloadRequest(BaseModel):
    entity_type: str = Field(..., min_length=1, max_length=128)
    as_of_period: str | None = Field(default=None, max_length=7)


@close_workflow_router.get("")
def get_workflow(
    organization_id: uuid.UUID = Query(...),
    as_of_period: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    get_organization_or_404(db, organization_id)
    from app.services.close_context.close_workflow_service import get_close_workflow

    try:
        payload = get_close_workflow(db, organization_id, as_of_period=as_of_period)
        db.commit()
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@close_workflow_router.get("/receipts")
def get_receipts(
    organization_id: uuid.UUID = Query(...),
    as_of_period: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    org = get_organization_or_404(db, organization_id)
    from app.services.close_context.close_workflow_service import list_load_receipts
    from app.services.reporting.org_reporting_settings import resolve_org_reporting_window

    if as_of_period:
        period = as_of_period
    else:
        period, _, _ = resolve_org_reporting_window(db, org)
    return {
        "organization_id": str(organization_id),
        "as_of_period": period,
        "receipts": list_load_receipts(db, organization_id, period),
    }


@close_workflow_router.post("/lock")
def post_lock(
    organization_id: uuid.UUID = Query(...),
    body: LockRequest | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    get_organization_or_404(db, organization_id)
    from app.services.close_context.close_workflow_service import lock_close

    req = body or LockRequest()
    result = lock_close(
        db,
        organization_id,
        locked_by=req.locked_by,
        run_freeze=req.run_freeze,
    )
    if not result.get("ok"):
        code = result.get("code")
        status = 409 if code in ("not_ready_to_lock", "freeze_failed") else 400
        raise HTTPException(status_code=status, detail=result)
    return result


@close_workflow_router.post("/reopen")
def post_reopen(
    organization_id: uuid.UUID = Query(...),
    body: ReopenRequest | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    get_organization_or_404(db, organization_id)
    from app.services.close_context.close_workflow_service import reopen_close

    req = body or ReopenRequest()
    result = reopen_close(db, organization_id, locked_by=req.locked_by)
    if not result.get("ok"):
        raise HTTPException(status_code=409, detail=result)
    return result


@close_workflow_router.post("/unload")
def post_unload(
    organization_id: uuid.UUID = Query(...),
    body: UnloadRequest = ...,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Self-serve unload of an entity dataset for the org (replace-delete semantics)."""
    get_organization_or_404(db, organization_id)
    from app.services.close_context.close_workflow_unload import unload_entity_dataset

    try:
        result = unload_entity_dataset(
            db,
            organization_id,
            entity_type=body.entity_type,
            as_of_period=body.as_of_period,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result
