#!/usr/bin/env python3
"""Load backend/demo_data/*.csv into the database for one organization (FK-safe order).

Usage (from repo root or backend folder, with PYTHONPATH including backend):

  cd backend
  .\\.venv\\Scripts\\python scripts/seed_demo_csv.py <organization-uuid>
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.services.demo_csv.loader import seed_demo_csv_folder  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo CSVs from backend/demo_data/")
    parser.add_argument("organization_id", type=uuid.UUID, help="Organization UUID")
    args = parser.parse_args()

    demo_dir = BACKEND_ROOT / "demo_data"
    db = SessionLocal()
    try:
        results = seed_demo_csv_folder(db, args.organization_id, demo_dir)
        for r in results:
            print(f"{r.filename}: kind={r.outcome.csv_kind} rows={r.outcome.rows_upserted}")
        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
