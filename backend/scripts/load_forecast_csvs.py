"""Load every Forecast_*.csv file into aligned forecast_* warehouse tables."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SCRIPTS_DIR.parent
sys.path.insert(0, str(_BACKEND_DIR))
sys.path.insert(0, str(_SCRIPTS_DIR))

from app.db.session import SessionLocal
from app.services.forecast_gl_detail.service import migrate_physical_forecast_gl_table
from load_versioned_csvs import load_versioned_files, matching_files

DEFAULT_FORECAST_FOLDER = Path.home() / "OneDrive" / "Documents" / "simple CSVS"


def resolve_forecast_folder(path: Path) -> Path:
    if path.is_file():
        return path.parent
    return path


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: python scripts/load_forecast_csvs.py <organization_id> [csv_folder_or_file]"
        )

    organization_id = uuid.UUID(sys.argv[1])
    folder = resolve_forecast_folder(Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_FORECAST_FOLDER)
    if not folder.exists():
        raise SystemExit(f"Forecast CSV folder not found: {folder}")

    files = matching_files(folder, "Forecast")
    if not files:
        raise SystemExit(f"No Forecast_*.csv files found in: {folder}")

    db = SessionLocal()
    try:
        migrated = migrate_physical_forecast_gl_table(db, organization_id)
        if migrated:
            print(f"Migrated {migrated} rows from legacy forecast_gl_detail landing table.")
            db.commit()
        load_versioned_files(db, organization_id, files, label="Forecast CSV")
    finally:
        db.close()


if __name__ == "__main__":
    main()
