"""Feasibility runner — PPI Phase 1.

Evaluates the constraints registry against a plan packet and returns structured
pass / warn / fail results.

Parity note: the thresholds and severities here reproduce ``runBudgetRiskChecks``
in ``frontend/public/budget-engine/index.html``. ``tests/test_predictive_planning.py``
pins that parity. If a rule changes on one side, change it on both or the Budget
Engine and this API will disagree about the same plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.services.predictive_planning.constraints import (
    ResolvedConstraint,
    Severity,
    resolve_constraints,
)

#: "pass" | "warn" | "fail" | "advisory" | "skipped"
_SEVERITY_TO_STATUS: dict[str, str] = {
    "ok": "pass",
    "low": "advisory",
    "medium": "warn",
    "high": "fail",
}


@dataclass
class ConstraintResult:
    id: str
    label: str
    domain: str
    severity: Severity | str
    status: str
    title: str
    detail: str
    observed: float | None = None
    required: float | None = None
    gap: float | None = None
    unit: str = "number"
    params_used: dict[str, Any] | None = None
    skipped_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "domain": self.domain,
            "severity": self.severity,
            "status": self.status,
            "title": self.title,
            "detail": self.detail,
            "observed": self.observed,
            "required": self.required,
            "gap": self.gap,
            "unit": self.unit,
            "params_used": self.params_used or {},
            "skipped_reason": self.skipped_reason,
        }


def _m(value: float | None) -> str:
    """Money, matching the Budget Engine's `$X.XM` shorthand."""
    if value is None:
        return "n/a"
    return f"${value / 1_000_000:.1f}M"


def _n(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:,.0f}"


