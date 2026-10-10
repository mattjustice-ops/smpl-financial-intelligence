"""Commission inputs for the planning engines (ASC 340-40), read from loaded data only.

- Policy: onboarding answers 7.14–7.20, read-only, with the Commission Policy Gate status and the
  readiness checks of those answers against the books.
- Plans: each plan's opportunity type, capitalize flag and amortization months from the versioned
  ``*_commission_plans`` tables.
- Rates: trailing 12 months of the commission schedule, payouts ÷ commission base, by opportunity type.
- Opening layer: the capitalized cohorts in the commission schedule through ``as_of`` (Actual through
  its last loaded month, then Forecast), amortized straight-line from the payout month with cumulative
  amortization rounded to the cent — the convention of the deferred commissions roll-forward. The
  schedule balance is checked against the loaded roll-forward at ``as_of``.
- Returns (7.21–7.24): how winbacks, restarts and expansion after a contraction are paid, the share of
  returned / expansion ARR above the customer's prior level measured from the customer ARR history
  (``actual_customer_arr_history``; CRM opportunities when it isn't loaded), and what the loaded payouts
  did with Reactivation opportunities.
- Clawbacks (7.41–7.42): the clawback window and amount recovered, checked against each plan's
  ``clawback_window_months`` and the loaded ``actual_commission_clawbacks`` rows.
- Sales plan (7.25–7.29): expected attainment, quota credit, attainment period, expansion owner and variable
  pay, checked against the loaded quotas, opportunities, payouts and employees (``sales_plan_inputs.py``).
- Sales team at ``as_of`` (the forecast year end the budget opens from): heads by territory and role,
  quotas, ramp curves, commission targets and attainment (``sales_team_inputs.py``).

Nothing is filled in: a missing table or field is reported in ``missing``.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.services.reporting.period_utils import period_range, to_period

CENT = Decimal("0.01")
ZERO = Decimal("0")
COMMISSION_QUESTIONS = ("7.14", "7.15", "7.16", "7.17", "7.18", "7.19", "7.20")
RETURN_QUESTIONS = ("7.21", "7.22", "7.23", "7.24")
CLAWBACK_QUESTIONS = ("7.41", "7.42")
AMOUNT_LABEL = {"full": "full", "prorated": "prorated over the clawback window",
                "prorated_term": "prorated over the contract term"}
CLAWED_BACK, WRITTEN_DOWN = "clawed back", "written down"
OPPORTUNITY_TYPES = {
    "new business": "new_business", "new_business": "new_business", "new": "new_business",
    "expansion": "expansion", "upsell": "expansion",
    "renewal": "renewal",
}


def _num(value: Any) -> Decimal | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return Decimal(str(value).strip())
    except InvalidOperation:
        return None


def _months(value: Any) -> int | None:
    n = _num(value)
    return int(n) if n is not None and n == n.to_integral_value() else None


def _flag(value: Any) -> bool | None:
    s = str(value or "").strip().lower()
    return True if s in ("y", "yes", "true", "1") else False if s in ("n", "no", "false", "0") else None


def _padd(period: str, n: int) -> str:
    i = int(period[:4]) * 12 + int(period[5:7]) - 1 + n
    return f"{i // 12:04d}-{i % 12 + 1:02d}"


def _age(through: str, paid: str) -> int:
    return (int(through[:4]) - int(paid[:4])) * 12 + int(through[5:7]) - int(paid[5:7]) + 1


def cumulative_amortization(cohorts: dict[str, list[tuple[Decimal, int]]], through: str) -> Decimal:
    """Straight-line from the payout month (that month carries 1/n), rounded to the cent on the total."""
    total = ZERO
    for paid, layers in cohorts.items():
        age = _age(through, paid)
        if age <= 0:
            continue
        for amount, n in layers:
            total += amount * min(age, n) / n
    return total.quantize(CENT)


def opening_layer(cohorts: dict[str, list[tuple[Decimal, int]]], as_of: str) -> dict[str, Any]:
    """Balance, current portion and month-by-month runoff after ``as_of`` of cohorts paid through ``as_of``."""
    paid = {p: layers for p, layers in cohorts.items() if p <= as_of}
    if not paid:
        return {"balance": 0.0, "current_portion": 0.0, "noncurrent_portion": 0.0, "runoff": []}
    capitalized = sum((a for layers in paid.values() for a, _ in layers), ZERO).quantize(CENT)
    at = cumulative_amortization(paid, as_of)
    balance = capitalized - at
    horizon = max(n - _age(as_of, p) for p, layers in paid.items() for _, n in layers)
    runoff = []
    prev = at
    for k in range(1, max(horizon, 0) + 1):
        period = _padd(as_of, k)
        cum = cumulative_amortization(paid, period)
        runoff.append({"period": period, "amortization": float(cum - prev)})
        prev = cum
    current = cumulative_amortization(paid, _padd(as_of, 12)) - at
    return {
        "balance": float(balance),
        "current_portion": float(current),
        "noncurrent_portion": float(balance - current),
        "runoff": runoff,
    }


def _rows(db: Session, table: str, org_id: uuid.UUID) -> list[dict[str, Any]] | None:
    from app.services.dashboard.query_utils import fetch_table_rows, table_exists

    if not table_exists(db, table):
        return None
    return fetch_table_rows(db, table, org_id)


def _plans(db: Session, org_id: uuid.UUID, missing: list[str]) -> dict[str, dict[str, Any]]:
    for table in ("forecast_commission_plans", "actual_commission_plans"):
        rows = _rows(db, table, org_id)
        if not rows:
            continue
        plans = {}
        for r in rows:
            plan_id = str(r.get("plan_id") or "").strip()
            if not plan_id:
                continue
            raw_type = str(r.get("eligible_opportunity_type") or "").strip().lower()
            plans[plan_id] = {
                "plan_id": plan_id,
                "role": r.get("role"),
                "opportunity_type": OPPORTUNITY_TYPES.get(raw_type),
                "capitalize": _flag(r.get("capitalize")),
                "amortization_months": _months(r.get("amortization_months")),
                "payout_lag_months": _months(r.get("payout_lag_months")),
                "capitalize_payroll_taxes": _flag(r.get("capitalize_payroll_taxes")),
                "clawback_window_months": _months(r.get("clawback_window_months")),
                "source_table": table,
            }
            if plans[plan_id]["opportunity_type"] is None:
                missing.append(f"{table}: plan {plan_id} has no recognized eligible_opportunity_type ({raw_type or 'blank'})")
        return plans
    missing.append("No forecast_commission_plans or actual_commission_plans rows")
    return {}


def _schedule_chain(db: Session, org_id: uuid.UUID, as_of: str, missing: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    """Actual schedule rows through its last loaded month (and ``as_of``), then Forecast rows after it."""
    actual = _rows(db, "actual_commission_schedule", org_id)
    if not actual:
        missing.append("actual_commission_schedule is not loaded")
        return [], []
    tables = ["actual_commission_schedule"]
    chain = [dict(r, period=to_period(str(r["period"]))) for r in actual if r.get("period")]
    last_actual = max(r["period"] for r in chain)
    chain = [r for r in chain if r["period"] <= as_of]
    if as_of > last_actual:
        forecast = _rows(db, "forecast_commission_schedule", org_id)
        rows = [dict(r, period=to_period(str(r["period"]))) for r in (forecast or []) if r.get("period")]
        rows = [r for r in rows if last_actual < r["period"] <= as_of]
        covered = {r["period"] for r in rows}
        gap = [p for p in period_range(_padd(last_actual, 1), as_of) if p not in covered]
        if gap:
            missing.append(f"forecast_commission_schedule has no rows for {gap[0]}–{gap[-1]}")
        if rows:
            tables.append("forecast_commission_schedule")
        chain += rows
    return chain, tables


def _rollforward_row(db: Session, org_id: uuid.UUID, as_of: str, tables: list[str]) -> tuple[str, dict[str, Any]] | None:
    table = tables[-1].replace("_commission_schedule", "_deferred_commissions_rollforward")
    for r in _rows(db, table, org_id) or []:
        if r.get("period") and to_period(str(r["period"])) == as_of:
            return table, r
    return None


def _kind(value: Any) -> str:
    return str(value or "").strip().lower()


def customer_return_history(opportunities: list[dict[str, Any]]) -> dict[str, Any]:
    """From CRM opportunity rows: how much returned ARR was above the ARR the customer left with
    (their last Churn row), and how much expansion ARR was above the level before their
    contractions (Contraction rows, or a return below the ARR left with, not yet recovered by later
    expansion).
    """
    order = {"churn": 0, "contraction": 0}
    by_customer: dict[str, list[tuple[str, int, str, Decimal, bool]]] = defaultdict(list)
    for o in opportunities:
        if not o.get("period") or not o.get("customer_id"):
            continue
        kind = _kind(o.get("opportunity_type"))
        won = _kind(o.get("close_status")) == "closed won"
        by_customer[str(o["customer_id"])].append(
            (to_period(str(o["period"])), order.get(kind, 1), kind, _num(o.get("amount_arr")) or ZERO, won))

    returned = with_departure = above_baseline = expansion = expansion_above = ZERO
    returns = returns_with_departure = 0
    for events in by_customer.values():
        left_with: Decimal | None = None
        unrecovered = ZERO
        for _, _, kind, amount, won in sorted(events):
            if kind == "churn":
                left_with, unrecovered = amount, ZERO
            elif kind == "contraction":
                unrecovered += amount
            elif kind == "reactivation" and won:
                returns += 1
                returned += amount
                if left_with is not None:
                    returns_with_departure += 1
                    with_departure += amount
                    above_baseline += max(ZERO, amount - left_with)
                    unrecovered, left_with = max(ZERO, left_with - amount), None
            elif kind == "expansion" and won:
                recovered = min(amount, unrecovered)
                unrecovered -= recovered
                expansion += amount
                expansion_above += amount - recovered
    periods = sorted(to_period(str(o["period"])) for o in opportunities if o.get("period"))
    return {
        "source": "opportunities",
        "from": periods[0] if periods else None,
        "to": periods[-1] if periods else None,
        "reactivation": {
            "count": returns,
            "arr": float(returned),
            "with_departure": returns_with_departure,
            "arr_with_departure": float(with_departure),
            "above_baseline_arr": float(above_baseline),
            "above_baseline_share": float(above_baseline / with_departure) if with_departure else None,
        },
        "expansion": {
            "arr": float(expansion),
            "above_prior_level_arr": float(expansion_above),
            "above_prior_level_share": float(expansion_above / expansion) if expansion else None,
        },
    }


HISTORY_ORDER = {"opening balance": 0, "churn": 1, "pause": 1, "contraction": 2, "reactivation": 3,
                 "new business": 3, "expansion": 4}


def customer_arr_history_returns(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """From the customer ARR history (one row per customer movement): the same measures as
    ``customer_return_history``, with every departure on record. A Churn or Pause row is the ARR the
    customer left with; a Reactivation after a Churn is a winback, after a Pause a restart. A return
    below the ARR left with leaves the shortfall for later expansion to recover, like a contraction.
    New Business after a departure (back past the winback window) starts the customer over.
    Each return's commissionable ARR is in ``bases`` by opportunity ID.
    """
    by_customer: dict[str, list[tuple[str, int, str, Decimal, Decimal, str]]] = defaultdict(list)
    for r in rows:
        kind = _kind(r.get("movement_type"))
        if not r.get("period") or not r.get("customer_id") or kind not in HISTORY_ORDER:
            continue
        by_customer[str(r["customer_id"])].append(
            (to_period(str(r["period"])), HISTORY_ORDER[kind], kind, abs(_num(r.get("movement_arr")) or ZERO),
             _num(r.get("beginning_arr")) or ZERO, str(r.get("opportunity_id") or "")))

    returned = with_departure = above_baseline = expansion = expansion_above = ZERO
    returns = returns_with_departure = back_as_new = 0
    split = {"churn": [0, ZERO], "pause": [0, ZERO]}
    bases: dict[str, float] = {}
    for events in by_customer.values():
        left_with: Decimal | None = None
        departed = ""
        unrecovered = ZERO
        for _, _, kind, amount, beginning, opp in sorted(events):
            if kind in ("churn", "pause"):
                left_with, departed, unrecovered = beginning, kind, ZERO
            elif kind == "contraction":
                unrecovered += amount
            elif kind == "reactivation":
                returns += 1
                returned += amount
                if left_with is not None:
                    returns_with_departure += 1
                    with_departure += amount
                    split[departed][0] += 1
                    split[departed][1] += amount
                    base = max(ZERO, amount - left_with)
                    above_baseline += base
                    if opp:
                        bases[opp] = float(base)
                    unrecovered, left_with = max(ZERO, left_with - amount), None
            elif kind == "expansion":
                recovered = min(amount, unrecovered)
                unrecovered -= recovered
                expansion += amount
                expansion_above += amount - recovered
                if opp:
                    bases[opp] = float(amount - recovered)
            elif kind == "new business":
                back_as_new += left_with is not None
                left_with, unrecovered = None, ZERO
    periods = sorted(e[0] for events in by_customer.values() for e in events)
    return {
        "source": "customer_arr_history",
        "from": periods[0] if periods else None,
        "to": periods[-1] if periods else None,
        "reactivation": {
            "count": returns,
            "arr": float(returned),
            "with_departure": returns_with_departure,
            "arr_with_departure": float(with_departure),
            "above_baseline_arr": float(above_baseline),
            "above_baseline_share": float(above_baseline / with_departure) if with_departure else None,
            "winbacks": {"count": split["churn"][0], "arr": float(split["churn"][1])},
            "restarts": {"count": split["pause"][0], "arr": float(split["pause"][1])},
            "back_as_new_business": back_as_new,
        },
        "expansion": {
            "arr": float(expansion),
            "above_prior_level_arr": float(expansion_above),
            "above_prior_level_share": float(expansion_above / expansion) if expansion else None,
        },
        "bases": bases,
    }


def _returns(db: Session, org_id: uuid.UUID, answers: dict[str, str], plans: dict[str, dict[str, Any]],
             as_of: str, missing: list[str]) -> dict[str, Any]:
    """Commission policy for customer returns and expansion after contraction (7.21–7.24), the history
    that measures it, what the loaded payouts did, and checks of the answers against those payouts."""
    opps = [o for o in (_rows(db, "actual_opportunities", org_id) or [])
            if o.get("period") and to_period(str(o["period"])) <= as_of]
    arr_history = [r for r in (_rows(db, "actual_customer_arr_history", org_id) or [])
                   if r.get("period") and to_period(str(r["period"])) <= as_of]
    if arr_history:
        history = customer_arr_history_returns(arr_history)
    else:
        if not opps:
            missing.append("Neither actual_customer_arr_history nor actual_opportunities is loaded: returns and "
                           "expansion after contraction can't be measured")
        history = customer_return_history(opps)
    bases = history.pop("bases", {})

    opp_by_id = {str(o.get("opportunity_id")): o for o in opps}
    paid = {"count": 0, "booked_arr": ZERO, "opportunity_arr": ZERO, "base_arr": ZERO, "commission": ZERO,
            "plan_types": set(), "off_policy": 0, "unmatched": 0}
    for p in _rows(db, "actual_commission_payouts", org_id) or []:
        o = opp_by_id.get(str(p.get("opportunity_id")))
        if not o or _kind(o.get("opportunity_type")) != "reactivation":
            continue
        booked = _num(p.get("booked_arr")) or ZERO
        base = _num(p.get("commission_base_arr"))
        base = booked if base is None else base
        paid["count"] += 1
        paid["booked_arr"] += booked
        paid["base_arr"] += base
        paid["opportunity_arr"] += _num(o.get("amount_arr")) or ZERO
        paid["commission"] += _num(p.get("commission_amount")) or ZERO
        plan = plans.get(str(p.get("plan_id") or ""))
        paid["plan_types"].add(plan["opportunity_type"] if plan else None)
        policy_base = bases.get(str(p.get("opportunity_id")))
        if policy_base is None:
            paid["unmatched"] += 1
        elif abs(Decimal(str(policy_base)) - base) >= 1:
            paid["off_policy"] += 1
    rate_types = sorted(t for t in paid["plan_types"] if t)
    practice = {
        "payouts": paid["count"],
        "booked_arr": float(paid["booked_arr"]),
        "commission_base_arr": float(paid["base_arr"]),
        "commission": float(paid["commission"]),
        "paid_on_full_amount": paid["count"] > 0 and abs(paid["base_arr"] - paid["opportunity_arr"]) < 1,
        "paid_above_prior_arr": (paid["count"] > 0 and not paid["off_policy"] and not paid["unmatched"])
        if history["source"] == "customer_arr_history" else None,
        "rate_type": rate_types[0] if len(rate_types) == 1 else None,
    }

    checks: list[dict[str, Any]] = []
    n, amount = practice["payouts"], f"${practice['commission']:,.0f}"
    for q, label in (("7.21", "winbacks"), ("7.22", "restarts")):
        a = answers.get(q)
        if a == "not_paid" and n:
            checks.append({"id": f"{label}_not_paid_vs_payouts", "questions": q, "status": "conflict",
                           "finding": f"{q} says {label} are not paid, but the loaded payouts include {n} commissions "
                                      f"({amount}) on Reactivation opportunities"})
        elif a == "above_prior_arr" and practice["paid_on_full_amount"]:
            checks.append({"id": f"{label}_above_prior_arr_vs_payouts", "questions": q, "status": "conflict",
                           "finding": f"{q} pays {label} only above the customer's prior ARR, but the {n} loaded "
                                      f"Reactivation payouts ({amount}) were paid on the full returned ARR"})
        elif a == "above_prior_arr" and practice["paid_above_prior_arr"] is False and n:
            checks.append({"id": f"{label}_above_prior_arr_vs_payouts", "questions": q, "status": "conflict",
                           "finding": f"{q} pays {label} only above the customer's prior ARR, but "
                                      f"{paid['off_policy'] + paid['unmatched']} of the {n} loaded Reactivation payouts "
                                      f"have a commission base that isn't the ARR above the customer's prior level in "
                                      f"the customer ARR history"})
        elif a == "full_amount" and n and not practice["paid_on_full_amount"]:
            checks.append({"id": f"{label}_full_amount_vs_payouts", "questions": q, "status": "conflict",
                           "finding": f"{q} pays {label} on the full returned ARR, but the {n} loaded Reactivation "
                                      f"payouts ({amount}) were paid on ${practice['commission_base_arr']:,.0f} of "
                                      f"${float(paid['opportunity_arr']):,.0f} returned ARR"})
    rate_answer = answers.get("7.23")
    if rate_answer and practice["rate_type"] and rate_answer != f"{practice['rate_type']}_rate":
        checks.append({"id": "return_rate_vs_payouts", "questions": "7.23", "status": "conflict",
                       "finding": f"7.23 says {rate_answer.replace('_', ' ')}, but the loaded Reactivation payouts "
                                  f"were paid under {practice['rate_type'].replace('_', ' ')} plans"})
    return {
        "answers": {q: answers.get(q) for q in RETURN_QUESTIONS},
        "history": history,
        "loaded_practice": practice,
        "checks": checks,
    }


def clawback_policy(answers: dict[str, str], plans: dict[str, dict[str, Any]],
                    clawbacks: list[dict[str, Any]] | None, missing: list[str],
                    opportunity_terms: dict[str, int] | None = None) -> dict[str, Any]:
    """Clawback policy (7.41 window, 7.42 amount) against each new-business and expansion plan's
    ``clawback_window_months`` and the loaded ``actual_commission_clawbacks`` rows.

    A row is clawed back inside the window (months paid before the customer stopped < window) and written
    down otherwise. Full recovers the commission paid; prorated recovers paid × (window − months paid) / window;
    prorated over the term recovers paid × (term − months paid) / term. The term is the row's
    ``contract_term_months``, else its opportunity's (``opportunity_terms`` by opportunity ID); a row with
    neither is reported in ``missing`` and not checked.
    """
    window_answer, amount_answer = answers.get("7.41"), answers.get("7.42")
    window = 0 if window_answer == "none" else int(window_answer) if window_answer else None
    plan_windows = {p["plan_id"]: p["clawback_window_months"] for p in plans.values()
                    if p["opportunity_type"] in ("new_business", "expansion")}
    rows = clawbacks or []
    clawed = [r for r in rows if _kind(r.get("treatment")) == CLAWED_BACK]
    written = [r for r in rows if _kind(r.get("treatment")) == WRITTEN_DOWN]
    practice = {
        "clawed_back": len(clawed),
        "clawed_back_amount": float(sum((_num(r.get("clawback_amount")) or ZERO for r in clawed), ZERO)),
        "written_down": len(written),
        "written_down_amount": float(sum((_num(r.get("unamortized_removed")) or ZERO for r in written), ZERO)),
    }
    checks: list[dict[str, Any]] = []

    def add(cid: str, questions: str, ok: bool, finding: str) -> None:
        checks.append({"id": cid, "questions": questions, "status": "pass" if ok else "conflict", "finding": finding})

    if window is not None:
        for plan_id, months in sorted(plan_windows.items()):
            if months is None:
                missing.append(f"Commission plan {plan_id} has no clawback_window_months")
        known = {p: m for p, m in plan_windows.items() if m is not None}
        if known:
            off = sorted(f"{p} ({m})" for p, m in known.items() if m != window)
            add("clawback_window_vs_plans", "7.41", not off,
                f"7.41 clawback window {window_answer}; " + (
                    f"plans with a different clawback_window_months: {', '.join(off)}" if off
                    else f"every new-business and expansion plan has {window} months"))
        if clawbacks is None:
            missing.append("actual_commission_clawbacks is not loaded: clawbacks can't be checked against 7.41")
        elif rows:
            wrong = []
            for r in rows:
                paid = _months(r.get("months_paid_before_stop"))
                if paid is None:
                    missing.append(f"actual_commission_clawbacks {r.get('customer_id')}: months_paid_before_stop "
                                   f"is blank")
                    continue
                inside = paid < window
                if (_kind(r.get("treatment")) == CLAWED_BACK) != inside:
                    wrong.append(f"{r.get('customer_id')} {r.get('treatment')} after {paid} months paid")
            policy = "with no clawback" if window == 0 else f"under a {window}-month window"
            add("clawbacks_follow_window", "7.41", not wrong,
                f"{len(clawed)} clawed back and {len(written)} written down {policy}"
                + (f"; outside the policy: {', '.join(wrong)}" if wrong else ""))

    if amount_answer and window and clawed:
        wrong, checked = [], 0
        label = AMOUNT_LABEL.get(amount_answer, amount_answer)
        for r in clawed:
            paid_amount, recovered = _num(r.get("commission_paid")), _num(r.get("clawback_amount"))
            months_paid = _months(r.get("months_paid_before_stop"))
            if paid_amount is None or recovered is None or months_paid is None:
                continue
            if amount_answer == "prorated_term":
                term = _months(r.get("contract_term_months")) or (opportunity_terms or {}).get(
                    str(r.get("opportunity_id") or ""))
                if not term:
                    missing.append(f"actual_commission_clawbacks {r.get('customer_id')}: no contract term on the row "
                                   f"(contract_term_months) or its opportunity, so the 7.42 amount can't be checked")
                    continue
                expected = paid_amount * max(0, term - months_paid) / term
            elif amount_answer == "prorated":
                expected = paid_amount * (window - months_paid) / window
            else:
                expected = paid_amount
            checked += 1
            if abs(recovered - expected.quantize(CENT)) >= 1:
                wrong.append(f"{r.get('customer_id')} recovered {float(recovered):,.2f} of {float(paid_amount):,.2f} "
                             f"paid ({label}: {float(expected):,.2f})")
        if checked:
            add("clawback_amount_vs_policy", "7.42", not wrong,
                f"7.42 says {label}; " + (f"recovered differently: {', '.join(wrong)}" if wrong
                                          else f"{checked} clawbacks recovered {label}"))
    return {
        "answers": {q: answers.get(q) for q in CLAWBACK_QUESTIONS},
        "plan_windows": plan_windows,
        "loaded_practice": practice,
        "checks": checks,
    }


def build_plan_inputs(db: Session, org: Organization, as_of: str) -> dict[str, Any]:
    from app.services.readiness.engine import _normalization_status, commission_policy_checks, normalize_answers
    from app.services.readiness.evidence import build_commission_facts
    from app.services.readiness.service import get_answers

    as_of = to_period(as_of)
    missing: list[str] = []
    row = get_answers(db, org)
    answers = normalize_answers(dict(row.answers) if row else {})
    commission_answers = {q: answers.get(q) for q in COMMISSION_QUESTIONS}
    gate = _normalization_status(answers)["commission_policy"]
    facts = build_commission_facts(db, org)
    policy = {
        "answers": commission_answers,
        "answered": any(v is not None for v in commission_answers.values()),
        "gate_resolved": gate["resolved"],
        "unresolved_questions": gate["unresolved_questions"],
        "checks": commission_policy_checks(answers, facts),
        "checks_as_of": facts.get("as_of"),
    }

    from app.services.readiness.sales_plan_inputs import sales_plan
    from app.services.readiness.sales_team_inputs import sales_team

    plans = _plans(db, org.id, missing)
    returns = _returns(db, org.id, answers, plans, as_of, missing)
    clawback_rows = _rows(db, "actual_commission_clawbacks", org.id)
    if clawback_rows is not None:
        clawback_rows = [r for r in clawback_rows if r.get("period") and to_period(str(r["period"])) <= as_of]
    terms = None
    if answers.get("7.42") == "prorated_term":
        terms = {str(o["opportunity_id"]): t for o in _rows(db, "actual_opportunities", org.id) or []
                 if o.get("opportunity_id") and (t := _months(o.get("contract_term_months")))}
    clawbacks = clawback_policy(answers, plans, clawback_rows, missing, terms)
    sales = sales_plan(db, org.id, answers, as_of)
    team = sales_team(db, org.id, answers, as_of, sales["measured"])
    chain, tables = _schedule_chain(db, org.id, as_of, missing)

    cohorts: dict[str, list[tuple[Decimal, int]]] = defaultdict(list)
    for r in chain:
        amount = _num(r.get("capitalized_amount"))
        if not amount:
            continue
        n = _months(r.get("amortization_months"))
        if not n or n <= 0:
            missing.append(f"{r['period']} {r.get('plan_id')}: capitalized {amount} with no amortization months")
            continue
        cohorts[r["period"]].append((amount, n))
    opening = opening_layer(cohorts, as_of)
    opening.update({
        "as_of": as_of,
        "source_tables": tables,
        "cohort_months": len(cohorts),
        "first_cohort": min(cohorts) if cohorts else None,
        "amortization_months": sorted({n for layers in cohorts.values() for _, n in layers}),
    })

    trailing = period_range(_padd(as_of, -11), as_of)
    by_type: dict[str, dict[str, Any]] = {}
    unplanned: set[str] = set()
    for r in chain:
        if r["period"] not in trailing:
            continue
        plan = plans.get(str(r.get("plan_id") or ""))
        kind = plan and plan["opportunity_type"]
        if not kind:
            unplanned.add(str(r.get("plan_id")))
            continue
        t = by_type.setdefault(kind, {"base": ZERO, "payout": ZERO, "plans": set(), "by_period": defaultdict(Decimal)})
        base, payout = _num(r.get("commission_base_arr")) or ZERO, _num(r.get("commission_payout")) or ZERO
        t["base"] += base
        t["payout"] += payout
        t["plans"].add(plan["plan_id"])
        t["by_period"][r["period"]] += base
    for plan_id in sorted(unplanned):
        missing.append(f"Schedule plan {plan_id} is not in the commission plans; its payouts are not in any rate")
    rates = {
        kind: {
            "rate": float(t["payout"] / t["base"]) if t["base"] else None,
            "base": float(t["base"]),
            "payout": float(t["payout"]),
            "plans": sorted(t["plans"]),
            "base_by_period": {p: float(v) for p, v in sorted(t["by_period"].items())},
        }
        for kind, t in by_type.items()
    }

    checks: list[dict[str, Any]] = []
    rf = _rollforward_row(db, org.id, as_of, tables) if tables else None
    payroll_tax_rate = None
    if rf:
        table, r = rf
        for field, key in (("ending_deferred_commissions", "balance"), ("current_portion", "current_portion")):
            loaded = _num(r.get(field))
            if loaded is None:
                missing.append(f"{table} {as_of}: {field} is blank")
                continue
            diff = Decimal(str(opening[key])) - loaded
            checks.append({
                "id": f"schedule_{key}_vs_rollforward",
                "status": "pass" if abs(diff) < CENT else "conflict",
                "finding": f"Commission schedule {key.replace('_', ' ')} at {as_of} {opening[key]:,.2f} vs "
                           f"{table} {field} {float(loaded):,.2f}; difference {float(diff):,.2f}",
            })
    elif tables:
        missing.append(f"No deferred commissions roll-forward row at {as_of} to check the schedule against")
    rf_tables = [t.replace("_commission_schedule", "_deferred_commissions_rollforward") for t in tables]
    tax, paid = ZERO, ZERO
    for table in rf_tables:
        for r in _rows(db, table, org.id) or []:
            if r.get("period") and to_period(str(r["period"])) in trailing:
                t, p = _num(r.get("payroll_tax_on_commissions")), _num(r.get("total_commission_payouts"))
                if t is not None and p:
                    tax, paid = tax + t, paid + p
    if paid:
        payroll_tax_rate = float(tax / paid)

    return {
        "organization_id": str(org.id),
        "as_of": as_of,
        "policy": policy,
        "plans": list(plans.values()),
        "trailing": {"start": trailing[0], "end": trailing[-1]},
        "rates": rates,
        "payroll_tax_rate": payroll_tax_rate,
        "opening": opening,
        "returns": returns,
        "clawbacks": clawbacks,
        "sales_plan": sales,
        "sales_team": team,
        "checks": checks,
        "missing": missing,
    }
