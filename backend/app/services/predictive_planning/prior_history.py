"""Closed-month company history the Monte Carlo lever priors are fitted from, read from the warehouse.

- ARR growth: month-end ARR from the actual MRR waterfall, the unbroken run of closed months ending at the close
  (the first month contributes its beginning ARR).
- Cost per lead: log(CPL / CPL in the same month a year earlier), CPL = GL marketing program spend ÷ MQLs from the
  actual marketing pipeline.
- Pipeline coverage: pipeline ARR created ÷ closed-won ARR per calendar quarter with all three months loaded.
- Sales attrition: closers' annualised attrition per closed quarter from the roster
  (``sales_team_inputs.closer_attrition_by_quarter``), over the same window.

A month missing an input is skipped, never filled.
"""

from __future__ import annotations

import math
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.services.readiness.sales_team_inputs import closer_attrition_by_quarter
from app.services.reporting.period_utils import prior_period
from app.services.reporting.three_statement_payload import (
    _aggregate_mrr_by_period,
    _normalize_mrr_metrics,
    _read_statement_table,
    _scenario_funnel,
    build_ts_data,
)

SOURCE = "warehouse"


def _arr_levels(mrr: dict[str, Any], as_of: str) -> tuple[list[float], list[str]]:
    levels: list[float] = []
    periods: list[str] = []
    for period in sorted(p for p in mrr if p <= as_of):
        metrics = _normalize_mrr_metrics(mrr[period])
        eop, bop = metrics.get("arr_eop"), metrics.get("arr_bop")
        if periods and periods[-1] != prior_period(period):
            levels, periods = [], []
        if eop is None or eop <= 0:
            levels, periods = [], []
            continue
        if not levels and bop is not None and bop > 0:
            levels.append(float(bop))
            periods.append(prior_period(period))
        levels.append(float(eop))
        periods.append(period)
    return levels, periods


def _gtm_series(
    funnel: dict[str, dict[str, float]], programs: dict[str, dict[str, Any]]
) -> dict[str, list[Any]]:
    def month(period: str) -> dict[str, float | None] | None:
        row = funnel.get(period)
        if row is None:
            return None
        lines = programs.get(period) or {}
        spend = sum(float(v or 0) for v in lines.values()) if lines else None
        mqls = row.get("mqls")
        return {
            "cpl": spend / mqls if spend and mqls else None,
            "pipe": row.get("pipeline_arr_created"),
            "won": row.get("closed_won_arr"),
        }

    out: dict[str, list[Any]] = {"cpl_log_ratios": [], "cpl_periods": [], "pipeline_cover": [], "pipeline_cover_periods": []}
    quarters: dict[str, dict[str, float]] = {}
    for period in sorted(funnel):
        cur = month(period)
        if cur is None:
            continue
        prior = month(f"{int(period[:4]) - 1:04d}{period[4:]}")
        if cur["cpl"] is not None and prior is not None and prior["cpl"] is not None:
            out["cpl_log_ratios"].append(math.log(cur["cpl"] / prior["cpl"]))
            out["cpl_periods"].append(period)
        q = f"{period[:4]}-Q{(int(period[5:7]) - 1) // 3 + 1}"
        bucket = quarters.setdefault(q, {"n": 0, "pipe": 0.0, "won": 0.0})
        if cur["pipe"] is not None and cur["won"] is not None:
            bucket["n"] += 1
            bucket["pipe"] += float(cur["pipe"])
            bucket["won"] += float(cur["won"])
    for q in sorted(quarters):
        b = quarters[q]
        if b["n"] == 3 and b["won"] > 0:
            out["pipeline_cover"].append(b["pipe"] / b["won"])
            out["pipeline_cover_periods"].append(q)
    return out


def build_prior_history(db: Session, organization_id: uuid.UUID, *, as_of: str) -> dict[str, Any]:
    """History payload for ``fit_priors_from_history`` from the organization's closed months through ``as_of``."""

    mrr = _aggregate_mrr_by_period(_read_statement_table(db, organization_id, "actual_mrr_waterfall"))
    levels, periods = _arr_levels(mrr, as_of)
    history: dict[str, Any] = {"monthly_ending_arr": levels, "periods": periods, "source": SOURCE}
    if not periods:
        return history
    first = periods[1] if len(periods) > 1 else periods[0]
    funnel = _scenario_funnel(db, organization_id, "Actual", first, as_of)
    actual = build_ts_data(
        db, organization_id, as_of=as_of, start_period=first, end_period=as_of, only=("Actual",)
    ).get("Actual") or {}
    history.update(_gtm_series(funnel, actual.get("gl_programs") or {}))
    attrition = closer_attrition_by_quarter(db, organization_id, first, as_of)
    history["attrition_pp"] = attrition["pp"]
    history["attrition_periods"] = attrition["periods"]
    return history
