"""Verify workforce operating model baseline (migration, data, recompute)."""

from __future__ import annotations

import sys
import uuid
from datetime import date
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sqlalchemy import inspect, text

from app.db.session import SessionLocal, engine
from app.services.workforce import feeds, service

ORG = uuid.UUID("8571e520-0687-4516-bdee-379f37c58c1f")
START = date(2026, 1, 1)
END = date(2026, 12, 31)


def main() -> int:
    errors: list[str] = []
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    required = [
        "workforce_employees",
        "workforce_open_requisitions",
        "workforce_hiring_ramp_assumptions",
        "workforce_compensation_bands",
        "workforce_department_allocation_rules",
        "workforce_period_summary",
    ]
    print("=== Migration / tables ===")
    for t in required:
        ok = t in tables
        print(f"  {t}: {'OK' if ok else 'MISSING'}")
        if not ok:
            errors.append(f"Missing table {t} — run: python -m alembic upgrade head")

    db = SessionLocal()
    try:
        print("\n=== Source row counts ===")
        for t in required[:-1]:
            n = db.execute(
                text(f'SELECT COUNT(*) FROM "{t}" WHERE organization_id = :org'),
                {"org": str(ORG)},
            ).scalar_one()
            print(f"  {t}: {n}")

        print("\n=== Recompute ===")
        plan = service.build_workforce_plan(
            db,
            ORG,
            scenario="Forecast",
            start_period=START,
            end_period=END,
            persist=True,
        )
        legacy = feeds.sync_legacy_headcount_plan(
            db, ORG, scenario="Forecast", start_period=START, end_period=END
        )
        db.commit()
        print(f"  period_summary rows: {len(plan.period_summary)}")
        print(f"  legacy headcount rows synced: {legacy}")
        non_zero = sum(1 for r in plan.period_summary if r.total_people_cost_monthly > 0)
        print(f"  periods with non-zero people cost: {non_zero}")
        if not plan.period_summary:
            errors.append("period_summary empty — upload workforce CSVs first")
        elif non_zero == 0:
            errors.append("all total_people_cost_monthly are zero — check employees/comp bands")

        summary_n = db.execute(
            text(
                'SELECT COUNT(*) FROM workforce_period_summary WHERE organization_id = :org AND total_people_cost_monthly <> 0'
            ),
            {"org": str(ORG)},
        ).scalar_one()
        print(f"  workforce_period_summary non-zero rows in DB: {summary_n}")

        if plan.validations:
            print("\n=== Validations ===")
            for v in plan.validations:
                print(f"  [{v.status}] {v.validation_name}: {v.message or ''}")
    except Exception as exc:
        db.rollback()
        errors.append(str(exc))
        print(f"\nERROR: {exc}")
    finally:
        db.close()

    print("\n=== Result ===")
    if errors:
        for e in errors:
            print(f"  FAIL: {e}")
        return 1
    print("  PASS: workforce baseline OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
