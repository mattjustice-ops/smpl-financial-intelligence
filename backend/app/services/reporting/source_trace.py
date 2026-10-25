"""The records behind one number.

An actual month opens to the ledger: the accounts on the line, the vendors on an
account when a vendor is stored, and the journal lines when that list is short
enough to read. A long journal is a count that ties to the account, and the
lines are a further step. A forecast month has no journal. Its bookings are the
opportunities. Closed deals explain bookings. They sit beside recognized
revenue and are not added into it.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import _table_columns, fetch_table_rows, table_exists
from app.services.reporting.gl_income_statement import (
    classify_gl_line,
    is_implementation_revenue,
    is_services_revenue,
)
from app.services.reporting.gl_income_statement import _norm
from app.services.reporting.period_utils import to_period
from app.services.reporting.pipeline_deals import DEAL_TYPES, _deal, _deal_period

JE_READABLE = 25
JE_PAGE = 100
DEAL_PAGE = 100
REVENUE_LINES = {"sub_rev", "rec_svc_rev", "impl_rev"}
COST_LINES = {"cogs", "sm", "rd", "ga"}
REDUCING = {"Contraction", "Churn"}
MOVEMENT_LABEL = {
    "New Business": "new business",
    "Expansion": "expansion",
    "Reactivation": "reactivation",
    "Contraction": "contraction",
    "Churn": "churn",
}
GROUP_FIELDS = (
    "account_number",
    "account_name",
    "statement",
    "statement_category",
    "category",
    "account_group",
    "department",
    "expense_type",
)


def build_source_trace(
    db: Session,
    organization_id: uuid.UUID,
    *,
    period: str,
    close: str,
    grain: str,
    account_number: str = "",
    account_name: str = "",
    include_entries: bool = False,
    offset: int = 0,
    deal_type: str = "",
    deal_offset: int = 0,
) -> dict[str, Any]:
    """One number, the month it belongs to, and the records that add up to it."""
    period = to_period(period)
    close = to_period(close)
    grain = (grain or "account").strip() or "account"
    number = str(account_number or "").strip()
    name = str(account_name or "").strip()
    movement = deal_type.strip()
    if movement not in DEAL_TYPES:
        movement = ""
    forecast = period > close
    if movement or grain == "opportunities" or (forecast and grain in REVENUE_LINES | {"revenue"}):
        return _opportunity_trace(
            db, organization_id, period, grain, forecast=forecast, movement=movement, offset=deal_offset
        )
    if forecast and grain in COST_LINES:
        return _empty(
            period,
            grain,
            forecast=True,
            note="This month has not closed, so there is no ledger for this line. The forecast amount is the engine's build, not a list of journal entries.",
        )
    if forecast and grain == "account":
        return _empty(
            period,
            grain,
            forecast=True,
            note="This month has not closed, so there are no journal entries. Bookings in a forecast month are the opportunities in the pipeline.",
        )
    deals = _load_deals(db, organization_id, period, closed=not forecast)
    groups = _account_groups(db, organization_id, period)
    matched = [row for row in groups if _keeps(row, grain, number, name)]
    accounts = _merge(matched)
    revenue_account = bool(accounts) and all(row["revenue"] for row in accounts)
    show_bookings = grain in REVENUE_LINES | {"revenue", "opportunities"} or (grain == "account" and revenue_account)
    vendors = None
    entries = None
    entry_count = 0
    if len(accounts) == 1:
        only = accounts[0]
        entry_count = only["count"]
        vendors = _vendors(db, organization_id, period, only, revenue=only["revenue"])
        if include_entries or entry_count <= JE_READABLE:
            entries = _entries(
                db,
                organization_id,
                period,
                only,
                revenue=only["revenue"],
                offset=offset if include_entries else 0,
                limit=JE_PAGE if include_entries else JE_READABLE,
            )
    note = _account_note(accounts, entries, entry_count)
    return {
        "period": period,
        "forecast": False,
        "grain": grain,
        "note": note,
        "accounts": accounts or None,
        "account_total": round(sum(row["amount"] for row in accounts), 2) if accounts else None,
        "vendors": vendors,
        "vendor_note": "These vendors total the account." if vendors else "",
        "entries": entries,
        "entry_count": entry_count if len(accounts) == 1 else sum(row["count"] for row in accounts),
        "entries_available": len(accounts) == 1 and entry_count > JE_READABLE,
        "entry_offset": offset if include_entries else 0,
        "bookings": _bookings(deals, forecast=False, aside=True) if show_bookings else None,
    }


def _opportunity_trace(
    db: Session,
    organization_id: uuid.UUID,
    period: str,
    grain: str,
    *,
    forecast: bool,
    movement: str,
    offset: int,
) -> dict[str, Any]:
    deals = _load_deals(db, organization_id, period, closed=not forecast)
    if movement:
        deals = [deal for deal in deals if deal.get("type") == movement]
    aside = grain in REVENUE_LINES or grain == "revenue"
    body = _empty(period, grain, forecast=forecast, note="")
    body["bookings"] = _bookings(deals, forecast=forecast, aside=aside and not forecast, movement=movement, offset=offset)
    body["note"] = body["bookings"]["note"]
    if forecast and not movement and grain in REVENUE_LINES | {"revenue"}:
        body["note"] = (
            "This month has not closed, so there is no ledger. "
            "Bookings in the forecast are the opportunities below. They are not recognized revenue."
        )
        body["bookings"]["note"] = body["note"]
    return body


def _empty(period: str, grain: str, *, forecast: bool, note: str) -> dict[str, Any]:
    return {
        "period": period,
        "forecast": forecast,
        "grain": grain,
        "note": note,
        "accounts": None,
        "account_total": None,
        "vendors": None,
        "vendor_note": "",
        "entries": None,
        "entry_count": 0,
        "entries_available": False,
        "entry_offset": 0,
        "bookings": None,
    }


def _account_note(accounts: list[dict[str, Any]], entries: list[dict[str, Any]] | None, entry_count: int) -> str:
    if not accounts:
        return "No journal lines are loaded for this line in this month."
    if len(accounts) > 1:
        return "These accounts total the line. Open an account for its journal entries."
    if entries is not None:
        return "These journal entries total the account."
    if entry_count > JE_READABLE:
        return f"{entry_count} journal entries. They total the account."
    return "This account is the line."


def _keeps(row: dict[str, Any], grain: str, number: str, name: str) -> bool:
    if grain == "account":
        if number:
            return str(row.get("account_number") or "").strip() == number
        if name:
            return str(row.get("account_name") or "").strip() == name
        return False
    if grain == "revenue":
        return row.get("line_key") in REVENUE_LINES
    if grain in REVENUE_LINES or grain in COST_LINES:
        return row.get("line_key") == grain
    return False


def _line_key(row: dict[str, Any]) -> str | None:
    line = classify_gl_line(row)
    if line == "revenue":
        label = f"{_norm(row.get('account_name'))} {_norm(row.get('account_group'))}"
        if is_implementation_revenue(label):
            return "impl_rev"
        if is_services_revenue(label):
            return "rec_svc_rev"
        return "sub_rev"
    if line in COST_LINES:
        return line
    return None


def _merge(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for row in groups:
        key = row.get("line_key")
        if not key:
            continue
        number = str(row.get("account_number") or "").strip()
        name = str(row.get("account_name") or "").strip()
        slot = merged.setdefault(
            (key, number or name),
            {"number": number, "name": name, "amount": 0.0, "count": 0, "revenue": key in REVENUE_LINES},
        )
        amount = float(row.get("amount") or 0.0)
        if slot["revenue"]:
            amount = -amount
        slot["amount"] += amount
        slot["count"] += int(row.get("count") or 0)
    out = []
    for slot in merged.values():
        slot["amount"] = round(slot["amount"], 2)
        out.append(slot)
    out.sort(key=lambda row: (row["number"], row["name"]))
    return out


def _bookings(
    deals: list[dict[str, Any]],
    *,
    forecast: bool,
    aside: bool,
    movement: str = "",
    offset: int = 0,
) -> dict[str, Any]:
    reducing = movement in REDUCING
    if reducing:
        chosen = list(deals)
        lost = []
    else:
        chosen = [deal for deal in deals if deal.get("outcome") != "lost"]
        lost = [] if movement else [deal for deal in deals if deal.get("outcome") == "lost"]
    won_items = [_deal_item(deal, forecast=forecast, signed=reducing) for deal in chosen]
    lost_items = [_deal_item(deal, forecast=False, signed=False) for deal in lost]
    total = round(sum(item["amount"] for item in won_items), 2) if won_items else None
    lost_total = round(sum(item["amount"] for item in lost_items), 2) if lost_items else 0.0
    count = len(won_items)
    start = max(0, offset)
    page = won_items[start:start + DEAL_PAGE]
    label = MOVEMENT_LABEL.get(movement, "")
    if not chosen and not lost:
        if movement and forecast:
            note = f"This month has not closed. No {label} opportunities are loaded. There are no journal entries."
        elif movement:
            note = f"No {label} deals are loaded for this month."
        elif forecast:
            note = "No opportunities are loaded for this month."
        else:
            note = "No closed opportunities are loaded for this month."
    elif movement and forecast:
        note = (
            f"This month has not closed. These are the {label} opportunities in the pipeline. "
            "There are no journal entries. The total is weighted ARR."
        )
    elif movement:
        note = f"These {label} deals are the {label} line for this month."
        if reducing:
            note += " The amounts are the reduction in ARR."
    elif forecast:
        note = "This month has not closed. These opportunities are the pipeline. There are no journal entries. The total is weighted ARR."
    elif aside:
        note = "Closed in this month. These are bookings. They are not added into this revenue account, and they are not tied to a journal line."
    else:
        note = "Deals that closed in this month. This is bookings. Recognized revenue is the ledger, and these deals are not added into it."
    if lost_items:
        note += " Lost deals are kept apart and are not in the total."
    if count > start + len(page):
        note += f" Showing {start + 1}–{start + len(page)} of {count}. The total includes every deal."
    return {
        "loaded": bool(chosen or lost),
        "forecast": forecast,
        "aside": aside,
        "heading": movement or ("Pipeline" if forecast else "Closed bookings"),
        "note": note,
        "total": total,
        "total_label": movement or ("Weighted pipeline" if forecast else "Closed won"),
        "count": count,
        "deal_offset": start,
        "deal_count": count,
        "deals": page,
        "lost": lost_items,
        "lost_total": lost_total,
    }


def _deal_item(deal: dict[str, Any], *, forecast: bool, signed: bool) -> dict[str, Any]:
    amount = deal["weighted"] if forecast else deal["arr"]
    if signed:
        amount = -abs(amount)
    return {
        "id": deal.get("id") or "",
        "customer": deal.get("customer") or "",
        "type": deal.get("type") or "",
        "stage": deal.get("stage") or "",
        "owner": deal.get("owner") or "",
        "amount": amount,
        "arr": deal["arr"],
        "probability": deal.get("prob"),
    }


def _load_deals(db: Session, organization_id: uuid.UUID, period: str, *, closed: bool) -> list[dict[str, Any]]:
    table = "actual_opportunities" if closed else "forecast_opportunities"
    out = []
    for raw in fetch_table_rows(db, table, organization_id):
        if _deal_period(raw) != period or raw.get("opportunity_type") not in DEAL_TYPES:
            continue
        deal = _deal(raw, closed=closed)
        deal["type"] = raw.get("opportunity_type") or ""
        out.append(deal)
    out.sort(key=lambda deal: (-abs(deal["weighted"]), str(deal.get("id") or "")))
    return out


def _account_groups(db: Session, organization_id: uuid.UUID, period: str) -> list[dict[str, Any]]:
    if not table_exists(db, "gl_actuals"):
        return []
    columns = _table_columns(db, "gl_actuals")
    if "amount" not in columns or "period" not in columns:
        return []
    present = [name for name in GROUP_FIELDS if name in columns]
    select = ", ".join(present + ["count(*) as entry_count", "sum(amount) as amount"])
    group = ", ".join(str(index + 1) for index in range(len(present)))
    where = ["organization_id = :org", "substr(cast(period as text), 1, 7) = :period"]
    if "version" in columns:
        where.append("lower(coalesce(version, '')) = 'actual'")
    rows = db.execute(
        text(f"select {select} from gl_actuals where {' and '.join(where)} group by {group}"),
        {"org": str(organization_id), "period": period},
    ).mappings()
    out = []
    for raw in rows:
        row = {name: raw.get(name) if name in present else "" for name in GROUP_FIELDS}
        row["count"] = int(raw["entry_count"] or 0)
        row["amount"] = float(raw["amount"] or 0.0)
        row["line_key"] = _line_key(row)
        out.append(row)
    return out


def _account_clause(account: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if account.get("number"):
        return "account_number = :account", {"account": account["number"]}
    return "account_name = :account", {"account": account.get("name") or ""}


def _vendors(
    db: Session,
    organization_id: uuid.UUID,
    period: str,
    account: dict[str, Any],
    *,
    revenue: bool,
) -> list[dict[str, Any]] | None:
    columns = _table_columns(db, "gl_actuals")
    if "vendor_name" not in columns:
        return None
    clause, params = _account_clause(account)
    where = ["organization_id = :org", "substr(cast(period as text), 1, 7) = :period", clause]
    if "version" in columns:
        where.append("lower(coalesce(version, '')) = 'actual'")
    params.update({"org": str(organization_id), "period": period})
    rows = db.execute(
        text(
            "select coalesce(nullif(trim(cast(vendor_name as text)), ''), '') as vendor, "
            f"count(*) as entry_count, sum(amount) as amount from gl_actuals where {' and '.join(where)} "
            "group by 1"
        ),
        params,
    ).mappings()
    found = []
    for raw in rows:
        amount = float(raw["amount"] or 0.0)
        if revenue:
            amount = -amount
        found.append({"vendor": str(raw["vendor"] or ""), "amount": round(amount, 2), "count": int(raw["entry_count"] or 0)})
    named = [row for row in found if row["vendor"]]
    if not named:
        return None
    shown = named + [row for row in found if not row["vendor"] and abs(row["amount"]) >= 0.005]
    shown.sort(key=lambda row: -abs(row["amount"]))
    gap = round(account["amount"] - sum(row["amount"] for row in shown), 2)
    if abs(gap) >= 0.01:
        shown.append({"vendor": "Remainder", "amount": gap, "count": 0})
    return shown


def _entries(
    db: Session,
    organization_id: uuid.UUID,
    period: str,
    account: dict[str, Any],
    *,
    revenue: bool,
    offset: int,
    limit: int,
) -> list[dict[str, Any]]:
    columns = _table_columns(db, "gl_actuals")
    fields = {
        "source_record_id": "id",
        "vendor_name": "vendor",
        "department": "department",
        "notes": "memo",
    }
    select = []
    for column, alias in fields.items():
        if column in columns:
            select.append(f"cast({column} as text) as {alias}")
        else:
            select.append(f"'' as {alias}")
    select.append("amount")
    clause, params = _account_clause(account)
    where = ["organization_id = :org", "substr(cast(period as text), 1, 7) = :period", clause]
    if "version" in columns:
        where.append("lower(coalesce(version, '')) = 'actual'")
    params.update({"org": str(organization_id), "period": period, "limit": limit, "offset": max(0, offset)})
    rows = db.execute(
        text(
            f"select {', '.join(select)} from gl_actuals where {' and '.join(where)} "
            "order by abs(amount) desc limit :limit offset :offset"
        ),
        params,
    ).mappings()
    out = []
    for raw in rows:
        amount = float(raw["amount"] or 0.0)
        if revenue:
            amount = -amount
        out.append(
            {
                "id": str(raw["id"] or ""),
                "vendor": str(raw["vendor"] or ""),
                "department": str(raw["department"] or ""),
                "memo": str(raw["memo"] or ""),
                "amount": round(amount, 2),
            }
        )
    return out
