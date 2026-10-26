"""Why a statement account moved, from the schedule that posted to it.

The schedule is chosen by the account's role, not by its number. A measure is
attached only when the schedule adds up to the account. A role with no schedule
keeps the account tie and an open why.
"""

from __future__ import annotations

import uuid
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import fetch_table_rows, table_exists
from app.services.reporting.gl_income_statement import is_implementation_revenue
from app.services.reporting.gl_rollup import labor_bucket

TIE = 1.0

_SCHEDULES: dict[str, tuple[tuple[str, str], ...]] = {
    "Actual": (
        ("actual_implementation_schedule", "implementation"),
        ("actual_recurring_services_schedule", "recurring"),
    ),
    "Budget": (
        ("budget_implementation_schedule", "implementation"),
        ("budget_recurring_services_schedule", "recurring"),
    ),
    "Forecast": (
        ("forecast_implementation_schedule", "implementation"),
        ("forecast_recurring_services_schedule", "recurring"),
    ),
}


def _num(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _period(value: Any) -> str:
    text = str(value or "")
    return text[:7]


def _expected(row: dict[str, Any]) -> float:
    raw = row.get("win_probability")
    if raw in (None, ""):
        return 1.0
    return _num(raw)


def schedule_activity(rows: list[dict[str, Any]], amount_key: str) -> dict[str, float] | None:
    """Count and average amount for one month. Fees already include any weighting."""
    total = 0.0
    expected = 0.0
    counted = 0
    for row in rows:
        amount = _num(row.get(amount_key))
        if amount == 0:
            continue
        total += amount
        weight = _expected(row) if amount_key == "implementation_fee" else 1.0
        expected += weight
        counted += 1
    if counted == 0 or expected == 0:
        return None
    count = round(expected) if abs(expected - round(expected)) < 1e-6 else round(expected, 2)
    return {"count": float(count), "total": round(total, 2), "average": round(total / expected, 2)}


def _ties(node: dict[str, Any], total: float) -> bool:
    return abs(abs(float(node.get("amount") or 0)) - abs(total)) <= TIE


def _tag(node: dict[str, Any], measures: list[dict[str, Any]], match: Callable[[dict[str, Any]], bool], total: float) -> bool:
    child_tagged = False
    for child in node.get("children") or []:
        if _tag(child, measures, match, total):
            child_tagged = True
    if child_tagged:
        return True
    if match(node) and _ties(node, total):
        node["measures"] = measures
        return True
    return False


def _is_implementation(node: dict[str, Any]) -> bool:
    return is_implementation_revenue(str(node.get("label") or ""))


def _is_recurring_services(node: dict[str, Any]) -> bool:
    label = str(node.get("label") or "").lower()
    return "recurring" in label and "service" in label and not is_implementation_revenue(label)


def attach_account_activity(
    tree: dict[str, Any],
    *,
    implementation_rows: list[dict[str, Any]] | None = None,
    recurring_rows: list[dict[str, Any]] | None = None,
) -> None:
    """Attach count and average fee where that schedule equals the account."""
    specs = (
        (implementation_rows or [], "implementation_fee", "implementations", "average implementation fee", _is_implementation),
        (recurring_rows or [], "recurring_services_revenue", "customers on recurring services", "average recurring services fee", _is_recurring_services),
    )
    for rows, amount_key, count_label, size_label, match in specs:
        activity = schedule_activity(rows, amount_key)
        if activity is None:
            continue
        measures = [
            {"label": count_label, "value": activity["count"]},
            {"label": size_label, "value": activity["average"]},
        ]
        for line in tree.get("lines") or []:
            _tag(line, measures, match, activity["total"])


def load_activity_rows(db: Session, organization_id: uuid.UUID) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Schedule rows by scenario and role. A missing table is an empty list."""
    loaded: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for scenario, tables in _SCHEDULES.items():
        by_role: dict[str, list[dict[str, Any]]] = {}
        for table, role in tables:
            by_role[role] = fetch_table_rows(db, table, organization_id) if table_exists(db, table) else []
        loaded[scenario] = by_role
    return loaded


def rows_for_period(rows: list[dict[str, Any]], period: str) -> list[dict[str, Any]]:
    return [row for row in rows if _period(row.get("period")) == period]


def _department(node_id: str) -> str:
    for part in str(node_id).split("|"):
        if part.startswith("department:"):
            name = part.split(":", 1)[1]
            if name and name != "__blank__":
                return name
    return ""


def attach_compensation_bridge(tree: dict[str, Any], departments: list[dict[str, Any]]) -> None:
    """Hires, departures, rate, and the reconciling bar, when that department's bridge equals the line.

    The bridge prices hires and departures from the roster. It excludes commissions.
    Mix and raises are not separate bars. They stay inside GL reconciling.
    """
    by_name = {
        str(row.get("department") or "").strip().casefold(): row
        for row in departments
        if row.get("ties") and str(row.get("department") or "").strip()
    }

    def walk(node: dict[str, Any]) -> None:
        for child in node.get("children") or []:
            walk(child)
        if node.get("role") != "compensation":
            return
        bridge = by_name.get(_department(str(node.get("id") or "")).casefold())
        if not bridge or not _ties(node, float(bridge.get("ending") or 0)):
            return
        facts = []
        for bar in bridge.get("bars") or []:
            fact: dict[str, Any] = {"label": bar.get("label") or "Item", "amount": bar.get("amount")}
            if bar.get("heads"):
                fact["heads"] = bar["heads"]
            facts.append(fact)
        if facts:
            node["bridge"] = {"beginning": bridge.get("beginning"), "ending": bridge.get("ending"), "facts": facts}

    for line in tree.get("lines") or []:
        walk(line)


def compensation_bridges_by_period(db: Session, organization_id: uuid.UUID, periods: list[str]) -> dict[str, list[dict[str, Any]]]:
    """Month-over-month compensation bridge for each actual period. Empty when the roster is not loaded."""
    from sqlalchemy.exc import SQLAlchemyError

    from app.services.reporting.period_utils import period_to_date
    from app.services.workforce.gl_payroll import gl_payroll
    from app.services.workforce.labor_bridge import build_labor_bridges
    from app.services.workforce.roster import load_roster

    try:
        roster, _source = load_roster(db, organization_id, "Forecast")
        if not roster:
            roster, _source = load_roster(db, organization_id, "Actual")
        if not roster:
            return {}
        payroll = gl_payroll(db, organization_id, "Actual")
    except SQLAlchemyError:
        return {}
    found: dict[str, list[dict[str, Any]]] = {}
    for period in periods:
        bridges = build_labor_bridges(
            close=period_to_date(period),
            roster=roster,
            budget_roster=[],
            actual_payroll=payroll,
            budget_payroll=None,
        )
        mom = next((bridge for bridge in bridges if bridge.get("id") == "mom" and bridge.get("available") is not False), None)
        if mom:
            found[period] = list(mom.get("departments") or [])
    return found


_PAYOUT_TABLES = ("commission_payouts", "renewal_commissions")


def load_commission_inputs(db: Session, organization_id: uuid.UUID) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Payout rows and the roster, by scenario. A missing table is an empty list."""
    loaded: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for scenario in ("Actual", "Budget", "Forecast"):
        prefix = scenario.lower()
        payouts: list[dict[str, Any]] = []
        for suffix in _PAYOUT_TABLES:
            table = f"{prefix}_{suffix}"
            if table_exists(db, table):
                payouts.extend(fetch_table_rows(db, table, organization_id))
        roster_table = f"{prefix}_employees"
        roster = fetch_table_rows(db, roster_table, organization_id) if table_exists(db, roster_table) else []
        loaded[scenario] = {"payouts": payouts, "roster": roster}
    return loaded


def _monthly_quota(row: dict[str, Any]) -> float | None:
    raw = row.get("commission_target")
    if raw in (None, ""):
        return None
    return round(_num(raw) / 12, 2)


def commission_payout_facts(
    payout_rows: list[dict[str, Any]], roster_rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]] | None, float]:
    """What we paid each person against that person's monthly commission quota.

    The quota is the roster commission target for the year, divided by twelve.
    Paid is the payout rows for the month, new business and renewals together.
    Capitalized and expensed treatment is not part of this comparison.
    Returns no facts when someone who was paid has no commission target, or a
    payout has no person.
    """
    quota_by_id: dict[str, float] = {}
    name_by_id: dict[str, str] = {}
    for row in roster_rows:
        employee_id = str(row.get("employee_id") or "").strip()
        if not employee_id:
            continue
        name_by_id[employee_id] = str(row.get("employee_name") or row.get("name") or employee_id)
        quota = _monthly_quota(row)
        if quota is not None:
            quota_by_id[employee_id] = quota

    paid_by_id: dict[str, float] = {}
    paid_name: dict[str, str] = {}
    paid_total = 0.0
    for row in payout_rows:
        amount = round(_num(row.get("commission_amount")), 2)
        if amount == 0:
            continue
        rep_id = str(row.get("rep_id") or row.get("employee_id") or "").strip()
        if not rep_id:
            return None, 0.0
        paid_total = round(paid_total + amount, 2)
        paid_by_id[rep_id] = round(paid_by_id.get(rep_id, 0.0) + amount, 2)
        paid_name[rep_id] = str(row.get("rep_name") or name_by_id.get(rep_id) or rep_id)

    if not paid_by_id or any(rep_id not in quota_by_id for rep_id in paid_by_id):
        return None, paid_total

    people = [
        {
            "label": paid_name[rep_id],
            "paid": paid_by_id[rep_id],
            "quota": quota_by_id[rep_id],
        }
        for rep_id in sorted(paid_by_id, key=lambda rep_id: paid_name[rep_id].casefold())
    ]
    quota_total = round(sum(person["quota"] for person in people), 2)
    facts = [{"label": "Payouts", "paid": paid_total, "quota": quota_total}, *people]
    return facts, paid_total


def _is_commission(node: dict[str, Any]) -> bool:
    bucket = labor_bucket(str(node.get("label") or ""))
    return bucket is not None and bucket[0] == "commission"


def attach_commission_payouts(
    tree: dict[str, Any],
    payout_rows: list[dict[str, Any]] | None = None,
    roster_rows: list[dict[str, Any]] | None = None,
) -> None:
    """Attach paid versus quota where those payouts are the amount on the commission line."""
    facts, paid_total = commission_payout_facts(payout_rows or [], roster_rows or [])
    if not facts:
        return

    def walk(node: dict[str, Any]) -> bool:
        child_tagged = False
        for child in node.get("children") or []:
            if walk(child):
                child_tagged = True
        if child_tagged:
            return True
        if _is_commission(node) and _ties(node, paid_total):
            node["payouts"] = facts
            return True
        return False

    for line in tree.get("lines") or []:
        walk(line)
