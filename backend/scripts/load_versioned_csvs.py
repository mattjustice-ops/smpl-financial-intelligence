"""Load Actual_*, Budget_*, and Forecast_* CSV files into aligned warehouse tables."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.demo_csv.loader import load_demo_csv

DEFAULT_FOLDER = Path.home() / "OneDrive" / "Documents" / "simple CSVS"
VALID_PREFIXES = {"Actual", "Actuals", "Budget", "Forecast"}


def matching_files(folder: Path, prefix: str | None) -> list[Path]:
    if prefix:
        prefixes = [prefix]
    else:
        prefixes = sorted(VALID_PREFIXES)
    files: list[Path] = []
    for item in prefixes:
        files.extend(folder.glob(f"{item}_*.csv"))
    return sorted(set(files))


def load_versioned_files(
    db: Session,
    organization_id: uuid.UUID,
    files: list[Path],
    *,
    label: str = "versioned CSV",
) -> tuple[int, int]:
    loaded = 0
    for path in files:
        result = load_demo_csv(db, organization_id, path.read_bytes(), filename=path.name)
        if result.header_error or result.integrity_error:
            print(f"FAILED {path.name}: {result.header_error or result.integrity_error}")
            continue
        loaded += 1
        print(f"LOADED {path.name}: {result.csv_kind} rows={result.rows_upserted}")
        if result.validation_errors:
            print(f"  validation_errors={len(result.validation_errors)}")
        if result.warnings:
            print(f"  warnings={len(result.warnings)}")
    print(f"\nLoaded {loaded} of {len(files)} {label} files.")
    return loaded, len(files)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: python scripts/load_versioned_csvs.py <organization_id> [csv_folder] [Actual|Budget|Forecast]"
        )

    organization_id = uuid.UUID(sys.argv[1])
    folder = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_FOLDER
    prefix = sys.argv[3] if len(sys.argv) > 3 else None
    if prefix and prefix not in VALID_PREFIXES:
        raise SystemExit(f"Invalid prefix {prefix!r}. Use one of: {', '.join(sorted(VALID_PREFIXES))}")
    if not folder.exists():
        raise SystemExit(f"CSV folder not found: {folder}")

    files = matching_files(folder, prefix)
    if not files:
        raise SystemExit(f"No versioned CSV files found in: {folder}")

    db = SessionLocal()
    try:
        label = f"{prefix} CSV" if prefix else "versioned CSV"
        load_versioned_files(db, organization_id, files, label=label)
    finally:
        db.close()


if __name__ == "__main__":
    main()
