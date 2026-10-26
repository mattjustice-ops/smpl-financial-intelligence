"""Usage meter the Board shows for hosting, product services, and development cloud.

Rows come from the warehouse tables the loader filled (``actual_vendor_usage`` and the Budget and
Forecast twins). The demo company fits a unit cost to its general ledger. A customer's own usage
spend is whatever they entered, or a method they gave us for that supplier.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import decimal_value, fetch_table_rows, table_exists
from app.services.reporting.period_utils import to_period

USAGE_TABLES: tuple[tuple[str, str], ...] = (
    ("Actual", "actual_vendor_usage"),
    ("Budget", "budget_vendor_usage"),
    ("Forecast", "forecast_vendor_usage"),
)

ACCOUNT_NAMES: dict[str, str] = {
    "5000": "Hosting",
    "5030": "Third-party product services",
    "6410": "Development cloud",
}

NOTE = (
    "Demo meter. Each bill is units of ending ARR, active customers, or engineers times a unit cost "
    "fitted so the bills match the general ledger. A customer's usage spend is the monthly amounts "
    "they enter, or a method they give us for that supplier."
)


def _period(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        return to_period(value)
    except (TypeError, ValueError):
        text = str(value)
        return text[:7] if len(text) >= 7 and text[4] == "-" else None


def _num(value: Any) -> float:
    return float(decimal_value(value))


def vendor_usage_from_rows(rows_by_scenario: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """``{note, accounts, scenarios: {scenario: {period: [vendor rows]}}}``."""
    scenarios: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for scenario, rows in rows_by_scenario.items():
        by_period: dict[str, list[dict[str, Any]]] = {}
        for raw in rows:
            period = _period(raw.get("period"))
            if not period:
                continue
            by_period.setdefault(period, []).append({
                "vendor": str(raw.get("vendor_name") or ""),
                "account": str(raw.get("account_number") or ""),
                "service": str(raw.get("service") or ""),
                "driver": str(raw.get("driver") or ""),
                "units": _num(raw.get("units")),
                "unit_cost": _num(raw.get("unit_cost")),
                "amount": _num(raw.get("amount")),
                "billing": str(raw.get("billing") or ""),
                "unit_cost_basis": str(raw.get("unit_cost_basis") or ""),
            })
        scenarios[scenario] = {
            period: sorted(items, key=lambda row: (row["account"], row["vendor"]))
            for period, items in by_period.items()
        }
    return {"note": NOTE, "accounts": dict(ACCOUNT_NAMES), "scenarios": scenarios}


def _entered(row: dict[str, Any]) -> bool:
    """A meter solved from the source ledger is not an explanation of that ledger."""
    basis = str(row.get("unit_cost_basis") or "").strip()
    return bool(basis) and "source GL" not in basis


def _measure_label(row: dict[str, Any]) -> str:
    driver = str(row.get("driver") or "").strip()
    service = str(row.get("service") or "").strip()
    if service and driver:
        return f"{service} — {driver}"
    return driver or service


def measures_by_account(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Units and unit cost the customer entered, keyed by account number.

    A repeated label in the same month is dropped. Two different measures must
    not be added together and presented as one.
    """
    grouped: dict[str, dict[str, float]] = {}
    repeated: dict[str, set[str]] = {}
    for row in rows:
        if not _entered(row):
            continue
        account = str(row.get("account") or row.get("account_number") or "").strip()
        label = _measure_label(row)
        if not account or not label:
            continue
        slot = grouped.setdefault(account, {})
        seen = repeated.setdefault(account, set())
        pairs = ((label, row.get("units")), (f"{label} unit cost", row.get("unit_cost")))
        for name, value in pairs:
            if value in (None, ""):
                continue
            if name in slot or name in seen:
                slot.pop(name, None)
                seen.add(name)
                continue
            slot[name] = float(value)
    return {
        account: [{"label": name, "value": value} for name, value in measures.items()]
        for account, measures in grouped.items()
        if measures
    }


def attach_usage_measures(tree: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    """Put entered usage on the account node. Fitted meters are left off."""
    from app.services.reporting.gl_rollup import iter_nodes

    by_account = measures_by_account(rows)
    if not by_account:
        return
    for line in tree.get("lines") or []:
        for node in iter_nodes(line):
            measures = by_account.get(str(node.get("account_number") or ""))
            if measures:
                node["measures"] = measures


def build_vendor_usage_payload(db: Session, organization_id: uuid.UUID) -> dict[str, Any]:
    """Meter rows from the warehouse. Empty when the tables are not loaded."""
    rows = {
        scenario: fetch_table_rows(db, table, organization_id) if table_exists(db, table) else []
        for scenario, table in USAGE_TABLES
    }
    return vendor_usage_from_rows(rows)
