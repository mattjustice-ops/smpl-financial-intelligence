"""The company's open budget. One row per organization and budget year."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps.request_context import get_request_user_id
from app.models.budget_working_plan import BudgetWorkingPlan
from app.models.organization import Organization
from app.services.auth.service import AuthService
from app.services.organizations import get_organization_or_404


def require_org_member(db: Session, organization_id: uuid.UUID) -> tuple[Organization, uuid.UUID]:
    user_id = get_request_user_id()
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    member_org = AuthService(db).get_member(user_id=user_id, organization_id=organization_id)
    if member_org is None:
        raise HTTPException(status_code=403, detail="You do not have access to this organization.")
    _member, org = member_org
    return org, user_id


def working_plan_payload(row: BudgetWorkingPlan) -> dict[str, Any]:
    updated = row.updated_at
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    return {
        "budget_year": row.budget_year,
        "plan_rev": row.plan_rev,
        "updated_at": updated.isoformat(),
        "levers": row.levers or {},
    }


def timestamps_match(stored: datetime | None, sent: datetime | None) -> bool:
    if stored is None or sent is None:
        return False
    if stored.tzinfo is None:
        stored = stored.replace(tzinfo=timezone.utc)
    if sent.tzinfo is None:
        sent = sent.replace(tzinfo=timezone.utc)
    return abs((stored - sent).total_seconds()) < 0.01


def get_working_plan(db: Session, organization_id: uuid.UUID, budget_year: int) -> BudgetWorkingPlan | None:
    require_org_member(db, organization_id)
    get_organization_or_404(db, organization_id)
    return db.scalars(
        select(BudgetWorkingPlan).where(
            BudgetWorkingPlan.organization_id == organization_id,
            BudgetWorkingPlan.budget_year == budget_year,
        )
    ).first()


def _conflict(row: BudgetWorkingPlan) -> None:
    raise HTTPException(
        status_code=409,
        detail={"code": "working_plan_changed", "plan": working_plan_payload(row)},
    )


def save_working_plan(
    db: Session,
    organization_id: uuid.UUID,
    *,
    budget_year: int,
    plan_rev: int,
    levers: dict[str, Any],
    base_updated_at: datetime | None,
    only_if_empty: bool,
) -> BudgetWorkingPlan:
    _org, user_id = require_org_member(db, organization_id)
    get_organization_or_404(db, organization_id)
    if not isinstance(levers, dict):
        raise HTTPException(status_code=422, detail="The working plan has to be an object.")
    row = db.scalars(
        select(BudgetWorkingPlan).where(
            BudgetWorkingPlan.organization_id == organization_id,
            BudgetWorkingPlan.budget_year == budget_year,
        )
    ).first()
    now = datetime.now(timezone.utc)
    if row is None:
        row = BudgetWorkingPlan(
            organization_id=organization_id,
            budget_year=budget_year,
            plan_rev=plan_rev,
            levers=levers,
            updated_by_user_id=user_id,
            updated_at=now,
        )
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            winner = db.scalars(
                select(BudgetWorkingPlan).where(
                    BudgetWorkingPlan.organization_id == organization_id,
                    BudgetWorkingPlan.budget_year == budget_year,
                )
            ).first()
            if winner is None:
                raise
            _conflict(winner)
        db.refresh(row)
        return row
    if only_if_empty or not timestamps_match(row.updated_at, base_updated_at):
        _conflict(row)
    row.plan_rev = plan_rev
    row.levers = levers
    row.updated_by_user_id = user_id
    row.updated_at = now
    db.commit()
    db.refresh(row)
    return row
