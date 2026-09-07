"""Backfill canonical pipeline waterfall columns from their CSV header synonyms.

The physical landing tables add one text column per CSV header, so when the pipeline
waterfall files shipped ``new_pipeline_created`` / ``slipped_arr`` the canonical
``pipeline_arr_created`` / ``slipped_pipeline_arr`` columns every reader queries were
left NULL. The bridge then saw zero created and zero slipped, failed the identity, and
back-solved a beginning balance that never existed.

The loader now aliases these headers on ingest (PHYSICAL_REQUIRED_ALIASES); this script
repairs rows that were loaded before that fix.

Read-only by default. Pass --apply to write.

  python scripts/backfill_pipeline_waterfall_aliases.py
  python scripts/backfill_pipeline_waterfall_aliases.py --apply
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import text

from app.core.config import get_settings
from app.core.db_guard import describe_target
from app.db.session import SessionLocal

# canonical column -> synonym that actually carried the value
ALIASES = {
    "pipeline_arr_created": "new_pipeline_created",
    "slipped_pipeline_arr": "slipped_arr",
}
TABLES = (
    "actual_pipeline_waterfall",
    "forecast_pipeline_waterfall",
    "budget_pipeline_waterfall",
)


def _columns(db, table: str) -> set[str]:
    rows = db.execute(
        text(
            "select column_name from information_schema.columns "
            "where table_schema = 'public' and table_name = :t"
        ),
        {"t": table},
    ).fetchall()
    return {r[0] for r in rows}


def _identity_report(db, table: str, org: str | None) -> None:
    """Beginning + created - won - lost - slipped should equal ending.

    Scoped to one organization. These tables hold every tenant, and summing a period
    across all of them produces a bridge and an ending that belong to nobody — which
    reads as a multi-million-dollar break in data that is actually clean.
    """
    cols = _columns(db, table)
    if not {"beginning_pipeline_arr", "ending_pipeline_arr"} <= cols:
        return
    if org is None:
        print("      (skipped — pass --organization-id for a meaningful identity check)")
        return

    def s(col: str) -> str:
        return f"coalesce(sum(nullif({col}, '')::numeric), 0)" if col in cols else "0"

    row = db.execute(
        text(
            f"""
            select period,
                   {s('beginning_pipeline_arr')} beg,
                   {s('pipeline_arr_created')}   created,
                   {s('closed_won_arr')}         won,
                   {s('closed_lost_arr')}        lost,
                   {s('slipped_pipeline_arr')}   slipped,
                   {s('ending_pipeline_arr')}    ending
            from {table}
            where organization_id = :org
            group by period order by period desc limit 3
            """
        ),
        {"org": org},
    ).fetchall()
    for r in row:
        period, beg, created, won, lost, slipped, ending = r
        calc = beg + created - won - lost - slipped
        delta = calc - ending
        mark = "ties" if abs(delta) < 1 else f"OFF by {float(delta):,.2f}"
        print(f"      {period}  bridge={float(calc):>15,.2f}  ending={float(ending):>15,.2f}  {mark}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes (default: report only)")
    ap.add_argument(
        "--organization-id",
        help="restrict the backfill to one tenant (recommended; omitting it writes table-wide)",
    )
    args = ap.parse_args()
    org = args.organization_id

    print(f"Database: {describe_target(get_settings().database_url)}")
    print(f"Mode:     {'APPLY' if args.apply else 'dry run (no writes)'}\n")

    db = SessionLocal()
    total = 0
    try:
        for table in TABLES:
            cols = _columns(db, table)
            if not cols:
                print(f"{table}: table not present, skipping")
                continue
            print(f"{table}:")
            for canonical, synonym in ALIASES.items():
                if canonical not in cols:
                    print(f"  {canonical:24} canonical column absent, skipping")
                    continue
                if synonym not in cols:
                    print(f"  {canonical:24} no {synonym} column — nothing to backfill")
                    continue
                n = db.execute(
                    text(
                        f"select count(*) from {table} "
                        f"where ({canonical} is null or {canonical} = '') "
                        f"and {synonym} is not null and {synonym} <> ''"
                        + (" and organization_id = :org" if org else "")
                    ),
                    {"org": org} if org else {},
                ).scalar()
                if not n:
                    print(f"  {canonical:24} already populated")
                    continue
                print(f"  {canonical:24} {n} row(s) to fill from {synonym}")
                total += n
                if args.apply:
                    db.execute(
                        text(
                            f"update {table} set {canonical} = {synonym} "
                            f"where ({canonical} is null or {canonical} = '') "
                            f"and {synonym} is not null and {synonym} <> ''"
                            + (" and organization_id = :org" if org else "")
                        ),
                        {"org": org} if org else {},
                    )
            print("    bridge identity, latest periods:")
            _identity_report(db, table, org)
            print()

        if args.apply:
            db.commit()
            print(f"Committed. {total} row(s) updated.")
        else:
            db.rollback()
            print(f"Dry run. {total} row(s) would be updated. Re-run with --apply to write.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
