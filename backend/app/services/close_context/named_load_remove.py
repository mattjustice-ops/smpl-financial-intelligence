"""Remove one named close load, or every load a system wrote for a month.

A name is ``System · Dataset · YYYY-MM``. Budget and Forecast rows are never
deleted. Rows with no load name are left in place.
"""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

# Dataset label on the close screen -> warehouse kind.
DATASET_KINDS: dict[str, tuple[str, ...]] = {
    "General ledger": ("gl_actuals",),
    "Invoices": ("invoices",),
    "Customers": ("customers",),
    "Vendors": ("vendors",),
    "Bills": ("bills",),
    "Fixed assets": ("fixed_assets",),
    "Subscriptions": ("subscriptions",),
    "Payments": ("payments",),
    "Contracts": ("contracts",),
    "Opportunities": ("opportunities",),
    "Bank transactions": ("bank_transactions",),
    "Employees": ("workforce_employees",),
    "Open requisitions": ("workforce_open_requisitions",),
}

# Physical tables that can carry load_name. Versioned ones delete Actual only.
PHYSICAL_TABLES: dict[str, dict[str, bool]] = {
    "gl_actuals": {"version": True, "period": True},
    "invoices": {},
    "customers": {},
    "subscriptions": {},
    "opportunities": {},
    "payments": {},
    "headcount_plan": {"version": True, "period": True},
    "workforce_employees": {"version": True},
    "workforce_open_requisitions": {"version": True},
}

PLAN_VERSIONS = frozenset({"budget", "forecast"})


def load_display_name(system: str, dataset: str, period: str) -> str:
    return f"{system.strip()} · {dataset.strip()} · {period.strip()}"


def _month_bounds(period: str) -> tuple[date, date]:
    if len(period) != 7 or period[4] != "-":
        raise ValueError("Period must be YYYY-MM.")
    year = int(period[:4])
    month = int(period[5:7])
    if month < 1 or month > 12:
        raise ValueError("Period must be YYYY-MM.")
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def kinds_for_removal(*, dataset: str | None, scope: str) -> tuple[str, ...]:
    if scope == "system":
        seen: list[str] = []
        for names in DATASET_KINDS.values():
            for name in names:
                if name not in seen:
                    seen.append(name)
        return tuple(seen)
    if scope != "name":
        raise ValueError("Scope must be name or system.")
    if not dataset or dataset not in DATASET_KINDS:
        raise ValueError("Choose a dataset this screen knows how to remove.")
    return DATASET_KINDS[dataset]


def removal_statements(
    *,
    system: str,
    dataset: str | None,
    period: str,
    scope: str,
) -> list[tuple[str, dict[str, Any]]]:
    """SQL that deletes one named load. Table names come from the allow-list."""
    system_name = system.strip()
    if not system_name:
        raise ValueError("Choose a system.")
    start, end = _month_bounds(period)
    kinds = kinds_for_removal(dataset=dataset, scope=scope)
    name = load_display_name(system_name, dataset, period) if scope == "name" and dataset else ""
    system_like = system_name.replace("%", "").replace("_", "") + " · %"
    month_like = "% · " + period
    statements: list[tuple[str, dict[str, Any]]] = []

    for kind in kinds:
        params: dict[str, Any] = {"kind": kind}
        if scope == "name":
            where = "organization_id = :organization_id AND csv_kind = :kind AND source_filename = :load_name"
            params["load_name"] = name
        else:
            where = (
                "organization_id = :organization_id AND csv_kind = :kind "
                "AND source_filename LIKE :system_like AND source_filename LIKE :month_like"
            )
            params["system_like"] = system_like
            params["month_like"] = month_like
        statements.append((f"delete from warehouse_csv_rows where {where}", params))

        spec = PHYSICAL_TABLES.get(kind)
        if spec is None:
            continue
        clauses = ["organization_id = :organization_id", "load_name is not null"]
        physical: dict[str, Any] = {}
        if scope == "name":
            clauses.append("load_name = :load_name")
            physical["load_name"] = name
        else:
            clauses.append("load_name like :system_like and load_name like :month_like")
            physical["system_like"] = system_like
            physical["month_like"] = month_like
        if spec.get("version"):
            clauses.append("version = 'Actual'")
        if spec.get("period"):
            clauses.append("period >= :period_start and period < :period_end")
            physical["period_start"] = start
            physical["period_end"] = end
        if kind == "gl_actuals":
            clauses.append("source_system = :source_system")
            physical["source_system"] = system_name[:64]
        statements.append((f'delete from "{kind}" where ' + " and ".join(clauses), physical))
    return statements


