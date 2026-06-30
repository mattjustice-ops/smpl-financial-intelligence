"""Neon storage snapshots and per-org warehouse footprint estimates."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.usage_event import UsageEvent
from app.services.ops.usage_tracking import record_usage_event

logger = logging.getLogger(__name__)

STORAGE_SNAPSHOT_MAX_AGE_HOURS = 20

# High-signal tenant tables used to estimate per-org warehouse footprint.
TENANT_FOOTPRINT_TABLES = (
    "gl_actuals",
    "warehouse_csv_rows",
    "forecast_gl_detail",
    "customers",
    "opportunities",
    "subscriptions",
    "invoices",
    "mrr_waterfall",
    "forecast_versions",
    "workforce_employees",
    "workforce_period_summary",
)


def _bytes_to_mb(value: int | float | None) -> float:
    if not value:
        return 0.0
    return round(float(value) / (1024 * 1024), 3)


def _bytes_to_gb(value: int | float | None) -> float:
    if not value:
        return 0.0
    return round(float(value) / (1024 * 1024 * 1024), 3)


def _existing_tables(db: Session, table_names: tuple[str, ...]) -> list[str]:
    if not table_names:
        return []
    placeholders = ", ".join(f":t{i}" for i in range(len(table_names)))
    params = {f"t{i}": name for i, name in enumerate(table_names)}
    rows = db.execute(
        text(
            f"""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name IN ({placeholders})
            """
        ),
        params,
    ).all()
    found = {row.table_name for row in rows}
    return [name for name in table_names if name in found]


def _database_size_bytes(db: Session) -> int:
    return int(db.scalar(text("SELECT pg_database_size(current_database())")) or 0)


def _top_tables(db: Session, *, limit: int = 10) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT
                relname AS table_name,
                pg_total_relation_size(relid) AS bytes
            FROM pg_catalog.pg_statio_user_tables
            ORDER BY bytes DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    ).all()
    return [
        {
            "table": row.table_name,
            "bytes": int(row.bytes or 0),
            "size_mb": _bytes_to_mb(row.bytes),
        }
        for row in rows
    ]


def _tenant_table_bytes(db: Session, table_names: list[str]) -> int:
    if not table_names:
        return 0
    total = 0
    for table in table_names:
        try:
            size = db.scalar(
                text("SELECT pg_total_relation_size(to_regclass(:table_name))"),
                {"table_name": f"public.{table}"},
            )
            total += int(size or 0)
        except Exception:
            logger.debug("Could not read size for table %s", table, exc_info=True)
    return total


def org_warehouse_footprint(db: Session) -> dict[str, dict[str, Any]]:
    """Approximate warehouse rows and storage share per organization."""
    tables = _existing_tables(db, TENANT_FOOTPRINT_TABLES)
    if not tables:
        return {}

    union_parts = [
        f"SELECT organization_id::text AS organization_id, COUNT(*)::bigint AS row_count "
        f"FROM {table} GROUP BY organization_id"
        for table in tables
    ]
    query = (
        "SELECT organization_id, SUM(row_count)::bigint AS warehouse_rows "
        f"FROM ({' UNION ALL '.join(union_parts)}) AS counts "
        "WHERE organization_id IS NOT NULL "
        "GROUP BY organization_id"
    )
    rows = db.execute(text(query)).all()

    total_rows = sum(int(row.warehouse_rows or 0) for row in rows)
    tenant_bytes = _tenant_table_bytes(db, tables)
    database_bytes = _database_size_bytes(db)
    allocatable_bytes = tenant_bytes or database_bytes

    footprint: dict[str, dict[str, Any]] = {}
    for row in rows:
        org_id = str(row.organization_id)
        warehouse_rows = int(row.warehouse_rows or 0)
        share = (warehouse_rows / total_rows) if total_rows else 0.0
        estimated_bytes = int(allocatable_bytes * share) if total_rows else 0
        footprint[org_id] = {
            "warehouse_rows": warehouse_rows,
            "row_share_pct": round(share * 100, 2),
            "estimated_storage_bytes": estimated_bytes,
            "estimated_storage_mb": _bytes_to_mb(estimated_bytes),
        }
    return footprint


def build_storage_snapshot_payload(db: Session) -> dict[str, Any]:
    database_bytes = _database_size_bytes(db)
    top_tables = _top_tables(db)
    org_footprint = org_warehouse_footprint(db)
    tenant_tables = _existing_tables(db, TENANT_FOOTPRINT_TABLES)
    tenant_bytes = _tenant_table_bytes(db, tenant_tables)
    return {
        "database_bytes": database_bytes,
        "database_gb": _bytes_to_gb(database_bytes),
        "tenant_table_bytes": tenant_bytes,
        "tenant_table_gb": _bytes_to_gb(tenant_bytes),
        "top_tables": top_tables,
        "tenant_tables_scanned": tenant_tables,
        "org_footprint": org_footprint,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }


def _latest_storage_event(db: Session) -> UsageEvent | None:
    from sqlalchemy import select

    return db.scalars(
        select(UsageEvent)
        .where(UsageEvent.event_type == "storage_snapshot")
        .order_by(UsageEvent.created_at.desc())
        .limit(1)
    ).first()


def storage_snapshot_history(db: Session, *, days: int = 90) -> list[dict[str, Any]]:
    from sqlalchemy import select

    since = datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 365)))
    events = db.scalars(
        select(UsageEvent)
        .where(
            UsageEvent.event_type == "storage_snapshot",
            UsageEvent.created_at >= since,
        )
        .order_by(UsageEvent.created_at.asc())
    ).all()
    history: list[dict[str, Any]] = []
    for event in events:
        meta = event.metadata_json or {}
        history.append(
            {
                "captured_at": event.created_at.isoformat(),
                "database_gb": meta.get("database_gb"),
                "tenant_table_gb": meta.get("tenant_table_gb"),
            }
        )
    return history


def maybe_collect_storage_snapshot(db: Session, *, force: bool = False) -> dict[str, Any] | None:
    latest = _latest_storage_event(db)
    if not force and latest is not None:
        age = datetime.now(timezone.utc) - latest.created_at
        if age < timedelta(hours=STORAGE_SNAPSHOT_MAX_AGE_HOURS):
            meta = dict(latest.metadata_json or {})
            meta["captured_at"] = latest.created_at.isoformat()
            return meta

    payload = build_storage_snapshot_payload(db)
    record_usage_event(
        event_type="storage_snapshot",
        feature="neon",
        metadata=payload,
        db=db,
    )
    return payload


def latest_storage_snapshot_payload(db: Session) -> dict[str, Any] | None:
    latest = _latest_storage_event(db)
    if latest is None:
        return None
    meta = dict(latest.metadata_json or {})
    meta["captured_at"] = latest.created_at.isoformat()
    return meta
