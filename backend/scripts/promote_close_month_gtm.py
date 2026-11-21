"""Promote Forecast GTM/sales detail into Actual for a newly closed month.

When close advances (e.g. 2026-06 → 2026-07) the board reads Actual for the close
month and drops Forecast for that period. This script fills uploadable detail:

  * actual_marketing_pipeline — copy Forecast channel rows for the close month
  * actual_sales_quotas — clone prior-month quota carriers; attainment from closed-won

Pipeline waterfall is not promoted or uploaded. After detail promote, this script
calls compile_close_month (Table Update) so actual_pipeline_waterfall is rebuilt
from opportunities and the prior ending. Waterfall CSVs go under not-for-upload.

Usage:
  DATABASE_URL=... python scripts/promote_close_month_gtm.py \\
      --organization-id 8571e520-0687-4516-bdee-379f37c58c1f \\
      --period 2026-07
"""
from __future__ import annotations

import argparse
import os
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

META = frozenset(
    {
        "organization_id",
        "source_row_number",
        "source_filename",
        "created_at",
        "updated_at",
    }
)


def _url(raw: str) -> str:
    if raw.startswith("postgresql://"):
        return "postgresql+psycopg://" + raw[len("postgresql://") :]
    return raw


def _dec(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"


def _prior(period: str) -> str:
    y, m = int(period[:4]), int(period[5:7])
    if m == 1:
        return f"{y - 1}-12"
    return f"{y}-{m - 1:02d}"


def _cols(conn: Connection, table: str) -> list[str]:
    return [
        r[0]
        for r in conn.execute(
            text(
                "select column_name from information_schema.columns "
                "where table_schema='public' and table_name=:t "
                "order by ordinal_position"
            ),
            {"t": table},
        )
    ]


def _delete_period(conn: Connection, table: str, org: str, period: str) -> int:
    return conn.execute(
        text(
            f"delete from {table} where organization_id=:o "
            f"and left(cast(period as text),7)=:p"
        ),
        {"o": org, "p": period},
    ).rowcount


def _next_source_row(conn: Connection, table: str, org: str) -> int:
    if "source_row_number" not in _cols(conn, table):
        return 1
    mx = conn.execute(
        text(f"select coalesce(max(source_row_number), 0) from {table} where organization_id=:o"),
        {"o": org},
    ).scalar()
    return int(mx or 0) + 1


def _insert_rows(
    conn: Connection,
    table: str,
    cols: list[str],
    rows: list[dict[str, Any]],
    *,
    org: str,
) -> int:
    if not rows:
        return 0
    usable = [c for c in cols if c in set(rows[0]) | META]
    placeholders = ", ".join(f":{c}" for c in usable)
    col_list = ", ".join(usable)
    stmt = text(f"insert into {table} ({col_list}) values ({placeholders})")
    next_row = _next_source_row(conn, table, org)
    now = datetime.now(timezone.utc)
    for i, row in enumerate(rows):
        payload = {c: row.get(c) for c in usable}
        payload["source_row_number"] = next_row + i
        payload["source_filename"] = "promote_close_month_gtm.py"
        payload["created_at"] = now
        payload["updated_at"] = now
        conn.execute(stmt, payload)
    return len(rows)


def promote_marketing(conn: Connection, org: str, period: str) -> int:
    src, dst = "forecast_marketing_pipeline", "actual_marketing_pipeline"
    dst_cols = _cols(conn, dst)
    rows = conn.execute(
        text(
            f"select * from {src} where organization_id=:o "
            f"and left(cast(period as text),7)=:p"
        ),
        {"o": org, "p": period},
    ).mappings().all()
    if not rows:
        raise SystemExit(f"no {src} rows for {period}")
    out: list[dict[str, Any]] = []
    for raw in rows:
        row = dict(raw)
        row["organization_id"] = uuid.UUID(org)
        row["version"] = "Actual"
        row["period"] = period
        if not row.get("closed_won_arr") and row.get("expected_closed_won_arr"):
            row["closed_won_arr"] = row["expected_closed_won_arr"]
        out.append({c: row.get(c) for c in dst_cols})
    deleted = _delete_period(conn, dst, org, period)
    inserted = _insert_rows(conn, dst, dst_cols, out, org=org)
    print(f"marketing_pipeline: deleted={deleted} inserted={inserted} (from {len(rows)} forecast)")
    return inserted


def promote_sales_quotas(conn: Connection, org: str, period: str) -> int:
    prior = _prior(period)
    dst = "actual_sales_quotas"
    dst_cols = _cols(conn, dst)
    prior_rows = conn.execute(
        text(
            f"select * from {dst} where organization_id=:o "
            f"and left(cast(period as text),7)=:p"
        ),
        {"o": org, "p": prior},
    ).mappings().all()
    if not prior_rows:
        raise SystemExit(f"no actual_sales_quotas for prior month {prior}")

    won_by_owner = defaultdict(lambda: Decimal("0"))
    total_won = Decimal("0")
    for owner, amount in conn.execute(
        text(
            """
            select owner, coalesce(sum(cast(amount_arr as numeric)), 0)
            from actual_opportunities
            where organization_id=:o
              and left(cast(actual_close_date as text),7)=:p
              and lower(coalesce(close_status,'')) like '%won%'
              and (
                    lower(coalesce(opportunity_type,'')) like '%new%'
                 or lower(coalesce(waterfall_type,'')) like '%new%'
              )
            group by owner
            """
        ),
        {"o": org, "p": period},
    ):
        amt = _dec(amount)
        total_won += amt
        if owner:
            won_by_owner[str(owner).strip().lower()] = amt

    # Prefer owner → rep_name match; if CRM names diverge from the quota file, allocate
    # company closed-won NB across Bookings ARR carriers by ramped quota share.
    matched_total = Decimal("0")
    draft: list[dict[str, Any]] = []
    for raw in prior_rows:
        row = dict(raw)
        row["organization_id"] = uuid.UUID(org)
        row["version"] = "Actual"
        row["period"] = period
        name = str(row.get("rep_name") or "").strip().lower()
        attained = won_by_owner.get(name, Decimal("0"))
        matched_total += attained
        row["_matched"] = attained
        draft.append(row)

    allocate = matched_total == 0 and total_won > 0
    carriers = [
        r
        for r in draft
        if _dec(r.get("ramped_monthly_quota_arr")) > 0
        and "bookings" in str(r.get("quota_type") or "").lower()
    ]
    if allocate and not carriers:
        carriers = [r for r in draft if _dec(r.get("ramped_monthly_quota_arr")) > 0]
    weight = sum((_dec(r.get("ramped_monthly_quota_arr")) for r in carriers), Decimal("0"))

    out: list[dict[str, Any]] = []
    for row in draft:
        ramped = _dec(row.get("ramped_monthly_quota_arr"))
        if allocate and row in carriers and weight > 0:
            attained = (total_won * ramped / weight).quantize(Decimal("0.01"))
            src = f"promoted from {prior}; NB won allocated by ramped quota (CRM owner names unmatched)"
        else:
            attained = row.pop("_matched", Decimal("0"))
            src = f"promoted from {prior}; attainment from closed-won NB by owner"
        row.pop("_matched", None)
        row["quota_attainment_actual_arr"] = _money(attained)
        row["quota_attainment_pct"] = _money(attained / ramped) if ramped else None
        row["source"] = src
        out.append(row)

    deleted = _delete_period(conn, dst, org, period)
    inserted = _insert_rows(conn, dst, dst_cols, out, org=org)
    with_att = sum(1 for r in out if _dec(r.get("quota_attainment_actual_arr")) > 0)
    print(
        f"sales_quotas: deleted={deleted} inserted={inserted} "
        f"nb_won={total_won} matched_by_name={matched_total} "
        f"allocated={allocate} rows_with_attainment={with_att}"
    )
    return inserted


# Customer-upload Actual files for the close pack core folder.
CSV_EXPORTS: tuple[tuple[str, str], ...] = (
    ("actual_marketing_pipeline", "Actual_marketing_pipeline.csv"),
    ("actual_sales_quotas", "Actual_Sales_Quotas.csv"),
)
# Computed on Table Update / compile_close_month — never a core upload.
CSV_COMPUTED: tuple[tuple[str, str], ...] = (
    ("actual_pipeline_waterfall", "Actual_pipeline_waterfall.csv"),
)

# Skip loader / audit columns when writing customer download files.
_CSV_SKIP = frozenset(
    {"source_row_number", "source_filename", "created_at", "updated_at"}
)


def export_actual_gtm_csvs(conn: Connection, org: str, csv_dir: str) -> None:
    """Rewrite the Actual GTM/sales CSV pack from warehouse (full history for the org)."""
    import csv
    from pathlib import Path

    out_dir = Path(csv_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for table, filename in CSV_EXPORTS:
        cols = [c for c in _cols(conn, table) if c not in _CSV_SKIP]
        order_bits = ["left(cast(period as text),7)"]
        for extra in ("marketing_channel", "opportunity_type", "employee_id", "rep_name"):
            if extra in cols:
                order_bits.append(extra)
        rows = conn.execute(
            text(
                f"select {', '.join(cols)} from {table} "
                f"where organization_id=:o "
                f"order by {', '.join(order_bits)}"
            ),
            {"o": org},
        ).mappings().all()
        path = out_dir / filename
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            writer.writeheader()
            for raw in rows:
                row = {}
                for c in cols:
                    val = raw.get(c)
                    if val is None:
                        row[c] = ""
                    elif c == "organization_id":
                        row[c] = str(val)
                    else:
                        row[c] = str(val)
                writer.writerow(row)
        periods = sorted({str(r.get("period") or "")[:7] for r in rows if r.get("period")})
        print(f"csv {filename}: {len(rows)} rows periods={periods[0] if periods else '—'}…{periods[-1] if periods else '—'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organization-id", required=True)
    parser.add_argument(
        "--period",
        action="append",
        dest="periods",
        help="YYYY-MM close month to promote (repeatable, e.g. --period 2026-07 --period 2026-08)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run inside a transaction and roll back",
    )
    parser.add_argument(
        "--csv-out",
        help="Rewrite flat Actual GTM/sales CSVs in this folder from warehouse after promote. "
        "Prefer --smpl-actuals-root for the Downloads close pack.",
    )
    parser.add_argument(
        "--smpl-actuals-root",
        help="Write marketing/quotas into {root}/{YYYY-MM}/ and compiled "
        "waterfall CSVs into {root}/{YYYY-MM}/not-for-upload/.",
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Skip promote; only export Actual GTM/sales tables to --csv-out",
    )
    args = parser.parse_args(argv)
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        print("DATABASE_URL is required", file=sys.stderr)
        return 1
    if args.export_only and not args.csv_out:
        print("--export-only requires --csv-out", file=sys.stderr)
        return 1
    if not args.export_only and not args.periods:
        print("pass --period YYYY-MM (repeatable) or --export-only", file=sys.stderr)
        return 1

    # Scripts run from backend/; ensure app imports resolve.
    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)

    from sqlalchemy.orm import Session

    from app.services.warehouse.compile_schedules import compile_close_month

    engine: Engine = create_engine(_url(raw))
    with engine.begin() as conn:
        close = conn.execute(
            text("select close_month::text from organizations where id=cast(:o as uuid)"),
            {"o": args.organization_id},
        ).scalar()
        if not args.export_only:
            for period in args.periods:
                print(f"org close_month={close}; promoting Actual for {period}")
                promote_marketing(conn, args.organization_id, period)
                promote_sales_quotas(conn, args.organization_id, period)
                session = Session(bind=conn)
                compiled = compile_close_month(
                    session,
                    uuid.UUID(args.organization_id),
                    period,
                    commit=False,
                )
                session.flush()
                print(
                    f"compile_close_month {period}: wrote={compiled.get('wrote')} "
                    f"(pipeline waterfall via Table Update)"
                )
        if args.csv_out:
            export_actual_gtm_csvs(conn, args.organization_id, args.csv_out)
        if args.smpl_actuals_root and args.periods:
            from pathlib import Path
            import csv as _csv

            def _write_period_csv(folder: Path, table: str, filename: str, period: str) -> int:
                folder.mkdir(parents=True, exist_ok=True)
                cols = [c for c in _cols(conn, table) if c not in _CSV_SKIP]
                rows = conn.execute(
                    text(
                        f"select {', '.join(cols)} from {table} "
                        f"where organization_id=:o and left(cast(period as text),7)=:p"
                    ),
                    {"o": args.organization_id, "p": period},
                ).mappings().all()
                path = folder / filename
                with path.open("w", newline="", encoding="utf-8") as fh:
                    writer = _csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
                    writer.writeheader()
                    for raw in rows:
                        writer.writerow(
                            {
                                c: ("" if raw.get(c) is None else str(raw.get(c)))
                                for c in cols
                            }
                        )
                return len(rows)

            root = Path(args.smpl_actuals_root)
            for period in args.periods:
                for table, filename in CSV_EXPORTS:
                    n = _write_period_csv(root / period, table, filename, period)
                    print(f"smpl-actuals {period}/{filename}: {n} rows (upload)")
                for table, filename in CSV_COMPUTED:
                    n = _write_period_csv(root / period / "not-for-upload", table, filename, period)
                    print(f"smpl-actuals {period}/not-for-upload/{filename}: {n} rows (computed)")
        if args.dry_run:
            raise RuntimeError("dry-run rollback")
    print("done")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        if str(exc) == "dry-run rollback":
            print("dry-run: rolled back")
            raise SystemExit(0)
        raise