def ensure_load_name_column(session: Session, table: str) -> None:
    if table not in PHYSICAL_TABLES:
        return
    session.execute(text(f'alter table "{table}" add column if not exists load_name varchar(256)'))


def apply_load_stamp(kind: str, payload: dict[str, Any], *, load_name: str | None, source_system: str | None) -> None:
    """Tag rows from this import. Plan versions are left untouched."""
    if not load_name or kind not in PHYSICAL_TABLES:
        return
    version = str(payload.get("version") or "").strip().lower()
    if version in PLAN_VERSIONS:
        return
    payload["load_name"] = load_name[:256]
    if kind == "gl_actuals":
        if source_system:
            payload["source_system"] = source_system.strip()[:64]
        payload["source_file"] = load_name[:256]


def remove_named_load(
    db: Session,
    organization_id: uuid.UUID,
    *,
    system: str,
    dataset: str | None,
    as_of_period: str,
    scope: str,
) -> dict[str, Any]:
    from app.models.organization import Organization

    org = db.get(Organization, organization_id)
    if org is None:
        raise ValueError("organization not found")
    compiled_only = system.strip().lower() == "compiled"
    if compiled_only:
        statements = []
        deleted = clear_compiled_period(db, organization_id, as_of_period)
        touched = ["calculated"]
    else:
        statements = removal_statements(system=system, dataset=dataset, period=as_of_period, scope=scope)
        deleted = 0
        touched = []
    for sql, params in statements:
        table = "warehouse_csv_rows"
        if sql.startswith('delete from "'):
            table = sql.split('"')[1]
            if table in PHYSICAL_TABLES:
                ensure_load_name_column(db, table)
        bound = {"organization_id": organization_id, **params}
        result = db.execute(text(sql), bound)
        count = int(result.rowcount or 0)
        if count:
            deleted += count
            if table not in touched:
                touched.append(table)
    if not compiled_only:
        deleted += clear_compiled_period(db, organization_id, as_of_period)

    from app.models.close_context_blob import CloseContextBlob
    from sqlalchemy import select

    from app.services.close_context.close_workflow_service import record_load_receipt
    from app.services.workspace.pipeline_ledger import record_pipeline_event

    blob = db.scalars(
        select(CloseContextBlob).where(
            CloseContextBlob.organization_id == organization_id,
            CloseContextBlob.as_of_period == as_of_period,
            CloseContextBlob.status == "COMPLETE",
        )
    ).first()
    if blob is not None:
        blob.status = "STALE"

    if compiled_only:
        label = f"Calculated schedules · {as_of_period.strip()}"
    elif scope == "name" and dataset:
        label = load_display_name(system, dataset, as_of_period)
    else:
        label = f"{system.strip()} · {as_of_period}"
    receipt = record_load_receipt(
        db,
        organization_id=organization_id,
        as_of_period=as_of_period,
        source="unload",
        status="complete",
        rows_staged=0,
        rows_applied=0,
        rows_rejected=0,
        entity_type=dataset or "system",
        error_summary={
            "action": "remove_named_load",
            "scope": scope,
            "system": system.strip(),
            "dataset": dataset,
            "load_name": label,
            "deleted_rows": deleted,
            "tables": touched,
        },
        filename=label,
    )
    record_pipeline_event(
        db,
        organization_id=organization_id,
        batch_id=None,
        event_type="dataset_unloaded",
        source="unload",
        entity_type=dataset or "system",
        period=as_of_period,
        metadata={"scope": scope, "load_name": label, "deleted_rows": deleted, "receipt_id": str(receipt.id)},
    )
    db.commit()
    if deleted:
        message = f"Removed {label}. {deleted} rows deleted. Import the dataset again."
    else:
        message = f"No rows were tagged with {label}, so nothing was deleted."
    return {
        "ok": True,
        "deleted_rows": deleted,
        "load_name": label,
        "tables": touched,
        "receipt_id": str(receipt.id),
        "message": message,
    }


