"""Predictive Planning Intelligence routes — Plan Assurance platform engine.

Additive by design for warehouse SoT: the caller supplies a deterministic plan
packet; the service evaluates constraints, derives What Has To Be True, optionally
runs seeded Monte Carlo, and persists assessments when a plan version is supplied.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.predictive_planning import (
    ConditionOut,
    ConstraintResultOut,
    FeasibilityOut,
    PlanAssessmentOut,
    PlanAssessmentRecordOut,
    PlanAssessmentRequest,
    ResolvedConstraintOut,
    SimulateOut,
    SimulateRequest,
    SimulationSummaryIn,
)
from app.services.predictive_planning.board_citation import assessment_citation_block
from app.services.predictive_planning.constraints import resolve_constraints
from app.services.predictive_planning.feasibility import run_feasibility
from app.services.predictive_planning.forecast_adapter import FORECAST_METHOD_NOTES
from app.services.predictive_planning.monte_carlo import run_packet_monte_carlo
from app.services.predictive_planning.persistence import (
    get_assessment,
    latest_assessment_for_plan,
    list_assessments_for_budget_version,
    list_assessments_for_forecast_version,
    persist_assessment,
)
from app.services.predictive_planning.priors import fit_priors_from_history
from app.services.predictive_planning.what_has_to_be_true import generate_what_has_to_be_true

predictive_planning_router = APIRouter(
    prefix="/predictive-planning",
    tags=["predictive-planning"],
)

METHOD_NOTES = [
    "Feasibility is deterministic: every result is a stated constraint evaluated against supplied plan values.",
    "Monte Carlo output is stress frequency under stated priors, not calibrated Probability of Attainment.",
    "A constraint with missing inputs is reported as skipped, never as a pass.",
]


def _flatten(overrides) -> dict[str, dict]:
    flat: dict[str, dict] = {}
    for constraint_id, override in (overrides or {}).items():
        entry = dict(override.params)
        if override.enabled is not None:
            entry["enabled"] = override.enabled
        flat[constraint_id] = entry
    return flat


def _resolved_out(constraints) -> list[ResolvedConstraintOut]:
    return [
        ResolvedConstraintOut(
            id=c.definition.id,
            domain=c.definition.domain,
            kind=c.definition.kind,
            label=c.definition.label,
            rationale=c.definition.rationale,
            enabled=c.enabled,
            params=c.params,
            param_sources=c.param_sources,
            levers=list(c.definition.levers),
            reads=list(c.definition.reads),
        )
        for c in constraints
    ]


def _record_out(row) -> PlanAssessmentRecordOut:
    return PlanAssessmentRecordOut(
        id=row.id,
        organization_id=row.organization_id,
        budget_version_id=row.budget_version_id,
        forecast_version_id=row.forecast_version_id,
        scenario=row.scenario,
        period_label=row.period_label,
        budget_year=row.budget_year,
        as_of=row.as_of,
        feasibility_verdict=row.feasibility_verdict,
        assessment=row.assessment,
        simulation_summary=row.simulation_summary,
        method_notes=row.method_notes,
        prior_source=row.prior_source,
        mc_seed=row.mc_seed,
        citation_note=row.citation_note,
        citation=assessment_citation_block(row),
        created_at=row.created_at,
    )


@predictive_planning_router.get("/constraints", response_model=list[ResolvedConstraintOut])
def get_constraints() -> list[ResolvedConstraintOut]:
    """Return the registry with default parameters."""

    return _resolved_out(resolve_constraints())


@predictive_planning_router.post("/assess", response_model=PlanAssessmentOut)
def assess_plan(
    body: PlanAssessmentRequest,
    db: Session = Depends(get_db),
) -> PlanAssessmentOut:
    """Run feasibility + WHTT; persist when a plan version id is present."""

    packet = body.packet.model_dump(by_alias=False)

    prior_fit = fit_priors_from_history(body.history)
    prior_source = body.prior_source or prior_fit["prior_source"]

    constraints = resolve_constraints(
        packet=packet,
        tenant_overrides=_flatten(body.tenant_overrides),
        version_overrides=_flatten(body.version_overrides),
    )

    report = run_feasibility(packet, constraints)

    stress_breaks: list[str] = []
    if body.simulation:
        stress_breaks = [*body.simulation.breaks, *body.simulation.watches]

    conditions = generate_what_has_to_be_true(
        report,
        stress_breaks=stress_breaks,
        include_passing=body.include_passing_conditions,
    )

    plan_ref = body.plan_ref.model_copy(
        update={
            "as_of": body.plan_ref.as_of or datetime.now(timezone.utc),
            "period_label": body.plan_ref.period_label or body.packet.period_label,
            "budget_year": body.plan_ref.budget_year or body.packet.budget_year,
        }
    )

    sources = sorted({f"packet.{field}" for c in constraints for field in c.definition.reads})
    if body.simulation:
        sources.append("caller.simulation_summary")

    notes = list(METHOD_NOTES)
    notes.append(prior_fit["label"])
    if plan_ref.scenario == "forecast":
        notes.extend(FORECAST_METHOD_NOTES)

    has_version = plan_ref.forecast_version_id is not None or plan_ref.budget_version_id is not None
    if not has_version:
        notes.append(
            "No plan version supplied — this assessment is transient and should not be cited in a board package."
        )

    feasibility_out = FeasibilityOut(
        verdict=report.verdict,
        counts=report.counts,
        results=[ConstraintResultOut(**r.to_dict()) for r in report.results],
    )
    whtt_out = [ConditionOut(**c.to_dict()) for c in conditions]
    constraints_out = _resolved_out(constraints)

    assessment_payload = {
        "feasibility": feasibility_out.model_dump(),
        "what_has_to_be_true": [c.model_dump() for c in whtt_out],
        "constraints_applied": [c.model_dump() for c in constraints_out],
        "simulation_summary": body.simulation.model_dump() if body.simulation else None,
        "method_card": prior_fit["method_card"],
    }

    persisted = False
    assessment_id = None
    if body.persist and has_version:
        row = persist_assessment(
            db,
            organization_id=plan_ref.organization_id,
            budget_version_id=plan_ref.budget_version_id,
            forecast_version_id=plan_ref.forecast_version_id,
            scenario=plan_ref.scenario,
            period_label=plan_ref.period_label,
            budget_year=plan_ref.budget_year,
            as_of=plan_ref.as_of or datetime.now(timezone.utc),
            feasibility_verdict=report.verdict,
            assessment=assessment_payload,
            simulation_summary=body.simulation.model_dump() if body.simulation else None,
            method_notes=notes,
            prior_source=prior_source,
            mc_seed=body.mc_seed,
        )
        db.commit()
        persisted = True
        assessment_id = row.id
        notes.append(f"Persisted assessment id={assessment_id}.")

    return PlanAssessmentOut(
        plan_ref=plan_ref,
        feasibility=feasibility_out,
        what_has_to_be_true=whtt_out,
        constraints_applied=constraints_out,
        simulation_summary=body.simulation,
        method_notes=notes,
        persisted=persisted,
        assessment_id=assessment_id,
        prior_source=prior_source,
        method_card=prior_fit["method_card"],
        _sources=sources,
    )


@predictive_planning_router.post("/simulate", response_model=SimulateOut)
def simulate_plan(body: SimulateRequest) -> SimulateOut:
    """Seeded server Monte Carlo over a plan packet (reproducible path stress)."""

    packet = body.packet.model_dump(by_alias=False)
    prior_fit = fit_priors_from_history(body.history)
    priors = {**prior_fit["priors"], **(body.priors or {})}
    prior_source = prior_fit["prior_source"] if not body.priors else (
        "caller_override" if prior_fit["prior_source"] == "independent_defaults" else prior_fit["prior_source"]
    )
    if body.priors and prior_fit["prior_source"] == "independent_defaults":
        prior_source = "caller_override"

    result = run_packet_monte_carlo(
        packet,
        n=body.n_trials,
        seed=body.seed,
        priors=priors,
        prior_source=prior_source,
    )
    summary = result.to_simulation_summary()
    summary["breaks"] = list(body.breaks)
    summary["watches"] = list(body.watches)

    plan_ref = body.plan_ref.model_copy(
        update={
            "as_of": body.plan_ref.as_of or datetime.now(timezone.utc),
            "period_label": body.plan_ref.period_label or body.packet.period_label,
            "budget_year": body.plan_ref.budget_year or body.packet.budget_year,
        }
    )

    return SimulateOut(
        plan_ref=plan_ref,
        seed=body.seed,
        prior_source=prior_source,
        priors=priors,
        method_card=prior_fit["method_card"],
        result=result.to_dict(),
        simulation_summary=SimulationSummaryIn(**summary),
        method_notes=result.method_notes + [prior_fit["label"]],
    )


@predictive_planning_router.get(
    "/assessments/{assessment_id}",
    response_model=PlanAssessmentRecordOut,
)
def get_persisted_assessment(
    assessment_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> PlanAssessmentRecordOut:
    row = get_assessment(db, assessment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="assessment_not_found")
    return _record_out(row)


@predictive_planning_router.get("/assessments", response_model=list[PlanAssessmentRecordOut])
def list_persisted_assessments(
    organization_id: uuid.UUID = Query(...),
    budget_version_id: uuid.UUID | None = None,
    forecast_version_id: uuid.UUID | None = None,
    latest: bool = Query(False),
    db: Session = Depends(get_db),
) -> list[PlanAssessmentRecordOut]:
    if budget_version_id is None and forecast_version_id is None:
        raise HTTPException(
            status_code=400,
            detail="budget_version_id_or_forecast_version_id_required",
        )
    if latest:
        row = latest_assessment_for_plan(
            db,
            organization_id,
            budget_version_id=budget_version_id,
            forecast_version_id=forecast_version_id,
        )
        return [_record_out(row)] if row else []

    rows = (
        list_assessments_for_budget_version(db, organization_id, budget_version_id)
        if budget_version_id
        else list_assessments_for_forecast_version(db, organization_id, forecast_version_id)  # type: ignore[arg-type]
    )
    return [_record_out(r) for r in rows]
