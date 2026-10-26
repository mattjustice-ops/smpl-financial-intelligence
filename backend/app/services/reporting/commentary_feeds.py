"""Count and size for the remaining statement lines, from the feed that posted them.

A measure is attached only when that feed adds up to the line. Payroll uses the
register: split components when the register has not named an account, and the
fully loaded cost when the row names the account it posted to. Subscription uses
recognized revenue by customer. Prepaid amortization uses the contracts that
amortize into the account. A feed that does not tie is left off.
"""

from __future__ import annotations

import uuid
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import fetch_table_rows, table_exists
from app.services.reporting.gl_income_statement import is_implementation_revenue
from app.services.reporting.gl_rollup import labor_bucket
from app.services.reporting.period_utils import prior_period

TIE = 1.0

# Labor role -> (register column, average label). Unsplit labor uses the fully loaded cost.
_COMPONENTS: dict[str, tuple[str, str]] = {
    "base": ("regular_wages", "average salary"),
    "bonus": ("bonus", "average bonus"),
    "severance": ("severance", "average severance"),
    "payroll_tax": ("employer_payroll_tax", "average payroll tax"),
    "match": ("retirement_match", "average retirement match"),
    "benefits": ("health_benefits", "average benefits"),
    "labor": ("total_payroll_cost", "average payroll cost"),
}

_FEEDS: dict[str, tuple[tuple[str, str], ...]] = {
    "Actual": (
        ("actual_payroll_register", "payroll"),
        ("actual_revenue_recognition", "recognition"),
        ("actual_prepaid_amortization_schedule", "prepaid"),
    ),
    "Budget": (
        ("budget_payroll_register", "payroll"),
        ("budget_revenue_recognition", "recognition"),
        ("budget_prepaid_amortization_schedule", "prepaid"),
    ),
    "Forecast": (
        ("forecast_payroll_register", "payroll"),
        ("forecast_revenue_recognition", "recognition"),
        ("forecast_prepaid_amortization_schedule", "prepaid"),
    ),
}


