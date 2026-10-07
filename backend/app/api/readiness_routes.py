"""Onboarding Readiness Score — per-module READY / PARTIAL / UNAVAILABLE and the score."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.organizations import get_organization_or_404
from app.services.readiness.commission_plan_inputs import build_plan_inputs
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


@readiness_router.get("/commission-plan-inputs")
def get_commission_plan_inputs(
    organization_id: uuid.UUID = Query(...),
    as_of: str = Query(..., pattern=r"^\d{4}-\d{2}$", description="Close the plan opens from, YYYY-MM"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Commission policy (read-only), plan rates and the deferred commissions opening runoff for the engines."""
    org = get_organization_or_404(db, organization_id)
    return build_plan_inputs(db, org, as_of)


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
