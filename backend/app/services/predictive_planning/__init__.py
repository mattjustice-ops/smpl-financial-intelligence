"""Predictive Planning Intelligence (PPI) — Phase 1.

Layer contract from ``docs/product/SMPL_Predictive_Planning_Intelligence_Framework.md``:
the deterministic finance engine owns every dollar, PPI tests the plan against
stated constraints, and the LLM narrates structured findings only. Nothing in this
package mutates warehouse source of truth.

Phase 1 scope shipped here: constraints registry, feasibility runner, and the
What-Has-To-Be-True generator, plus the assessment DTO assembled in
``app/api/predictive_planning_routes.py``.

Not in scope here: probability of attainment, trajectory, forecast accuracy, and
simulation. Monte Carlo and named stress cases currently run client-side in the
Budget Engine; this package accepts their recorded output as input but does not
recompute it.
"""

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
from app.services.predictive_planning.what_has_to_be_true import (
    Condition,
    generate_what_has_to_be_true,
)

__all__ = [
    "REGISTRY",
    "REGISTRY_BY_ID",
    "Condition",
    "ConstraintDef",
    "ConstraintResult",
    "FeasibilityReport",
    "ResolvedConstraint",
    "generate_what_has_to_be_true",
    "resolve_constraints",
    "run_feasibility",
]
