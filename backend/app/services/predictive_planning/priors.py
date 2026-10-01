"""Company-history prior fitting for Plan Assurance Monte Carlo.

Returns lever vols and lever correlations grounded in supplied history series.
When history is thin, missing, or not company actuals, falls back to
DEFAULT_PRIORS with an honest ``prior_source`` label — never silently claims a
history fit.
"""

from __future__ import annotations

import math
from typing import Any

from app.services.predictive_planning.monte_carlo import (
    DEFAULT_PRIORS,
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
    "cplLog": "cost per lead",
    "attrPp": "sales attrition",
    "pipe": "pipeline coverage",
}


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


def _period_span(periods: list[Any] | None, n_levels: int) -> str | None:
    labels = [str(p) for p in (periods or []) if p]
    if len(labels) != n_levels or not labels:
        return None
    return f"{labels[0]}..{labels[-1]}"


def fit_priors_from_history(history: dict[str, Any] | None) -> dict[str, Any]:
    """Fit MC priors and correlations from an optional history payload.

    Optional keys (any subset):
      monthly_ending_arr: list[float]  # closed month-end ARR levels, oldest first
      periods: list[str]               # labels matching monthly_ending_arr
      source: str                      # e.g. "warehouse"; demo/backcast sources are never fitted
      ending_arr: list[float]          # year-end ARR levels, oldest first
      ending_arr_yoy_pp: list[float]   # annual growth rates in pp
      cpl_log_ratios: list[float]      # log CPL year-over-year ratios
      attrition_pp: list[float]
      pipeline_cover: list[float]
      correlations: dict[str, float]   # caller-supplied "<a>:<b>" -> rho

    Monthly ARR growth is annualised as sd(monthly growth pp) * sqrt(12), which
    assumes month-to-month growth deviations are independent. Correlations are
    estimated only for lever series of equal length with at least
    MIN_CORRELATION_PAIRS aligned observations.
    """

    history = history or {}
    sig = dict(DEFAULT_PRIORS)
    fitted: list[str] = []
    skipped: list[str] = []
    basis: dict[str, dict[str, Any]] = {}
    source = str(history.get("source") or "").strip() or None
    non_actual = source is not None and source.lower() in NON_ACTUAL_SOURCES

    lever_series: dict[str, list[float]] = {}

    monthly_levels = [v for v in _clean(history.get("monthly_ending_arr")) if v > 0]
    annual_yoy = _clean(history.get("ending_arr_yoy_pp"))
    annual_levels = _clean(history.get("ending_arr"))
    if monthly_levels:
        growth = _growth_pp_series(monthly_levels)
        sd = _series_stdev(growth)
        lever_series["yoyPp"] = growth
        basis["yoyPp"] = {
            "method": "monthly_arr_growth_annualised",
            "observations": len(growth),
            "required": MIN_POINTS,
            "span": _period_span(history.get("periods"), len(monthly_levels)),
            "source": source,
        }
        yoy_sd = sd * math.sqrt(12) if sd is not None else None
    else:
        growth = annual_yoy or _growth_pp_series(annual_levels)
        lever_series["yoyPp"] = growth
        basis["yoyPp"] = {
            "method": "annual_arr_growth",
            "observations": len(growth),
            "required": MIN_POINTS,
            "source": source,
        }
        yoy_sd = _series_stdev(growth)

    if yoy_sd is not None and not non_actual:
        sig["yoyPp"] = max(1.0, min(12.0, yoy_sd))
        fitted.append("yoyPp")
    else:
        skipped.append("yoyPp")

    for lever, key, lo, hi in (
        ("cplLog", "cpl_log_ratios", 0.05, 0.8),
        ("attrPp", "attrition_pp", 0.5, 10.0),
        ("pipe", "pipeline_cover", 0.15, 2.0),
    ):
        values = _clean(history.get(key))
        lever_series[lever] = values
        basis[lever] = {"observations": len(values), "required": MIN_POINTS, "source": source}
        sd = _series_stdev(values)
        if sd is not None and not non_actual:
            sig[lever] = max(lo, min(hi, sd))
            fitted.append(lever)
        else:
            skipped.append(lever)

    for lever in LEVERS:
        basis[lever]["fitted"] = lever in fitted
        basis[lever]["value"] = sig[lever]

    correlations: dict[str, float] = {}
    correlation_basis: dict[str, dict[str, Any]] = {}
    if not non_actual:
        for i, a in enumerate(LEVERS):
            for b in LEVERS[i + 1 :]:
                xs, ys = lever_series.get(a) or [], lever_series.get(b) or []
                if len(xs) != len(ys) or len(xs) < MIN_CORRELATION_PAIRS:
                    continue
                rho = _pearson(xs, ys)
                if rho is None:
                    continue
                key = correlation_key(a, b)
                correlations[key] = max(-0.95, min(0.95, rho))
                correlation_basis[key] = {"source": "history_fit", "observations": len(xs)}

    supplied, rejected = normalize_correlations(history.get("correlations"))
    for key, rho in supplied.items():
        correlations[key] = rho
        correlation_basis[key] = {"source": "caller_supplied"}

    if non_actual:
        prior_source = "independent_defaults"
        label = (
            f"Default priors — the history supplied is {source} data, not company actuals, "
            "so nothing was fitted."
        )
    elif not fitted:
        prior_source = "independent_defaults"
        yoy_obs = basis["yoyPp"]["observations"]
        label = (
            "Default priors — not enough company history to fit "
            f"({yoy_obs} ARR growth observation{'s' if yoy_obs != 1 else ''}; {MIN_POINTS} needed)."
        )
    elif skipped:
        prior_source = "history_partial"
        label = (
            f"Fitted from company history: {', '.join(_LEVER_LABELS[k] for k in fitted)}. "
            f"Defaults kept for {', '.join(_LEVER_LABELS[k] for k in skipped)} (no usable history)."
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
    yb = basis["yoyPp"]
    if yb["observations"]:
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
            "priors": sig,
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
