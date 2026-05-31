"""Load, sync, and aggregate Forecast_gl_detail.csv rows."""

from __future__ import annotations

import re
import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.demo_finance import ForecastGlDetail, GlActual
from app.services.financial_statements.financial_statement_service import parse_period, table_exists
from app.services.reporting.period_utils import to_period

_OPEX_IS_KEYS = frozenset(
    {
        "sales_and_marketing",
        "research_and_development",
        "general_and_administrative",
        "customer_success",
    }
)

GL_WAREHOUSE_TABLE_NAMES: tuple[str, ...] = ("gl_actuals", "forecast_gl_detail")


def ensure_gl_warehouse_tables(session: Session) -> list[str]:
    """Create GL mart tables when Alembic migrations were not applied locally."""
    import app.models  # noqa: F401 — register ORM metadata
    from app.db.base import Base
    from app.db.session import engine

    created: list[str] = []
    for name in GL_WAREHOUSE_TABLE_NAMES:
        if table_exists(session, name):
            continue
        table = Base.metadata.tables.get(name)
        if table is None:
            continue
        try:
            # Use the shared engine so DDL commits outside the upload transaction.
            table.create(engine, checkfirst=True)
        except Exception:
            continue
        if table_exists(session, name):
            created.append(name)
    return created


def _upsert_rows(session: Session, model: type[Any], batch: list[dict[str, Any]], *, chunk_size: int = 500) -> None:
    if not batch:
        return
    table = model.__table__
    pk_cols = [c.name for c in table.primary_key.columns]
    for i in range(0, len(batch), chunk_size):
        chunk = batch[i : i + chunk_size]
        stmt = pg_insert(model).values(chunk)
        excluded = stmt.excluded
        upd: dict[str, Any] = {}
        for col in table.columns:
            if col.name in pk_cols or col.name == "created_at":
                continue
            upd[col.name] = getattr(excluded, col.name)
        upd["updated_at"] = func.now()
        session.execute(stmt.on_conflict_do_update(index_elements=pk_cols, set_=upd))


_STATEMENT_TO_IS_KEY: dict[str, str] = {
    "revenue": "revenue",
    "cost of revenue": "cost_of_revenue",
    "sales and marketing": "sales_and_marketing",
    "research and development": "research_and_development",
    "general and administrative": "general_and_administrative",
    "customer success": "customer_success",
}


def _parse_gl_account(gl_account: str) -> tuple[str, str]:
    raw = (gl_account or "").strip()
    match = re.match(r"^(\d+)\s+(.*)$", raw)
    if match:
        return match.group(1), match.group(2).strip()
    if raw.isdigit():
        return raw, raw
    return raw[:64] or "0", raw or "Unknown"


def _signed_forecast_amount(*, line_type: str | None, amount: Decimal) -> Decimal:
    if line_type and line_type.lower() == "revenue":
        return abs(amount)
    if line_type and line_type.lower() == "expense":
        return -abs(amount)
    return amount


def _management_include(raw: dict[str, Any]) -> bool:
    flag = str(raw.get("management_view_include") or "Yes").strip().lower()
    return flag in {"yes", "y", "true", "1"}


def _row_index_key(row: dict[str, Any], *, idx: int) -> str:
    period = row.get("period")
    ps = period.strftime("%Y-%m") if hasattr(period, "strftime") else str(period)[:7]
    acct_num, _ = _parse_gl_account(str(row.get("gl_account") or ""))
    return (
        f"{ps}:{acct_num}:{row.get('department') or ''}:{row.get('account_group') or ''}:"
        f"{row.get('expense_type') or ''}:{row.get('sub_department') or ''}:{idx}"
    )


