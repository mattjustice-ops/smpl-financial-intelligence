"""One-time schema sync for the expanded demo warehouse.

Use this when Alembic did not create the expanded/forecast tables in the local
database. It connects to the same DATABASE_URL used by the FastAPI app.
"""

from __future__ import annotations

import sys
import csv
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.db.base import Base
import app.models  # noqa: F401 - register ORM metadata


FORECAST_TABLES = [
    "gl_actuals",
    "warehouse_csv_rows",
    "forecast_assumptions",
    "forecast_bookings_summary",
    "forecast_cash_collections",
    "forecast_cash_flow_statement",
    "forecast_balance_sheet",
    "forecast_income_statement",
    "forecast_gl_detail",
    "forecast_headcount_plan",
    "forecast_marketing_pipeline",
    "forecast_mrr_waterfall",
    "forecast_opportunities",
    "forecast_quota_capacity",
    "forecast_revenue_schedule",
    "forecast_working_capital_metrics",
    "forecast_driver_assumptions",
    "forecast_deferred_revenue_waterfall",
    "forecast_operating_cash_flow_bridge",
]

MANAGED_COLUMNS = {"organization_id", "created_at", "updated_at"}


def _safe_identifier(value: str) -> str:
    ident = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip().lstrip("\ufeff"))
    ident = "_".join(part for part in ident.split("_") if part)
    if not ident:
        raise ValueError("empty SQL identifier")
    if ident[0].isdigit():
        ident = f"_{ident}"
    return ident[:63]


def _quote_ident(value: str) -> str:
    return f'"{_safe_identifier(value)}"'


def _exec(conn, sql: str) -> None:
    conn.execute(text(sql))


def _table_exists(conn, table_name: str) -> bool:
    return conn.execute(text("select to_regclass(:name)"), {"name": f"public.{table_name}"}).scalar() is not None


def _sync_existing_versioned_tables(engine) -> None:
    """Patch pre-existing canonical tables that Alembic may not have updated."""
    with engine.begin() as conn:
        if _table_exists(conn, "gl_actuals"):
            print("Syncing gl_actuals columns/primary key...")
            _exec(conn, "alter table gl_actuals add column if not exists version varchar(64) not null default 'Actual'")
            _exec(conn, "alter table gl_actuals add column if not exists statement_category varchar(128)")
            _exec(conn, "alter table gl_actuals add column if not exists account_group varchar(128)")
            _exec(conn, "alter table gl_actuals add column if not exists expense_type varchar(128)")
            _exec(conn, "alter table gl_actuals add column if not exists department varchar(256) not null default ''")
            _exec(conn, "alter table gl_actuals add column if not exists cost_center varchar(128) not null default ''")
            _exec(conn, "alter table gl_actuals add column if not exists sub_department varchar(256) not null default ''")
            _exec(conn, "alter table gl_actuals add column if not exists vendor_id varchar(128) not null default ''")
            _exec(conn, "alter table gl_actuals add column if not exists vendor_name varchar(512)")
            _exec(conn, "alter table gl_actuals add column if not exists source_file varchar(256) not null default ''")
            _exec(conn, "alter table gl_actuals add column if not exists source_record_id varchar(256) not null default ''")
            _exec(conn, "alter table gl_actuals add column if not exists notes text")
            _exec(conn, "alter table gl_actuals drop constraint if exists pk_gl_actuals")
            _exec(
                conn,
                """
                alter table gl_actuals
                add constraint pk_gl_actuals primary key (
                    organization_id,
                    version,
                    period,
                    account_number,
                    department,
                    cost_center,
                    sub_department,
                    source_file,
                    source_record_id,
                    subsidiary,
                    source_system
                )
                """,
            )

        if _table_exists(conn, "headcount_plan"):
            print("Syncing headcount_plan columns/primary key...")
            _exec(conn, "alter table headcount_plan add column if not exists version varchar(64) not null default 'Actual'")
            _exec(conn, "alter table headcount_plan add column if not exists payroll_tax_rate numeric(18, 6)")
            _exec(conn, "alter table headcount_plan add column if not exists benefits_rate numeric(18, 6)")
            _exec(conn, "alter table headcount_plan add column if not exists total_people_cost numeric(18, 2)")
            _exec(conn, "alter table headcount_plan drop constraint if exists pk_headcount_plan")
            _exec(
                conn,
                """
                alter table headcount_plan
                add constraint pk_headcount_plan primary key (
                    organization_id,
                    version,
                    period,
                    department
                )
                """,
            )


def _create_missing_tables(engine) -> None:
    tables = [Base.metadata.tables[name] for name in FORECAST_TABLES if name in Base.metadata.tables]
    Base.metadata.create_all(engine, tables=tables)


VERSION_PREFIXES = {
    "actual": "actual",
    "actuals": "actual",
    "budget": "budget",
    "forecast": "forecast",
}


def _versioned_table_name(csv_path: Path) -> str | None:
    stem = csv_path.stem
    if "_" not in stem:
        return None
    prefix, base = stem.split("_", 1)
    normalized_prefix = VERSION_PREFIXES.get(prefix.lower())
    if normalized_prefix is None:
        return None
    return _safe_identifier(f"{normalized_prefix}_{base}")


def _headers(csv_path: Path) -> list[str]:
    with csv_path.open("r", newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        try:
            return [_safe_identifier(h) for h in next(reader) if h and _safe_identifier(h) not in MANAGED_COLUMNS]
        except StopIteration:
            return []


def _sync_versioned_csv_tables(engine, csv_folder: Path) -> None:
    if not csv_folder.exists():
        print(f"CSV folder not found, skipping versioned CSV column sync: {csv_folder}")
        return

    with engine.begin() as conn:
        csv_paths = [
            *csv_folder.glob("Actual_*.csv"),
            *csv_folder.glob("Actuals_*.csv"),
            *csv_folder.glob("Budget_*.csv"),
            *csv_folder.glob("Forecast_*.csv"),
        ]
        for csv_path in sorted(set(csv_paths)):
            table_name = _versioned_table_name(csv_path)
            if table_name is None:
                continue
            headers = _headers(csv_path)
            if not headers:
                continue
            print(f"Syncing {table_name} to {csv_path.name} headers...")
            q_table = _quote_ident(table_name)
            _exec(
                conn,
                f"""
                create table if not exists {q_table} (
                    organization_id uuid not null references organizations(id) on delete cascade,
                    source_row_number integer not null,
                    source_filename text,
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now(),
                    primary key (organization_id, source_row_number)
                )
                """,
            )
            _exec(conn, f"alter table {q_table} add column if not exists source_row_number integer")
            _exec(conn, f"alter table {q_table} add column if not exists source_filename text")
            for header in headers:
                if header in {"source_row_number", "source_filename"}:
                    continue
                _exec(conn, f"alter table {q_table} add column if not exists {_quote_ident(header)} text")


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)

    with engine.connect() as conn:
        db_info = conn.execute(text("select current_database(), current_schema(), current_user")).one()
        print(f"Using DATABASE_URL: {settings.database_url}")
        print(f"Connected to database/schema/user: {db_info}")

    _sync_existing_versioned_tables(engine)
    _create_missing_tables(engine)
    csv_folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "OneDrive" / "Documents" / "simple CSVS"
    _sync_versioned_csv_tables(engine, csv_folder)

    inspector = inspect(engine)
    existing = set(inspector.get_table_names(schema="public"))
    print("\nWarehouse table check:")
    for table_name in FORECAST_TABLES:
        status = "OK" if table_name in existing else "MISSING"
        print(f"  {table_name}: {status}")


if __name__ == "__main__":
    main()
