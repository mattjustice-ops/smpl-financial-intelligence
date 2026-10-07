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

    plans = _plans(db, org.id, missing)
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
        "checks": checks,
        "missing": missing,
    }
