"""Predictive Planning Intelligence routes — PPI Phase 1.

Additive by design: nothing here reads or writes warehouse source of truth. The
caller supplies a deterministic plan packet, the service evaluates it against the
constraints registry, and the response is an assessment artifact.

Assessments are **computed, not persisted**. Persisting them keyed by
``(organization_id, forecast_version_id, as_of)`` is the remaining Phase 1 step and
needs a model plus migration — see the PPI framework doc.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.schemas.predictive_planning import (
    ConditionOut,
    ConstraintResultOut,
    FeasibilityOut,
    PlanAssessmentOut,
    PlanAssessmentRequest,
    ResolvedConstraintOut,
)
from app.services.predictive_planning.constraints import resolve_constraints
from app.services.predictive_planning.feasibility import run_feasibility
from app.services.predictive_planning.what_has_to_be_true import generate_what_has_to_be_true

predictive_planning_router = APIRouter(
    prefix="/predictive-planning",
    tags=["predictive-planning"],
)

METHOD_NOTES = [
    "Feasibility is deterministic: every result is a stated constraint evaluated against supplied plan values.",
    "Simulation figures are echoed from the caller, not recomputed here.",
    "Monte Carlo output is stress frequency under stated priors, not calibrated Probability of Attainment.",
    "A constraint with missing inputs is reported as skipped, never as a pass.",
]


def _flatten(overrides) -> dict[str, dict]:
    """Collapse ConstraintOverride objects into the shape resolve_constraints wants."""
    flat: dict[str, dict] = {}
    for constraint_id, override in (overrides or {}).items():
        entry = dict(override.params)
        if override.enabled is not None:
            entry["enabled"] = override.enabled
        flat[constraint_id] = entry
    return flat


@predictive_planning_router.get("/constraints", response_model=list[ResolvedConstraintOut])
def get_constraints() -> list[ResolvedConstraintOut]:
    """Return the registry with default parameters.

    Tenant and version overlays are applied at assessment time; this endpoint is
    the governed baseline every surface should agree on.
    """

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
        for c in resolve_constraints()
    ]


@predictive_planning_router.post("/assess", response_model=PlanAssessmentOut)
def assess_plan(body: PlanAssessmentRequest) -> PlanAssessmentOut:
    """Run feasibility and derive What Has To Be True for a plan packet."""

    packet = body.packet.model_dump(by_alias=False)

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
    if plan_ref.forecast_version_id is None and plan_ref.budget_version_id is None:
        notes.append(
            "No plan version supplied — this assessment is transient and should not be cited in a board package."
        )

    return PlanAssessmentOut(
        plan_ref=plan_ref,
        feasibility=FeasibilityOut(
            verdict=report.verdict,
            counts=report.counts,
            results=[ConstraintResultOut(**r.to_dict()) for r in report.results],
        ),
        what_has_to_be_true=[ConditionOut(**c.to_dict()) for c in conditions],
        constraints_applied=[
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
        ],
        simulation_summary=body.simulation,
        method_notes=notes,
        persisted=False,
        _sources=sources,
    )
