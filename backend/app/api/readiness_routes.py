"""Onboarding Readiness Score — per-module READY / PARTIAL / UNAVAILABLE and the score."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.organizations import get_organization_or_404
from app.services.readiness.engine import validate_answers
from app.services.readiness.registry import catalog
from app.services.readiness.service import readiness_payload, save_answers

readiness_router = APIRouter(prefix="/readiness", tags=["readiness"])


@readiness_router.get("")
def get_readiness(
    organization_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    org = get_organization_or_404(db, organization_id)
    return readiness_payload(db, org)


@readiness_router.get("/questions")
def get_readiness_questions() -> dict[str, Any]:
    return catalog()


@readiness_router.put("/answers")
def put_readiness_answers(
    organization_id: uuid.UUID = Query(...),
    answers: dict[str, Any] = Body(..., embed=True),
    user_id: str | None = Header(None, alias="X-SFI-User-Id"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    org = get_organization_or_404(db, organization_id)
    errors = validate_answers(answers)
    if errors:
        raise HTTPException(status_code=422, detail={"message": "Invalid answers", "errors": errors})
    save_answers(db, org, answers, updated_by=user_id)
    return readiness_payload(db, org)
