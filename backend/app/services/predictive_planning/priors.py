"""Company-history prior fitting for Plan Assurance Monte Carlo.

Returns independent vols (and optional correlations) grounded in supplied
history series. When history is thin or missing, falls back to DEFAULT_PRIORS
with an honest ``prior_source`` label — never silently claims a hist fit.
"""

from __future__ import annotations

import math
from typing import Any

from app.services.predictive_planning.monte_carlo import DEFAULT_PRIORS


def _series_stdev(values: list[float]) -> float | None:
    clean = [float(v) for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if len(clean) < 3:
        return None
    mu = sum(clean) / len(clean)
    var = sum((v - mu) ** 2 for v in clean) / (len(clean) - 1)
    return math.sqrt(var)


def _yoy_pp_series(ending_arr: list[float]) -> list[float]:
    out: list[float] = []
    for i in range(1, len(ending_arr)):
        prev, cur = ending_arr[i - 1], ending_arr[i]
        if prev and prev > 0:
            out.append((cur / prev - 1.0) * 100.0)
    return out


def fit_priors_from_history(
    history: dict[str, Any] | None,
    *,
    min_points: int = 3,
) -> dict[str, Any]:
    """Fit MC priors from optional history payload.

    Expected optional keys (any subset):
      ending_arr_yoy_pp: list[float]  # YoY pp changes
      ending_arr: list[float]         # year-end ARR levels (derive YoY)
      cpl_log_ratios: list[float]       # log CPL YoY ratios
      attrition_pp: list[float]
      pipeline_cover: list[float]
      correlations: dict[str, float]  # optional precomputed joints
    """

    history = history or {}
    sig = dict(DEFAULT_PRIORS)
    fitted: list[str] = []
    skipped: list[str] = []

    yoy_pp = list(history.get("ending_arr_yoy_pp") or [])
    if not yoy_pp and history.get("ending_arr"):
        yoy_pp = _yoy_pp_series(list(history["ending_arr"]))
    sd = _series_stdev(yoy_pp)
    if sd is not None and len(yoy_pp) >= min_points:
        sig["yoyPp"] = max(1.0, min(12.0, sd))
        fitted.append("yoyPp")
    else:
        skipped.append("yoyPp")

    cpl = list(history.get("cpl_log_ratios") or [])
    sd = _series_stdev(cpl)
    if sd is not None and len(cpl) >= min_points:
        sig["cplLog"] = max(0.05, min(0.8, sd))
        fitted.append("cplLog")
    else:
        skipped.append("cplLog")

    attr = list(history.get("attrition_pp") or [])
    sd = _series_stdev(attr)
    if sd is not None and len(attr) >= min_points:
        sig["attrPp"] = max(0.5, min(10.0, sd))
        fitted.append("attrPp")
    else:
        skipped.append("attrPp")

    pipe = list(history.get("pipeline_cover") or [])
    sd = _series_stdev(pipe)
    if sd is not None and len(pipe) >= min_points:
        sig["pipe"] = max(0.15, min(2.0, sd))
        fitted.append("pipe")
    else:
        skipped.append("pipe")

    correlations = history.get("correlations")
    if not isinstance(correlations, dict):
        correlations = None

    if not fitted:
        source = "independent_defaults"
        label = "Hardcoded independent priors (insufficient company history to fit)."
    elif skipped:
        source = "history_partial"
        label = (
            f"Partially history-fit ({', '.join(fitted)}); "
            f"defaults retained for {', '.join(skipped)}."
        )
    else:
        source = "history_fit"
        label = "Company-history fitted independent vols (correlations optional)."

    return {
        "priors": sig,
        "prior_source": source,
        "label": label,
        "fitted": fitted,
        "skipped": skipped,
        "correlations": correlations,
        "method_card": {
            "what": "Monte Carlo lever priors for Plan Assurance path stress",
            "source": source,
            "priors": sig,
            "correlations": correlations,
            "not_claimed": [
                "Calibrated Probability of Attainment",
                "Causal forecasts of ARR / cash",
                "AutoML time-series prediction",
            ],
            "notes": [
                label,
                "Levers are drawn independently unless correlations are supplied.",
                "Breach rates are stress frequencies under these priors, not PoA.",
            ],
        },
    }
