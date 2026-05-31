"""Clear CSV-backed Actual/Budget/Forecast warehouse data for one organization."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings


VERSIONED_PREFIXES = ("actual_", "budget_", "forecast_")


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/reset_versioned_warehouse.py <organization_id>")

    organization_id = uuid.UUID(sys.argv[1])
    settings = get_settings()
    engine = create_engine(settings.database_url)

    with engine.begin() as conn:
        tables = conn.execute(
            text(
                """
                select table_name
                from information_schema.tables
                where table_schema = 'public'
                  and table_type = 'BASE TABLE'
                  and (
                    table_name like 'actual\\_%' escape '\\'
                    or table_name like 'budget\\_%' escape '\\'
                    or table_name like 'forecast\\_%' escape '\\'
                  )
                order by table_name
                """
            )
        ).scalars()

        deleted_tables = 0
        for table_name in tables:
            has_org = conn.execute(
                text(
                    """
                    select 1
                    from information_schema.columns
                    where table_schema = 'public'
                      and table_name = :table_name
                      and column_name = 'organization_id'
                    """
                ),
                {"table_name": table_name},
            ).scalar()
            if not has_org:
                continue
            conn.execute(
                text(f'delete from "{table_name}" where organization_id = :organization_id'),
                {"organization_id": str(organization_id)},
            )
            deleted_tables += 1
            print(f"Cleared {table_name}")

        # Canonical typed tables that receive versioned CSV rows in addition to
        # the flexible actual_*/budget_* physical tables.
        for table_name in ("gl_actuals", "headcount_plan"):
            exists = conn.execute(text("select to_regclass(:name)"), {"name": f"public.{table_name}"}).scalar()
            if exists:
                conn.execute(
                    text(
                        f"""
                        delete from {table_name}
                        where organization_id = :organization_id
                          and version in ('Actual', 'Budget', 'Forecast')
                        """
                    ),
                    {"organization_id": str(organization_id)},
                )
                print(f"Cleared versioned rows from {table_name}")

        exists = conn.execute(text("select to_regclass('public.warehouse_csv_rows')")).scalar()
        if exists:
            conn.execute(
                text(
                    """
                    delete from warehouse_csv_rows
                    where organization_id = :organization_id
                      and (
                        csv_kind like 'actual_%'
                        or csv_kind like 'budget_%'
                        or csv_kind like 'forecast_%'
                      )
                    """
                ),
                {"organization_id": str(organization_id)},
            )
            print("Cleared versioned rows from warehouse_csv_rows")

        print(f"\nCleared CSV-backed versioned warehouse data for {organization_id} from {deleted_tables} tables.")


if __name__ == "__main__":
    main()
