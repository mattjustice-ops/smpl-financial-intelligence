"""Remove one named close load, or every load a system wrote for a month.

A name is ``System · Dataset · YYYY-MM``. Budget and Forecast rows are never
deleted. Rows with no load name are left in place.
"""

from __future__ import annotations

import uuid
from datetime import date
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
    statements = removal_statements(system=system, dataset=dataset, period=as_of_period, scope=scope)
    deleted = 0
    touched: list[str] = []
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

    label = load_display_name(system, dataset, as_of_period) if scope == "name" and dataset else f"{system.strip()} · {as_of_period}"
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
