"""What Has To Be True generator — PPI Phase 1.

Turns feasibility failures and stress breaks into the explicit conditions a plan
implicitly assumes. The Budget Engine already *implies* these inside check detail
strings and stress break reasons; this module makes them a first-class structured
artifact so they can be reviewed, exported and narrated without prose parsing.

Discipline: every condition is derived from a deterministic constraint result or a
recorded stress outcome. Nothing here invents a number or a probability.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.predictive_planning.constraints import REGISTRY_BY_ID
from app.services.predictive_planning.feasibility import ConstraintResult, FeasibilityReport

#: A break recorded by the Budget Engine stress suite maps onto the constraint it
#: threatens. Keys mirror ``classifyScenarioOutcome`` in the Budget Engine.
STRESS_REASON_TO_CONSTRAINT: dict[str, str] = {
    "Dec cash floor": "cash_floor",
    "Mid-year cash trough vs floor": "cash_path",
    "Cash down ≥50% vs plan": "cash_floor",
    "Cash down ≥5% vs plan": "cash_floor",
    "NB AE cover": "nb_cover",
    "CS cover": "cs_cover",
    "EBITDA turns negative": "ebitda",
    "Marketing spend +20%": "gtm_spend",
    "Dec ARR vs YoY target": "arr_path",
    "Dec ARR vs YoY target (cash ≈ noise)": "arr_path",
}

_UNIT_FORMATTERS = {
    "currency": lambda v: f"${v / 1_000_000:.1f}M",
    "count": lambda v: f"{v:,.0f}",
    "percent": lambda v: f"{v:.0f}%",
    "ratio": lambda v: f"{v * 100:.1f}%",
    "multiple": lambda v: f"{v:.1f}×",
    "number": lambda v: f"{v:,.2f}",
}


def _fmt(value: float | None, unit: str) -> str:
    if value is None:
        return "n/a"
    return _UNIT_FORMATTERS.get(unit, _UNIT_FORMATTERS["number"])(value)


@dataclass
class Condition:
    """One explicit thing that must hold for the plan to be deliverable."""

    constraint_id: str
    domain: str
    verdict: str  # "must_close" | "must_confirm" | "must_hold"
    statement: str
    rationale: str
    observed: float | None
    required: float | None
    gap: float | None
    unit: str
    levers: list[str]
    origin: str  # "feasibility" | "stress"
    severity: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "domain": self.domain,
            "verdict": self.verdict,
            "statement": self.statement,
            "rationale": self.rationale,
            "observed": self.observed,
            "required": self.required,
            "gap": self.gap,
            "unit": self.unit,
            "levers": self.levers,
            "origin": self.origin,
            "severity": self.severity,
        }


def _statement_for(result: ConstraintResult) -> str:
    """Phrase the condition as a requirement, not a description of the failure."""

    definition = REGISTRY_BY_ID.get(result.id)
    label = definition.label if definition else result.label
    required = _fmt(result.required, result.unit)
    observed = _fmt(result.observed, result.unit)
    kind = definition.kind if definition else "target"

    if result.status == "advisory":
        return f"{label}: plan runs above target at {observed} vs {required} — confirm the upside is intentional and resourced."

    if kind == "identity":
        return f"{label} must reconcile: currently {observed} against {required}. Close the gap of {_fmt(result.gap, result.unit)} before the plan is internally consistent."
    if kind == "coverage":
        return f"{label}: capacity must reach {required}; the plan ends at {observed}. Add {_fmt(abs(result.gap or 0), result.unit)} of coverage or reduce the load."
    if kind == "ceiling":
        return f"{label} must stay at or below {required}; the plan implies {observed}."
    return f"{label} must reach at least {required}; the plan delivers {observed}."


def _verdict_for(result: ConstraintResult) -> str:
    if result.status == "fail":
        return "must_close"
    if result.status == "warn":
        return "must_confirm"
    return "must_confirm"


def generate_what_has_to_be_true(
    feasibility: FeasibilityReport,
    stress_breaks: list[str] | None = None,
    include_passing: bool = False,
) -> list[Condition]:
    """Derive the structured WHTT list.

    Conditions come from two origins. Feasibility results give the conditions the
    plan violates *as written*. Stress breaks give conditions the plan satisfies
    today but that fail under recorded lever shocks — those become ``must_hold``,
    the thing to instrument rather than fix.

    ``include_passing`` adds satisfied constraints as ``must_hold`` so a reviewer
    can see the full set of load-bearing assumptions, not only the broken ones.
    """

    conditions: list[Condition] = []
    seen: set[str] = set()

    severity_rank = {"fail": 0, "warn": 1, "advisory": 2, "pass": 3}
    ordered = sorted(
        feasibility.results,
        key=lambda r: (severity_rank.get(r.status, 4), r.id),
    )

    for result in ordered:
        if result.status == "skipped":
            continue
        if result.status == "pass" and not include_passing:
            continue

        definition = REGISTRY_BY_ID.get(result.id)
        levers = list(definition.levers) if definition else []
        rationale = definition.rationale if definition else ""

        if result.status == "pass":
            statement = f"{result.label} must stay within policy — currently satisfied at {_fmt(result.observed, result.unit)}."
            verdict = "must_hold"
        else:
            statement = _statement_for(result)
            verdict = _verdict_for(result)

        conditions.append(
            Condition(
                constraint_id=result.id,
                domain=result.domain,
                verdict=verdict,
                statement=statement,
                rationale=rationale,
                observed=result.observed,
                required=result.required,
                gap=result.gap,
                unit=result.unit,
                levers=levers,
                origin="feasibility",
                severity=result.severity,
            )
        )
        seen.add(result.id)

    for reason in stress_breaks or []:
        constraint_id = STRESS_REASON_TO_CONSTRAINT.get(reason)
        if not constraint_id or constraint_id in seen:
            continue
        definition = REGISTRY_BY_ID.get(constraint_id)
        if not definition:
            continue
        conditions.append(
            Condition(
                constraint_id=constraint_id,
                domain=definition.domain,
                verdict="must_hold",
                statement=(
                    f"{definition.label} holds in the base plan but breaks under stress "
                    f"(\"{reason}\"). It must hold for the plan to survive that case."
                ),
                rationale=definition.rationale,
                observed=None,
                required=None,
                gap=None,
                unit="number",
                levers=list(definition.levers),
                origin="stress",
                severity="medium",
            )
        )
        seen.add(constraint_id)

    return conditions
