"""One fact for every metric the board deck can show.

The deck reads this registry. It does not compute a second gross margin, a second
pipeline figure, or a growth rate of its own. A bridge that does not tie is a fact,
and the sentence is not allowed to explain the gap.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.services.reporting.export.board_chart_service import _grr, _nrr, _wf
from app.services.reporting.export.board_metrics_snapshot import build_metrics_snapshot
from app.services.reporting.export.board_platform_metrics import (
    _cash_bridge_table_amount,
    _cash_wf_amount,
    _fy_budget_gross_margin_pct,
    _fy_outlook_gross_margin_pct,
    gross_margin_pct,
    gross_margin_pct_horizon,
)
from app.services.reporting.export.board_slide_commentary_payload import fmt_deck_money, fmt_deck_pct
from app.services.reporting.export.is_line_resolver import ending_cash_at, fs_sum_periods
from app.services.reporting.export.metric_registry import (
    arr_bridge_identity_expected,
    compute_churn_arr,
    compute_contraction_arr,
    compute_ending_arr,
    compute_expansion_arr,
    compute_net_new_arr,
    compute_new_business_arr,
    compute_reactivation_arr,
)
from app.services.reporting.export.schemas import ReportingBundle
from app.services.reporting.export.period_views import qtd_periods, ytd_periods
from app.services.reporting.period_utils import prior_period

ZERO = Decimal("0")
MONEY_TOLERANCE = Decimal("1")
MATERIALITY = Decimal("10000")
ON_PLAN_RATIO = Decimal("0.02")
PERCENT_CAP = Decimal("2")

STANDARD_PROFILE = {
    "id": "smpl-standard",
    "label": "SMPL standard board deck",
    "slides": [
        "cover",
        "executive_dashboard",
        "arr_analysis",
        "pl_review",
        "cash_liquidity",
        "gtm_funnel",
        "pipeline",
        "risks",
        "outlook",
        "board_actions",
        "appendix_cfs",
    ],
    "title_pattern": "{slide} — {period}",
    "comparison": "budget",
}


def attach_deck_facts(
    payload: dict[str, Any],
    bundle: ReportingBundle,
    cash_bridge_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach the registry and make the payload show one value per fact."""
    built = build_fact_registry(bundle, cash_bridge_data=cash_bridge_data)
    payload["deck_profile"] = dict(STANDARD_PROFILE)
    payload["facts"] = built["facts"]
    payload["fact_ties"] = built["ties"]
    _publish(payload, built["by_id"])
    warnings = list(payload.get("payload_warnings") or [])
    for tie in built["ties"]:
        if not tie["ok"]:
            warnings.append(tie["detail"])
    payload["payload_warnings"] = warnings
    return payload


