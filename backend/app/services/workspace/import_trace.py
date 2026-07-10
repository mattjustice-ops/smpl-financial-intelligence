"""Live DB verification for CSV/API ingest — trace batch → destination table."""

from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.demo_csv.loader import _kind_from_filename, _physical_version_table_name
from app.services.financial_statements.financial_statement_service import table_exists
from app.services.workspace.pipeline_ledger import batch_to_payload, get_batch

# Physical tables the board / MDA reporting stack reads directly.
REPORTING_PHYSICAL_TABLES: frozenset[str] = frozenset(
    {
        "actual_mrr_waterfall",
        "budget_mrr_waterfall",
        "forecast_mrr_waterfall",
        "actual_income_statement",
        "budget_income_statement",
        "forecast_income_statement",
        "actual_balance_sheet",
        "budget_balance_sheet",
        "forecast_balance_sheet",
        "actual_cash_flow_bridge",
        "budget_cash_flow_bridge",
        "forecast_cash_flow_bridge",
    }
)

MRR_TRACE_TABLES: tuple[str, ...] = (
    "actual_mrr_waterfall",
    "budget_mrr_waterfall",
    "forecast_mrr_waterfall",
)


def database_fingerprint() -> dict[str, str]:
    """Non-secret hint so Neon console queries can be matched to Railway prod."""
    raw = get_settings().database_url
    normalized = raw.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgres://", "postgresql://"
    )
    parsed = urlparse(normalized)
    host = (parsed.hostname or "unknown").lower()
    database = (parsed.path or "").lstrip("/").split("?")[0] or "unknown"
    provider = "neon" if "neon" in host else ("railway" if "railway" in host else "postgres")
    return {
        "host": host,
        "database": database,
        "provider": provider,
    }


def resolve_csv_destination(filename: str | None) -> dict[str, Any]:
    """Explain where a filename lands before/after ingest."""
    physical_table = _physical_version_table_name(filename)
    filename_kind = _kind_from_filename(filename)

    if physical_table is not None:
        reporting_reads = physical_table in REPORTING_PHYSICAL_TABLES
        reporting_table = physical_table if reporting_reads else _reporting_table_for(physical_table)
        warnings: list[str] = []
        if not reporting_reads:
            warnings.append(
                f'Non-standard filename created table "{physical_table}". '
                f'Board and MDA read "{reporting_table or "actual_mrr_waterfall"}" — '
                f'rename the file to the canonical SMPL template (e.g. Actual_MRR_Waterfall.csv).'
            )
        if reporting_reads:
            warnings.append(
                f'Uploading replaces all rows for your org in "{physical_table}" '
                "(full snapshot, not merge). Include every period you need in the file."
            )
        return {
            "destination_kind": "physical_warehouse",
            "destination_table": physical_table,
            "reporting_table": reporting_table,
            "reporting_reads_this_table": reporting_reads,
            "replace_all_org_rows": True,
            "filename_kind": filename_kind,
            "warnings": warnings,
        }

    if filename_kind is not None:
        return {
            "destination_kind": "raw_warehouse",
            "destination_table": "warehouse_csv_rows",
            "reporting_table": None,
            "reporting_reads_this_table": False,
            "replace_all_org_rows": False,
            "csv_kind": filename_kind,
            "filename_kind": filename_kind,
            "warnings": [
                f'File lands in warehouse_csv_rows (csv_kind="{filename_kind}"). '
                "Board and MDA exports do not read this table — rename to the SMPL template filename."
            ],
        }

    return {
        "destination_kind": "unknown",
        "destination_table": None,
        "reporting_table": None,
        "reporting_reads_this_table": False,
        "replace_all_org_rows": False,
        "filename_kind": filename_kind,
        "warnings": ["Could not resolve destination from filename — check SMPL upload templates."],
    }


def _reporting_table_for(physical_table: str) -> str | None:
    """Map variant physical tables (e.g. actual_mrr_waterfall_june_only) to reporting table."""
    for base in MRR_TRACE_TABLES:
        if physical_table == base or physical_table.startswith(f"{base}_"):
            return base
    if physical_table in REPORTING_PHYSICAL_TABLES:
        return physical_table
    return None


