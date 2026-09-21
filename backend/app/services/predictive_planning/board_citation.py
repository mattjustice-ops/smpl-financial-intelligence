"""Board citation helpers — consume persisted Plan Assurance assessments."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.plan_assessment import PlanAssessment
from app.services.predictive_planning.persistence import (
    latest_assessment_for_plan,
)


def assessment_citation_block(row: PlanAssessment) -> dict[str, Any]:
    """Structured evidence block safe to attach to board / MDA commentary."""

    payload = row.assessment or {}
    whtt = payload.get("what_has_to_be_true") or []
    feasibility = payload.get("feasibility") or {}
    sim = row.simulation_summary or payload.get("simulation_summary") or {}

    must_close = [c for c in whtt if c.get("verdict") == "must_close"]
    must_confirm = [c for c in whtt if c.get("verdict") == "must_confirm"]
    must_hold = [c for c in whtt if c.get("verdict") == "must_hold"]

    return {
        "assessment_id": str(row.id),
        "as_of": row.as_of.isoformat() if row.as_of else None,
        "scenario": row.scenario,
        "budget_version_id": str(row.budget_version_id) if row.budget_version_id else None,
        "forecast_version_id": str(row.forecast_version_id) if row.forecast_version_id else None,
        "feasibility_verdict": row.feasibility_verdict,
        "counts": feasibility.get("counts"),
        "what_has_to_be_true": {
            "must_close": must_close,
            "must_confirm": must_confirm,
            "must_hold": must_hold,
        },
        "simulation": {
            "trials": sim.get("trials"),
            "p_arr_miss": sim.get("p_arr_miss"),
            "p_cash_below_floor": sim.get("p_cash_below_floor"),
            "p_ops_liquidity": sim.get("p_ops_liquidity"),
            "p_ae_short": sim.get("p_ae_short"),
            "priors": sim.get("priors"),
        },
        "prior_source": row.prior_source,
        "mc_seed": row.mc_seed,
        "citation_note": row.citation_note,
        "method_notes": row.method_notes
        or [
            "Persisted Plan Assurance assessment — cite only with version id.",
            "Monte Carlo figures are stress frequencies under stated priors, not PoA.",
        ],
    }


def board_plan_assurance_evidence(
    db: Session,
    organization_id,
    *,
    budget_version_id=None,
    forecast_version_id=None,
) -> dict[str, Any] | None:
    """Load the latest persisted assessment for board commentary / export."""

    row = latest_assessment_for_plan(
        db,
        organization_id,
        budget_version_id=budget_version_id,
        forecast_version_id=forecast_version_id,
    )
    if row is None:
        return None
    return assessment_citation_block(row)


def metrics_from_plan_assurance(evidence: dict[str, Any] | None) -> dict[str, str]:
    """Flatten a citation block into board-slide metric strings (risks slide)."""

    if not evidence:
        return {}
    whtt = evidence.get("what_has_to_be_true") or {}
    must_close = whtt.get("must_close") or []
    must_hold = whtt.get("must_hold") or []
    sim = evidence.get("simulation") or {}

    def _stmts(rows: list, limit: int = 3) -> str:
        parts = [str(r.get("statement") or "").strip() for r in rows[:limit]]
        return " | ".join(p for p in parts if p) or "none"

    out = {
        "plan_assurance_verdict": str(evidence.get("feasibility_verdict") or "n/a"),
        "plan_assurance_assessment_id": str(evidence.get("assessment_id") or ""),
        "plan_assurance_must_close": _stmts(must_close),
        "plan_assurance_must_hold": _stmts(must_hold),
        "plan_assurance_prior_source": str(evidence.get("prior_source") or "n/a"),
    }
    if sim.get("trials") is not None:
        out["plan_assurance_mc_trials"] = str(sim.get("trials"))
    if sim.get("p_cash_below_floor") is not None:
        out["plan_assurance_p_cash_below_floor"] = f"{float(sim['p_cash_below_floor']) * 100:.1f}%"
    if sim.get("p_arr_miss") is not None:
        out["plan_assurance_p_arr_miss"] = f"{float(sim['p_arr_miss']) * 100:.1f}%"
    note = evidence.get("citation_note")
    if note:
        out["plan_assurance_citation_note"] = str(note)[:240]
    return out
