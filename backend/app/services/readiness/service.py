"""Readiness Score service — load answers, gather warehouse evidence, run the CAL engine."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.models.onboarding_readiness import OnboardingReadinessAnswers
from app.models.organization import Organization
from app.services.readiness.engine import assess, normalize_answers
from app.services.readiness.evidence import build_evidence
from app.services.readiness.registry import catalog


def ensure_readiness_table(db: Session) -> bool:
    """Create the answers table if missing (deploys don't run Alembic automatically)."""
    bind = db.get_bind()
    table = OnboardingReadinessAnswers.__table__
    from sqlalchemy import inspect

    if inspect(bind).has_table(table.name):
        return False
    table.create(bind=bind, checkfirst=True)
    return True


def get_answers(db: Session, org: Organization) -> OnboardingReadinessAnswers | None:
    return db.get(OnboardingReadinessAnswers, org.id)


def save_answers(
    db: Session,
    org: Organization,
    updates: Mapping[str, Any],
    *,
    updated_by: str | None = None,
) -> dict[str, str]:
    """Merge answers (``None`` clears a question) and return the stored set."""
    row = get_answers(db, org)
    current = dict(row.answers) if row else {}
    for qid, value in updates.items():
        if value is None:
            current.pop(str(qid), None)
        else:
            current[str(qid)] = str(value).strip().lower()
    stored = normalize_answers(current)
    if row is None:
        row = OnboardingReadinessAnswers(organization_id=org.id, answers=stored, updated_by=updated_by)
        db.add(row)
    else:
        row.answers = stored
        row.updated_by = updated_by
    db.commit()
    return stored


def readiness_payload(db: Session, org: Organization) -> dict[str, Any]:
    row = get_answers(db, org)
    answers = dict(row.answers) if row else {}
    evidence, meta = build_evidence(db, org)
    result = assess(evidence, answers)
    return {
        "organization_id": str(org.id),
        "organization_name": org.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "answers": normalize_answers(answers),
        "answers_updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
        "answers_updated_by": row.updated_by if row else None,
        **meta,
        **result,
        "questions": catalog(),
    }