def build_fact_registry(
    bundle: ReportingBundle,
    cash_bridge_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    as_of = bundle.as_of_period
    facts: list[dict[str, Any]] = []
    ties: list[dict[str, Any]] = []

    def add(fact: dict[str, Any] | None) -> None:
        if fact is not None:
            facts.append(fact)

    for horizon, periods in (
        ("cm", [as_of]),
        ("qtd", qtd_periods(as_of)),
        ("ytd", ytd_periods(as_of)),
    ):
        add(_flow_fact(bundle, f"revenue.{horizon}", "Revenue", periods, favorable_up=True))
        add(_flow_fact(bundle, f"ebitda.{horizon}", "EBITDA", periods, needle="ebitda", favorable_up=True))
        gm = _margin_fact(bundle, f"gross_margin.{horizon}", "Gross margin", periods if horizon != "cm" else [as_of], month=horizon == "cm")
        add(gm)

    add(_point_fact("cash.ending", "Ending cash", as_of, ending_cash_at(bundle, as_of, "Actual"), ending_cash_at(bundle, as_of, "Budget"), favorable_up=True, definition="cash.ending.v1 point in time"))
    add(_point_fact("arr.ending", "Ending ARR", as_of, compute_ending_arr(bundle, as_of, "Actual"), compute_ending_arr(bundle, as_of, "Budget"), favorable_up=True, definition="arr.ending.v1 point in time"))
    add(_point_fact("arr.net_new", "Net new ARR", as_of, compute_net_new_arr(bundle, as_of, "Actual"), compute_net_new_arr(bundle, as_of, "Budget"), favorable_up=True, definition="net_new = new business + expansion + reactivation − contraction − churn"))
    add(_point_fact("arr.new_business", "New business ARR", as_of, compute_new_business_arr(bundle, as_of, "Actual"), compute_new_business_arr(bundle, as_of, "Budget"), favorable_up=True, definition="arr.new_business.v1"))
    add(_point_fact("arr.expansion", "Expansion ARR", as_of, compute_expansion_arr(bundle, as_of, "Actual"), compute_expansion_arr(bundle, as_of, "Budget"), favorable_up=True, definition="arr.expansion.v1"))
    add(_point_fact("arr.churn", "Churn ARR", as_of, compute_churn_arr(bundle, as_of, "Actual"), compute_churn_arr(bundle, as_of, "Budget"), favorable_up=False, definition="arr.churn.v1"))
    add(_point_fact("arr.contraction", "Contraction ARR", as_of, compute_contraction_arr(bundle, as_of, "Actual"), compute_contraction_arr(bundle, as_of, "Budget"), favorable_up=False, definition="arr.contraction.v1"))

    grr = _grr(bundle, as_of)
    if grr is not None:
        over = grr > 1
        facts.append({
            "id": "arr.gross_retention",
            "label": "Gross retention",
            "period": as_of,
            "unit": "ratio",
            "value": float(min(grr, Decimal("1")) if over else grr),
            "display": "n/m" if over else _pct(grr),
            "definition": "arr.gross_retention.v1 (beginning − churn − contraction) / beginning; never above 100%",
            "status": None,
            "percent_offered": not over,
        })
        ties.append({
            "id": "arr.gross_retention",
            "ok": not over,
            "detail": "Gross retention is above 100%, so the tile is n/m." if over else "Gross retention is within 100%.",
        })
    nrr = _nrr(bundle, as_of)
    if nrr is not None:
        facts.append({
            "id": "arr.net_retention",
            "label": "Net retention",
            "period": as_of,
            "unit": "ratio",
            "value": float(nrr),
            "display": _pct(nrr),
            "definition": "arr.net_retention.v1 (beginning + expansion + reactivation − contraction − churn) / beginning",
            "status": None,
            "percent_offered": True,
        })

    created = _wf(bundle, "pipeline", "pipeline_created", as_of)
    created_budget = _wf(bundle, "pipeline", "pipeline_created", as_of, "Budget")
    add(_point_fact("pipeline.created", "Pipeline created", as_of, created, created_budget, favorable_up=True, definition="pipeline.created.v1 opportunities entering pipeline in the period"))
    snap = build_metrics_snapshot(bundle)
    if snap.pipeline_from_marketing and created and abs(snap.pipeline_from_marketing - created) > MONEY_TOLERANCE:
        ties.append({
            "id": "pipeline.created",
            "ok": False,
            "detail": (
                f"Pipeline created has two sources. The deck uses the pipeline waterfall "
                f"({fmt_deck_money(created)}), not the marketing-channel sum ({fmt_deck_money(snap.pipeline_from_marketing)})."
            ),
        })

    coverage = _coverage(bundle, as_of, snap)
    if coverage is not None:
        facts.append(coverage)

    outlook_gm = _fy_outlook_gross_margin_pct(bundle)
    budget_gm = _fy_budget_gross_margin_pct(bundle)
    if outlook_gm is not None or budget_gm is not None:
        facts.append({
            "id": "gross_margin.fy",
            "label": "FY gross margin",
            "period": as_of[:4],
            "unit": "ratio",
            "value": float(outlook_gm / 100) if outlook_gm is not None else None,
            "budget": float(budget_gm / 100) if budget_gm is not None else None,
            "display": _pct(outlook_gm / 100) if outlook_gm is not None else "n/m",
            "definition": "gross_margin.v1 sum of gross profit / sum of revenue for actual closed months plus forecast open months",
            "status": _status(outlook_gm, budget_gm, favorable_up=True, money=False) if outlook_gm is not None and budget_gm is not None else None,
            "percent_offered": outlook_gm is not None,
        })

    growth = _required_growth(bundle, as_of)
    if growth is not None:
        facts.append(growth)

    ties.extend(_arr_tie(bundle, as_of))
    ties.extend(_cash_tie(bundle, as_of, cash_bridge_data))
    return {"facts": facts, "ties": ties, "by_id": {fact["id"]: fact for fact in facts}}


def fact_registry_prompt(payload: dict[str, Any]) -> str:
    facts = payload.get("facts") or []
    ties = [tie for tie in (payload.get("fact_ties") or []) if not tie.get("ok")]
    lines = [
        "FACT REGISTRY. Every number on every slide is one of these facts. Do not compute a new one.",
        "A status word must match the fact: ahead, on plan, or behind. Do not say tracking, in line, or on plan unless the status is on plan.",
        "Do not state a percent when percent_offered is false. Write n/m.",
        "Do not give a cause unless the payload has an evidence id for it. Do not invent a board ask. If board_actions is empty, the slide says no asks were entered.",
        "A failed tie is stated as a gap. It is not given a cause.",
    ]
    if ties:
        lines.append("TIE FAILURES:")
        lines.extend(f"- {tie['detail']}" for tie in ties)
    if facts:
        brief = [
            {
                "id": fact["id"],
                "display": fact.get("display"),
                "status": fact.get("status"),
                "percent_offered": fact.get("percent_offered", True),
            }
            for fact in facts
        ]
        import json
        lines.append("FACTS:")
        lines.append(json.dumps(brief, separators=(",", ":")))
    return "\n".join(lines) + "\n\n"


def _publish(payload: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> None:
    arr = payload.get("arr_analysis")
    if isinstance(arr, dict):
        retention = by_id.get("arr.gross_retention")
        if retention and not retention.get("percent_offered"):
            arr["gsr_pct"] = "n/m"
        coverage = by_id.get("pipeline.coverage")
        arr["pipeline_coverage_x"] = coverage["display"] if coverage else "n/m"
    gtm = payload.get("gtm_performance")
    created = by_id.get("pipeline.created")
    if isinstance(gtm, dict) and created and created.get("display"):
        gtm["total_pipeline"] = created["display"]
    if not payload.get("board_actions"):
        payload["board_actions_note"] = "No asks were entered for this close."


def _flow_fact(bundle: ReportingBundle, fact_id: str, label: str, periods: list[str], *, needle: str = "revenue", favorable_up: bool) -> dict[str, Any] | None:
    actual = fs_sum_periods(bundle, periods, "Actual", needle)
    budget = fs_sum_periods(bundle, periods, "Budget", needle)
    if not actual and not budget:
        return None
    return _money_fact(fact_id, label, bundle.as_of_period, actual, budget, favorable_up=favorable_up, definition=f"{fact_id}.v1 sum of the statement line")


def _margin_fact(bundle: ReportingBundle, fact_id: str, label: str, periods: list[str], *, month: bool) -> dict[str, Any] | None:
    if month:
        actual = gross_margin_pct(bundle, bundle.as_of_period, "Actual")
        budget = gross_margin_pct(bundle, bundle.as_of_period, "Budget")
    else:
        actual = gross_margin_pct_horizon(bundle, periods, "Actual")
        budget = gross_margin_pct_horizon(bundle, periods, "Budget")
    if actual is None and budget is None:
        return None
    offered = actual is not None
    return {
        "id": fact_id,
        "label": label,
        "period": bundle.as_of_period,
        "unit": "ratio",
        "value": float(actual / 100) if actual is not None else None,
        "budget": float(budget / 100) if budget is not None else None,
        "display": _pct(actual / 100) if actual is not None else "n/m",
        "definition": "gross_margin.v1 gross profit / revenue for the same period",
        "status": _status(actual, budget, favorable_up=True, money=False) if actual is not None and budget is not None else None,
        "percent_offered": offered,
    }


def _point_fact(fact_id: str, label: str, period: str, actual: Decimal | None, budget: Decimal | None, *, favorable_up: bool, definition: str) -> dict[str, Any] | None:
    if not actual and not budget:
        return None
    return _money_fact(fact_id, label, period, actual or ZERO, budget or ZERO, favorable_up=favorable_up, definition=definition)


def _money_fact(fact_id: str, label: str, period: str, actual: Decimal, budget: Decimal, *, favorable_up: bool, definition: str) -> dict[str, Any]:
    variance = actual - budget if budget else None
    percent = None
    offered = False
    if budget and variance is not None and abs(budget) >= MATERIALITY:
        percent = variance / abs(budget)
        offered = abs(percent) <= PERCENT_CAP
    return {
        "id": fact_id,
        "label": label,
        "period": period,
        "unit": "USD",
        "value": float(actual),
        "budget": float(budget) if budget else None,
        "variance": float(variance) if variance is not None else None,
        "display": fmt_deck_money(actual),
        "definition": definition,
        "status": _status(actual, budget, favorable_up=favorable_up) if budget else None,
        "percent_offered": offered,
        "variance_percent": float(percent) if offered and percent is not None else None,
    }


def _coverage(bundle: ReportingBundle, as_of: str, snap) -> dict[str, Any] | None:
    """Open pipeline divided by new-business budget still to close after this month."""
    del snap
    open_pipeline = abs(_wf(bundle, "pipeline", "ending_pipeline", as_of))
    year = int(as_of[:4])
    month = int(as_of[5:7])
    remaining = ZERO
    for future in range(month + 1, 13):
        remaining += compute_new_business_arr(bundle, f"{year}-{future:02d}", "Budget")
    if open_pipeline <= 0 or remaining <= 0:
        return None
    ratio = open_pipeline / remaining
    return {
        "id": "pipeline.coverage",
        "label": "Pipeline coverage",
        "period": as_of,
        "unit": "multiple",
        "value": float(ratio),
        "display": f"{float(ratio):.1f}x",
        "definition": "pipeline.coverage.v1 open pipeline / new-business budget after the close month",
        "status": "ahead" if ratio >= 3 else "on plan" if ratio >= 2 else "behind",
        "percent_offered": True,
    }


def _required_growth(bundle: ReportingBundle, as_of: str) -> dict[str, Any] | None:
    year = as_of[:4]
    fiscal_end = f"{year}-12"
    current = compute_ending_arr(bundle, as_of, "Actual")
    target = compute_ending_arr(bundle, fiscal_end, "Forecast")
    month = int(as_of[5:7])
    months_left = 12 - month
    if current <= 0 or target <= 0 or months_left <= 0:
        return None
    rate = (target / current) ** (Decimal(1) / Decimal(months_left)) - 1
    return {
        "id": "arr.required_monthly_growth",
        "label": "Required monthly ARR growth",
        "period": as_of,
        "unit": "ratio",
        "value": float(rate),
        "display": _pct(rate),
        "definition": "arr.required_monthly_growth.v1 (forecast ending ARR / current ending ARR) ^ (1 / months left) − 1",
        "status": None,
        "percent_offered": abs(rate) <= PERCENT_CAP,
    }


def _arr_tie(bundle: ReportingBundle, as_of: str) -> list[dict[str, Any]]:
    expected, actual = arr_bridge_identity_expected(bundle, as_of, "Actual")
    if not expected and not actual:
        return []
    gap = actual - expected
    ok = abs(gap) <= MONEY_TOLERANCE
    return [{
        "id": "arr.bridge",
        "ok": ok,
        "detail": (
            "ARR bridge ties to ending ARR."
            if ok
            else f"ARR bridge does not tie. Movements end at {fmt_deck_money(expected)}; ending ARR is {fmt_deck_money(actual)}; residual {fmt_deck_money(gap)}."
        ),
    }]


def _cash_tie(bundle: ReportingBundle, as_of: str, cash_bridge_data: dict[str, Any] | None) -> list[dict[str, Any]]:
    prior = prior_period(as_of)
    beginning = ending_cash_at(bundle, prior, "Actual")
    ending = ending_cash_at(bundle, as_of, "Actual")
    if not beginning and not ending:
        return []

    def part(field: str, wf_types: tuple[str, ...], *, outflow: bool) -> Decimal:
        table = _cash_bridge_table_amount(cash_bridge_data, "Actual", as_of, field, abs_out=outflow)
        if table is not None and table != ZERO:
            return table
        return _cash_wf_amount(bundle, as_of, "Actual", *wf_types, abs_out=outflow)

    collections = part("collections", ("cash_collections", "collections"), outflow=False)
    payroll = part("payroll", ("payroll_cash_out", "payroll"), outflow=True)
    vendor = part("vendor", ("vendor_cash_out", "vendor_payments", "vendor"), outflow=True)
    commissions = part("commission", ("commission_cash_out", "commissions", "commission"), outflow=True)
    capex = part("capex", ("capex",), outflow=True)
    if not any((collections, payroll, vendor, commissions, capex)):
        return []
    expected = beginning + collections - payroll - vendor - commissions - capex
    gap = ending - expected
    ok = abs(gap) <= MONEY_TOLERANCE
    return [{
        "id": "cash.bridge",
        "ok": ok,
        "detail": (
            "Cash bridge ties to ending cash."
            if ok
            else f"Cash bridge does not tie. The listed movements end at {fmt_deck_money(expected)}; ending cash is {fmt_deck_money(ending)}; residual {fmt_deck_money(gap)}."
        ),
    }]


def _status(actual: Decimal | None, budget: Decimal | None, *, favorable_up: bool, money: bool = True) -> str | None:
    if actual is None or budget is None or budget == ZERO:
        return None
    variance = actual - budget
    band = abs(budget) * ON_PLAN_RATIO
    floor = max(MATERIALITY, band) if money else band
    if abs(variance) <= floor:
        return "on plan"
    better = variance > 0 if favorable_up else variance < 0
    return "ahead" if better else "behind"


def _pct(ratio: Decimal | None) -> str:
    if ratio is None:
        return "n/m"
    return fmt_deck_pct(ratio, as_percent=False) if abs(ratio) > Decimal("1.5") else fmt_deck_pct(ratio)
