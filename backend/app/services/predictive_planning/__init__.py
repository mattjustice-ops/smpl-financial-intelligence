"""Predictive Planning Intelligence (PPI) — Plan Assurance platform engine.

Layer contract from ``docs/product/SMPL_Predictive_Planning_Intelligence_Framework.md``:
the deterministic finance engine owns every dollar; PPI tests the plan against
stated constraints, runs seeded path stress, and the LLM narrates structured
findings only. Nothing in this package mutates warehouse source of truth.

Surfaces (Budget now; Forecast/Board via adapters) post a plan packet to
``/api/v1/predictive-planning/assess`` and optionally ``/simulate``.
"""

from app.services.predictive_planning.board_citation import (
    assessment_citation_block,
    board_plan_assurance_evidence,
    metrics_from_plan_assurance,
)
from app.services.predictive_planning.constraints import (
    REGISTRY,
    REGISTRY_BY_ID,
    ConstraintDef,
    ResolvedConstraint,
    resolve_constraints,
)
from app.services.predictive_planning.feasibility import (
    ConstraintResult,
    FeasibilityReport,
    run_feasibility,
)
from app.services.predictive_planning.forecast_adapter import (
    FORECAST_METHOD_NOTES,
    build_forecast_plan_packet,
)
from app.services.predictive_planning.monte_carlo import (
    DEFAULT_PRIORS,
    run_packet_monte_carlo,
)
from app.services.predictive_planning.priors import fit_priors_from_history
from app.services.predictive_planning.what_has_to_be_true import (
    Condition,
    generate_what_has_to_be_true,
)

__all__ = [
    "REGISTRY",
    "REGISTRY_BY_ID",
    "DEFAULT_PRIORS",
    "Condition",
    "ConstraintDef",
    "ConstraintResult",
    "FeasibilityReport",
    "ResolvedConstraint",
    "FORECAST_METHOD_NOTES",
    "assessment_citation_block",
    "board_plan_assurance_evidence",
    "build_forecast_plan_packet",
    "fit_priors_from_history",
    "generate_what_has_to_be_true",
    "metrics_from_plan_assurance",
    "resolve_constraints",
    "run_feasibility",
    "run_packet_monte_carlo",
]
