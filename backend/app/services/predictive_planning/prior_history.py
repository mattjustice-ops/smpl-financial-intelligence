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

_BRIDGE = (
    ("nbLog", "nb_log_ratios", "nb_periods", "arr_nb"),
    ("expLog", "exp_log_ratios", "exp_periods", "arr_exp"),
    ("contLog", "cont_log_ratios", "cont_periods", "arr_cont"),
    ("churnLog", "churn_log_ratios", "churn_periods", "arr_churn"),
)


def _shift_month(period: str, delta: int) -> str:
    year, month = int(period[:4]), int(period[5:7])
    index = year * 12 + (month - 1) + delta
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def _component_points(mrr: dict[str, Any], as_of: str, key: str) -> list[tuple[str, float]]:
    points: list[tuple[str, float]] = []
    for period in sorted(p for p in mrr if p <= as_of and len(p) == 7):
        metrics = _normalize_mrr_metrics(mrr[period])
        value = metrics.get(key)
        if value is None:
            continue
        points.append((period, abs(float(value))))
    return points


def _log_changes(points: list[tuple[str, float]]) -> tuple[list[float], list[str], str]:
    """Width of a full-year component: trailing-twelve-month log change, else same-month log change.

    A month that is missing, or a total that is zero, is skipped. Nothing is filled in.
    """

    idx = {period: value for period, value in points}
    trailing: list[float] = []
    trailing_periods: list[str] = []
    for period in sorted(idx):
        window = [_shift_month(period, -k) for k in range(11, -1, -1)]
        prior = [_shift_month(period, -k) for k in range(23, 11, -1)]
        if any(month not in idx for month in window + prior):
            continue
        current = sum(idx[month] for month in window)
        previous = sum(idx[month] for month in prior)
        if current > 0 and previous > 0:
            trailing.append(math.log(current / previous))
            trailing_periods.append(period)
    if len(trailing) >= 3:
        return trailing, trailing_periods, "trailing_twelve_month_log_change"

    same: list[float] = []
    same_periods: list[str] = []
    for period in sorted(idx):
        previous = _shift_month(period, -12)
        if previous in idx and idx[period] > 0 and idx[previous] > 0:
            same.append(math.log(idx[period] / idx[previous]))
            same_periods.append(period)
    return same, same_periods, "same_month_yoy_log_change"


def bridge_log_history(mrr: dict[str, Any], as_of: str) -> dict[str, Any]:
    """Log-change history for new business, expansion, contraction and churn."""

    out: dict[str, Any] = {}
    for lever, values_key, periods_key, metric in _BRIDGE:
        values, periods, method = _log_changes(_component_points(mrr, as_of, metric))
        out[values_key] = values
        out[periods_key] = periods
        out[f"{lever}_method"] = method
    return out


def cogs_percent_history(income: dict[str, Any] | None) -> tuple[list[float], list[str]]:
    """Monthly cost of revenue as a percent of revenue. A month without revenue is skipped."""

    values: list[float] = []
    periods: list[str] = []
    for period in sorted(income or {}):
        row = income.get(period) or {}
        revenue = row.get("revenue")
        cogs = row.get("cogs")
        if revenue is None or cogs is None:
            continue
        try:
            revenue_f, cogs_f = float(revenue), float(cogs)
        except (TypeError, ValueError):
            continue
        if revenue_f > 0:
            values.append(cogs_f / revenue_f * 100.0)
            periods.append(str(period))
    return values, periods


def _num(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return number


def attainment_history(rows: list[dict[str, Any]] | None, as_of: str) -> tuple[list[float], list[str]]:
    """Closers' monthly attainment of ramped quota, in percentage points."""

    actual: dict[str, float] = {}
    ramped: dict[str, float] = {}
    for row in rows or []:
        if str(row.get("quota_type") or "").strip().lower() != "bookings arr":
            continue
        period = str(row.get("period") or "")[:7]
        if len(period) != 7 or period > as_of:
            continue
        got = _num(row.get("quota_attainment_actual_arr"))
        quota = _num(row.get("ramped_monthly_quota_arr"))
        if got is None or quota is None:
            continue
        actual[period] = actual.get(period, 0.0) + got
        ramped[period] = ramped.get(period, 0.0) + quota
    values: list[float] = []
    periods: list[str] = []
    for period in sorted(ramped):
        if ramped[period] > 0:
            values.append(actual.get(period, 0.0) / ramped[period] * 100.0)
            periods.append(period)
    return values, periods


def annual_billing_history(rows: list[dict[str, Any]] | None, as_of: str) -> tuple[list[float], list[str]]:
    """Share of closed-won new-business ARR on a term of at least 12 months, in percentage points.

    A deal with no term is left out of that month. A month with no termed deals is skipped.
    """

    annual: dict[str, float] = {}
    total: dict[str, float] = {}
    for row in rows or []:
        if str(row.get("opportunity_type") or "").strip().lower() != "new business":
            continue
        if str(row.get("close_status") or "").strip().lower() != "closed won":
            continue
        period = str(row.get("period") or "")[:7]
        if len(period) != 7 or period > as_of:
            continue
        term = _num(row.get("contract_term_months"))
        amount = _num(row.get("amount_arr"))
        if term is None or amount is None:
            continue
        amount = abs(amount)
        total[period] = total.get(period, 0.0) + amount
        if term >= 12:
            annual[period] = annual.get(period, 0.0) + amount
    values: list[float] = []
    periods: list[str] = []
    for period in sorted(total):
        if total[period] > 0:
            values.append(annual.get(period, 0.0) / total[period] * 100.0)
            periods.append(period)
    return values, periods


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
    history.update(bridge_log_history(mrr, as_of))
    cogs, cogs_periods = cogs_percent_history((actual.get("is") or {}))
    history["cogs_pct_rev"] = cogs
    history["cogs_periods"] = cogs_periods
    from app.services.readiness.commission_plan_inputs import _rows

    attainment, attainment_periods = attainment_history(_rows(db, "actual_sales_quotas", organization_id), as_of)
    history["attainment_pp"] = attainment
    history["attainment_periods"] = attainment_periods
    billing, billing_periods = annual_billing_history(_rows(db, "actual_opportunities", organization_id), as_of)
    history["annual_bill_pp"] = billing
    history["annual_bill_periods"] = billing_periods
    attrition = closer_attrition_by_quarter(db, organization_id, first, as_of)
    history["attrition_pp"] = attrition["pp"]
    history["attrition_periods"] = attrition["periods"]
    return history
