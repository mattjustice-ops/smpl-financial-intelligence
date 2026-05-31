"""Load Forecast_*.csv files only when the target forecast_* table is empty."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.demo_csv.loader import _physical_version_table_name, load_demo_csv


DEFAULT_FOLDER = Path.home() / "OneDrive" / "Documents" / "simple CSVS"


def table_row_count(engine, table_name: str, organization_id: uuid.UUID) -> int | None:
    with engine.connect() as conn:
        exists = conn.execute(text("select to_regclass(:name)"), {"name": f"public.{table_name}"}).scalar()
        if not exists:
            return 0
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
            return None
        return int(
            conn.execute(
                text(f'select count(*) from "{table_name}" where organization_id = :organization_id'),
                {"organization_id": str(organization_id)},
            ).scalar()
            or 0
        )


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: python scripts/load_missing_forecast_csvs.py <organization_id> [forecast_csv_folder]"
        )

    organization_id = uuid.UUID(sys.argv[1])
    folder = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_FOLDER
    if not folder.exists():
        raise SystemExit(f"Forecast CSV folder not found: {folder}")

    files = sorted(folder.glob("Forecast_*.csv"))
    if not files:
        raise SystemExit(f"No Forecast_*.csv files found in: {folder}")

    engine = create_engine(get_settings().database_url)
    db = SessionLocal()
    loaded = 0
    skipped = 0
    failed = 0
    try:
        for path in files:
            table_name = _physical_version_table_name(path.name)
            if not table_name:
                print(f"SKIP {path.name}: no forecast table mapping")
                skipped += 1
                continue
            count = table_row_count(engine, table_name, organization_id)
            if count is None:
                print(f"SKIP {path.name}: {table_name} has no organization_id column")
                skipped += 1
                continue
            if count > 0:
                print(f"SKIP {path.name}: {table_name} already has {count} rows")
                skipped += 1
                continue

            result = load_demo_csv(db, organization_id, path.read_bytes(), filename=path.name)
            if result.header_error or result.integrity_error:
                print(f"FAILED {path.name}: {result.header_error or result.integrity_error}")
                failed += 1
                continue
            loaded += 1
            print(f"LOADED {path.name}: {table_name} rows={result.rows_upserted}")

        print(f"\nLoaded={loaded} Skipped={skipped} Failed={failed} Total={len(files)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
