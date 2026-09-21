"""Persist and retrieve Plan Assurance assessments."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.plan_assessment import PlanAssessment


def persist_assessment(
    db: Session,
    *,
    organization_id: uuid.UUID,
    as_of: datetime,
    feasibility_verdict: str,
    assessment: dict[str, Any],
    budget_version_id: uuid.UUID | None = None,
    forecast_version_id: uuid.UUID | None = None,
    scenario: str = "budget",
    period_label: str | None = None,
    budget_year: int | None = None,
    simulation_summary: dict[str, Any] | None = None,
    method_notes: list[str] | None = None,
    prior_source: str | None = None,
    mc_seed: int | None = None,
    citation_note: str | None = None,
) -> PlanAssessment:
    """Insert a version-keyed assessment row. Caller must commit."""

    row = PlanAssessment(
        organization_id=organization_id,
        budget_version_id=budget_version_id,
        forecast_version_id=forecast_version_id,
        scenario=scenario,
        period_label=period_label,
        budget_year=budget_year,
        as_of=as_of,
        feasibility_verdict=feasibility_verdict,
        assessment=assessment,
        simulation_summary=simulation_summary,
        method_notes=method_notes,
        prior_source=prior_source,
        mc_seed=mc_seed,
        citation_note=citation_note
        or (
            "Board-citable only when keyed to a promoted plan version. "
            "Monte Carlo figures are stress frequencies under stated priors, not PoA."
        ),
    )
    db.add(row)
    db.flush()
    return row


def get_assessment(db: Session, assessment_id: uuid.UUID) -> PlanAssessment | None:
    return db.get(PlanAssessment, assessment_id)


def list_assessments_for_budget_version(
    db: Session,
    organization_id: uuid.UUID,
    budget_version_id: uuid.UUID,
) -> list[PlanAssessment]:
    stmt = (
        select(PlanAssessment)
        .where(
            PlanAssessment.organization_id == organization_id,
            PlanAssessment.budget_version_id == budget_version_id,
        )
        .order_by(PlanAssessment.as_of.desc(), PlanAssessment.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def list_assessments_for_forecast_version(
    db: Session,
    organization_id: uuid.UUID,
    forecast_version_id: uuid.UUID,
) -> list[PlanAssessment]:
    stmt = (
        select(PlanAssessment)
        .where(
            PlanAssessment.organization_id == organization_id,
            PlanAssessment.forecast_version_id == forecast_version_id,
        )
        .order_by(PlanAssessment.as_of.desc(), PlanAssessment.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def latest_assessment_for_plan(
    db: Session,
    organization_id: uuid.UUID,
    *,
    budget_version_id: uuid.UUID | None = None,
    forecast_version_id: uuid.UUID | None = None,
) -> PlanAssessment | None:
    if budget_version_id is None and forecast_version_id is None:
        return None
    rows = (
        list_assessments_for_budget_version(db, organization_id, budget_version_id)
        if budget_version_id
        else list_assessments_for_forecast_version(db, organization_id, forecast_version_id)  # type: ignore[arg-type]
    )
    return rows[0] if rows else None
