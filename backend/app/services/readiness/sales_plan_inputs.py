"""Sales quota and comp plan (onboarding 7.25–7.29) checked against the loaded sales team, from loaded data only.

- 7.25 expected attainment vs the closers' attainment in ``actual_sales_quotas`` (closers are the rows with
  quota type Bookings ARR).
- 7.26 quota credit vs what the loaded attainment counts: closed-won new business, new + expansion, or net new
  (less contraction and churn) owned by the rep that month in ``actual_opportunities``.
- 7.27 attainment period vs the loaded payouts: a monthly plan pays the accelerated rate exactly when the rep's
  monthly attainment reached the plan threshold.
- 7.28 expansion owner vs the owners of closed-won expansion opportunities (closer in the quotas, Customer
  Success in ``actual_employees``, or an account manager role).
- 7.29 variable pay vs the plan: commission at quota (annual quota × new-business base rate) against the HRIS
  commission target of each closer role.

Nothing is filled in: a missing table or field is reported in ``missing``.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.services.readiness.commission_plan_inputs import _kind, _num, _rows
from app.services.reporting.period_utils import to_period

ZERO = Decimal("0")
SALES_PLAN_QUESTIONS = ("7.25", "7.26", "7.27", "7.28", "7.29")
ATTAINMENT_REVIEW_GAP = Decimal("0.15")
TARGET_TOLERANCE = Decimal("0.10")
CREDIT = {"new_business_arr": {"new business": 1},
          "new_and_expansion_arr": {"new business": 1, "expansion": 1},
          "net_new_arr": {"new business": 1, "expansion": 1, "contraction": -1, "churn": -1}}
WON = {"new business": "closed won", "expansion": "closed won", "contraction": "contraction", "churn": "churn"}


def _money(x: Decimal) -> str:
    return f"${x:,.0f}"


def _upto(rows: list[dict[str, Any]] | None, as_of: str) -> list[dict[str, Any]]:
    return [dict(r, period=to_period(str(r["period"]))) for r in rows or []
            if r.get("period") and to_period(str(r["period"])) <= as_of]


def sales_plan(db: Session, org_id: uuid.UUID, answers: dict[str, str], as_of: str) -> dict[str, Any]:
    missing: list[str] = []
    quotas = _upto(_rows(db, "actual_sales_quotas", org_id), as_of)
    closers = [r for r in quotas if _kind(r.get("quota_type")) == "bookings arr"]
    if not closers:
        missing.append("actual_sales_quotas has no Bookings ARR rows: closer quota and attainment can't be measured")
    opps = _upto(_rows(db, "actual_opportunities", org_id), as_of)
    if not opps:
        missing.append("actual_opportunities is not loaded: quota credit and deal owners can't be checked")
    employees = _rows(db, "actual_employees", org_id) or []
    if not employees:
        missing.append("actual_employees is not loaded: closer comp and Customer Success roles can't be checked")
    plans = {str(r.get("plan_id")): r for r in _rows(db, "actual_commission_plans", org_id) or [] if r.get("plan_id")}
    payouts = _upto(_rows(db, "actual_commission_payouts", org_id), as_of)

    checks: list[dict[str, Any]] = []

    def add(cid: str, q: str, status: str, finding: str) -> None:
        checks.append({"id": cid, "questions": q, "status": status, "finding": finding})

    months = sorted({r["period"] for r in closers})
    attained = sum((_num(r.get("quota_attainment_actual_arr")) or ZERO for r in closers), ZERO)
    ramped = sum((_num(r.get("ramped_monthly_quota_arr")) or ZERO for r in closers), ZERO)
    measured = attained / ramped if ramped else None
    a = answers.get("7.25")
    if a and measured is not None:
        gap = Decimal(a) / 100 - measured
        add("expected_attainment_vs_quotas", "7.25", "pass" if abs(gap) <= ATTAINMENT_REVIEW_GAP else "review",
            f"Hiring is planned at {a}% attainment; closers attained {measured:.0%} of ramped quota "
            f"{months[0]}–{months[-1]} ({_money(attained)} of {_money(ramped)})")

    rep_of = {str(r.get("rep_name")): str(r.get("employee_id")) for r in closers}
    credited: dict[str, dict[tuple[str, str], Decimal]] = {k: defaultdict(Decimal) for k in CREDIT}
    for o in opps:
        kind, rep = _kind(o.get("opportunity_type")), rep_of.get(str(o.get("owner")))
        if rep is None or WON.get(kind) != _kind(o.get("close_status")):
            continue
        amount = abs(_num(o.get("amount_arr")) or ZERO)
        for credit, sign in CREDIT.items():
            if kind in sign:
                credited[credit][(o["period"], rep)] += sign[kind] * amount
    fits = {credit: all(abs((_num(r.get("quota_attainment_actual_arr")) or ZERO) - c[(r["period"], str(r.get("employee_id")))]) < 1
                        for r in closers) for credit, c in credited.items()} if closers and opps else {}
    a = answers.get("7.26")
    if a and fits:
        matched = [k.replace("_", " ") for k, ok in fits.items() if ok]
        add("quota_credit_vs_attainment", "7.26", "pass" if fits.get(a) else "conflict",
            f"7.26 credits {a.replace('_', ' ')}; the loaded attainment matches "
            + (", ".join(matched) if matched else "none of new business, new + expansion or net new")
            + " owned by the rep that month")

    pct = {(r["period"], str(r.get("employee_id"))): _num(r.get("quota_attainment_pct")) for r in closers}
    tested = off = 0
    for p in payouts:
        plan = plans.get(str(p.get("plan_id")))
        base, acc, threshold = (_num(plan.get(k)) if plan else None
                                for k in ("base_commission_rate", "accelerated_rate", "accelerator_threshold"))
        rate, att = _num(p.get("commission_rate")), pct.get((p["period"], str(p.get("rep_id"))))
        if None in (base, acc, threshold, rate, att) or base == acc:
            continue
        tested += 1
        off += (rate == acc) != (att >= threshold)
    a = answers.get("7.27")
    if a and tested:
        monthly = off == 0
        status = ("pass" if monthly else "conflict") if a == "monthly" else ("conflict" if monthly else "review")
        add("attainment_period_vs_payouts", "7.27", status,
            f"{tested - off} of {tested} accelerator-plan payouts follow the rep's monthly attainment "
            f"(accelerated rate exactly when that month's attainment reached the threshold); 7.27 says {a}")

    dept_of = {str(e.get("employee_name")): str(e.get("department") or "") for e in employees}
    role_of = {str(e.get("employee_name")): _kind(e.get("role")) for e in employees}
    owners: dict[str, int] = defaultdict(int)
    for o in opps:
        if _kind(o.get("opportunity_type")) == "expansion" and _kind(o.get("close_status")) == "closed won":
            name = str(o.get("owner"))
            owners["account_executives" if name in rep_of else "customer_success" if dept_of.get(name) == "Customer Success"
                   else "account_managers" if "account manager" in role_of.get(name, "") else "other"] += 1
    exp_paid = sum(1 for p in payouts if _kind((plans.get(str(p.get("plan_id"))) or {}).get("eligible_opportunity_type")) == "expansion")
    a = answers.get("7.28")
    if a and owners:
        ok = (exp_paid == 0) if a == "not_paid" else set(owners) == {a}
        add("expansion_owner_vs_opportunities", "7.28", "pass" if ok else "conflict",
            "Closed-won expansion owners: " + ", ".join(f"{k.replace('_', ' ')} {n}" for k, n in sorted(owners.items()))
            + f"; {exp_paid} expansion payouts; 7.28 says {a.replace('_', ' ')}")

    nb_plan = next((r for r in plans.values() if _kind(r.get("eligible_opportunity_type")) == "new business"), None)
    nb_rate = _num(nb_plan.get("base_commission_rate")) if nb_plan else None
    closer_ids = {str(r.get("employee_id")) for r in closers}
    roles: dict[str, tuple[Decimal, Decimal]] = {}
    for e in employees:
        if str(e.get("employee_id")) in closer_ids or str(e.get("employee_name")) in rep_of:
            quota, target = _num(e.get("annual_quota_arr")), _num(e.get("commission_target"))
            if quota and target:
                roles.setdefault(str(e.get("role")), (quota, target))
    a = answers.get("7.29")
    if a and nb_rate is not None and roles:
        at_quota = {role: (quota * nb_rate, target) for role, (quota, target) in roles.items()}
        fits_target = all(abs(pay - target) <= TARGET_TOLERANCE * target for pay, target in at_quota.values())
        detail = "; ".join(f"{role}: {_money(pay)} at quota vs {_money(target)} commission target"
                           for role, (pay, target) in sorted(at_quota.items()))
        if a == "through_commission_plan":
            add("variable_pay_vs_commission_plan", "7.29", "pass" if fits_target else "review",
                f"New-business plan {nb_plan.get('plan_id')} at {nb_rate:.2%}: {detail}"
                + ("" if fits_target else " — the plan pays a different amount at quota than the HRIS target"))
        else:
            add("variable_pay_vs_commission_plan", "7.29", "review",
                f"Variable pay is a bonus in addition to commissions, so planned labor cost carries both; {detail}")
    elif a and not roles:
        missing.append("No closer in actual_employees has an annual quota and commission target: 7.29 can't be checked")

    return {
        "answers": {q: answers.get(q) for q in SALES_PLAN_QUESTIONS},
        "measured": {
            "months": [months[0], months[-1]] if months else None,
            "closer_attainment": float(measured) if measured is not None else None,
            "quota_credit_matches": sorted(k for k, ok in fits.items() if ok),
            "accelerator_payouts_tested": tested,
            "accelerator_payouts_off_monthly": off,
            "expansion_owners": dict(owners),
        },
        "checks": checks,
        "missing": missing,
    }
