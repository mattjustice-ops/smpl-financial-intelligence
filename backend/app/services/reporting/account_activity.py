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