def _pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def _get(packet: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in packet and packet[key] is not None:
            return packet[key]
    return None


# --- individual evaluators -------------------------------------------------
# Each returns (severity, title, detail, observed, required, gap, unit).

def _eval_arr_path(p: dict[str, Any], q: dict[str, Any]):
    dec, target = _get(p, "dec_arr"), _get(p, "target_arr")
    if dec is None or target is None:
        return None
    tolerance = max(q["abs_tolerance"], target * q["rel_tolerance"])
    gap = dec - target
    growth = _get(p, "yoy_growth_pct") or 0.0
    if abs(gap) <= tolerance:
        return ("ok", "Dec ARR path", f"Hits YoY target {_m(target)} ({growth:.1f}%).", dec, target, gap, "currency")
    if gap < 0:
        return ("high", "Dec ARR short of YoY target", f"{_m(dec)} vs target {_m(target)} ({_m(gap)}).", dec, target, gap, "currency")
    return ("low", "Dec ARR above YoY target", f"{_m(dec)} vs {_m(target)} — confirm intentional upside.", dec, target, gap, "currency")


def _eval_arr_bridge(p: dict[str, Any], q: dict[str, Any]):
    bop, nn, dec = _get(p, "bop_arr"), _get(p, "fy_nn"), _get(p, "dec_arr")
    if bop is None or nn is None or dec is None:
        return None
    bridge = bop + nn
    gap = bridge - dec
    tolerance = max(q["abs_tolerance"], dec * q["rel_tolerance"])
    if abs(gap) <= tolerance:
        return ("ok", "ARR bridge identity", f"BOP {_m(bop)} + NN {_m(nn)} = Dec {_m(dec)}.", bridge, dec, gap, "currency")
    return ("high", "ARR bridge broken", f"BOP+NN {_m(bridge)} vs Dec EOP {_m(dec)} (gap {_m(gap)}).", bridge, dec, gap, "currency")


def _eval_grr_floor(p: dict[str, Any], q: dict[str, Any]):
    avg, low = _get(p, "avg_grr"), _get(p, "min_grr")
    if avg is None or low is None:
        return None
    if low >= q["min_month_floor"] and avg >= q["avg_floor"]:
        return ("ok", "GRR floor", f"Avg {_pct(avg)} · min month {_pct(low)}.", low, q["min_month_floor"], low - q["min_month_floor"], "ratio")
    if low >= q["hard_min_month"]:
        return ("medium", "GRR soft vs floor", f"Avg {_pct(avg)} · min {_pct(low)} (policy ≥{_pct(q['min_month_floor'])} min).", low, q["min_month_floor"], low - q["min_month_floor"], "ratio")
    return ("high", "GRR below floor", f"Min month {_pct(low)} · avg {_pct(avg)}.", low, q["min_month_floor"], low - q["min_month_floor"], "ratio")


def _eval_cash_floor(p: dict[str, Any], q: dict[str, Any]):
    end = _get(p, "end_cash")
    if end is None:
        return None
    floor = q["floor"]
    gap = end - floor
    if end >= floor:
        return ("ok", "Dec cash floor", f"{_m(end)} ≥ floor {_m(floor)}.", end, floor, gap, "currency")
    severity = "high" if end < floor * q["hard_breach_ratio"] else "medium"
    return (severity, "Dec cash below floor", f"{_m(end)} vs floor {_m(floor)} ({_m(gap)}).", end, floor, gap, "currency")


def _eval_cash_path(p: dict[str, Any], q: dict[str, Any]):
    low, end = _get(p, "min_cash"), _get(p, "end_cash")
    if low is None:
        return None
    floor = q["floor"]
    period = _get(p, "min_cash_period") or "trough"
    gap = low - floor
    if low >= floor:
        return ("ok", "Intra-year cash path", f"All months ≥ floor · trough {_m(low)} ({period}).", low, floor, gap, "currency")
    if end is not None and end >= floor:
        return ("medium", "Mid-year cash dip below floor", f"Trough {_m(low)} in {period} · Dec recovers to {_m(end)}.", low, floor, gap, "currency")
    return ("high", "Cash path breaches floor", f"Trough {_m(low)} ({period}) · Dec {_m(end)}.", low, floor, gap, "currency")


def _eval_nb_cover(p: dict[str, Any], q: dict[str, Any]):
    have, need = _get(p, "sales_end"), _get(p, "ae_needed")
    if have is None or need is None:
        return None
    gap = have - need
    if have >= need:
        return ("ok", "NB AE coverage", f"{_n(have)} ending AEs cover need {_n(need)}.", have, need, gap, "count")
    return ("high", "NB AE shortfall", f"{_n(have)} ending vs {_n(need)} needed for budget NB.", have, need, gap, "count")


def _eval_cs_cover(p: dict[str, Any], q: dict[str, Any]):
    have, need = _get(p, "cs_end"), _get(p, "cs_needed")
    if have is None or need is None:
        return None
    gap = have - need
    if have >= need:
        return ("ok", "CS coverage", f"{_n(have)} ending CS cover need {_n(need)}.", have, need, gap, "count")
    return ("high", "CS headcount shortfall", f"{_n(have)} ending vs {_n(need)} needed (expansion + churn cover).", have, need, gap, "count")


def _eval_bench(p: dict[str, Any], q: dict[str, Any]):
    cover = _get(p, "cover_pct")
    if cover is None:
        return None
    target = q["target_pct"]
    hire = _get(p, "hire_pct") or 0.0
    gap = cover - target
    if cover + q["slack_pp"] >= target:
        return ("ok", "Existing bench cover", f"Bench covers {cover:.0f}% of budget (target {target:.0f}%).", cover, target, gap, "percent")
    return ("medium", "Bench cover below expectation", f"{cover:.0f}% bench / {hire:.0f}% from hires (target bench {target:.0f}%).", cover, target, gap, "percent")


def _eval_pipeline(p: dict[str, Any], q: dict[str, Any]):
    coverage = _get(p, "pipeline_coverage")
    if coverage is None:
        return None
    minimum = q["min_multiple"]
    gap = coverage - minimum
    if coverage + 1e-9 >= minimum:
        return ("ok", "Pipeline coverage", f"{coverage:.1f}× on NB funnel (min {minimum:.1f}×).", coverage, minimum, gap, "multiple")
    return ("medium", "Pipeline coverage thin", f"{coverage:.1f}× vs min {minimum:.1f}× — funnel may understate required MQLs.", coverage, minimum, gap, "multiple")


def _eval_gtm_mql(p: dict[str, Any], q: dict[str, Any]):
    channel, required = _get(p, "fy_ch_mql") or 0.0, _get(p, "fy_mql") or 0.0
    gap = channel - required
    if abs(gap) <= q["abs_tolerance"]:
        return ("ok", "GTM MQL identity", f"Channel MQLs {_n(channel)} match funnel required {_n(required)}.", channel, required, gap, "count")
    return ("medium", "GTM MQL mismatch", f"Channel {_n(channel)} vs required {_n(required)} — check allocation.", channel, required, gap, "count")


def _eval_gtm_spend(p: dict[str, Any], q: dict[str, Any]):
    identity, actual = _get(p, "fy_spend_id") or 0.0, _get(p, "fy_mkt") or 0.0
    gap = actual - identity
    tolerance = max(q["abs_tolerance"], actual * q["rel_tolerance"])
    if abs(gap) <= tolerance:
        return ("ok", "GTM spend = MQL × CPL", f"Program {_m(actual)} ties to funnel × blended CPL.", actual, identity, gap, "currency")
    return ("medium", "GTM spend identity off", f"Spend {_m(actual)} vs MQL×CPL {_m(identity)} (gap {_m(abs(gap))}).", actual, identity, gap, "currency")


def _eval_gtm_mix(p: dict[str, Any], q: dict[str, Any]):
    drift = _get(p, "mix_dev_max")
    if drift is None:
        return None
    ceiling = q["max_drift"]
    if drift <= ceiling:
        return ("ok", "Channel mix sums to 100%", f"Max period mix drift {drift * 100:.1f}pp.", drift, ceiling, drift - ceiling, "ratio")
    return ("medium", "Channel mix not normalized", f"Max |mix−100%| {drift * 100:.1f}pp — renormalize channel weights.", drift, ceiling, drift - ceiling, "ratio")


def _eval_jan_hc(p: dict[str, Any], q: dict[str, Any]):
    actual, expected = _get(p, "jan_hc"), _get(p, "jan_hc_expected")
    if actual is None or expected is None:
        return None
    gap = actual - expected
    if abs(gap) <= q["abs_tolerance"]:
        return ("ok", "Jan HC lock", f"Jan {_n(actual)} matches Dec'26 forecast lock {_n(expected)}.", actual, expected, gap, "count")
    return ("high", "Jan HC unlocked from Dec'26", f"Jan {_n(actual)} vs lock {_n(expected)}.", actual, expected, gap, "count")


def _eval_ebitda(p: dict[str, Any], q: dict[str, Any]):
    ebitda = _get(p, "fy_ebitda")
    if ebitda is None:
        return None
    floor = q["floor"]
    revenue = _get(p, "fy_rev")
    if ebitda >= floor:
        return ("ok", "FY EBITDA", f"{_m(ebitda)} on {_m(revenue)} revenue.", ebitda, floor, ebitda - floor, "currency")
    return ("medium", "FY EBITDA negative", f"{_m(ebitda)} — confirm burn vs cash floor and growth case.", ebitda, floor, ebitda - floor, "currency")


def _eval_sm_tie(p: dict[str, Any], q: dict[str, Any]):
    gtm, income_statement = _get(p, "fy_gtm_sm"), _get(p, "fy_is_sm")
    if gtm is None or income_statement is None:
        return None
    ceiling = income_statement * q["ratio_ceiling"]
    gap = gtm - ceiling
    if gtm <= ceiling:
        return ("ok", "GTM inside IS S&M", f"Implied GTM S&M {_m(gtm)} ≤ IS S&M {_m(income_statement)}.", gtm, ceiling, gap, "currency")
    return ("medium", "GTM S&M exceeds IS S&M", f"GTM implied {_m(gtm)} vs IS {_m(income_statement)} — check MKT_SM_RATIO / dept P&L.", gtm, ceiling, gap, "currency")


EVALUATORS: dict[str, Callable[[dict[str, Any], dict[str, Any]], Any]] = {
    "arr_path": _eval_arr_path,
    "arr_bridge": _eval_arr_bridge,
    "grr_floor": _eval_grr_floor,
    "cash_floor": _eval_cash_floor,
    "cash_path": _eval_cash_path,
    "nb_cover": _eval_nb_cover,
    "cs_cover": _eval_cs_cover,
    "bench": _eval_bench,
    "pipeline": _eval_pipeline,
    "gtm_mql": _eval_gtm_mql,
    "gtm_spend": _eval_gtm_spend,
    "gtm_mix": _eval_gtm_mix,
    "jan_hc": _eval_jan_hc,
    "ebitda": _eval_ebitda,
    "sm_tie": _eval_sm_tie,
}


@dataclass
class FeasibilityReport:
    verdict: str  # "pass" | "warn" | "fail"
    results: list[ConstraintResult]
    counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "counts": self.counts,
            "results": [r.to_dict() for r in self.results],
        }

    def blocking(self) -> list[ConstraintResult]:
        return [r for r in self.results if r.status in ("fail", "warn", "advisory")]


