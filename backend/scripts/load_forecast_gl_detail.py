"""Load Forecast_gl_detail.csv, migrate legacy landing table if needed, sync gl_actuals."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.services.demo_csv.loader import load_demo_csv
from app.services.forecast_gl_detail.service import migrate_physical_forecast_gl_table

DEFAULT_FILE = Path.home() / "OneDrive" / "Documents" / "simple CSVS" / "Forecast_gl_detail.csv"
DEFAULT_ORG = "8571e520-0687-4516-bdee-379f37c58c1f"


def main() -> None:
    org_id = uuid.UUID(sys.argv[1]) if len(sys.argv) > 1 else uuid.UUID(DEFAULT_ORG)
    csv_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_FILE
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    db = SessionLocal()
    try:
        migrated = migrate_physical_forecast_gl_table(db, org_id)
        if migrated:
            print(f"Migrated {migrated} rows from legacy forecast_gl_detail landing table.")
            db.commit()

        result = load_demo_csv(db, org_id, csv_path.read_bytes(), filename=csv_path.name)
        if result.header_error or result.integrity_error:
            raise SystemExit(str(result.header_error or result.integrity_error))
        db.commit()
        print(
            f"Loaded {csv_path.name}: kind={result.csv_kind} rows={result.rows_upserted} "
            f"validation_errors={len(result.validation_errors)}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
