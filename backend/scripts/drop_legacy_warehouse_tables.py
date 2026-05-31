"""Drop legacy demo warehouse tables after Actual/Budget/Forecast split.

Keeps:
- organizations (tenant root required by foreign keys)
- alembic_version (migration bookkeeping)
- any table beginning with actual_, budget_, or forecast_

Everything else in the public schema is considered legacy for this local demo
warehouse cleanup and is dropped with CASCADE.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings


PROTECTED_TABLES = {"organizations", "alembic_version"}
PROTECTED_PREFIXES = ("actual_", "budget_", "forecast_")


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually drop tables. Without this flag, only prints what would be dropped.",
    )
    args = parser.parse_args()

    engine = create_engine(get_settings().database_url)

    with engine.begin() as conn:
        db_info = conn.execute(text("select current_database(), current_schema(), current_user")).one()
        print(f"Connected to database/schema/user: {db_info}")

        tables = [
            row[0]
            for row in conn.execute(
                text(
                    """
                    select table_name
                    from information_schema.tables
                    where table_schema = 'public'
                      and table_type = 'BASE TABLE'
                    order by table_name
                    """
                )
            )
        ]

        to_drop = [
            table
            for table in tables
            if table not in PROTECTED_TABLES
            and not table.lower().startswith(PROTECTED_PREFIXES)
        ]

        kept = [table for table in tables if table not in to_drop]

        print("\nKeeping tables:")
        for table in kept:
            print(f"  KEEP {table}")

        print("\nLegacy tables selected for drop:")
        if not to_drop:
            print("  none")
        for table in to_drop:
            print(f"  DROP {table}")

        if not args.apply:
            print("\nDry run only. Re-run with --apply to drop these tables.")
            return

        for table in to_drop:
            conn.execute(text(f"drop table if exists public.{_quote_ident(table)} cascade"))
            print(f"Dropped {table}")

        print("\nDone.")


if __name__ == "__main__":
    main()
