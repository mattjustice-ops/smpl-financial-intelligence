"""Company-history prior fitting for Plan Assurance Monte Carlo.

Returns lever vols and lever correlations measured from supplied history series. A lever with too little history,
or history that is not company actuals, gets no prior and is not drawn; the label names it. Nothing is defaulted
or clamped.
"""

from __future__ import annotations

import math
from typing import Any

from app.services.predictive_planning.monte_carlo import (
    LEVERS,
    correlation_key,
    normalize_correlations,
)

#: Growth rates needed before a vol is fitted (4+ ARR levels for monthly history).
MIN_POINTS = 3
#: Paired observations needed before a correlation is estimated from history.
MIN_CORRELATION_PAIRS = 12
#: History sources that are not company actuals and must never be fitted.
NON_ACTUAL_SOURCES = frozenset({"demo_seed", "demo", "synthetic", "backcast"})

_LEVER_LABELS = {
    "yoyPp": "ARR growth",
    "nbLog": "new business",
    "expLog": "expansion",
    "contLog": "contraction",
    "churnLog": "churn",
    "billPp": "annual billing",
    "cogsPp": "cost of revenue",
    "cplLog": "cost per lead",
    "attrPp": "sales attrition",
    "pipe": "pipeline coverage",
    "attainPp": "quota attainment",
}
_SERIES = (
    ("cplLog", "cpl_log_ratios", "cpl_periods", "same_month_yoy_log_cpl",
     "same-month year-over-year log change in program spend per MQL"),
    ("attrPp", "attrition_pp", "attrition_periods", "quarterly_closer_attrition_annualised",
     "closers' quarterly departures ÷ average heads, annualised"),
    ("pipe", "pipeline_cover", "pipeline_cover_periods", "quarterly_pipeline_over_won",
     "quarterly pipeline created / closed-won"),
    ("nbLog", "nb_log_ratios", "nb_periods", "trailing_year_log_new_business",
     "log change in trailing-twelve-month new-business ARR"),
    ("expLog", "exp_log_ratios", "exp_periods", "trailing_year_log_expansion",
     "log change in trailing-twelve-month expansion ARR"),
    ("contLog", "cont_log_ratios", "cont_periods", "trailing_year_log_contraction",
     "log change in trailing-twelve-month contraction ARR"),
    ("churnLog", "churn_log_ratios", "churn_periods", "trailing_year_log_churn",
     "log change in trailing-twelve-month churn ARR"),
    ("billPp", "annual_bill_pp", "annual_bill_periods", "monthly_annual_billing_share",
     "share of closed-won new-business ARR on a term of 12 months or more, in percentage points"),
    ("cogsPp", "cogs_pct_rev", "cogs_periods", "monthly_cogs_percent_of_revenue",
     "cost of revenue as a percent of revenue"),
    ("attainPp", "attainment_pp", "attainment_periods", "monthly_closer_attainment",
     "closers' attainment of ramped quota, in percentage points"),
)


def _clean(values: list[Any] | None) -> list[float]:
    out: list[float] = []
    for v in values or []:
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if not math.isnan(f):
            out.append(f)
    return out


