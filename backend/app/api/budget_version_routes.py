"""Budget version lifecycle routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.budget_working_plan import BudgetWorkingPlan
from app.schemas.budget_version import (
    BudgetDraftCreate,
    BudgetPromoteResponse,
    BudgetVersionOut,
    BudgetWorkingPlanOut,
    BudgetWorkingPlanPut,
)
from app.services.budget_version_service import (
    list_budget_versions,
    promote_budget_version,
    save_budget_draft,
)
from app.services.budget_working_plan_service import get_working_plan, save_working_plan

budget_versions_router = APIRouter(prefix="/budget/versions", tags=["budget-versions"])
budget_working_router = APIRouter(prefix="/budget/working", tags=["budget-working"])


@budget_working_router.get("", response_model=BudgetWorkingPlanOut)
def read_working_plan(
    organization_id: uuid.UUID,
    budget_year: int,
    db: Session = Depends(get_db),
) -> BudgetWorkingPlan:
    row = get_working_plan(db, organization_id, budget_year)
    if row is None:
        raise HTTPException(status_code=404, detail="No company budget saved yet.")
    return row


@budget_working_router.put("", response_model=BudgetWorkingPlanOut)
def put_working_plan(
    organization_id: uuid.UUID,
    body: BudgetWorkingPlanPut,
    db: Session = Depends(get_db),
) -> BudgetWorkingPlan:
    return save_working_plan(
        db,
        organization_id,
        budget_year=body.budget_year,
        plan_rev=body.plan_rev,
        levers=body.levers,
        base_updated_at=body.base_updated_at,
        only_if_empty=body.only_if_empty,
    )


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
