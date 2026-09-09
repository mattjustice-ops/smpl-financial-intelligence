"""Constraints registry — PPI Phase 1.

The Budget Engine shipped these checks as inline JavaScript in
``frontend/public/budget-engine/index.html`` (``runBudgetRiskChecks``). This module
makes the same rules a declarative, server-side registry so Budget, Forecast and
Board can share one definition instead of forking the thresholds.

**Defaults here intentionally mirror the shipped JS exactly.** Changing a default
changes product behaviour once a surface calls the API — treat edits as product
decisions, not cleanup.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Domain = Literal["arr", "retention", "liquidity", "sales", "gtm", "headcount", "pnl"]
Kind = Literal["identity", "floor", "ceiling", "coverage", "target"]
Severity = Literal["ok", "low", "medium", "high"]

#: Params the packet supplies directly today. Packet values win over registry
#: defaults so existing Budget Engine behaviour is preserved, but an explicit
#: tenant/version override still wins over the packet.
PACKET_SUPPLIED_PARAMS: dict[str, dict[str, str]] = {
    "cash_floor": {"floor": "cash_floor"},
    "cash_path": {"floor": "cash_floor"},
    "bench": {"target_pct": "bench_target"},
    "pipeline": {"min_multiple": "pipeline_min"},
}


@dataclass(frozen=True)
class ConstraintDef:
    """One hard or soft bound the plan must respect."""

    id: str
    domain: Domain
    kind: Kind
    label: str
    #: Why Finance cares — used verbatim as the rationale on What-Has-To-Be-True.
    rationale: str
    #: Default thresholds. Overridable per tenant and per plan version.
    params: dict[str, Any] = field(default_factory=dict)
    #: Packet fields read by the evaluator; surfaces as `_sources` on the assessment.
    reads: tuple[str, ...] = ()
    #: Levers that actually move this constraint, for remediation text.
    levers: tuple[str, ...] = ()
    #: Worst severity this constraint can emit.
    max_severity: Severity = "high"


REGISTRY: tuple[ConstraintDef, ...] = (
    ConstraintDef(
        id="arr_path",
        domain="arr",
        kind="target",
        label="Dec ARR path",
        rationale="Ending ARR is the plan's headline commitment; drift here invalidates every downstream driver.",
        params={"rel_tolerance": 0.002, "abs_tolerance": 1000.0},
        reads=("dec_arr", "target_arr", "yoy_growth_pct"),
        levers=("yoy_ending_arr_growth_pct", "component mix", "churn mix"),
    ),
    ConstraintDef(
        id="arr_bridge",
        domain="arr",
        kind="identity",
        label="ARR bridge identity",
        rationale="BOP + FY net new must equal Dec EOP, or the ARR schedule is internally inconsistent.",
        params={"rel_tolerance": 0.001, "abs_tolerance": 500.0},
        reads=("bop_arr", "fy_nn", "dec_arr"),
        levers=("monthly net new", "component mix"),
    ),
    ConstraintDef(
        id="grr_floor",
        domain="retention",
        kind="floor",
        label="GRR floor",
        rationale="Retention below policy forces more new business to hold the same ARR path.",
        params={"avg_floor": 0.92, "min_month_floor": 0.90, "hard_min_month": 0.85},
        reads=("avg_grr", "min_grr"),
        levers=("churn mix", "contraction mix"),
    ),
    ConstraintDef(
        id="cash_floor",
        domain="liquidity",
        kind="floor",
        label="Dec cash floor",
        rationale="Ending cash below the floor means the plan cannot be funded as written.",
        params={"floor": 10_000_000.0, "hard_breach_ratio": 0.85},
        reads=("end_cash", "cash_floor"),
        levers=("burn", "hiring pace", "marketing spend", "financing"),
    ),
    ConstraintDef(
        id="cash_path",
        domain="liquidity",
        kind="floor",
        label="Intra-year cash path",
        rationale="A mid-year trough below the floor is a real financing event even when December recovers.",
        params={"floor": 10_000_000.0},
        reads=("min_cash", "min_cash_period", "end_cash", "cash_floor"),
        levers=("spend phasing", "hiring pace", "collections timing"),
    ),
    ConstraintDef(
        id="nb_cover",
        domain="sales",
        kind="coverage",
        label="NB AE coverage",
        rationale="Ending new-business AEs must cover the AE need implied by quota math, or bookings are uncarryable.",
        reads=("sales_end", "ae_needed"),
        levers=("sales hiring", "quota", "ramp assumptions"),
    ),
    ConstraintDef(
        id="cs_cover",
        domain="sales",
        kind="coverage",
        label="CS coverage",
        rationale="CS capacity must cover expansion and churn-mitigation load implied by the plan.",
        reads=("cs_end", "cs_needed"),
        levers=("CS hiring", "coverage ratio", "churn mix"),
    ),
    ConstraintDef(
        id="bench",
        domain="sales",
        kind="coverage",
        label="Existing bench cover",
        rationale="Plans leaning on unhired reps carry ramp risk the bench does not.",
        params={"target_pct": 60.0, "slack_pp": 0.5},
        reads=("cover_pct", "hire_pct", "bench_target"),
        levers=("existing bench cover %", "hiring plan"),
        max_severity="medium",
    ),
    ConstraintDef(
        id="pipeline",
        domain="gtm",
        kind="floor",
        label="Pipeline coverage",
        rationale="Thin coverage understates the MQL and spend the funnel actually requires.",
        params={"min_multiple": 2.5},
        reads=("pipeline_coverage", "pipeline_min"),
        levers=("pipeline coverage multiple", "win rate", "MQL volume"),
        max_severity="medium",
    ),
    ConstraintDef(
        id="gtm_mql",
        domain="gtm",
        kind="identity",
        label="GTM MQL identity",
        rationale="Channel MQLs must reconcile to funnel-required MQLs or channel allocation is wrong.",
        params={"abs_tolerance": 2.0},
        reads=("fy_ch_mql", "fy_mql"),
        levers=("channel mix", "channel MQL targets"),
        max_severity="medium",
    ),
    ConstraintDef(
        id="gtm_spend",
        domain="gtm",
        kind="identity",
        label="GTM spend = MQL x CPL",
        rationale="Program spend must equal required MQLs times blended CPL, or marketing cost is unexplained.",
        params={"rel_tolerance": 0.005, "abs_tolerance": 100.0},
        reads=("fy_mkt", "fy_spend_id"),
        levers=("blended CPL", "channel mix", "program spend"),
        max_severity="medium",
    ),
    ConstraintDef(
        id="gtm_mix",
        domain="gtm",
        kind="identity",
        label="Channel mix sums to 100%",
        rationale="Un-normalized channel weights silently distort MQL and spend by channel.",
        params={"max_drift": 0.02},
        reads=("mix_dev_max",),
        levers=("channel weights",),
        max_severity="medium",
    ),
    ConstraintDef(
        id="jan_hc",
        domain="headcount",
        kind="identity",
        label="Jan HC lock",
        rationale="January headcount must equal the prior-December lock, or the plan restates history.",
        params={"abs_tolerance": 1.0},
        reads=("jan_hc", "jan_hc_expected"),
        levers=("hiring plan", "December lock"),
    ),
    ConstraintDef(
        id="ebitda",
        domain="pnl",
        kind="floor",
        label="FY EBITDA",
        rationale="Negative FY EBITDA has to be a deliberate growth choice tested against the cash floor.",
        params={"floor": 0.0},
        reads=("fy_ebitda", "fy_rev"),
        levers=("opex", "hiring pace", "marketing spend"),
        max_severity="medium",
    ),
    ConstraintDef(
        id="sm_tie",
        domain="pnl",
        kind="ceiling",
        label="GTM inside IS S&M",
        rationale="Implied GTM S&M is a component of the income-statement S&M line, never larger than it.",
        params={"ratio_ceiling": 1.02},
        reads=("fy_gtm_sm", "fy_is_sm"),
        levers=("MKT_SM_RATIO", "dept P&L allocation"),
        max_severity="medium",
    ),
)

REGISTRY_BY_ID: dict[str, ConstraintDef] = {c.id: c for c in REGISTRY}


@dataclass(frozen=True)
class ResolvedConstraint:
    """A constraint with its effective params and where each value came from."""

    definition: ConstraintDef
    params: dict[str, Any]
    param_sources: dict[str, str]
    enabled: bool = True

    @property
    def id(self) -> str:
        return self.definition.id


def resolve_constraints(
    packet: dict[str, Any] | None = None,
    tenant_overrides: dict[str, dict[str, Any]] | None = None,
    version_overrides: dict[str, dict[str, Any]] | None = None,
) -> list[ResolvedConstraint]:
    """Overlay overrides onto registry defaults.

    Precedence, highest first: version override, tenant override, packet-supplied
    value, registry default. Packet precedence keeps today's Budget Engine
    behaviour intact (the cash floor and bench target are user levers) while still
    letting an org pin a governed value.

    An override may carry ``{"enabled": False}`` to disable a constraint entirely.
    """

    packet = packet or {}
    tenant_overrides = tenant_overrides or {}
    version_overrides = version_overrides or {}

    resolved: list[ResolvedConstraint] = []
    for definition in REGISTRY:
        params = dict(definition.params)
        sources = {key: "default" for key in params}

        for param, packet_key in PACKET_SUPPLIED_PARAMS.get(definition.id, {}).items():
            value = packet.get(packet_key)
            if value is not None:
                params[param] = value
                sources[param] = f"packet.{packet_key}"

        enabled = True
        for layer_name, layer in (("tenant", tenant_overrides), ("version", version_overrides)):
            override = layer.get(definition.id)
            if not override:
                continue
            for key, value in override.items():
                if key == "enabled":
                    enabled = bool(value)
                    continue
                params[key] = value
                sources[key] = layer_name

        resolved.append(
            ResolvedConstraint(
                definition=definition,
                params=params,
                param_sources=sources,
                enabled=enabled,
            )
        )

    return resolved