_IDENT = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
_NAME_COLUMNS = ("load_name", "source_filename")


CALCULATED_TABLES = (
    "actual_mrr_waterfall",
    "actual_deferred_revenue_waterfall",
    "actual_cash_flow_bridge",
    "actual_cash_collections",
)


def is_customer_load_name(name: str) -> bool:
    """A calculated row is not a file the customer loaded."""
    parsed = parse_load_display_name(name)
    if parsed is None:
        return False
    return parsed[0].lower() != "compiled"


def clear_compiled_period(db: Session, organization_id: uuid.UUID, period: str) -> int:
    """Delete calculated schedule rows for one month. Journals, budget, and forecast stay."""
    _month_bounds(period)
    present = db.execute(
        text(
            """
            select table_name
            from information_schema.tables
            where table_schema = 'public'
              and table_name = any(:tables)
            """
        ),
        {"tables": list(CALCULATED_TABLES)},
    ).all()
    if not isinstance(present, list):
        return 0
    deleted = 0
    for row in present:
        table = str(row[0])
        if table not in CALCULATED_TABLES:
            continue
        result = db.execute(
            text(
                f'delete from "{table}" '
                "where organization_id = :organization_id "
                "and left(cast(period as text), 7) = :period "
                "and (source_filename like 'compiled:%' or source_filename like 'Compiled · %')"
            ),
            {"organization_id": organization_id, "period": period},
        )
        deleted += int(result.rowcount or 0)
    return deleted


def parse_load_display_name(name: str) -> tuple[str, str, str] | None:
    parts = [part.strip() for part in str(name or "").split(" · ")]
    if len(parts) < 3:
        return None
    period = parts[-1]
    try:
        _month_bounds(period)
    except ValueError:
        return None
    return parts[0], " · ".join(parts[1:-1]), period


def _plan_filename(filename: str) -> bool:
    base = (filename or "").replace("\\", "/").split("/")[-1].lower()
    return base.startswith("budget_") or base.startswith("forecast_")