def _table_has_column(db: Session, table_name: str, column_name: str) -> bool:
    row = db.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table
              AND column_name = :column
            LIMIT 1
            """
        ),
        {"table": table_name, "column": column_name},
    ).first()
    return row is not None


def table_live_stats(
    db: Session,
    organization_id: uuid.UUID,
    table_name: str,
    *,
    sample_limit: int = 5,
) -> dict[str, Any]:
    oid = str(organization_id)
    if not table_exists(db, table_name):
        return {
            "table": table_name,
            "exists": False,
            "row_count": 0,
            "periods": [],
            "sample_rows": [],
        }

    row_count = int(
        db.execute(
            text(f'SELECT count(*) FROM "{table_name}" WHERE organization_id = CAST(:oid AS uuid)'),
            {"oid": oid},
        ).scalar()
        or 0
    )

    periods: list[str] = []
    if _table_has_column(db, table_name, "period"):
        period_rows = db.execute(
            text(
                f"""
                SELECT DISTINCT period
                FROM "{table_name}"
                WHERE organization_id = CAST(:oid AS uuid)
                  AND period IS NOT NULL
                  AND trim(period::text) <> ''
                """
            ),
            {"oid": oid},
        )
        seen: set[str] = set()
        for row in period_rows:
            raw = str(row[0]).strip()
            normalized = raw[:7] if len(raw) >= 7 else raw
            if normalized and normalized not in seen:
                seen.add(normalized)
                periods.append(normalized)
        periods.sort()

    sample_rows: list[dict[str, Any]] = []
    if row_count and sample_limit > 0:
        cols = ["source_row_number", "source_filename"]
        if _table_has_column(db, table_name, "period"):
            cols.append("period")
        if _table_has_column(db, table_name, "version"):
            cols.append("version")
        if _table_has_column(db, table_name, "ending_mrr"):
            cols.append("ending_mrr")
        elif _table_has_column(db, table_name, "ending_arr"):
            cols.append("ending_arr")

        select_list = ", ".join(f'"{c}"' for c in cols)
        for row in db.execute(
            text(
                f"""
                SELECT {select_list}
                FROM "{table_name}"
                WHERE organization_id = CAST(:oid AS uuid)
                ORDER BY source_row_number NULLS LAST
                LIMIT :lim
                """
            ),
            {"oid": oid, "lim": sample_limit},
        ).mappings():
            sample_rows.append({k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in dict(row).items()})

    return {
        "table": table_name,
        "exists": True,
        "row_count": row_count,
        "periods": periods,
        "sample_rows": sample_rows,
    }


def warehouse_csv_kind_stats(
    db: Session,
    organization_id: uuid.UUID,
    csv_kind: str,
    *,
    sample_limit: int = 3,
) -> dict[str, Any]:
    oid = str(organization_id)
    row_count = int(
        db.execute(
            text(
                """
                SELECT count(*)
                FROM warehouse_csv_rows
                WHERE organization_id = CAST(:oid AS uuid)
                  AND csv_kind = :kind
                """
            ),
            {"oid": oid, "kind": csv_kind},
        ).scalar()
        or 0
    )
    sample_rows: list[dict[str, Any]] = []
    if row_count:
        for row in db.execute(
            text(
                """
                SELECT source_row_number, source_filename, payload
                FROM warehouse_csv_rows
                WHERE organization_id = CAST(:oid AS uuid)
                  AND csv_kind = :kind
                ORDER BY source_row_number
                LIMIT :lim
                """
            ),
            {"oid": oid, "kind": csv_kind, "lim": sample_limit},
        ).mappings():
            sample_rows.append(dict(row))
    return {
        "table": "warehouse_csv_rows",
        "csv_kind": csv_kind,
        "row_count": row_count,
        "sample_rows": sample_rows,
    }


def org_mrr_data_trace(db: Session, organization_id: uuid.UUID) -> dict[str, Any]:
    """Row counts + periods for MRR physical tables and common variant tables."""
    tables: dict[str, Any] = {}
    for table in MRR_TRACE_TABLES:
        tables[table] = table_live_stats(db, organization_id, table, sample_limit=3)

    # Include any actual_mrr_waterfall_* variant tables created by non-canonical filenames.
    variants = [
        str(r[0])
        for r in db.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name LIKE 'actual_mrr_waterfall_%'
                ORDER BY table_name
                """
            )
        )
    ]
    for table in variants:
        if table not in tables:
            tables[table] = table_live_stats(db, organization_id, table, sample_limit=3)

    return {
        "database": database_fingerprint(),
        "organization_id": str(organization_id),
        "mrr_tables": tables,
        "neon_query_hint": (
            "In Neon SQL Editor, confirm the host matches database.host above (Railway prod DATABASE_URL). "
            'Then: SELECT period, * FROM actual_mrr_waterfall WHERE organization_id = '
            f"'{organization_id}' ORDER BY period;"
        ),
    }


