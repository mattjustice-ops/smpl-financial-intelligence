"""Campfire sandbox import. Reads Campfire. Does not post back."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.campfire.client import CampfireError
from app.services.campfire.sandbox_import import import_campfire_dataset, remove_sandbox_load

campfire_router = APIRouter(prefix="/integrations/campfire", tags=["campfire"])


class CampfireImportRequest(BaseModel):
    dataset: str = Field(..., max_length=64)
    as_of_period: str = Field(..., min_length=7, max_length=7)


class CampfireRemoveRequest(BaseModel):
    dataset: str | None = Field(default=None, max_length=64)
    as_of_period: str = Field(..., min_length=7, max_length=7)
    scope: str = Field(default="name", max_length=16)


@campfire_router.post("/import")
def campfire_import(body: CampfireImportRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return import_campfire_dataset(db, dataset=body.dataset, as_of_period=body.as_of_period)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except CampfireError as exc:
        raise HTTPException(status_code=502, detail=f"Campfire could not be read ({exc.status}).") from exc


@campfire_router.post("/remove")
def campfire_remove(body: CampfireRemoveRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return remove_sandbox_load(
            db,
            dataset=body.dataset,
            as_of_period=body.as_of_period,
            scope=body.scope,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