def _series_stdev(values: list[float]) -> float | None:
    if len(values) < MIN_POINTS:
        return None
    mu = sum(values) / len(values)
    var = sum((v - mu) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(var)


def _growth_pp_series(levels: list[float]) -> list[float]:
    out: list[float] = []
    for i in range(1, len(levels)):
        prev, cur = levels[i - 1], levels[i]
        if prev and prev > 0:
            out.append((cur / prev - 1.0) * 100.0)
    return out


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n != len(ys) or n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(sxx * syy)


def _period_span(periods: list[Any] | None, n: int) -> str | None:
    labels = [str(p) for p in (periods or []) if p]
    if len(labels) != n or not labels:
        return None
    return f"{labels[0]}..{labels[-1]}"


def _labels(levers: list[str]) -> str:
    return ", ".join(_LEVER_LABELS[k] for k in levers)


def fit_priors_from_history(
    history: dict[str, Any] | None,
    levers: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any]:
    """Fit MC priors and correlations from an optional history payload.

    Optional keys (any subset):
      monthly_ending_arr: list[float]  # closed month-end ARR levels, oldest first
      periods: list[str]               # labels matching monthly_ending_arr
      source: str                      # e.g. "warehouse"; demo/backcast sources are never fitted
      ending_arr: list[float]          # year-end ARR levels, oldest first
      ending_arr_yoy_pp: list[float]   # annual growth rates in pp
      cpl_log_ratios: list[float]      # log(CPL / same month a year earlier), CPL = program spend / MQLs
      cpl_periods: list[str]
      attrition_pp: list[float]        # closers' annualised attrition per quarter, pp
      attrition_periods: list[str]
      pipeline_cover: list[float]      # quarterly pipeline created / closed-won
      pipeline_cover_periods: list[str]
      correlations: dict[str, float]   # caller-supplied "<a>:<b>" -> rho

    Monthly ARR growth is annualised as sd(monthly growth pp) * sqrt(12), which
    assumes month-to-month growth deviations are independent. Correlations are
    estimated only between fitted levers whose series have equal length and at
    least MIN_CORRELATION_PAIRS aligned observations.
    """

    history = history or {}
    use = tuple(levers) if levers is not None else LEVERS
    sig: dict[str, float] = {}
    basis: dict[str, dict[str, Any]] = {}
    source = str(history.get("source") or "").strip() or None
    non_actual = source is not None and source.lower() in NON_ACTUAL_SOURCES

    lever_series: dict[str, list[float]] = {}

    monthly_levels = [v for v in _clean(history.get("monthly_ending_arr")) if v > 0]
    annual_yoy = _clean(history.get("ending_arr_yoy_pp"))
    annual_levels = _clean(history.get("ending_arr"))
    if "yoyPp" in use and monthly_levels:
        growth = _growth_pp_series(monthly_levels)
        sd = _series_stdev(growth)
        basis["yoyPp"] = {
            "method": "monthly_arr_growth_annualised",
            "observations": len(growth),
            "required": MIN_POINTS,
            "span": _period_span(history.get("periods"), len(monthly_levels)),
            "source": source,
        }
        yoy_sd = sd * math.sqrt(12) if sd is not None else None
    elif "yoyPp" in use:
        growth = annual_yoy or _growth_pp_series(annual_levels)
        basis["yoyPp"] = {
            "method": "annual_arr_growth",
            "observations": len(growth),
            "required": MIN_POINTS,
            "source": source,
        }
        yoy_sd = _series_stdev(growth)
    else:
        growth = []
        yoy_sd = None
    if "yoyPp" in use:
        lever_series["yoyPp"] = growth
        if yoy_sd is not None and not non_actual:
            sig["yoyPp"] = yoy_sd

    for lever, key, period_key, method, _ in _SERIES:
        if lever not in use:
            continue
        values = _clean(history.get(key))
        lever_series[lever] = values
        basis[lever] = {
            "method": history.get(f"{lever}_method") or method,
            "observations": len(values),
            "required": MIN_POINTS,
            "source": source,
        }
        span = _period_span(history.get(period_key), len(values))
        if span:
            basis[lever]["span"] = span
        sd = _series_stdev(values)
        if sd is not None and not non_actual:
            sig[lever] = sd

    fitted = [k for k in use if k in sig]
    skipped = [k for k in use if k not in sig]
    for lever in use:
        basis[lever]["fitted"] = lever in sig
        basis[lever]["value"] = sig.get(lever)

    correlations: dict[str, float] = {}
    correlation_basis: dict[str, dict[str, Any]] = {}
    for i, a in enumerate(fitted):
        for b in fitted[i + 1 :]:
            xs, ys = lever_series.get(a) or [], lever_series.get(b) or []
            if len(xs) != len(ys) or len(xs) < MIN_CORRELATION_PAIRS:
                continue
            rho = _pearson(xs, ys)
            if rho is None:
                continue
            key = correlation_key(a, b, use)
            correlations[key] = rho
            correlation_basis[key] = {"source": "history_fit", "observations": len(xs)}

    supplied, rejected = normalize_correlations(history.get("correlations"), use)
    for key, rho in supplied.items():
        a, b = key.split(":")
        if a in sig and b in sig:
            correlations[key] = rho
            correlation_basis[key] = {"source": "caller_supplied"}
        else:
            rejected.append(f"{key}: a lever in the pair has no fitted prior")

    if non_actual:
        prior_source = "not_fitted"
        label = (
            f"No lever priors — the history supplied is {source} data, not company actuals, "
            "so nothing was fitted and no lever is drawn."
        )
    elif not fitted:
        prior_source = "not_fitted"
        yoy_obs = basis.get("yoyPp", {}).get("observations", 0)
        detail = (
            f" ({yoy_obs} ARR growth observation{'s' if yoy_obs != 1 else ''}; {MIN_POINTS} needed)"
            if "yoyPp" in use
            else ""
        )
        label = (
            "No lever priors — not enough company history to fit any"
            f"{detail}, so no lever is drawn."
        )
    elif skipped:
        prior_source = "history_partial"
        label = (
            f"Fitted from company history: {_labels(fitted)}. "
            f"Not drawn (no usable history): {_labels(skipped)}."
        )
    else:
        prior_source = "history_fit"
        label = "All lever vols fitted from company history."

    if correlations:
        corr_label = "Correlated draws: " + ", ".join(
            f"{k} rho={v:+.2f} ({correlation_basis[k]['source']})" for k, v in sorted(correlations.items())
        )
    else:
        corr_label = (
            "Independent draws — no correlations supplied, and fewer than "
            f"{MIN_CORRELATION_PAIRS} paired history observations to estimate any."
        )

    history_note = None
    yb = basis.get("yoyPp")
    if yb and yb["observations"]:
        origin = source or "unspecified source"
        if yb["method"] == "monthly_arr_growth_annualised":
            span = f", month-end ARR {yb['span']}" if yb.get("span") else ""
            history_note = (
                f"ARR growth history: {yb['observations']} monthly growth rates ({origin}{span}); "
                "annual vol = sd of monthly growth x sqrt(12)."
            )
        else:
            history_note = (
                f"ARR growth history: {yb['observations']} annual growth rates ({origin}); "
                "vol = sd of annual growth."
            )

    notes = [label, corr_label]
    if history_note:
        notes.append(history_note)
    for lever, _, _, _, what in _SERIES:
        if lever not in use:
            continue
        b = basis[lever]
        if lever in sig:
            span = f", {b['span']}" if b.get("span") else ""
            notes.append(f"{_LEVER_LABELS[lever].capitalize()} history: {b['observations']} observations of {what}{span}.")
    notes.extend(f"Correlation ignored — {r}." for r in rejected)
    notes.append("Breach rates are stress frequencies under these priors, not PoA.")

    return {
        "priors": sig,
        "prior_source": prior_source,
        "label": label,
        "fitted": fitted,
        "skipped": skipped,
        "correlations": correlations or None,
        "method_card": {
            "what": "Monte Carlo lever priors for Plan Assurance path stress",
            "source": prior_source,
            "priors": dict(sig),
            "correlations": correlations,
            "correlation_basis": correlation_basis,
            "history_basis": basis,
            "history_source": source,
            "not_claimed": [
                "Calibrated Probability of Attainment",
                "Causal forecasts of ARR / cash",
                "AutoML time-series prediction",
            ],
            "notes": notes,
        },
    }
