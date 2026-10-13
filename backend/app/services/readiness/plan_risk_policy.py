"""Plan risk policy (onboarding 7.43-7.58): the company's watch and break cutoffs and its management levers.

The Forecast and Budget Engines (outlook ``RISK_POLICY``) and the Plan Assurance service read the values here.
Shares are fractions (25 -> 0.25); amounts are dollars; counts and days are integers. An unanswered question is None and listed in
``missing``; a band pair answered out of order (the break or alarm level not above the watch level) is listed
in ``conflicts`` and both values are None. Callers report a cutoff or lever with no value as not set.
"""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.models.onboarding_readiness import OnboardingReadinessAnswers
from app.services.readiness.engine import normalize_answers

POLICY: tuple[tuple[str, str, str], ...] = (
    ("cash_watch_shortfall", "7.43", "share"),
    ("cash_alarm_shortfall", "7.44", "share"),
    ("floor_hard_breach_share", "7.45", "share"),
    ("p_floor_watch", "7.46", "share"),
    ("p_floor_break", "7.47", "share"),
    ("p_cash_watch_watch", "7.48", "share"),
    ("p_cash_watch_break", "7.49", "share"),
    ("p_arr_miss_watch", "7.50", "share"),
    ("arr_miss_tolerance", "7.51", "share"),
    ("named_breaks_for_break", "7.52", "count"),
    ("program_cut", "7.53", "share"),
    ("dso_improvement_days", "7.54", "count"),
    ("case_cash_watch", "7.55", "share"),
    ("case_watch_amount", "7.56", "amount"),
    ("case_break_amount", "7.57", "amount"),
    ("case_overspend_watch", "7.58", "share"),
)
QUESTION_OF: dict[str, str] = {key: qid for key, qid, _ in POLICY}
# (lower, higher): the higher level must be strictly above the lower one.
ORDERED: tuple[tuple[str, str], ...] = (
    ("cash_watch_shortfall", "cash_alarm_shortfall"),
    ("p_floor_watch", "p_floor_break"),
    ("p_cash_watch_watch", "p_cash_watch_break"),
    ("case_watch_amount", "case_break_amount"),
)


def resolve_policy(answers: Mapping[str, str]) -> dict[str, Any]:
    values: dict[str, float | int | None] = {}
    missing: list[str] = []
    for key, qid, kind in POLICY:
        a = answers.get(qid)
        if a is None:
            values[key] = None
            missing.append(qid)
        else:
            values[key] = float(a) / 100 if kind == "share" else float(a) if kind == "amount" else int(a)
    conflicts: list[str] = []
    for lo, hi in ORDERED:
        if values[lo] is not None and values[hi] is not None and values[hi] <= values[lo]:
            conflicts.append(f"{QUESTION_OF[hi]} ({answers[QUESTION_OF[hi]]}) is not above "
                             f"{QUESTION_OF[lo]} ({answers[QUESTION_OF[lo]]})")
            values[lo] = values[hi] = None
    return {
        "values": values,
        "questions": dict(QUESTION_OF),
        "missing": missing,
        "conflicts": conflicts,
        "source": "onboarding answers 7.43-7.58 (Plan Risk Policy)",
    }


def plan_risk_policy(db: Session, organization_id: uuid.UUID) -> dict[str, Any]:
    row = db.get(OnboardingReadinessAnswers, organization_id)
    return resolve_policy(normalize_answers(dict(row.answers) if row else {}))
