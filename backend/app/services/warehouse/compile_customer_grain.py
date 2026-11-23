"""Compile customer ARR history for a close month from subscriptions + opportunities.

Writes ``actual_customer_arr_history`` only when the customer did not upload that
month. Stamps first-month revenue and latest-new-business dates so no-start /
winback / first-year lines follow the onboarding bucket policy.
"""

from __future__ import annotations

import calendar
import logging
import uuid
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import table_exists
from app.services.mrr.engine import (
    NEW_BUSINESS,
    MovementType,
    customer_age,
)
from app.services.mrr.service import bucket_policy
from app.services.warehouse.event_labels import EventLabels

logger = logging.getLogger(__name__)

HISTORY_TABLE = "actual_customer_arr_history"
COMPILED_PREFIX = "compiled:"
CENT = Decimal("0.01")

# Columns we want on history for later product/UOM grain. Written when present.
FORWARD_COLUMNS = (
    "parent_id",
    "subsidiary_id",
    "product_code",
    "product_name",
    "is_core_product",
    "uom",
    "qty_this_month",
    "qty_last_month",
    "billing_cadence",
    "classification_subtype",
    "first_month_revenue",
    "latest_new_business_date",
    "last_new_business_revenue",
    "contract_id",
    "succeeds_contract_id",
)

LINE_TO_MOVEMENT = {
    "new": MovementType.NEW,
    "expansion": MovementType.EXPANSION,
    "contraction": MovementType.CONTRACTION,
    "churn": MovementType.CHURN,
    "reactivation": MovementType.REACTIVATION,
}

MOVEMENT_LABEL = {
    "new_logo": "New Business",
    "winback": "Reactivation",
    "first_year_expansion": "Expansion",
    "first_year_contraction": "Contraction",
    "no_start": "Churn",
    "expansion": "Expansion",
    "contraction": "Contraction",
    "churn": "Churn",
    "reactivation": "Reactivation",
}

WATERFALL_COLUMN = {
    "new_logo": "new_business_arr",
    "winback": "reactivation_arr",
    "first_year_expansion": "expansion_arr",
    "first_year_contraction": "contraction_arr",
    "no_start": "churn_arr",
    "expansion": "expansion_arr",
    "contraction": "contraction_arr",
    "churn": "churn_arr",
    "reactivation": "reactivation_arr",
}


def money(value: Decimal) -> str:
    return f"{value.quantize(CENT, rounding=ROUND_HALF_UP):.2f}"


