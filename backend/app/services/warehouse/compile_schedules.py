"""Compile the close schedules from imported customer files.

Bookings come from opportunities whose label is a closed-won word.
When a subscription book is loaded, ARR opens on the contracts active on the
first of the month and ends on the contracts active at month-end. New business,
expansion, contraction, and reactivation come from opportunities. Churn is the
ARR of a customer who is gone at month-end. A renewal is not a movement.
Without a subscription book, ARR still comes from customer ARR movements when
that file is loaded, and otherwise from opportunities opened on last month's
compiled ending. Deferred revenue is last month's balance, plus this month's
billings, minus revenue recognized on the ledger. Collections are the billings
whose collection month is this close. The operating bridge uses those
collections and the ledger's cash costs, and it ends on the cash the statements
already built. A file the customer loaded for that month is left as they loaded
it, except an ARR row that the subscription book ties, which is replaced.
"""

from __future__ import annotations

import calendar
import logging
import uuid
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import table_exists
from app.services.reporting.gl_one_book import ONE_BOOK_SQL
from app.services.reporting.period_utils import prior_period
from app.services.warehouse.event_labels import EventLabels, labels_from_json

logger = logging.getLogger(__name__)

CENT = Decimal("0.01")
# Calculated rows are not a customer load. The name has no " · " separators, so
# the import screen does not list them beside the files the customer uploaded.
COMPILED_PREFIX = "compiled:"
ARR_TABLE = "actual_mrr_waterfall"
DR_TABLE = "actual_deferred_revenue_waterfall"
BRIDGE_TABLE = "actual_cash_flow_bridge"
COLLECTIONS_TABLE = "actual_cash_collections"


def money(value: Decimal) -> str:
    return f"{value.quantize(CENT, rounding=ROUND_HALF_UP):.2f}"


