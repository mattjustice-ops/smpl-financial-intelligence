"""Print where workforce headcount data lives for an organization."""

from __future__ import annotations

import sys
import uuid
from datetime import date
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sqlalchemy import func, inspect, select, text

from app.db.session import SessionLocal
from app.models.demo_finance import ForecastHeadcountPlan, HeadcountPlan, WarehouseCsvRow
from app.services.workforce.legacy_headcount import PHYSICAL_HEADCOUNT_TABLES, load_legacy_headcount_rows

ORG = uuid.UUID("8571e520-0687-4516-bdee-379f37c58c1f")
START = date(2026, 5, 1)
END = date(2026, 5, 31)


def main() -> int:
    db = SessionLocal()
    try:
        print(f"Organization: {ORG}")
        for version in ("Actual", "Forecast"):
            print(f"\n=== {version} ===")
            model = ForecastHeadcountPlan if version == "Forecast" else HeadcountPlan
            typed = db.scalar(
                select(func.count())
                .select_from(model)
                .where(model.organization_id == ORG, model.version == version)
            )
            print(f"typed rows: {typed or 0}")

            table = PHYSICAL_HEADCOUNT_TABLES[version]
            physical = 0
            if inspect(db.get_bind()).has_table(table):
                physical = db.scalar(
                    text(f'SELECT COUNT(*) FROM "{table}" WHERE organization_id = :org'),
                    {"org": ORG},
                )
            print(f"physical {table} rows: {physical or 0}")

            kinds = ("headcount_plan", f"{version.lower()}_headcount_plan", "forecast_headcount_plan_upload")
            wh = db.scalar(
                select(func.count())
                .select_from(WarehouseCsvRow)
                .where(
                    WarehouseCsvRow.organization_id == ORG,
                    WarehouseCsvRow.csv_kind.in_(kinds),
                )
            )
            print(f"warehouse_csv_rows: {wh or 0}")

            snaps = load_legacy_headcount_rows(
                db, ORG, scenario=version, start_period=START, end_period=END
            )
            total_hc = sum((s.headcount for s in snaps), start=0)
            print(f"legacy snapshots in May: {len(snaps)} rows, total headcount={total_hc}")
            for snap in snaps[:5]:
                print(f"  {snap.period} {snap.department}: {snap.headcount}")
            if len(snaps) > 5:
                print("  ...")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