def _num(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _period(value: Any) -> str:
    return str(value or "")[:7]


def _department(node_id: str) -> str:
    for part in str(node_id).split("|"):
        if part.startswith("department:"):
            name = part.split(":", 1)[1].strip()
            if name and name != "__blank__":
                return name
    return ""


def _ties(node: dict[str, Any], total: float) -> bool:
    return abs(abs(float(node.get("amount") or 0)) - abs(total)) <= TIE


def _gl_account(row: dict[str, Any]) -> str:
    return str(row.get("gl_account") or "").strip()


def _component_row(row: dict[str, Any]) -> bool:
    """A register row whose account is a placeholder, so the component columns are the posting."""
    account = _gl_account(row)
    return bool(account) and not account.isdigit()


def _tally(rows: list[dict[str, Any]], amount_of: Callable[[dict[str, Any]], float], id_key: str) -> dict[str, Any] | None:
    totals: dict[str, float] = {}
    for row in rows:
        amount = round(amount_of(row), 2)
        if amount == 0:
            continue
        ident = str(row.get(id_key) or "").strip()
        if not ident:
            return None
        totals[ident] = round(totals.get(ident, 0.0) + amount, 2)
    if not totals:
        return None
    total = round(sum(totals.values()), 2)
    return {
        "count": len(totals),
        "total": total,
        "average": round(total / len(totals), 2),
        "ids": set(totals),
    }


def _people_measures(current: dict[str, Any], prior: dict[str, Any] | None, count_label: str, size_label: str) -> list[dict[str, Any]]:
    measures = [
        {"label": count_label, "value": current["count"]},
        {"label": size_label, "value": current["average"]},
    ]
    if prior is not None:
        arrived = len(current["ids"] - prior["ids"])
        left = len(prior["ids"] - current["ids"])
        measures.append({"label": "hires" if count_label == "employees" else "customers added", "value": arrived})
        measures.append({"label": "departures" if count_label == "employees" else "customers ended", "value": left})
    return measures


def _in_department(rows: list[dict[str, Any]], department: str) -> list[dict[str, Any]]:
    if not department:
        return list(rows)
    folded = department.casefold()
    return [row for row in rows if str(row.get("department") or "").strip().casefold() == folded]


def _payroll_measures(
    node: dict[str, Any],
    current_rows: list[dict[str, Any]],
    prior_rows: list[dict[str, Any]] | None,
) -> list[dict[str, Any]] | None:
    bucket = labor_bucket(str(node.get("label") or ""))
    if bucket is None or bucket[0] not in _COMPONENTS:
        return None
    amount_key, size_label = _COMPONENTS[bucket[0]]
    department = _department(str(node.get("id") or ""))
    current = _in_department(current_rows, department)
    prior = _in_department(prior_rows, department) if prior_rows is not None else None
    account = str(node.get("account_number") or "").strip()

    def finish(chosen: list[dict[str, Any]], earlier: list[dict[str, Any]] | None, key: str, label: str) -> list[dict[str, Any]] | None:
        tally = _tally(chosen, lambda row: _num(row.get(key)), "employee_id")
        if tally is None or not _ties(node, tally["total"]):
            return None
        prior_tally = {"ids": set()} if earlier is None else (_tally(earlier, lambda row: _num(row.get(key)), "employee_id") or {"ids": set()})
        # earlier is None only when the prior month is not loaded. Pass None so hires are omitted.
        compared = None if earlier is None else prior_tally
        return _people_measures(tally, compared, "employees", label)

    if account:
        exact = [row for row in current if _gl_account(row) == account]
        earlier = [row for row in prior if _gl_account(row) == account] if prior is not None else None
        if exact:
            posted = finish(exact, earlier, amount_key, size_label)
            if posted:
                return posted
            if amount_key != "total_payroll_cost":
                posted = finish(exact, earlier, "total_payroll_cost", "average payroll cost")
                if posted:
                    return posted
            return None
    pooled = [row for row in current if _component_row(row)]
    earlier_pooled = [row for row in prior if _component_row(row)] if prior is not None else None
    return finish(pooled, earlier_pooled, amount_key, size_label)


def _subscription_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chosen = []
    for row in rows:
        kind = str(row.get("revenue_type") or "").lower()
        if "subscription" in kind and "recurring" not in kind and "implementation" not in kind:
            chosen.append(row)
    return chosen


def _is_subscription(node: dict[str, Any]) -> bool:
    label = str(node.get("label") or "").lower()
    if "subscription" not in label or is_implementation_revenue(label):
        return False
    return not ("recurring" in label and "service" in label)


def _subscription_measures(
    node: dict[str, Any],
    current_rows: list[dict[str, Any]],
    prior_rows: list[dict[str, Any]] | None,
) -> list[dict[str, Any]] | None:
    if not _is_subscription(node):
        return None
    tally = _tally(_subscription_rows(current_rows), lambda row: _num(row.get("recognized_revenue")), "customer_id")
    if tally is None or not _ties(node, tally["total"]):
        return None
    compared = None
    if prior_rows is not None:
        compared = _tally(_subscription_rows(prior_rows), lambda row: _num(row.get("recognized_revenue")), "customer_id") or {"ids": set()}
    return _people_measures(tally, compared, "customers", "average subscription revenue")


def _prepaid_amount(row: dict[str, Any]) -> float:
    for key in ("amortization", "monthly_amortization", "prepaid_amortization"):
        if row.get(key) not in (None, ""):
            return _num(row.get(key))
    return 0.0


def _prepaid_measures(node: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    account = str(node.get("account_number") or "").strip()
    if not account:
        return None
    department = _department(str(node.get("id") or ""))
    chosen = []
    for index, row in enumerate(rows):
        if str(row.get("account_number") or "").strip() != account:
            continue
        row_department = str(row.get("department") or "").strip()
        if department and row_department.casefold() != department.casefold():
            continue
        if not department and row_department:
            continue
        amount = round(_prepaid_amount(row), 2)
        if amount == 0:
            continue
        ident = str(row.get("contract_id") or "").strip() or f"row-{index}"
        chosen.append({"contract_id": ident, "amount": amount})
    tally = _tally(chosen, lambda row: _num(row.get("amount")), "contract_id")
    if tally is None or not _ties(node, tally["total"]):
        return None
    return [
        {"label": "prepaid contracts", "value": tally["count"]},
        {"label": "average amortization", "value": tally["average"]},
    ]


def _apply(node: dict[str, Any], measures: list[dict[str, Any]] | None) -> None:
    if measures and not node.get("measures"):
        node["measures"] = measures


def attach_commentary_feeds(
    tree: dict[str, Any],
    *,
    payroll_rows: list[dict[str, Any]] | None = None,
    prior_payroll_rows: list[dict[str, Any]] | None = None,
    recognition_rows: list[dict[str, Any]] | None = None,
    prior_recognition_rows: list[dict[str, Any]] | None = None,
    prepaid_rows: list[dict[str, Any]] | None = None,
) -> None:
    """Attach count and size where the feed equals the line. An existing measure is left as it is."""
    payroll_rows = payroll_rows or []
    recognition_rows = recognition_rows or []
    prepaid_rows = prepaid_rows or []

    def walk(node: dict[str, Any]) -> None:
        for child in node.get("children") or []:
            walk(child)
        if node.get("measures"):
            return
        _apply(node, _payroll_measures(node, payroll_rows, prior_payroll_rows))
        if node.get("measures"):
            return
        _apply(node, _subscription_measures(node, recognition_rows, prior_recognition_rows))
        if node.get("measures"):
            return
        _apply(node, _prepaid_measures(node, prepaid_rows))

    for line in tree.get("lines") or []:
        walk(line)


def load_commentary_feeds(db: Session, organization_id: uuid.UUID) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Payroll, recognition, and prepaid rows by scenario. A missing table is an empty list."""
    loaded: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for scenario, tables in _FEEDS.items():
        by_role: dict[str, list[dict[str, Any]]] = {}
        for table, role in tables:
            by_role[role] = fetch_table_rows(db, table, organization_id) if table_exists(db, table) else []
        loaded[scenario] = by_role
    return loaded


def feeds_for_period(feeds: dict[str, list[dict[str, Any]]], period: str) -> dict[str, Any]:
    """Current rows, and the prior month only when that month is loaded."""
    out: dict[str, Any] = {}
    prior = prior_period(period)
    for role in ("payroll", "recognition", "prepaid"):
        rows = feeds.get(role) or []
        periods = {_period(row.get("period")) for row in rows}
        out[role] = [row for row in rows if _period(row.get("period")) == period]
        out[f"prior_{role}"] = [row for row in rows if _period(row.get("period")) == prior] if prior in periods else None
    return out
