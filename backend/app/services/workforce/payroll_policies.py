"""
Payroll policies for planning payroll load.

Rates and timing come from the loaded payroll policy file (employer tax, health premium per head,
401(k) match terms, merit, payout timing). The policy file sets the match terms but not who defers,
so the realized match share of wages and bonus comes from the payroll register for the year.
"""

from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import fetch_table_rows
from app.services.reporting.period_utils import to_period

POLICY_TABLES: dict[str, str] = {
    "Actual": "actual_payroll_policies",
    "Forecast": "forecast_payroll_policies",
    "Budget": "budget_payroll_policies",
}
REGISTER_TABLES: dict[str, str] = {
    "Actual": "actual_payroll_register",
    "Forecast": "forecast_payroll_register",
}
PLAN_POLICY_VERSION = "Forecast"


def _num(value: Any) -> Decimal | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return Decimal(str(value).replace(",", "").strip())
    except InvalidOperation:
        return None


def _period(value: Any) -> str | None:
    text = str(value or "").strip()
    return to_period(text) if text else None


def policy_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Loaded policy rows; numeric values as numbers, payout terms as text."""
    out = []
    for r in rows:
        name = str(r.get("policy") or "").strip()
        if not name:
            continue
        raw = str(r.get("value") or "").strip()
        num = _num(raw)
        out.append(
            {
                "policy": name,
                "value": float(num) if num is not None else raw,
                "effective_from": _period(r.get("effective_from")),
                "effective_to": _period(r.get("effective_to")),
                "applies_to": str(r.get("applies_to") or "").strip(),
            }
        )
    return sorted(out, key=lambda p: (p["policy"], p["effective_from"] or ""))


def realized_retirement_match(rows: Iterable[dict[str, Any]], periods: set[str]) -> dict[str, Any] | None:
    """Register 401(k) match ÷ (regular wages + bonus) over the given months."""
    match, base, seen = Decimal(0), Decimal(0), set()
    for r in rows:
        period = _period(r.get("period"))
        if period not in periods:
            continue
        m = _num(r.get("retirement_match"))
        w = _num(r.get("regular_wages"))
        if m is None or w is None:
            continue
        match += m
        base += w + (_num(r.get("bonus")) or Decimal(0))
        seen.add(period)
    if not base:
        return None
    months = sorted(seen)
    return {
        "rate": float(match / base),
        "match": round(float(match), 2),
        "base": round(float(base), 2),
        "span": f"{months[0]} to {months[-1]}",
        "months": len(months),
    }


def payroll_policies_payload(
    *,
    as_of_period: str,
    policies: list[dict[str, Any]],
    actual_register: list[dict[str, Any]],
    forecast_register: list[dict[str, Any]],
) -> dict[str, Any]:
    """Policy rows plus the year's realized match: actual register through close, forecast register after."""
    year = as_of_period[:4]
    year_periods = {f"{year}-{m:02d}" for m in range(1, 13)}
    closed = {p for p in year_periods if p <= as_of_period}
    open_ = year_periods - closed
    rows = [r for r in actual_register if _period(r.get("period")) in closed]
    rows += [r for r in forecast_register if _period(r.get("period")) in open_]
    return {
        "version": PLAN_POLICY_VERSION,
        "policies": policy_rows(policies),
        "retirement_match_realized": realized_retirement_match(rows, year_periods),
    }


def load_payroll_policies(db: Session, organization_id: uuid.UUID, *, as_of_period: str) -> dict[str, Any]:
    return payroll_policies_payload(
        as_of_period=to_period(as_of_period),
        policies=fetch_table_rows(db, POLICY_TABLES[PLAN_POLICY_VERSION], organization_id),
        actual_register=fetch_table_rows(db, REGISTER_TABLES["Actual"], organization_id),
        forecast_register=fetch_table_rows(db, REGISTER_TABLES["Forecast"], organization_id),
    )