def forecast_gl_payload_to_gl_actuals(
    organization_id: uuid.UUID,
    row: dict[str, Any],
    *,
    row_index: int,
) -> dict[str, Any]:
    acct_num, acct_name = _parse_gl_account(str(row.get("gl_account") or ""))
    period = row.get("period")
    if isinstance(period, str):
        period = parse_period(period)
    amount = row.get("forecast_amount")
    if amount is None:
        amount = Decimal("0")
    elif not isinstance(amount, Decimal):
        amount = Decimal(str(amount))

    return {
        "organization_id": organization_id,
        "version": str(row.get("scenario") or row.get("version") or "Forecast"),
        "period": period,
        "account_number": acct_num,
        "account_name": acct_name,
        "statement": row.get("statement_category"),
        "category": row.get("statement_category"),
        "statement_category": row.get("statement_category"),
        "account_group": row.get("account_group"),
        "expense_type": row.get("expense_type"),
        "department": str(row.get("department") or ""),
        "cost_center": str(row.get("cost_center") or ""),
        "sub_department": str(row.get("sub_department") or ""),
        "vendor_id": "",
        "vendor_name": None,
        "source_file": str(row.get("source") or "Forecast_gl_detail.csv"),
        "source_record_id": _row_index_key(row, idx=row_index),
        "amount": _signed_forecast_amount(line_type=str(row.get("line_type")), amount=amount),
        "currency": "USD",
        "subsidiary": "",
        "source_system": "forecast_gl_detail",
        "notes": row.get("notes"),
    }


def sync_forecast_gl_detail_to_gl_actuals(
    session: Session,
    organization_id: uuid.UUID,
    rows: list[dict[str, Any]],
) -> int:
    """Upsert Forecast GL lines into gl_actuals (version Forecast) for dashboards."""
    if not table_exists(session, "gl_actuals"):
        ensure_gl_warehouse_tables(session)
    if not table_exists(session, "gl_actuals"):
        return 0

    payloads: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        if not _management_include(row):
            continue
        period = row.get("period")
        if period is None:
            continue
        payloads.append(forecast_gl_payload_to_gl_actuals(organization_id, row, row_index=idx))

    if not payloads:
        return 0

    try:
        with session.begin_nested():
            session.execute(
                delete(GlActual).where(
                    GlActual.organization_id == organization_id,
                    GlActual.version == "Forecast",
                    GlActual.source_system == "forecast_gl_detail",
                )
            )
            _upsert_rows(session, GlActual, payloads)
    except Exception:
        return 0

    return len(payloads)


