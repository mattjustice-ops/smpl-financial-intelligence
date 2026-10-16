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
            })
        scenarios[scenario] = {
            period: sorted(items, key=lambda row: (row["account"], row["vendor"]))
            for period, items in by_period.items()
        }
    return {"note": NOTE, "accounts": dict(ACCOUNT_NAMES), "scenarios": scenarios}


def build_vendor_usage_payload(db: Session, organization_id: uuid.UUID) -> dict[str, Any]:
    """Meter rows from the warehouse. Empty when the tables are not loaded."""
    rows = {
        scenario: fetch_table_rows(db, table, organization_id) if table_exists(db, table) else []
        for scenario, table in USAGE_TABLES
    }
    return vendor_usage_from_rows(rows)