def _table_flags(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            select table_name, column_name
            from information_schema.columns
            where table_schema = 'public'
              and column_name in (
                'organization_id', 'load_name', 'source_filename', 'source_file', 'version', 'updated_at', 'csv_kind'
              )
            """
        )
    ).all()
    columns: dict[str, set[str]] = {}
    for table, column in rows:
        if not _IDENT.match(str(table)):
            continue
        columns.setdefault(str(table), set()).add(str(column))
    chosen: list[dict[str, Any]] = []
    for table, cols in columns.items():
        if "organization_id" not in cols:
            continue
        allowed = (
            table == "warehouse_csv_rows"
            or table in PHYSICAL_TABLES
            or table.startswith("actual_")
            or table.startswith("budget_")
            or table.startswith("forecast_")
        )
        if not allowed:
            continue
        if "load_name" not in cols and "source_filename" not in cols and "source_file" not in cols:
            continue
        chosen.append(
            {
                "table": table,
                "load_name": "load_name" in cols,
                "source_filename": "source_filename" in cols,
                "source_file": "source_file" in cols,
                "version": "version" in cols,
                "updated_at": "updated_at" in cols,
                "csv_kind": "csv_kind" in cols,
            }
        )
    return chosen


def _count_names(db: Session, organization_id: uuid.UUID, period: str) -> dict[str, int]:
    suffix = f" · {period}"
    counts: dict[str, int] = {}
    for spec in _table_flags(db):
        table = spec["table"]
        for column in _NAME_COLUMNS:
            if not spec[column]:
                continue
            found = db.execute(
                text(
                    f'select "{column}" as name, count(*) as n from "{table}" '
                    f'where organization_id = :organization_id and "{column}" like :month_like '
                    f'group by "{column}"'
                ),
                {"organization_id": organization_id, "month_like": f"%{suffix}"},
            ).all()
            for name, count in found:
                label = str(name or "")
                parsed = parse_load_display_name(label)
                if parsed is None or parsed[2] != period:
                    continue
                counts[label] = max(counts.get(label, 0), int(count or 0))
    return counts


def _receipt_counts(db: Session, organization_id: uuid.UUID, period: str) -> dict[str, tuple[int, int, str]]:
    from sqlalchemy import select

    from app.models.close_workflow import CloseLoadReceipt

    rows = db.scalars(
        select(CloseLoadReceipt)
        .where(
            CloseLoadReceipt.organization_id == organization_id,
            CloseLoadReceipt.as_of_period == period,
        )
        .order_by(CloseLoadReceipt.created_at.desc())
    ).all()
    latest: dict[str, Any] = {}
    for row in rows:
        name = (row.filename or "").strip()
        if name and name not in latest:
            latest[name] = row
    out: dict[str, tuple[int, int, str]] = {}
    for name, row in latest.items():
        if row.source == "unload":
            continue
        if int(row.rows_rejected or 0) > 0:
            result = "Loaded with row errors"
        elif row.status == "failed":
            result = "Failed"
        else:
            result = "Loaded"
        out[name] = (int(row.rows_applied or 0), int(row.rows_rejected or 0), result)
    return out


def list_period_loads(db: Session, organization_id: uuid.UUID, as_of_period: str) -> list[dict[str, Any]]:
    """Named loads stored for one month. Any month, including a Campfire month."""
    from sqlalchemy import select

    from app.models.organization import Organization

    period = as_of_period.strip()
    _month_bounds(period)
    names = _count_names(db, organization_id, period)
    receipts = _receipt_counts(db, organization_id, period)
    sandbox = db.scalars(select(Organization).where(Organization.slug == "campfire-sandbox")).first()
    if sandbox is not None and sandbox.id != organization_id:
        for name, count in _count_names(db, sandbox.id, period).items():
            if name.startswith("Campfire · "):
                names[name] = max(names.get(name, 0), count)
        for name, payload in _receipt_counts(db, sandbox.id, period).items():
            if name.startswith("Campfire · ") and name not in receipts:
                receipts[name] = payload
    loads: list[dict[str, Any]] = []
    for name in sorted(names):
        count = names[name]
        if count <= 0:
            continue
        parsed = parse_load_display_name(name)
        if parsed is None:
            continue
        system, dataset, month = parsed
        if not is_customer_load_name(name):
            continue
        applied, rejected, result = receipts.get(name, (count, 0, "Loaded"))
        loads.append(
            {
                "name": name,
                "system": system,
                "dataset": dataset,
                "month": month,
                "applied": applied,
                "rejected": rejected,
                "result": result,
            }
        )
    return loads


def stamp_csv_period_load(
    db: Session,
    organization_id: uuid.UUID,
    *,
    filename: str | None,
    as_of_period: str,
    csv_kind: str | None,
    applied: int,
    rejected: int,
) -> dict[str, Any]:
    """Name a CSV the same way a system load is named. Budget and Forecast stay unnamed."""
    from app.services.close_context.close_workflow_service import record_load_receipt

    period = as_of_period.strip()
    _month_bounds(period)
    base = (filename or "upload.csv").replace("\\", "/").split("/")[-1]
    if _plan_filename(base):
        return {"stamped": False, "load_name": None}
    load_name = load_display_name("CSV", base, period)
    started = datetime.now(timezone.utc) - timedelta(minutes=15)
    kind = (csv_kind or "").strip()
    for spec in _table_flags(db):
        table = str(spec["table"])
        if spec["source_filename"] and kind and (table == "warehouse_csv_rows" or table == kind):
            where = "organization_id = :organization_id and source_filename = :filename"
            params: dict[str, Any] = {
                "organization_id": organization_id,
                "filename": filename,
                "load_name": load_name,
            }
            if table == "warehouse_csv_rows" and spec["csv_kind"]:
                where += " and csv_kind = :kind"
                params["kind"] = kind
            db.execute(text(f'update "{table}" set source_filename = :load_name where {where}'), params)
            if spec["load_name"] and table != "warehouse_csv_rows":
                db.execute(
                    text(
                        f'update "{table}" set load_name = :load_name '
                        "where organization_id = :organization_id and source_filename = :load_name"
                    ),
                    {"organization_id": organization_id, "load_name": load_name},
                )
        if kind in PHYSICAL_TABLES and table == kind and spec["updated_at"]:
            ensure_load_name_column(db, table)
            sets = ["load_name = :load_name"]
            if spec["source_file"]:
                sets.append("source_file = :load_name")
            if table == "gl_actuals":
                sets.append("source_system = 'CSV'")
            version_sql = " and (load_name is null or load_name = '' or load_name = :load_name)"
            if spec["version"]:
                version_sql += " and version = 'Actual'"
            db.execute(
                text(
                    f'update "{table}" set ' + ", ".join(sets) +
                    f" where organization_id = :organization_id and updated_at >= :started{version_sql}"
                ),
                {"organization_id": organization_id, "load_name": load_name, "started": started},
            )
    receipt = record_load_receipt(
        db,
        organization_id=organization_id,
        as_of_period=period,
        source="csv_upload",
        status="partial" if rejected else "complete",
        rows_staged=applied + rejected,
        rows_applied=applied,
        rows_rejected=rejected,
        entity_type=base,
        filename=load_name,
    )
    db.commit()
    return {"stamped": True, "load_name": load_name, "receipt_id": str(receipt.id)}


def remove_csv_load(
    db: Session,
    organization_id: uuid.UUID,
    *,
    dataset: str,
    as_of_period: str,
) -> dict[str, Any]:
    """Delete one CSV load. Does not move the close month. Budget and Forecast stay."""
    from app.models.organization import Organization
    from app.services.close_context.close_workflow_service import record_load_receipt
    from app.services.workspace.pipeline_ledger import record_pipeline_event

    org = db.get(Organization, organization_id)
    if org is None:
        raise ValueError("organization not found")
    base = (dataset or "").strip()
    if not base or _plan_filename(base):
        raise ValueError("Budget and forecast loads stay.")
    period = as_of_period.strip()
    _month_bounds(period)
    label = load_display_name("CSV", base, period)
    deleted = 0
    touched: list[str] = []
    for spec in _table_flags(db):
        table = str(spec["table"])
        matches: list[str] = []
        if spec["load_name"]:
            matches.append("load_name = :load_name")
        if spec["source_filename"]:
            matches.append("source_filename = :load_name")
        if spec["source_file"] and table in PHYSICAL_TABLES:
            matches.append("source_file = :load_name")
        if not matches:
            continue
        clauses = ["organization_id = :organization_id", "(" + " or ".join(matches) + ")"]
        if spec["version"]:
            clauses.append("(version is null or version = 'Actual')")
        result = db.execute(
            text(f'delete from "{table}" where ' + " and ".join(clauses)),
            {"organization_id": organization_id, "load_name": label},
        )
        count = int(result.rowcount or 0)
        if count:
            deleted += count
            touched.append(table)
    deleted += clear_compiled_period(db, organization_id, period)
    receipt = record_load_receipt(
        db,
        organization_id=organization_id,
        as_of_period=period,
        source="unload",
        status="complete",
        rows_staged=0,
        rows_applied=0,
        rows_rejected=0,
        entity_type=base,
        filename=label,
        error_summary={"action": "remove_named_load", "system": "CSV", "load_name": label, "deleted_rows": deleted},
    )
    record_pipeline_event(
        db,
        organization_id=organization_id,
        batch_id=None,
        event_type="dataset_unloaded",
        source="unload",
        entity_type=base,
        period=period,
        metadata={"load_name": label, "deleted_rows": deleted, "receipt_id": str(receipt.id)},
    )
    db.commit()
    if deleted:
        message = f"Removed {label}. {deleted} rows deleted. The close month stays where it is."
    else:
        message = f"No rows were tagged with {label}, so nothing was deleted. The close month stays where it is."
    return {
        "ok": True,
        "deleted_rows": deleted,
        "load_name": label,
        "tables": touched,
        "receipt_id": str(receipt.id),
        "message": message,
    }