def forecast_gl_rows_as_gl_raw(session: Session, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    """Return forecast_gl_detail ORM rows as dicts compatible with management GL classification."""
    if not table_exists(session, "forecast_gl_detail"):
        return []
    out: list[dict[str, Any]] = []
    for row in session.scalars(
        select(ForecastGlDetail).where(ForecastGlDetail.organization_id == organization_id)
    ).all():
        if not _management_include(
            {
                "management_view_include": row.management_view_include,
            }
        ):
            continue
        out.append(
            {
                "period": row.period,
                "version": row.scenario,
                "scenario": row.scenario,
                "line_type": row.line_type,
                "statement_category": row.statement_category,
                "department": row.department,
                "sub_department": row.sub_department,
                "account_group": row.account_group,
                "expense_type": row.expense_type,
                "gl_account": row.gl_account,
                "forecast_amount": row.forecast_amount,
                "management_view_include": row.management_view_include,
                "sbc_flag": row.sbc_flag,
                "one_time_flag": row.one_time_flag,
                "non_cash_flag": row.non_cash_flag,
                "source": row.source,
                "notes": row.notes,
                "amount": _signed_forecast_amount(
                    line_type=row.line_type,
                    amount=row.forecast_amount or Decimal("0"),
                ),
                "account_name": _parse_gl_account(row.gl_account)[1],
                "account_number": _parse_gl_account(row.gl_account)[0],
                "category": row.statement_category,
            }
        )
    return out


def aggregate_forecast_gl_to_income_maps(
    session: Session,
    organization_id: uuid.UUID,
    *,
    start: date,
    end: date,
) -> dict[str, dict[str, Decimal]]:
    """Build per-period income statement totals from forecast_gl_detail when IS mart is empty."""
    if not table_exists(session, "forecast_gl_detail"):
        return {}
    out: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
    for row in session.scalars(
        select(ForecastGlDetail).where(ForecastGlDetail.organization_id == organization_id)
    ).all():
        if not _management_include({"management_view_include": row.management_view_include}):
            continue
        period = parse_period(row.period)
        if period is None or period < start or period > end:
            continue
        ps = to_period(period)
        key = _STATEMENT_TO_IS_KEY.get((row.statement_category or "").strip().lower())
        if not key:
            continue
        amt = _signed_forecast_amount(
            line_type=row.line_type,
            amount=row.forecast_amount or Decimal("0"),
        )
        if key == "revenue":
            out[ps][key] += abs(amt)
        else:
            out[ps][key] += abs(amt)
        if key in _OPEX_IS_KEYS:
            out[ps]["total_opex"] += abs(amt)
    for ps, metrics in out.items():
        rev = metrics.get("revenue", Decimal("0"))
        cogs = metrics.get("cost_of_revenue", Decimal("0"))
        opex = metrics.get("total_opex", Decimal("0"))
        metrics["gross_profit"] = rev - cogs
        metrics["ebitda"] = metrics["gross_profit"] - opex
    return {p: dict(v) for p, v in out.items()}


def migrate_physical_forecast_gl_table(session: Session, organization_id: uuid.UUID) -> int:
    """One-time import from legacy text-only forecast_gl_detail landing table, if present."""
    if not table_exists(session, "forecast_gl_detail"):
        return 0
    col_rows = session.execute(
        text(
            """
            select column_name, data_type
            from information_schema.columns
            where table_schema = 'public' and table_name = 'forecast_gl_detail'
            """
        )
    ).mappings()
    columns = {str(r["column_name"]): str(r["data_type"]).lower() for r in col_rows}
    if "forecast_amount" in columns and columns.get("forecast_amount", "").startswith("numeric"):
        return 0
    if "gl_account" not in columns:
        return 0

    legacy_rows = session.execute(
        text(
            """
            select *
            from forecast_gl_detail
            where organization_id = :oid
            order by source_row_number
            """
        ),
        {"oid": str(organization_id)},
    ).mappings()
    payloads: list[dict[str, Any]] = []
    for idx, raw in enumerate(legacy_rows, start=1):
        period = parse_period(raw.get("period"))
        if period is None:
            continue
        amount_raw = raw.get("forecast_amount")
        if amount_raw in (None, ""):
            continue
        payloads.append(
            {
                "organization_id": organization_id,
                "scenario": str(raw.get("scenario") or "Forecast"),
                "period": period,
                "line_type": raw.get("line_type"),
                "statement_category": raw.get("statement_category"),
                "department": str(raw.get("department") or ""),
                "sub_department": str(raw.get("sub_department") or ""),
                "account_group": raw.get("account_group"),
                "expense_type": raw.get("expense_type"),
                "gl_account": str(raw.get("gl_account") or ""),
                "management_view_include": str(raw.get("management_view_include") or "Yes"),
                "accounting_view_include": str(raw.get("accounting_view_include") or "Yes"),
                "sbc_flag": str(raw.get("sbc_flag") or "No"),
                "one_time_flag": str(raw.get("one_time_flag") or "No"),
                "non_cash_flag": str(raw.get("non_cash_flag") or "No"),
                "forecast_amount": Decimal(str(amount_raw)),
                "source": raw.get("source"),
                "notes": raw.get("notes"),
            }
        )
    if not payloads:
        return 0
    session.execute(delete(ForecastGlDetail).where(ForecastGlDetail.organization_id == organization_id))
    _upsert_rows(session, ForecastGlDetail, payloads)
    sync_forecast_gl_detail_to_gl_actuals(session, organization_id, payloads)
    return len(payloads)
