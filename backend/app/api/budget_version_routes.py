"""Budget version lifecycle routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.budget_version import BudgetDraftCreate, BudgetPromoteResponse, BudgetVersionOut
from app.services.budget_version_service import (
    list_budget_versions,
    promote_budget_version,
    save_budget_draft,
)

budget_versions_router = APIRouter(prefix="/budget/versions", tags=["budget-versions"])


@budget_versions_router.get("", response_model=list[BudgetVersionOut])
def get_budget_versions(
    organization_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[BudgetVersionOut]:
    versions = list_budget_versions(db, organization_id)
    return [BudgetVersionOut.model_validate(v) for v in versions]


@budget_versions_router.post("/draft", response_model=BudgetVersionOut)
def create_or_update_budget_draft(
    organization_id: uuid.UUID,
    body: BudgetDraftCreate,
    db: Session = Depends(get_db),
) -> BudgetVersionOut:
    version = save_budget_draft(
        db,
        organization_id,
        version_name=body.version_name,
        as_of_period=body.as_of_period,
        budget_year=body.budget_year,
        levers=body.levers,
        results=body.results,
        tables=body.tables,
        version_id=body.version_id,
    )
    return BudgetVersionOut.model_validate(version)


@budget_versions_router.post("/{version_id}/promote", response_model=BudgetPromoteResponse)
def promote_version(
    organization_id: uuid.UUID,
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> BudgetPromoteResponse:
    version = promote_budget_version(db, organization_id, version_id)
    return BudgetPromoteResponse(version=BudgetVersionOut.model_validate(version))
