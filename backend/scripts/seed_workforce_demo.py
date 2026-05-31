"""Load only workforce demo CSVs (no customers/opportunities seed). Run after alembic upgrade head."""

from __future__ import annotations

import sys
import uuid
from datetime import date
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sqlalchemy import inspect

from app.db.session import SessionLocal, engine
from app.services.demo_csv.loader import seed_workforce_demo_folder
from app.services.organizations import get_organization_or_404
from app.services.workforce import feeds, service

ORG = uuid.UUID("8571e520-0687-4516-bdee-379f37c58c1f")
START = date(2026, 1, 1)
END = date(2026, 12, 31)

REQUIRED_TABLES = [
    "workforce_employees",
    "workforce_compensation_bands",
    "workforce_hiring_ramp_assumptions",
    "workforce_department_allocation_rules",
    "workforce_open_requisitions",
    "workforce_period_summary",
]


def main() -> int:
    tables = set(inspect(engine).get_table_names())
    missing = [t for t in REQUIRED_TABLES if t not in tables]
    if missing:
        print("FAIL: missing tables:", ", ".join(missing))
        print("Run migrations first:")
        print("  cd backend")
        print("  .\\.venv312\\Scripts\\python.exe -m alembic upgrade head")
        print("Or: powershell -ExecutionPolicy Bypass -File .\\scripts\\fix-db-migrate-and-seed.ps1")
        return 1

    demo_dir = BACKEND / "demo_data"
    db = SessionLocal()
    try:
        get_organization_or_404(db, ORG)
        for row in seed_workforce_demo_folder(db, ORG, demo_dir):
            print(f"  OK {row.filename}: {row.outcome.rows_upserted} rows")

        plan = service.build_workforce_plan(
            db, ORG, scenario="Forecast", start_period=START, end_period=END, persist=True
        )
        legacy = feeds.sync_legacy_headcount_plan(
            db, ORG, scenario="Forecast", start_period=START, end_period=END
        )
        db.commit()
        non_zero = sum(1 for r in plan.period_summary if r.total_people_cost_monthly > 0)
        print(f"  recompute: {len(plan.period_summary)} period rows, {non_zero} with payroll")
        print(f"  legacy headcount rows synced: {legacy}")
        if not plan.period_summary or non_zero == 0:
            print("FAIL: workforce plan empty after load")
            return 1
        print("PASS: workforce demo data loaded")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"FAIL: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
