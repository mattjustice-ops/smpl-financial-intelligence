"""Load every Forecast_*.csv file into aligned forecast_* warehouse tables."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.services.demo_csv.loader import load_demo_csv


DEFAULT_FORECAST_FOLDER = Path.home() / "OneDrive" / "Documents" / "simple CSVS"


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: python scripts/load_forecast_csvs.py <organization_id> [forecast_csv_folder]"
        )

    organization_id = uuid.UUID(sys.argv[1])
    folder = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_FORECAST_FOLDER
    if not folder.exists():
        raise SystemExit(f"Forecast CSV folder not found: {folder}")

    files = sorted(folder.glob("Forecast_*.csv"))
    if not files:
        raise SystemExit(f"No Forecast_*.csv files found in: {folder}")

    db = SessionLocal()
    try:
        loaded = 0
        for path in files:
            result = load_demo_csv(
                db,
                organization_id,
                path.read_bytes(),
                filename=path.name,
            )
            if result.header_error or result.integrity_error:
                print(f"FAILED {path.name}: {result.header_error or result.integrity_error}")
                continue
            loaded += 1
            print(f"LOADED {path.name}: {result.csv_kind} rows={result.rows_upserted}")
            if result.validation_errors:
                print(f"  validation_errors={len(result.validation_errors)}")
            if result.warnings:
                print(f"  warnings={len(result.warnings)}")
        print(f"\nLoaded {loaded} of {len(files)} Forecast CSV files.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