def _dec(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


def rollup_arr(beginning: Decimal, lines: dict[str, Decimal]) -> dict[str, Decimal]:
    """Beginning plus the five movements. Contraction and churn reduce ARR."""
    new = lines.get("new", Decimal("0"))
    expansion = lines.get("expansion", Decimal("0"))
    contraction = lines.get("contraction", Decimal("0"))
    churn = lines.get("churn", Decimal("0"))
    reactivation = lines.get("reactivation", Decimal("0"))
    ending = beginning + new + expansion + reactivation - contraction - churn
    return {
        "beginning": beginning,
        "new": new,
        "expansion": expansion,
        "contraction": contraction,
        "churn": churn,
        "reactivation": reactivation,
        "ending": ending,
        "net_new": ending - beginning,
        "renewal": beginning - contraction - churn,
    }


def retention(beginning: Decimal, lines: dict[str, Decimal]) -> tuple[Decimal | None, Decimal | None]:
    if beginning <= 0:
        return None, None
    contraction = lines.get("contraction", Decimal("0"))
    churn = lines.get("churn", Decimal("0"))
    expansion = lines.get("expansion", Decimal("0"))
    reactivation = lines.get("reactivation", Decimal("0"))
    grr = (beginning - contraction - churn) / beginning
    nrr = (beginning + expansion + reactivation - contraction - churn) / beginning
    return grr, nrr


def rollup_deferred(beginning: Decimal, billings: Decimal, recognized: Decimal) -> dict[str, Decimal]:
    return {
        "beginning": beginning,
        "billings": billings,
        "recognized": recognized,
        "ending": beginning + billings - recognized,
    }


def unexplained_cash(
    beginning: Decimal,
    ending: Decimal,
    collections: Decimal,
    payroll: Decimal,
    commission: Decimal,
    vendor: Decimal,
    tax: Decimal,
    interest: Decimal,
    capex: Decimal,
    financing: Decimal = Decimal("0"),
) -> Decimal:
    """Cash the named bridge lines do not explain (ending − measured path).

    Measured path: beginning + collections − payroll − commission − vendor
    − tax − interest − capex + financing. A non-zero result is a failed foot,
    not a line that forces the bridge to tie.
    """
    measured = (
        beginning
        + collections
        - payroll
        - commission
        - vendor
        - tax
        - interest
        - capex
        + financing
    )
    return ending - measured


# Kept as an alias so older callers/tests that still import the name fail loudly
# if they expect a residual "other" plug — prefer unexplained_cash.
def bridge_plug(*args, **kwargs) -> Decimal:
    return unexplained_cash(*args, **kwargs)


def cash_costs(
    rows: list[tuple[str, str, Any]],
    *,
    account_maps: dict[str, str] | None = None,
    account_numbers: list[str] | None = None,
) -> dict[str, Decimal]:
    """Group a month of ledger activity by map (preferred) or file account group.

    ``rows`` are (account_group, account_name, amount). When ``account_numbers``
    aligns with ``rows`` and ``account_maps`` has bridge/P&L lines, mapped accounts
    win over group heuristics. Mapped ``exclude`` is skipped.
    """
    payroll = commission = vendor = interest = recognized = Decimal("0")
    tax_expense = Decimal("0")
    maps = account_maps or {}
    for index, (group, name, amount) in enumerate(rows):
        kind = str(group or "").strip().lower()
        label = str(name or "").strip().lower()
        value = _dec(amount)
        account = ""
        if account_numbers is not None and index < len(account_numbers):
            account = str(account_numbers[index] or "").strip()
        mapped = maps.get(account, "").strip().lower() if account else ""
        if mapped == "exclude":
            continue
        if mapped == "payroll":
            payroll += value
            continue
        if mapped == "commission":
            commission += value
            continue
        if mapped == "vendor":
            vendor += value
            continue
        if mapped == "interest":
            interest += value
            continue
        if mapped == "tax":
            tax_expense += value
            continue
        if mapped == "revenue":
            recognized += -value
            continue
        if kind == "revenue":
            recognized += -value
        elif "commission" in label:
            commission += value
        elif kind == "labor" or (kind == "cogs" and "labor" in label):
            payroll += value
        elif kind == "interest":
            interest += value
        elif kind == "taxes":
            tax_expense += value
        elif kind in {"marketing expense", "technology expense", "g&a expense"} or (
            kind == "cogs" and "labor" not in label
        ):
            vendor += value
    return {
        "recognized": recognized,
        "payroll": payroll,
        "commission": commission,
        "vendor": vendor,
        "tax": tax_expense if tax_expense > 0 else Decimal("0"),
        "interest": interest,
    }


def bookings_and_movements(
    opportunities: list[dict[str, Any]],
    labels: EventLabels,
) -> tuple[Decimal, dict[str, Decimal]]:
    """Closed-won ARR, and the waterfall lines named by opportunity type."""
    bookings = Decimal("0")
    lines = {name: Decimal("0") for name in ("new", "expansion", "contraction", "churn", "reactivation")}
    for row in opportunities:
        amount = abs(_dec(row.get("amount_arr")))
        if labels.is_closed_won(
            row.get("waterfall_type"),
            row.get("pipeline_movement_type"),
            row.get("close_status"),
        ):
            bookings += amount
        line = labels.movement(row.get("opportunity_type"), row.get("waterfall_line"), row.get("movement_type"))
        if line:
            lines[line] += amount
    return bookings, lines


def _as_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def arr_from_subscription_book(
    subscriptions: list[dict[str, Any]],
    opportunities: list[dict[str, Any]],
    period: str,
    labels: EventLabels,
) -> dict[str, Any] | None:
    """ARR for one month from the subscription book and the opportunities.

    Beginning is the ARR active on the 1st. Ending is the ARR active on
    month-end. Churn is a customer who is gone, valued after that customer's
    opportunities for the month. The result is tied only when those movements
    land on the month-end book.
    """
    year_text, month_text = period.split("-", 1)
    year, month = int(year_text), int(month_text)
    start = date(year, month, 1)
    end = date(year, month, calendar.monthrange(year, month)[1])
    beginning_by: dict[str, Decimal] = {}
    ending_by: dict[str, Decimal] = {}
    covered = False
    for row in subscriptions:
        opened = _as_date(row.get("start_date") or row.get("contract_start_date"))
        closed = _as_date(row.get("end_date") or row.get("contract_end_date"))
        if opened is None or opened > end or (closed is not None and closed < start):
            continue
        covered = True
        amount = _dec(row.get("current_arr"))
        customer = str(row.get("customer_id") or "")
        if opened <= start and (closed is None or closed >= start):
            beginning_by[customer] = beginning_by.get(customer, Decimal("0")) + amount
        if opened <= end and (closed is None or closed >= end):
            ending_by[customer] = ending_by.get(customer, Decimal("0")) + amount
    if not covered:
        return None

    _, lines = bookings_and_movements(opportunities, labels)
    lines["churn"] = Decimal("0")
    by_customer: dict[str, dict[str, Decimal]] = {}
    for row in opportunities:
        line = labels.movement(row.get("opportunity_type"), row.get("waterfall_line"), row.get("movement_type"))
        if line not in {"new", "expansion", "contraction", "reactivation"}:
            continue
        customer = str(row.get("customer_id") or "")
        bucket = by_customer.setdefault(
            customer,
            {name: Decimal("0") for name in ("new", "expansion", "contraction", "reactivation")},
        )
        bucket[line] += abs(_dec(row.get("amount_arr")))

    churn = Decimal("0")
    customers = set(beginning_by) | set(ending_by) | set(by_customer)
    for customer in customers:
        begin = beginning_by.get(customer, Decimal("0"))
        finish = ending_by.get(customer, Decimal("0"))
        moved = by_customer.get(customer, {})
        up = moved.get("new", Decimal("0")) + moved.get("expansion", Decimal("0")) + moved.get("reactivation", Decimal("0"))
        down = moved.get("contraction", Decimal("0"))
        if finish == 0 and (begin > 0 or up > 0 or down > 0):
            churn += begin + up - down
    lines["churn"] = churn
    beginning = sum(beginning_by.values(), Decimal("0"))
    ending = sum(ending_by.values(), Decimal("0"))
    rolled = rollup_arr(beginning, lines)
    return {
        "beginning": beginning,
        "ending": ending,
        "lines": lines,
        "tied": money(rolled["ending"]) == money(ending),
    }


def movements_from_history(rows: list[dict[str, Any]], labels: EventLabels) -> tuple[Decimal | None, dict[str, Decimal]]:
    """Customer movements already labeled on the ARR history file."""
    lines = {name: Decimal("0") for name in ("new", "expansion", "contraction", "churn", "reactivation")}
    beginning = Decimal("0")
    saw_beginning = False
    for row in rows:
        if row.get("beginning_arr") not in (None, ""):
            beginning += _dec(row.get("beginning_arr"))
            saw_beginning = True
        line = labels.movement(row.get("waterfall_line"), row.get("movement_type"))
        if line:
            lines[line] += abs(_dec(row.get("movement_arr")))
    return (beginning if saw_beginning else None), lines


def load_event_labels(db: Session, organization_id: uuid.UUID) -> EventLabels:
    raw = None
    try:
        columns = {col["name"] for col in inspect(db.get_bind()).get_columns("organizations")}
    except Exception:
        columns = set()
    if "contract_event_labels" in columns:
        found = db.execute(
            text("select contract_event_labels from organizations where id = :id"),
            {"id": str(organization_id)},
        ).first()
        raw = found[0] if found else None
        if isinstance(raw, str):
            import json

            raw = json.loads(raw) if raw else None
    return labels_from_json(raw)


def compile_close_month(db: Session, organization_id: uuid.UUID, period: str) -> dict[str, Any]:
    """Write this month's schedules and return what the close screen reads.

    A failure leaves the loaded files untouched and returns an empty result.
    """
    month = str(period or "")[:7]
    empty: dict[str, Any] = {"bookings": None, "deferred": None, "wrote": False}
    if len(month) != 7 or month[4] != "-":
        return empty
    try:
        result = _compile(db, organization_id, month)
        if result.get("wrote"):
            db.commit()
        return result
    except Exception:
        logger.exception("close schedules were not compiled for %s", month)
        db.rollback()
        return empty


def _compile(db: Session, organization_id: uuid.UUID, period: str) -> dict[str, Any]:
    labels = load_event_labels(db, organization_id)
    org = str(organization_id)
    wrote = False
    opportunities = _opportunities(db, org, period)
    bookings, opportunity_lines = bookings_and_movements(opportunities, labels)
    bookings_value: Decimal | None = bookings if opportunities else None

    book = arr_from_subscription_book(_subscriptions(db, org, period), opportunities, period, labels)
    history: list[dict[str, Any]] = []
    arr_lines = opportunity_lines
    beginning: Decimal | None = None
    source = "opportunities"
    replace_loaded = False
    if book is not None and book["tied"]:
        arr_lines = book["lines"]
        beginning = book["beginning"]
        source = "subscriptions"
        replace_loaded = True
    elif book is None:
        history = _history(db, org, period)
        if history:
            history_beginning, arr_lines = movements_from_history(history, labels)
            beginning = history_beginning
            source = "customer_arr_history"
        if beginning is None and (history or opportunities):
            beginning = _prior_ending(db, org, prior_period(period))
    if beginning is not None and (replace_loaded or ((history or opportunities) and not _customer_loaded(db, ARR_TABLE, org, period))):
        rolled = rollup_arr(beginning, arr_lines)
        grr, nrr = retention(beginning, arr_lines)
        values = {
            "version": "Actual",
            "beginning_arr": money(rolled["beginning"]),
            "new_business_arr": money(rolled["new"]),
            "expansion_arr": money(rolled["expansion"]),
            "contraction_arr": money(rolled["contraction"]),
            "churn_arr": money(rolled["churn"]),
            "reactivation_arr": money(rolled["reactivation"]),
            "renewal_arr": money(rolled["renewal"]),
            "net_new_arr": money(rolled["net_new"]),
            "ending_arr": money(rolled["ending"]),
            "waterfall_check": "0.00",
            "new_logo_arr": money(rolled["new"]),
            "winback_arr": "0.00",
            "first_year_expansion_arr": "0.00",
            "first_year_contraction_arr": "0.00",
            "no_start_arr": "0.00",
            "new_business_bucket_arr": money(rolled["new"]),
            "customer_success_beginning_arr": money(rolled["beginning"]),
            "customer_success_expansion_arr": money(rolled["expansion"]),
            "customer_success_contraction_arr": money(rolled["contraction"]),
            "customer_success_churn_arr": money(rolled["churn"]),
            "customer_success_reactivation_arr": money(rolled["reactivation"]),
        }
        if grr is not None and nrr is not None:
            values["gross_retention_rate"] = f"{grr.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP):.4f}"
            values["net_dollar_retention_rate"] = f"{nrr.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP):.4f}"
        wrote = (
            _write_summary(
                db,
                ARR_TABLE,
                org,
                period,
                values,
                f"{COMPILED_PREFIX}{source}:{period}",
                replace_existing=replace_loaded,
            )
            or wrote
        )

    costs = _ledger_costs(db, org, period)
    billings = _billings(db, org, period)
    collected = _collections(db, org, period)
    prior_deferred = _prior_deferred(db, org, prior_period(period))
    deferred: dict[str, float] | None = None
    if (billings is not None or costs is not None) and not _customer_loaded(db, DR_TABLE, org, period):
        rolled_dr = rollup_deferred(
            prior_deferred if prior_deferred is not None else Decimal("0"),
            billings or Decimal("0"),
            (costs or {}).get("recognized", Decimal("0")),
        )
        wrote = _write_summary(
            db,
            DR_TABLE,
            org,
            period,
            {
                "version": "Actual",
                "beginning_deferred_revenue": money(rolled_dr["beginning"]),
                "new_billings": money(rolled_dr["billings"]),
                "revenue_recognized": money(rolled_dr["recognized"]),
                "ending_deferred_revenue": money(rolled_dr["ending"]),
                "waterfall_check": "0.00",
            },
            f"{COMPILED_PREFIX}invoices:{period}",
        ) or wrote
        deferred = {key: float(value) for key, value in rolled_dr.items()}
    elif _customer_loaded(db, DR_TABLE, org, period):
        deferred = _read_deferred(db, org, period)

    if collected is not None and not _customer_loaded(db, COLLECTIONS_TABLE, org, period):
        wrote = _write_summary(
            db,
            COLLECTIONS_TABLE,
            org,
            period,
            {
                "version": "Actual",
                "cash_collections": money(collected),
                "driver": "Compiled from invoices collected in this month",
            },
            f"{COMPILED_PREFIX}invoices:{period}",
        ) or wrote

    cash = None
    nested = db.begin_nested()
    try:
        cash = _statement_cash(db, organization_id, period)
        nested.commit()
    except Exception:
        logger.warning("cash statement was not read for %s", period)
        nested.rollback()
        cash = None
    if (
        cash is not None
        and costs is not None
        and not _customer_loaded(db, BRIDGE_TABLE, org, period)
    ):
        collections = collected or Decimal("0")
        capex = -_dec(cash.get("capital_expenditures"))
        gap = unexplained_cash(
            _dec(cash.get("beginning_cash")),
            _dec(cash.get("ending_cash")),
            collections,
            costs["payroll"],
            costs["commission"],
            costs["vendor"],
            costs["tax"],
            costs["interest"],
            capex,
        )
        wrote = _write_summary(
            db,
            BRIDGE_TABLE,
            org,
            period,
            {
                "version": "Actual",
                "beginning_cash": money(_dec(cash.get("beginning_cash"))),
                "ending_cash": money(_dec(cash.get("ending_cash"))),
                "cash_collections": money(collections),
                "collections": money(collections),
                "cash_collections_from_invoices": money(collections),
                "payroll_cash_out": money(costs["payroll"]),
                "commission_cash_out": money(costs["commission"]),
                "vendor_cash_out_n30": money(costs["vendor"]),
                "tax_cash_out": money(costs["tax"]),
                "interest_cash_out": money(costs["interest"]),
                "capex": money(capex),
                "financing_to_maintain_cash_floor": "0.00",
                "financing": "0.00",
                # Named lines only — never plug the residual into "other operating".
                "other_operating_cash_out": "0.00",
                "bridge_check": money(gap),
                "notes": (
                    "Compiled from invoices and the ledger. "
                    "bridge_check is cash the measured lines do not explain."
                    if gap
                    else "Compiled from invoices and the ledger."
                ),
            },
            f"{COMPILED_PREFIX}ledger:{period}",
        ) or wrote

    return {
        "bookings": float(bookings_value) if bookings_value is not None else None,
        "deferred": deferred,
        "wrote": wrote,
    }


def _opportunities(db: Session, org: str, period: str) -> list[dict[str, Any]]:
    if not table_exists(db, "actual_opportunities"):
        return []
    rows = db.execute(
        text(
            """
            select customer_id, opportunity_type, waterfall_type, pipeline_movement_type, close_status, amount_arr
            from actual_opportunities
            where organization_id = :org and left(cast(period as text), 7) = :period
            """
        ),
        {"org": org, "period": period},
    ).mappings()
    return [dict(row) for row in rows]


def _subscriptions(db: Session, org: str, period: str) -> list[dict[str, Any]]:
    year_text, month_text = period.split("-", 1)
    year, month = int(year_text), int(month_text)
    start = date(year, month, 1).isoformat()
    end = date(year, month, calendar.monthrange(year, month)[1]).isoformat()
    if table_exists(db, "actual_subscriptions"):
        rows = db.execute(
            text(
                """
                select customer_id,
                       contract_start_date as start_date,
                       contract_end_date as end_date,
                       current_arr
                from actual_subscriptions
                where organization_id = :org
                  and contract_start_date <= :end
                  and (contract_end_date is null or contract_end_date = '' or contract_end_date >= :start)
                """
            ),
            {"org": org, "start": start, "end": end},
        ).mappings()
        found = [dict(row) for row in rows]
        if found:
            return found
    if not table_exists(db, "subscriptions"):
        return []
    rows = db.execute(
        text(
            """
            select customer_id, start_date, end_date, current_arr
            from subscriptions
            where organization_id = :org
              and start_date <= :end
              and (end_date is null or end_date >= :start)
            """
        ),
        {"org": org, "start": start, "end": end},
    ).mappings()
    return [dict(row) for row in rows]


def _history(db: Session, org: str, period: str) -> list[dict[str, Any]]:
    if not table_exists(db, "actual_customer_arr_history"):
        return []
    rows = db.execute(
        text(
            """
            select movement_type, waterfall_line, beginning_arr, movement_arr
            from actual_customer_arr_history
            where organization_id = :org and left(cast(period as text), 7) = :period
            """
        ),
        {"org": org, "period": period},
    ).mappings()
    return [dict(row) for row in rows]


def _prior_ending(db: Session, org: str, period: str) -> Decimal | None:
    if not table_exists(db, ARR_TABLE):
        return None
    found = db.execute(
        text(
            """
            select ending_arr
            from actual_mrr_waterfall
            where organization_id = :org and left(cast(period as text), 7) = :period
            limit 1
            """
        ),
        {"org": org, "period": period},
    ).first()
    if found is None or found[0] in (None, ""):
        return None
    return _dec(found[0])


def _billings(db: Session, org: str, period: str) -> Decimal | None:
    if table_exists(db, "actual_invoice_billing_schedule"):
        found = db.execute(
            text(
                """
                select coalesce(sum(cast(billings as numeric)), 0), count(*)
                from actual_invoice_billing_schedule
                where organization_id = :org and left(cast(period as text), 7) = :period
                """
            ),
            {"org": org, "period": period},
        ).first()
        if found and int(found[1] or 0) > 0:
            return _dec(found[0])
    if not table_exists(db, "actual_invoices"):
        return None
    found = db.execute(
        text(
            """
            select coalesce(sum(cast(invoice_amount as numeric)), 0), count(*)
            from actual_invoices
            where organization_id = :org and left(cast(invoice_period as text), 7) = :period
            """
        ),
        {"org": org, "period": period},
    ).first()
    if found is None or int(found[1] or 0) == 0:
        return None
    return _dec(found[0])


def _collections(db: Session, org: str, period: str) -> Decimal | None:
    if not table_exists(db, "actual_invoice_billing_schedule"):
        return None
    found = db.execute(
        text(
            """
            select coalesce(sum(cast(billings as numeric)), 0), count(*)
            from actual_invoice_billing_schedule
            where organization_id = :org
              and left(cast(collection_period as text), 7) = :period
            """
        ),
        {"org": org, "period": period},
    ).first()
    if found is None:
        return None
    present = db.execute(
        text("select 1 from actual_invoice_billing_schedule where organization_id = :org limit 1"),
        {"org": org},
    ).first()
    if present is None:
        return None
    return _dec(found[0])


def _prior_deferred(db: Session, org: str, period: str) -> Decimal | None:
    if not table_exists(db, DR_TABLE):
        return None
    found = db.execute(
        text(
            """
            select ending_deferred_revenue
            from actual_deferred_revenue_waterfall
            where organization_id = :org and left(cast(period as text), 7) = :period
            limit 1
            """
        ),
        {"org": org, "period": period},
    ).first()
    if found is None or found[0] in (None, ""):
        return None
    return _dec(found[0])


def _ledger_costs(db: Session, org: str, period: str) -> dict[str, Decimal] | None:
    if not table_exists(db, "gl_actuals"):
        return None
    rows = db.execute(
        text(
            f"""
            select coalesce(account_number, ''), coalesce(account_group, ''),
                   coalesce(account_name, ''), sum(cast(amount as numeric))
            from gl_actuals
            where organization_id = :org
              and lower(version) = 'actual'
              and to_char(period, 'YYYY-MM') = :period
              and {ONE_BOOK_SQL}
            group by 1, 2, 3
            """
        ),
        {"org": org, "period": period},
    ).all()
    if not rows:
        return None
    from app.services.reporting.account_maps import load_account_maps
    import uuid as _uuid

    try:
        org_id = _uuid.UUID(str(org))
    except ValueError:
        org_id = None
    maps = load_account_maps(db, org_id) if org_id is not None else {}
    return cash_costs(
        [(str(group), str(name), amount) for _acct, group, name, amount in rows],
        account_maps=maps,
        account_numbers=[str(acct) for acct, _group, _name, _amount in rows],
    )


def _statement_cash(db: Session, organization_id: uuid.UUID, period: str) -> dict[str, Any] | None:
    from app.services.reporting.gl_balance_sheet import gl_balance_sheet_and_cash_flow_by_period

    _, cash_flow = gl_balance_sheet_and_cash_flow_by_period(db, organization_id, "actual")
    row = cash_flow.get(period)
    if not row or row.get("ending_cash") is None:
        return None
    return row


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


def _read_deferred(db: Session, org: str, period: str) -> dict[str, float] | None:
    found = db.execute(
        text(
            """
            select beginning_deferred_revenue, new_billings, revenue_recognized, ending_deferred_revenue
            from actual_deferred_revenue_waterfall
            where organization_id = :org and left(cast(period as text), 7) = :period
            limit 1
            """
        ),
        {"org": org, "period": period},
    ).first()
    if found is None:
        return None
    beginning, billings, recognized, ending = found
    return {
        "beginning": float(_dec(beginning)),
        "billings": float(_dec(billings)),
        "recognized": float(_dec(recognized)),
        "ending": float(_dec(ending)),
    }


def _write_summary(
    db: Session,
    table: str,
    org: str,
    period: str,
    values: dict[str, str],
    filename: str,
    replace_existing: bool = False,
) -> bool:
    if not table_exists(db, table):
        return False
    columns = {
        str(name)
        for (name,) in db.execute(
            text(
                """
                select column_name
                from information_schema.columns
                where table_schema = 'public' and table_name = :table
                """
            ),
            {"table": table},
        ).all()
    }
    if "period" not in columns:
        return False
    db.execute(
        text(
            f"""
            delete from "{table}"
            where organization_id = :org
              and left(cast(period as text), 7) = :period
              and (
                :replace_existing
                or coalesce(source_filename, '') like 'compiled:%'
                or coalesce(source_filename, '') like 'Compiled · %'
              )
            """
        ),
        {
            "org": org,
            "period": period,
            "replace_existing": replace_existing,
        },
    )
    nxt = db.execute(
        text(f'select coalesce(max(source_row_number), 0) + 1 from "{table}" where organization_id = :org'),
        {"org": org},
    ).scalar()
    payload: dict[str, Any] = {
        "organization_id": org,
        "source_row_number": int(nxt or 1),
        "source_filename": filename,
        "period": f"{period}-01",
    }
    payload.update(values)
    used = [key for key in payload if key in columns or key in {"organization_id", "source_row_number", "source_filename"}]
    names = ", ".join(f'"{key}"' for key in used)
    marks = ", ".join(f":{key}" for key in used)
    db.execute(
        text(f'insert into "{table}" ({names}) values ({marks})'),
        {key: payload[key] for key in used},
    )
    return True
