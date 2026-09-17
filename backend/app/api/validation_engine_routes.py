"""Validation Engine API — Monthly Align Allow + GL mapping queue (owner surface)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.organizations import get_organization_or_404
from app.services.validation_engine import (
    assert_import_mapping_clear,
    get_validation_status,
    map_account,
    record_allow,
    revoke_allow,
    seed_demo_mapping_queue_if_empty,
    unmap_account,
    upsert_mapping_queue,
)

validation_engine_router = APIRouter(prefix="/validation-engine", tags=["validation-engine"])


class AllowRequest(BaseModel):
    allowed_by: str = Field(..., min_length=1, max_length=256)
    notes: str | None = Field(default=None, max_length=2000)


class RevokeRequest(BaseModel):
    revoked_by: str | None = Field(default=None, max_length=256)


class MapAccountRequest(BaseModel):
    account_id: str = Field(..., min_length=1, max_length=128)
    mapped_to: str = Field(..., min_length=1, max_length=64)
    mapped_by: str | None = Field(default=None, max_length=256)


class UnmapAccountRequest(BaseModel):
    account_id: str = Field(..., min_length=1, max_length=128)
    unmapped_by: str | None = Field(default=None, max_length=256)


class UpsertQueueRequest(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)


@validation_engine_router.get("/status")
def validation_status(
    organization_id: uuid.UUID = Query(...),
    as_of_period: str = Query(..., min_length=7, max_length=7),
    seed_demo_queue: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    get_organization_or_404(db, organization_id)
    if seed_demo_queue:
        try:
            return seed_demo_mapping_queue_if_empty(db, organization_id, as_of_period)
        except ValueError as exc:
            if str(exc) == "no_freeze_pack":
                return {
                    "organization_id": str(organization_id),
                    "as_of_period": as_of_period,
                    "freeze_status": None,
                    "allowed": False,
                    "mapping_queue": [],
                    "mapping_open_count": 0,
                    "mapping_material_open_count": 0,
                    "import_hard_id_blocked": False,
                    "monthly_align": {
                        "ties": "owner_reviews_in_engine",
                        "mapping_clear": True,
                        "allow": False,
                        "ready_for_board": False,
                    },
                    "note": "No freeze pack yet — run freeze before Monthly Align Allow.",
                }
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return get_validation_status(db, organization_id, as_of_period)


@validation_engine_router.post("/allow")
def validation_allow(
    body: AllowRequest,
    organization_id: uuid.UUID = Query(...),
    as_of_period: str = Query(..., min_length=7, max_length=7),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    get_organization_or_404(db, organization_id)
    try:
        return record_allow(
            db,
            organization_id,
            as_of_period,
            allowed_by=body.allowed_by,
            notes=body.notes,
        )
    except ValueError as exc:
        code = str(exc)
        status = 409 if code in ("no_freeze_pack", "freeze_not_complete", "mapping_queue_open") else 400
        raise HTTPException(status_code=status, detail=code) from exc


@validation_engine_router.post("/revoke-allow")
def validation_revoke_allow(
    body: RevokeRequest,
    organization_id: uuid.UUID = Query(...),
    as_of_period: str = Query(..., min_length=7, max_length=7),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    get_organization_or_404(db, organization_id)
    try:
        return revoke_allow(
            db, organization_id, as_of_period, revoked_by=body.revoked_by
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@validation_engine_router.post("/mapping/upsert")
def validation_mapping_upsert(
    body: UpsertQueueRequest,
    organization_id: uuid.UUID = Query(...),
    as_of_period: str = Query(..., min_length=7, max_length=7),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    get_organization_or_404(db, organization_id)
    try:
        return upsert_mapping_queue(db, organization_id, as_of_period, body.items)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@validation_engine_router.post("/mapping/map")
def validation_mapping_map(
    body: MapAccountRequest,
    organization_id: uuid.UUID = Query(...),
    as_of_period: str = Query(..., min_length=7, max_length=7),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    get_organization_or_404(db, organization_id)
    try:
        return map_account(
            db,
            organization_id,
            as_of_period,
            account_id=body.account_id,
            mapped_to=body.mapped_to,
            mapped_by=body.mapped_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@validation_engine_router.post("/mapping/unmap")
def validation_mapping_unmap(
    body: UnmapAccountRequest,
    organization_id: uuid.UUID = Query(...),
    as_of_period: str = Query(..., min_length=7, max_length=7),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    get_organization_or_404(db, organization_id)
    try:
        return unmap_account(
            db,
            organization_id,
            as_of_period,
            account_id=body.account_id,
            unmapped_by=body.unmapped_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@validation_engine_router.post("/import-gate/check")
def validation_import_gate_check(
    organization_id: uuid.UUID = Query(...),
    as_of_period: str = Query(..., min_length=7, max_length=7),
    fail_closed: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Import/close hard-ID probe — material open mapping blocks when fail_closed."""
    get_organization_or_404(db, organization_id)
    try:
        status = assert_import_mapping_clear(
            db, organization_id, as_of_period, fail_closed=fail_closed
        )
        return {"ok": True, **status}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
