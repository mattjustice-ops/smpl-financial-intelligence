"""Compile close flux-event grain from GL detail for commentary.

OpEx and CoR writers share one statement-agnostic table. BS writers can land
later without a rebuild.
"""

from __future__ import annotations

import logging
import re
import uuid
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.dashboard.query_utils import table_exists
from app.services.reporting.gl_income_statement import classify_gl_line
from app.services.reporting.gl_one_book import ONE_BOOK_SQL
from app.services.reporting.period_utils import prior_period, to_period

logger = logging.getLogger(__name__)

FLUX_TABLE = "actual_close_flux_events"
COMPILED_PREFIX = "compiled:"
MATERIALITY = Decimal("10000")
CENT = Decimal("0.01")
OPEX_LINES = frozenset({"sm", "rd", "ga", "unmapped"})
COGS_LINES = frozenset({"cogs"})
PAYROLL_RE = re.compile(
    r"salary|salaries|wage|payroll|bonus|commission|benefits|pto|severance",
    re.IGNORECASE,
)


def money(value: Decimal | float | int | None) -> str:
    if value is None:
        return "0.00"
    return str(Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP))


def _dec(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


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


def _customer_loaded(db: Session, org: str, period: str, section: str) -> bool:
    if not table_exists(db, FLUX_TABLE):
        return False
    found = db.execute(
        text(
            f"""
            select 1
            from "{FLUX_TABLE}"
            where organization_id = :org
              and left(cast(period as text), 7) = :period
              and section = :section
              and coalesce(source_filename, '') not like 'compiled:%'
              and coalesce(source_filename, '') not like 'Compiled · %'
            limit 1
            """
        ),
        {"org": org, "period": period, "section": section},
    ).first()
    return found is not None


def flux_status_by_period(
    db: Session, organization_id: uuid.UUID, periods: list[str]
) -> dict[str, dict[str, Any]]:
    """Row counts and source for flux events by period."""
    org = str(organization_id)
    out: dict[str, dict[str, Any]] = {}
    if not periods or not table_exists(db, FLUX_TABLE):
        return out
    rows = db.execute(
        text(
            f"""
            select left(cast(period as text), 7) as period,
                   count(*)::int as row_count,
                   bool_or(
                     coalesce(source_filename, '') not like 'compiled:%'
                     and coalesce(source_filename, '') not like 'Compiled · %'
                   ) as has_customer,
                   bool_or(
                     coalesce(source_filename, '') like 'compiled:%'
                     or coalesce(source_filename, '') like 'Compiled · %'
                   ) as has_compiled
            from "{FLUX_TABLE}"
            where organization_id = :org
              and left(cast(period as text), 7) = any(:periods)
            group by 1
            """
        ),
        {"org": org, "periods": list(periods)},
    ).all()
    for period, row_count, has_customer, has_compiled in rows:
        source = "customer" if has_customer else ("compiled" if has_compiled else "none")
        out[str(period)] = {"rows": int(row_count or 0), "source": source}
    return out


def load_flux_events(
    db: Session,
    organization_id: uuid.UUID,
    period: str,
    *,
    section: str | None = None,
    account_numbers: set[str] | None = None,
) -> list[dict[str, Any]]:
    if not table_exists(db, FLUX_TABLE):
        return []
    clauses = [
        "organization_id = :org",
        "left(cast(period as text), 7) = :period",
    ]
    params: dict[str, Any] = {"org": str(organization_id), "period": to_period(period)}
    if section:
        clauses.append("section = :section")
        params["section"] = section
    sql = f"""
        select section, account_number, account_name, event_kind, counterparty,
               counterparty_id, department, tag, amount, prior_amount,
               tx_count, prior_tx_count, is_credit
        from "{FLUX_TABLE}"
        where {" and ".join(clauses)}
        order by abs(cast(coalesce(nullif(amount, ''), '0') as numeric)) desc,
                 coalesce(counterparty, ''), coalesce(account_number, '')
    """
    rows = [dict(row) for row in db.execute(text(sql), params).mappings()]
    if account_numbers is not None:
        wanted = {str(a).strip() for a in account_numbers if str(a).strip()}
        if wanted:
            rows = [
                row
                for row in rows
                if str(row.get("account_number") or "").strip() in wanted
                or not str(row.get("account_number") or "").strip()
            ]
    return rows


def brief_flux_for_rollup(
    rows: list[dict[str, Any]],
    *,
    materiality: float = float(MATERIALITY),
) -> list[dict[str, Any]]:
    """One named counterparty per account (largest), with others count — revenue-events shape."""
    by_account: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        amount = abs(_dec(row.get("amount")))
        if amount < Decimal(str(materiality)) and abs(_dec(row.get("prior_amount"))) < Decimal(str(materiality)):
            continue
        account = str(row.get("account_number") or "").strip() or str(row.get("account_name") or "").strip()
        if not account:
            continue
        by_account[account].append(row)

    events: list[dict[str, Any]] = []
    for account, items in by_account.items():
        ordered = sorted(items, key=lambda item: (-abs(_dec(item.get("amount"))), str(item.get("counterparty") or "")))
        named = ordered[0]
        rest = ordered[1:]
        counterparty = str(named.get("counterparty") or "").strip() or str(named.get("department") or "Activity")
        kind = str(named.get("event_kind") or "vendor_spend")
        bucket = {
            "vendor_spend": "Vendor",
            "payroll_batch": "Payroll",
            "credit_reversal": "Credit",
        }.get(kind, kind.replace("_", " ").title())
        account_label = " ".join(
            part
            for part in (
                str(named.get("account_number") or "").strip(),
                str(named.get("account_name") or "").strip(),
            )
            if part
        )
        events.append(
            {
                "bucket": bucket,
                "customer": counterparty,
                "amount": float(abs(_dec(named.get("amount")))),
                "others": len(rest),
                "others_amount": float(sum(abs(_dec(item.get("amount"))) for item in rest)),
                "outcome": "occurred",
                "account_number": str(named.get("account_number") or ""),
                "account_label": account_label,
                "department": str(named.get("department") or ""),
                "event_kind": kind,
                "tag": str(named.get("tag") or ""),
                "prior_amount": float(abs(_dec(named.get("prior_amount")))),
                "tx_count": int(_dec(named.get("tx_count"))),
                "prior_tx_count": int(_dec(named.get("prior_tx_count"))),
            }
        )
    return events


def compile_opex_flux_events(
    db: Session,
    organization_id: uuid.UUID,
    period: str,
) -> bool:
    """Write OpEx flux rows for ``period`` when the customer did not upload them."""
    return _compile_section_flux(
        db,
        organization_id,
        period,
        section="opex",
        lines=OPEX_LINES,
    )


def compile_cogs_flux_events(
    db: Session,
    organization_id: uuid.UUID,
    period: str,
) -> bool:
    """Write CoR / cogs flux rows for ``period`` when the customer did not upload them."""
    return _compile_section_flux(
        db,
        organization_id,
        period,
        section="cogs",
        lines=COGS_LINES,
        stamp_usage_tags=True,
    )


def compile_close_flux_events(
    db: Session,
    organization_id: uuid.UUID,
    period: str,
) -> bool:
    """Compile every flux section writer that is live for Table Update."""
    wrote = compile_opex_flux_events(db, organization_id, period)
    wrote = compile_cogs_flux_events(db, organization_id, period) or wrote
    return wrote


def _compile_section_flux(
    db: Session,
    organization_id: uuid.UUID,
    period: str,
    *,
    section: str,
    lines: frozenset[str],
    stamp_usage_tags: bool = False,
) -> bool:
    org = str(organization_id)
    period = to_period(period)
    if not table_exists(db, FLUX_TABLE) or not table_exists(db, "gl_actuals"):
        return False
    if _customer_loaded(db, org, period, section):
        return False

    prior = prior_period(period)
    current_rows = _gl_activity(db, org, period, lines=lines)
    prior_rows = _gl_activity(db, org, prior, lines=lines)
    if not current_rows and not prior_rows:
        return False

    usage_tags: dict[tuple[str, str], str] = {}
    if stamp_usage_tags:
        usage_tags = _usage_tags_by_account_vendor(db, org, period)

    current = _index_activity(current_rows)
    previous = _index_activity(prior_rows)
    keys = set(current) | set(previous)
    candidates: list[tuple[tuple[str, str, str, str, str], dict[str, Any]]] = []
    for key in keys:
        cur = current.get(key) or {"amount": Decimal("0"), "tx_count": 0}
        prev = previous.get(key) or {"amount": Decimal("0"), "tx_count": 0}
        amount = cur["amount"]
        prior_amount = prev["amount"]
        account_number, account_name, counterparty, department, counterparty_id = key
        tag = usage_tags.get((account_number, counterparty.casefold()), "") if stamp_usage_tags else ""
        candidates.append(
            (
                key,
                {
                    "section": section,
                    "account_number": account_number,
                    "account_name": account_name,
                    "event_kind": _event_kind(account_name, amount),
                    "counterparty": counterparty or department,
                    "counterparty_id": counterparty_id,
                    "department": department,
                    "tag": tag,
                    "amount": money(amount),
                    "prior_amount": money(prior_amount),
                    "tx_count": str(int(cur["tx_count"])),
                    "prior_tx_count": str(int(prev["tx_count"])),
                    "is_credit": "true" if amount < 0 else "false",
                    "_amount": amount,
                    "_prior_amount": prior_amount,
                },
            )
        )
    out = _apply_materiality(candidates)
    if not out:
        return False
    return _replace_compiled(db, org, period, section, out, f"{COMPILED_PREFIX}flux:{period}:{section}")


def _usage_tags_by_account_vendor(db: Session, org: str, period: str) -> dict[tuple[str, str], str]:
    """Optional service/driver (or commit) labels from actual_vendor_usage — facts only."""
    if not table_exists(db, "actual_vendor_usage"):
        return {}
    columns = _table_columns(db, "actual_vendor_usage")
    if "period" not in columns or "account_number" not in columns:
        return {}
    select = [
        "coalesce(nullif(trim(cast(account_number as text)), ''), '') as account_number",
        "coalesce(nullif(trim(cast(vendor_name as text)), ''), '') as vendor_name",
    ]
    if "service" in columns:
        select.append("coalesce(nullif(trim(cast(service as text)), ''), '') as service")
    else:
        select.append("'' as service")
    if "driver" in columns:
        select.append("coalesce(nullif(trim(cast(driver as text)), ''), '') as driver")
    else:
        select.append("'' as driver")
    if "minimum_commit" in columns:
        select.append("minimum_commit")
    else:
        select.append("null as minimum_commit")
    if "actual_usage" in columns:
        select.append("actual_usage")
    else:
        select.append("null as actual_usage")
    sql = f"""
        select {", ".join(select)}
        from actual_vendor_usage
        where organization_id = :org
          and left(to_char(cast(period as date), 'YYYY-MM'), 7) = :period
    """
    try:
        rows = [dict(row) for row in db.execute(text(sql), {"org": org, "period": period}).mappings()]
    except Exception:
        # Some warehouses store period as text YYYY-MM; retry without cast(date).
        sql_text = f"""
            select {", ".join(select)}
            from actual_vendor_usage
            where organization_id = :org
              and left(cast(period as text), 7) = :period
        """
        try:
            rows = [dict(row) for row in db.execute(text(sql_text), {"org": org, "period": period}).mappings()]
        except Exception:
            logger.exception("vendor usage tags were not loaded for %s", period)
            return {}
    out: dict[tuple[str, str], str] = {}
    for row in rows:
        account = str(row.get("account_number") or "").strip()
        vendor = str(row.get("vendor_name") or "").strip()
        if not account or not vendor:
            continue
        service = str(row.get("service") or "").strip()
        driver = str(row.get("driver") or "").strip()
        parts: list[str] = []
        if service and driver:
            parts.append(f"{service} — {driver}")
        elif service or driver:
            parts.append(service or driver)
        commit = row.get("minimum_commit")
        usage = row.get("actual_usage")
        if commit not in (None, ""):
            parts.append(f"commit {commit}")
        if usage not in (None, "") and usage != commit:
            parts.append(f"usage {usage}")
        if not parts:
            continue
        out[(account, vendor.casefold())] = "; ".join(parts)[:240]
    return out


def _apply_materiality(
    candidates: list[tuple[tuple[str, str, str, str, str], dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Keep $10k+ rows; keep a sole under-threshold driver per account."""
    material_accounts: set[str] = set()
    kept: list[dict[str, Any]] = []
    under: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for key, row in candidates:
        account = key[0] or key[1] or ""
        amount = abs(_dec(row.get("_amount")))
        prior_amount = abs(_dec(row.get("_prior_amount")))
        delta = abs(_dec(row.get("_amount")) - _dec(row.get("_prior_amount")))
        clean = {k: v for k, v in row.items() if not str(k).startswith("_")}
        if amount >= MATERIALITY or prior_amount >= MATERIALITY or delta >= MATERIALITY:
            kept.append(clean)
            material_accounts.add(account)
        else:
            under[account].append(row)
    for account, rows in under.items():
        if account in material_accounts or not rows:
            continue
        best = max(
            rows,
            key=lambda item: (
                abs(_dec(item.get("_amount")) - _dec(item.get("_prior_amount"))),
                abs(_dec(item.get("_amount"))),
            ),
        )
        if abs(_dec(best.get("_amount"))) <= 0 and abs(_dec(best.get("_prior_amount"))) <= 0:
            continue
        kept.append({k: v for k, v in best.items() if not str(k).startswith("_")})
    return kept


def _event_kind(account_name: str, amount: Decimal) -> str:
    if PAYROLL_RE.search(account_name or ""):
        return "payroll_batch"
    if amount < 0:
        return "credit_reversal"
    return "vendor_spend"


def _gl_activity(
    db: Session,
    org: str,
    period: str,
    *,
    lines: frozenset[str],
) -> list[dict[str, Any]]:
    columns = _table_columns(db, "gl_actuals")
    if "period" not in columns or "amount" not in columns:
        return []
    vendor_expr = (
        "coalesce(nullif(trim(cast(vendor_name as text)), ''), '')"
        if "vendor_name" in columns
        else "''"
    )
    vendor_id_expr = (
        "coalesce(nullif(trim(cast(vendor_id as text)), ''), '')"
        if "vendor_id" in columns
        else "''"
    )
    notes_expr = (
        "coalesce(nullif(trim(cast(notes as text)), ''), '')" if "notes" in columns else "''"
    )
    sql = f"""
        select to_char(period, 'YYYY-MM') as period,
               statement, statement_category, category, account_group, expense_type,
               coalesce(nullif(trim(cast(account_number as text)), ''), '') as account_number,
               coalesce(nullif(trim(cast(account_name as text)), ''), '') as account_name,
               coalesce(nullif(trim(cast(department as text)), ''), '') as department,
               {vendor_expr} as vendor_name,
               {vendor_id_expr} as vendor_id,
               {notes_expr} as notes,
               sum(amount) as amount,
               count(*)::int as tx_count
        from gl_actuals
        where organization_id = :org
          and lower(version) = 'actual'
          and left(to_char(period, 'YYYY-MM'), 7) = :period
          and {ONE_BOOK_SQL}
        group by 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
    """
    raw = [dict(row) for row in db.execute(text(sql), {"org": org, "period": period}).mappings()]
    from app.services.reporting.account_maps import load_account_maps, stamp_account_maps

    stamp_account_maps(raw, load_account_maps(db, uuid.UUID(org)))
    out: list[dict[str, Any]] = []
    for row in raw:
        line = classify_gl_line(row)
        if line not in lines:
            continue
        out.append(row)
    return out


def _index_activity(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str, str, str], dict[str, Any]]:
    indexed: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        key = (
            str(row.get("account_number") or "").strip(),
            str(row.get("account_name") or "").strip(),
            str(row.get("vendor_name") or "").strip(),
            str(row.get("department") or "").strip(),
            str(row.get("vendor_id") or "").strip(),
        )
        slot = indexed.setdefault(key, {"amount": Decimal("0"), "tx_count": 0})
        slot["amount"] += _dec(row.get("amount"))
        slot["tx_count"] += int(row.get("tx_count") or 0)
    return indexed


def _replace_compiled(
    db: Session,
    org: str,
    period: str,
    section: str,
    rows: list[dict[str, Any]],
    filename: str,
) -> bool:
    columns = _table_columns(db, FLUX_TABLE)
    required = {"period", "section", "event_kind"}
    if not required.issubset(columns):
        return False
    db.execute(
        text(
            f"""
            delete from "{FLUX_TABLE}"
            where organization_id = :org
              and left(cast(period as text), 7) = :period
              and section = :section
              and (
                coalesce(source_filename, '') like 'compiled:%'
                or coalesce(source_filename, '') like 'Compiled · %'
              )
            """
        ),
        {"org": org, "period": period, "section": section},
    )
    nxt = db.execute(
        text(
            f'select coalesce(max(source_row_number), 0) + 1 from "{FLUX_TABLE}" '
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
            "version": "Actual",
            "period": f"{period}-01",
            "section": section,
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
            text(f'insert into "{FLUX_TABLE}" ({names}) values ({marks})'),
            {key: payload[key] for key in used},
        )
    return True