def run_feasibility(
    packet: dict[str, Any],
    constraints: list[ResolvedConstraint] | None = None,
) -> FeasibilityReport:
    """Evaluate every enabled constraint against the plan packet.

    Verdict rules: any ``high`` makes the plan **fail**; any ``medium`` makes it
    **warn**; ``low`` is advisory and does not block. A constraint whose inputs are
    absent is reported as ``skipped`` rather than silently passing — a missing
    input is not evidence of a healthy plan.
    """

    resolved = constraints if constraints is not None else resolve_constraints(packet)
    results: list[ConstraintResult] = []

    for constraint in resolved:
        definition = constraint.definition
        if not constraint.enabled:
            results.append(
                ConstraintResult(
                    id=definition.id,
                    label=definition.label,
                    domain=definition.domain,
                    severity="ok",
                    status="skipped",
                    title=definition.label,
                    detail="Disabled by override.",
                    params_used=constraint.params,
                    skipped_reason="disabled_by_override",
                )
            )
            continue

        evaluator = EVALUATORS.get(definition.id)
        outcome = evaluator(packet, constraint.params) if evaluator else None

        if outcome is None:
            results.append(
                ConstraintResult(
                    id=definition.id,
                    label=definition.label,
                    domain=definition.domain,
                    severity="ok",
                    status="skipped",
                    title=definition.label,
                    detail="Inputs not present in packet.",
                    params_used=constraint.params,
                    skipped_reason="missing_inputs",
                )
            )
            continue

        severity, title, detail, observed, required, gap, unit = outcome
        results.append(
            ConstraintResult(
                id=definition.id,
                label=definition.label,
                domain=definition.domain,
                severity=severity,
                status=_SEVERITY_TO_STATUS[severity],
                title=title,
                detail=detail,
                observed=observed,
                required=required,
                gap=gap,
                unit=unit,
                params_used=constraint.params,
            )
        )

    counts = {
        "pass": sum(1 for r in results if r.status == "pass"),
        "warn": sum(1 for r in results if r.status == "warn"),
        "fail": sum(1 for r in results if r.status == "fail"),
        "advisory": sum(1 for r in results if r.status == "advisory"),
        "skipped": sum(1 for r in results if r.status == "skipped"),
    }

    if counts["fail"]:
        verdict = "fail"
    elif counts["warn"]:
        verdict = "warn"
    else:
        verdict = "pass"

    return FeasibilityReport(verdict=verdict, results=results, counts=counts)