def trace_batch(
    db: Session,
    organization_id: uuid.UUID,
    batch_id: uuid.UUID,
) -> dict[str, Any] | None:
    batch = get_batch(db, organization_id=organization_id, batch_id=batch_id)
    if batch is None:
        return None

    meta = batch.metadata_json or {}
    csv_kind = batch.entity_type or meta.get("csv_kind")
    destination = resolve_csv_destination(batch.filename)
    dest_table = meta.get("destination_table") or destination.get("destination_table")

    destination_stats: dict[str, Any] | None = None
    if destination.get("destination_kind") == "raw_warehouse" and csv_kind:
        destination_stats = warehouse_csv_kind_stats(db, organization_id, str(csv_kind))
    elif dest_table:
        destination_stats = table_live_stats(db, organization_id, str(dest_table))

    reporting_table = destination.get("reporting_table")
    reporting_stats = None
    if reporting_table and reporting_table != dest_table:
        reporting_stats = table_live_stats(db, organization_id, reporting_table, sample_limit=5)

    return {
        "batch": batch_to_payload(batch),
        "database": database_fingerprint(),
        "destination": destination,
        "destination_live": destination_stats,
        "reporting_live": reporting_stats,
        "neon_query_hint": _neon_hint(organization_id, dest_table, reporting_table),
    }


def _neon_hint(
    organization_id: uuid.UUID,
    dest_table: str | None,
    reporting_table: str | None,
) -> str:
    table = reporting_table or dest_table or "actual_mrr_waterfall"
    return (
        f"SELECT period, source_filename, * FROM {table} "
        f"WHERE organization_id = '{organization_id}' ORDER BY period;"
    )


def enrich_ingest_result(
    db: Session,
    organization_id: uuid.UUID,
    result: dict[str, Any],
    *,
    filename: str | None,
) -> dict[str, Any]:
    """Attach destination + live row counts to ingest API responses."""
    destination = resolve_csv_destination(filename)
    csv_kind = result.get("csv_kind") or result.get("entity_type")
    dest_table = destination.get("destination_table")

    live: dict[str, Any] | None = None
    if destination.get("destination_kind") == "raw_warehouse" and csv_kind:
        live = warehouse_csv_kind_stats(db, organization_id, str(csv_kind))
    elif dest_table:
        live = table_live_stats(db, organization_id, str(dest_table))

    reporting_live = None
    reporting_table = destination.get("reporting_table")
    if reporting_table and reporting_table != dest_table:
        reporting_live = table_live_stats(db, organization_id, reporting_table, sample_limit=5)

    merged_warnings = list(result.get("warnings") or []) + list(destination.get("warnings") or [])

    out = dict(result)
    out["destination"] = destination
    out["destination_live"] = live
    out["reporting_live"] = reporting_live
    out["database"] = database_fingerprint()
    out["warnings"] = merged_warnings
    out["neon_query_hint"] = _neon_hint(organization_id, dest_table, reporting_table)
    return out