def _dec(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


def _as_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    text_value = str(value).strip()
    if len(text_value) >= 10 and text_value[4] == "-":
        return date.fromisoformat(text_value[:10])
    if len(text_value) >= 7 and text_value[4] == "-":
        year, month = int(text_value[:4]), int(text_value[5:7])
        return date(year, month, 1)
    return None


def _period_date(period: str) -> date:
    return date(int(period[:4]), int(period[5:7]), 1)


def _opportunity_closed(opp: dict[str, Any], labels: EventLabels) -> bool:
    """Actual history only includes closed-won bookings and closed reducing deals."""
    stage_bits = (
        opp.get("waterfall_type"),
        opp.get("pipeline_movement_type"),
        opp.get("close_status"),
        opp.get("stage"),
    )
    if labels.is_closed_won(*stage_bits):
        return True
    joined = " ".join(str(bit or "").casefold() for bit in stage_bits)
    if "closed lost" in joined or joined.strip() in {"churn", "contraction", "lost"}:
        return True
    line = labels.movement(opp.get("opportunity_type"), opp.get("waterfall_line"), opp.get("movement_type"))
    if line in {"churn", "contraction"} and ("closed" in joined or "lost" in joined or "churn" in joined):
        return True
    return False


def _table_columns(db: Session, table: str) -> set[str]:
    rows = db.execute(
        text(
            """
            select column_name
            from information_schema.columns
            where table_schema = 'public' and table_name = :table
            """
        ),
        {"table": table},
    ).all()
    return {str(name) for (name,) in rows}


def _customer_loaded(db: Session, table: str, org: str, period: str) -> bool:
    if not table_exists(db, table):
        return False
    found = db.execute(
        text(
            f"""
            select 1
            from "{table}"
            where organization_id = :org
              and left(cast(period as text), 7) = :period
              and coalesce(source_filename, '') not like 'compiled:%'
              and coalesce(source_filename, '') not like 'Compiled · %'
            limit 1
            """
        ),
        {"org": org, "period": period},
    ).first()
    return found is not None


def compile_customer_arr_history(
    db: Session,
    organization_id: uuid.UUID,
    period: str,
    *,
    opportunities: list[dict[str, Any]],
    subscriptions: list[dict[str, Any]],
    labels: EventLabels,
) -> bool:
    """Write compiled customer ARR history for ``period`` when none was uploaded."""
    org = str(organization_id)
    if not table_exists(db, HISTORY_TABLE):
        return False
    if _customer_loaded(db, HISTORY_TABLE, org, period):
        return False
    if not opportunities and not subscriptions:
        return False

    policy = bucket_policy(db, organization_id)
    period_dt = _period_date(period)
    names = _customer_names(db, org)
    begin_by, end_by = _arr_by_customer(subscriptions, period)
    active_months = _active_months_before(db, org, period_dt)
    lifetime_first = _lifetime_first_month(active_months)

    rows: list[dict[str, Any]] = []
    for opp in opportunities:
        if not _opportunity_closed(opp, labels):
            continue
        line_key = labels.movement(
            opp.get("opportunity_type"),
            opp.get("waterfall_line"),
            opp.get("movement_type"),
        )
        if not line_key:
            continue
        movement = LINE_TO_MOVEMENT.get(line_key)
        if movement is None:
            continue
        customer = str(opp.get("customer_id") or "").strip()
        if not customer:
            continue
        amount = abs(_dec(opp.get("amount_arr")))
        if amount == 0:
            continue

        before = active_months.get(customer) or []
        age = customer_age(period_dt, movement, before, policy)
        waterfall_line = (age.line if age and age.line else line_key)
        if waterfall_line == "new":
            waterfall_line = "new_logo"
        bucket = age.bucket if age else (
            NEW_BUSINESS if line_key in {"new", "reactivation"} else "Customer Success"
        )
        age_months = age.age_months if age else None
        latest_nb = age.first_mrr_period if age else None
        if movement == MovementType.NEW and (not before or (age and age.line in {"new_logo", "winback"})):
            latest_nb = period_dt
        first_month = lifetime_first.get(customer) or latest_nb

        begin = begin_by.get(customer, Decimal("0"))
        end = end_by.get(customer)
        if end is None:
            delta = -amount if line_key in {"contraction", "churn"} else amount
            end = begin + delta
            if end < 0:
                end = Decimal("0")

        row: dict[str, Any] = {
            "version": "Actual",
            "customer_id": customer,
            "customer_name": str(opp.get("customer_name") or names.get(customer) or customer),
            "segment": str(opp.get("segment") or ""),
            "movement_type": MOVEMENT_LABEL.get(waterfall_line, line_key.replace("_", " ").title()),
            "beginning_arr": money(begin),
            "movement_arr": money(-amount) if line_key in {"contraction", "churn"} else money(amount),
            "ending_arr": money(end),
            "waterfall_column": WATERFALL_COLUMN.get(waterfall_line, f"{line_key}_arr"),
            "waterfall_line": waterfall_line,
            "customer_bucket": bucket,
            "movement_id": str(opp.get("movement_id") or opp.get("opportunity_id") or ""),
            "note": "",
            "churn_type": "no_start" if waterfall_line == "no_start" else "",
            "first_mrr_period": (first_month.isoformat()[:7] if first_month else ""),
            "customer_age_months": str(age_months) if age_months is not None else "",
            "movement_subcategory": "",
            # Forward-compatible blanks
            "parent_id": "",
            "subsidiary_id": "",
            "product_code": "",
            "product_name": "",
            "is_core_product": "",
            "uom": "",
            "qty_this_month": "",
            "qty_last_month": "",
            "billing_cadence": str(opp.get("billing_cadence") or ""),
            "classification_subtype": "",
            "first_month_revenue": first_month.isoformat()[:7] if first_month else "",
            "latest_new_business_date": latest_nb.isoformat()[:7] if latest_nb else "",
            "last_new_business_revenue": (
                money(amount) if waterfall_line in {"new_logo", "winback"} else ""
            ),
            "contract_id": "",
            "succeeds_contract_id": "",
        }
        rows.append(row)

    if not rows:
        return False
    return _write_history_rows(db, org, period, rows, f"{COMPILED_PREFIX}customer_grain:{period}")


def _arr_by_customer(
    subscriptions: list[dict[str, Any]], period: str
) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
    year, month = int(period[:4]), int(period[5:7])
    start = date(year, month, 1)
    end = date(year, month, calendar.monthrange(year, month)[1])
    beginning: dict[str, Decimal] = {}
    ending: dict[str, Decimal] = {}
    for row in subscriptions:
        opened = _as_date(row.get("start_date") or row.get("contract_start_date"))
        closed = _as_date(row.get("end_date") or row.get("contract_end_date"))
        if opened is None or opened > end or (closed is not None and closed < start):
            continue
        customer = str(row.get("customer_id") or "")
        if not customer:
            continue
        amount = _dec(row.get("current_arr") or row.get("current_mrr") or 0)
        # current_mrr is monthly; prefer ARR when present
        if row.get("current_arr") in (None, "") and row.get("current_mrr") not in (None, ""):
            amount = _dec(row.get("current_mrr")) * 12
        if opened <= start and (closed is None or closed >= start):
            beginning[customer] = beginning.get(customer, Decimal("0")) + amount
        if opened <= end and (closed is None or closed >= end):
            ending[customer] = ending.get(customer, Decimal("0")) + amount
    return beginning, ending


def _customer_names(db: Session, org: str) -> dict[str, str]:
    if not table_exists(db, "actual_customers"):
        return {}
    columns = _table_columns(db, "actual_customers")
    if "customer_id" not in columns:
        return {}
    name_col = "customer_name" if "customer_name" in columns else None
    if not name_col:
        return {}
    rows = db.execute(
        text(
            f"""
            select customer_id, {name_col}
            from actual_customers
            where organization_id = :org
            """
        ),
        {"org": org},
    ).all()
    return {str(cid): str(name or cid) for cid, name in rows if cid}


def _active_months_before(db: Session, org: str, period_dt: date) -> dict[str, list[date]]:
    """Months before ``period_dt`` with positive ARR, by customer."""
    found: dict[str, set[date]] = {}
    if table_exists(db, HISTORY_TABLE):
        rows = db.execute(
            text(
                f"""
                select customer_id, period, ending_arr, beginning_arr, movement_type
                from "{HISTORY_TABLE}"
                where organization_id = :org
                  and left(cast(period as text), 7) < :period
                """
            ),
            {"org": org, "period": period_dt.isoformat()[:7]},
        ).mappings()
        for raw in rows:
            customer = str(raw.get("customer_id") or "")
            month = _as_date(raw.get("period"))
            if not customer or month is None:
                continue
            ending = _dec(raw.get("ending_arr"))
            beginning = _dec(raw.get("beginning_arr"))
            if ending > 0 or beginning > 0:
                found.setdefault(customer, set()).add(month.replace(day=1))
    if table_exists(db, "actual_subscriptions"):
        rows = db.execute(
            text(
                """
                select customer_id, contract_start_date, contract_end_date, current_arr
                from actual_subscriptions
                where organization_id = :org
                """
            ),
            {"org": org},
        ).mappings()
        last = date(period_dt.year, period_dt.month, 1)
        # step back one month as inclusive upper bound for "before"
        if last.month == 1:
            stop = date(last.year - 1, 12, 1)
        else:
            stop = date(last.year, last.month - 1, 1)
        for raw in rows:
            if _dec(raw.get("current_arr")) <= 0:
                continue
            customer = str(raw.get("customer_id") or "")
            opened = _as_date(raw.get("contract_start_date"))
            closed = _as_date(raw.get("contract_end_date"))
            if not customer or opened is None:
                continue
            cursor = opened.replace(day=1)
            end_cap = stop
            if closed is not None:
                end_cap = min(stop, closed.replace(day=1))
            while cursor <= end_cap:
                found.setdefault(customer, set()).add(cursor)
                if cursor.month == 12:
                    cursor = date(cursor.year + 1, 1, 1)
                else:
                    cursor = date(cursor.year, cursor.month + 1, 1)
    return {cid: sorted(months) for cid, months in found.items()}


def _lifetime_first_month(active_months: dict[str, list[date]]) -> dict[str, date]:
    return {cid: months[0] for cid, months in active_months.items() if months}


def _write_history_rows(
    db: Session,
    org: str,
    period: str,
    rows: list[dict[str, Any]],
    filename: str,
) -> bool:
    columns = _table_columns(db, HISTORY_TABLE)
    if "period" not in columns or "customer_id" not in columns:
        return False
    db.execute(
        text(
            f"""
            delete from "{HISTORY_TABLE}"
            where organization_id = :org
              and left(cast(period as text), 7) = :period
              and (
                coalesce(source_filename, '') like 'compiled:%'
                or coalesce(source_filename, '') like 'Compiled · %'
              )
            """
        ),
        {"org": org, "period": period},
    )
    nxt = db.execute(
        text(
            f'select coalesce(max(source_row_number), 0) + 1 from "{HISTORY_TABLE}" '
            "where organization_id = :org"
        ),
        {"org": org},
    ).scalar()
    start = int(nxt or 1)
    for index, values in enumerate(rows):
        payload: dict[str, Any] = {
            "organization_id": org,
            "source_row_number": start + index,
            "source_filename": filename,
            "period": f"{period}-01",
        }
        payload.update(values)
        used = [
            key
            for key in payload
            if key in columns or key in {"organization_id", "source_row_number", "source_filename"}
        ]
        names = ", ".join(f'"{key}"' for key in used)
        marks = ", ".join(f":{key}" for key in used)
        db.execute(
            text(f'insert into "{HISTORY_TABLE}" ({names}) values ({marks})'),
            {key: payload[key] for key in used},
        )
    return True
