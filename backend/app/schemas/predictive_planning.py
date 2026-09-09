"""Predictive Planning Intelligence API schemas — the Phase 1 assessment DTO.

Field aliases accept the Budget Engine's camelCase packet
(``buildBudgetAssurancePacket``) unchanged, so the frontend can post what it
already computes without a translation layer.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PlanPacket(BaseModel):
    """Deterministic plan outputs the constraints are evaluated against.

    Every field is optional: a constraint whose inputs are absent is reported as
    ``skipped`` rather than passing silently.
    """

    period_label: str | None = None
    budget_year: int | None = None

    yoy_growth_pct: float | None = Field(default=None, alias="yoyGrowthPct")
    bop_arr: float | None = Field(default=None, alias="bopArr")
    dec_arr: float | None = Field(default=None, alias="decArr")
    target_arr: float | None = Field(default=None, alias="targetArr")
    fy_nn: float | None = Field(default=None, alias="fyNn")
    fy_rev: float | None = Field(default=None, alias="fyRev")
    fy_ebitda: float | None = Field(default=None, alias="fyEbitda")

    end_cash: float | None = Field(default=None, alias="endCash")
    cash_floor: float | None = Field(default=None, alias="cashFloor")
    min_cash: float | None = Field(default=None, alias="minCash")
    min_cash_period: str | None = Field(default=None, alias="minCashPeriod")
    cash_by_month: list[float] | None = Field(default=None, alias="cashByMonth")

    fy_mkt: float | None = Field(default=None, alias="fyMkt")
    fy_mql: float | None = Field(default=None, alias="fyMql")
    fy_ch_mql: float | None = Field(default=None, alias="fyChMql")
    fy_spend_id: float | None = Field(default=None, alias="fySpendId")
    mix_dev_max: float | None = Field(default=None, alias="mixDevMax")

    avg_grr: float | None = Field(default=None, alias="avgGrr")
    min_grr: float | None = Field(default=None, alias="minGrr")

    sales_end: float | None = Field(default=None, alias="salesEnd")
    cs_end: float | None = Field(default=None, alias="csEnd")
    ae_needed: float | None = Field(default=None, alias="aeNeeded")
    cs_needed: float | None = Field(default=None, alias="csNeeded")
    cover_pct: float | None = Field(default=None, alias="coverPct")
    hire_pct: float | None = Field(default=None, alias="hirePct")
    bench_target: float | None = Field(default=None, alias="benchTarget")

    jan_hc: float | None = Field(default=None, alias="janHc")
    jan_hc_expected: float | None = Field(default=None, alias="janHcExpected")
    dec_hc: float | None = Field(default=None, alias="decHc")

    pipeline_coverage: float | None = Field(default=None, alias="pipelineCoverage")
    pipeline_min: float | None = Field(default=None, alias="pipelineMin")

    fy_is_sm: float | None = Field(default=None, alias="fyIsSm")
    fy_gtm_sm: float | None = Field(default=None, alias="fyGtmSm")

    model_config = {"populate_by_name": True, "extra": "ignore"}


class PlanRef(BaseModel):
    """What plan this assessment is about.

    ``forecast_version_id`` / ``budget_version_id`` are how an assessment becomes
    attributable. Assessments computed without one are transient — useful for a
    live editing surface, not citable in a board package.
    """

    organization_id: uuid.UUID
    forecast_version_id: uuid.UUID | None = None
    budget_version_id: uuid.UUID | None = None
    scenario: str = "budget"
    period_label: str | None = None
    budget_year: int | None = None
    as_of: datetime | None = None


class SimulationSummaryIn(BaseModel):
    """Recorded output of the Budget Engine stress suite and Monte Carlo.

    Accepted and echoed, never recomputed here. Naming discipline: these are
    stress frequencies under stated priors, not calibrated Probability of
    Attainment.
    """

    trials: int | None = None
    breaks: list[str] = Field(default_factory=list)
    watches: list[str] = Field(default_factory=list)
    p_arr_miss: float | None = None
    p_cash_below_floor: float | None = None
    p_ops_liquidity: float | None = None
    p_ae_short: float | None = None
    priors: dict[str, Any] | None = None

    model_config = {"extra": "ignore"}


class ConstraintOverride(BaseModel):
    """Per-tenant or per-version overlay on a registry constraint."""

    enabled: bool | None = None
    params: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "ignore"}


class PlanAssessmentRequest(BaseModel):
    plan_ref: PlanRef
    packet: PlanPacket
    simulation: SimulationSummaryIn | None = None
    tenant_overrides: dict[str, ConstraintOverride] = Field(default_factory=dict)
    version_overrides: dict[str, ConstraintOverride] = Field(default_factory=dict)
    include_passing_conditions: bool = False


class ConstraintResultOut(BaseModel):
    id: str
    label: str
    domain: str
    severity: str
    status: str
    title: str
    detail: str
    observed: float | None = None
    required: float | None = None
    gap: float | None = None
    unit: str = "number"
    params_used: dict[str, Any] = Field(default_factory=dict)
    skipped_reason: str | None = None


class ConditionOut(BaseModel):
    constraint_id: str
    domain: str
    verdict: str
    statement: str
    rationale: str
    observed: float | None = None
    required: float | None = None
    gap: float | None = None
    unit: str = "number"
    levers: list[str] = Field(default_factory=list)
    origin: str
    severity: str


class FeasibilityOut(BaseModel):
    verdict: str
    counts: dict[str, int]
    results: list[ConstraintResultOut]


class ResolvedConstraintOut(BaseModel):
    id: str
    domain: str
    kind: str
    label: str
    rationale: str
    enabled: bool
    params: dict[str, Any]
    param_sources: dict[str, str]
    levers: list[str]
    reads: list[str]


class PlanAssessmentOut(BaseModel):
    """The Phase 1 assessment artifact."""

    plan_ref: PlanRef
    feasibility: FeasibilityOut
    what_has_to_be_true: list[ConditionOut]
    constraints_applied: list[ResolvedConstraintOut]
    simulation_summary: SimulationSummaryIn | None = None
    method_notes: list[str] = Field(default_factory=list)
    persisted: bool = False
    sources: list[str] = Field(default_factory=list, alias="_sources")

    model_config = {"populate_by_name": True}
