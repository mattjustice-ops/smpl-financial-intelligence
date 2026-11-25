"""Restore P&L stock-comp (5040 / 6140) for July-forward close packs.

July+ packs post APIC 3311 from Actual_SBC_Schedule but omit the matching
expense accounts. This writes COA + GL expense rows from the schedule splits
(cogs/sm/rd/ga), allocates them across departments by labor weights already
in the month's GL, then optionally reloads July into the warehouse.
"""
from __future__ import annotations

import csv
import os
import uuid
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(r"C:\Users\mattj\Downloads\SMPL-actuals")
ORG = "8571e520-0687-4516-bdee-379f37c58c1f"
CENT = Decimal("0.01")
SBC_EXPENSE_TYPE = "Stock-Based Compensation"
COA_5040 = {
    "account_number": "5040",
    "account_name": "Stock-Based Compensation COGS",
    "statement": "Income Statement",
    "statement_category": "Cost of Revenue",
    "account_group": "COGS",
    "expense_type": SBC_EXPENSE_TYPE,
    "description": "Stock comp allocated to cost of revenue from Actual_SBC_Schedule",
}
COA_6140 = {
    "account_number": "6140",
    "account_name": "Stock-Based Compensation",
    "statement": "Income Statement",
    "statement_category": "Operating Expense",
    "account_group": "Stock Compensation",
    "expense_type": SBC_EXPENSE_TYPE,
    "description": "Stock comp from Actual_SBC_Schedule (non-cash)",
}
FUNCTION_DEPTS = {
    "sm": ("Sales", "Marketing", "Customer Success"),
    "rd": ("Engineering", "Product"),
    "ga": ("Finance", "G&A", "Support"),
}


def q(x: Decimal) -> Decimal:
    return x.quantize(CENT, ROUND_HALF_UP)


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
        fields = list(rows[0].keys()) if rows else []
    return fields, rows


def _write(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _schedule(base: Path) -> dict[str, Decimal]:
    path = base / "not-for-upload" / "Actual_SBC_Schedule.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    _, rows = _read(path)
    if not rows:
        raise ValueError(f"empty SBC schedule: {path}")
    row = rows[0]
    return {
        key: q(Decimal(str(row.get(key) or "0")))
        for key in ("total_sbc", "cogs_sbc", "sm_sbc", "rd_sbc", "ga_sbc")
    }


def _ensure_coa(base: Path) -> None:
    path = base / "Actual_chart_of_accounts.csv"
    fields, rows = _read(path)
    by_number = {r["account_number"]: r for r in rows}
    changed = False
    for spec in (COA_5040, COA_6140):
        existing = by_number.get(spec["account_number"])
        if existing is None:
            rows.append(dict(spec))
            changed = True
        else:
            for key, value in spec.items():
                if existing.get(key) != value:
                    existing[key] = value
                    changed = True
    if changed:
        rows.sort(key=lambda r: r["account_number"])
        _write(path, fields, rows)
        print("  COA: upserted 5040 / 6140")
    else:
        print("  COA: already has 5040 / 6140")


def _labor_weights(gl_rows: list[dict[str, str]], account_numbers: set[str], departments: tuple[str, ...] | None) -> dict[tuple[str, str], Decimal]:
    weights: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    for row in gl_rows:
        number = (row.get("account_number") or "").strip()
        if number not in account_numbers:
            continue
        dept = (row.get("department") or "").strip()
        if departments is not None and dept not in departments:
            continue
        cc = (row.get("cost_center") or "").strip()
        weights[(dept, cc)] += q(Decimal(str(row.get("amount") or "0")))
    return {key: value for key, value in weights.items() if value > 0}


def _allocate(total: Decimal, weights: dict[tuple[str, str], Decimal]) -> list[tuple[str, str, Decimal]]:
    if total == 0:
        return []
    if not weights:
        return [("", "", total)]
    grand = sum(weights.values(), Decimal("0"))
    parts: list[tuple[str, str, Decimal]] = []
    allocated = Decimal("0")
    ordered = sorted(weights.items(), key=lambda item: (-item[1], item[0][0], item[0][1]))
    for index, ((dept, cc), weight) in enumerate(ordered):
        if index == len(ordered) - 1:
            amount = q(total - allocated)
        else:
            amount = q(total * weight / grand)
            allocated += amount
        if amount:
            parts.append((dept, cc, amount))
    return parts


def _template_row(gl_rows: list[dict[str, str]], period: str) -> dict[str, str]:
    sample = next(row for row in gl_rows if (row.get("period") or "")[:7] == period)
    return {
        "organization_id": sample.get("organization_id") or ORG,
        "version": sample.get("version") or "Actual",
        "period": period,
        "statement": "Income Statement",
        "currency": sample.get("currency") or "USD",
        "subsidiary": sample.get("subsidiary") or "US Parent",
        "vendor_id": "",
        "vendor_name": "",
        "source_file": "Actual_SBC_Schedule.csv",
        "source_system": "Equity",
        "sub_department": "",
    }


def _expense_rows(period: str, gl_rows: list[dict[str, str]], sched: dict[str, Decimal]) -> list[dict[str, str]]:
    base = _template_row(gl_rows, period)
    out: list[dict[str, str]] = []

    def add(account: dict[str, str], dept: str, cc: str, amount: Decimal, line: str) -> None:
        out.append(
            {
                **base,
                "account_number": account["account_number"],
                "account_name": account["account_name"],
                "statement_category": account["statement_category"],
                "account_group": account["account_group"],
                "expense_type": SBC_EXPENSE_TYPE,
                "department": dept or "Unassigned",
                "cost_center": cc,
                "source_record_id": f"Actual-{period}-{cc or dept or 'na'}-{account['account_number']}",
                "amount": f"{amount:.2f}",
                "notes": f"stock comp from Actual_SBC_Schedule ({line}; non-cash)",
            }
        )

    cogs_weights = _labor_weights(gl_rows, {"5010", "5020"}, None)
    for dept, cc, amount in _allocate(sched["cogs_sbc"], cogs_weights):
        add(COA_5040, dept, cc, amount, "cogs_sbc")

    for line, depts in FUNCTION_DEPTS.items():
        weights = _labor_weights(gl_rows, {"6100"}, depts)
        for dept, cc, amount in _allocate(sched[f"{line}_sbc"], weights):
            add(COA_6140, dept, cc, amount, f"{line}_sbc")

    total = sum((q(Decimal(row["amount"])) for row in out), Decimal("0"))
    if total != sched["total_sbc"]:
        # Penny fix on the largest opex row.
        opex = [row for row in out if row["account_number"] == "6140"]
        if opex:
            delta = sched["total_sbc"] - total
            opex[0]["amount"] = f"{q(Decimal(opex[0]['amount']) + delta):.2f}"
    return out


def patch_month(period: str) -> dict[str, Decimal]:
    base = ROOT / period
    print(period)
    sched = _schedule(base)
    _ensure_coa(base)

    gl_path = base / "Actual_gl_detail.csv"
    fields, rows = _read(gl_path)
    kept = [row for row in rows if (row.get("account_number") or "").strip() not in {"5040", "6140"}]
    removed = len(rows) - len(kept)
    added = _expense_rows(period, kept, sched)
    _write(gl_path, fields, kept + added)
    expense = sum((q(Decimal(row["amount"])) for row in added), Decimal("0"))
    print(
        f"  GL: removed {removed} old SBC expense rows; wrote {len(added)} "
        f"totaling {expense} (schedule {sched['total_sbc']})"
    )
    return sched


def reload_july(database_url: str | None = None) -> None:
    """Load patched July COA/GL. Prefer inserting only missing SBC expense rows.

    Full stamped CSV reloads can duplicate existing July GL under a different
    source_file; this path only upserts 5040/6140 (+ COA) after deleting those
    accounts for the period.
    """
    load_dotenv(
        Path(r"C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence\backend\.env"),
        override=True,
    )
    if database_url:
        os.environ["DATABASE_URL"] = database_url

    from sqlalchemy import text

    from app.db.session import SessionLocal
    from app.services.demo_csv.loader import load_demo_csv_core
    from app.services.warehouse.compile_schedules import compile_close_month

    period = "2026-07"
    pack = ROOT / period
    org = uuid.UUID(ORG)
    db = SessionLocal()
    try:
        deleted = db.execute(
            text(
                """
                delete from gl_actuals
                where organization_id = :org
                  and lower(version) = 'actual'
                  and to_char(period, 'YYYY-MM') = :p
                  and account_number in ('5040', '6140')
                """
            ),
            {"org": str(org), "p": period},
        )
        db.commit()
        print("cleared existing 5040/6140 rows:", deleted.rowcount)

        for name in ("Actual_chart_of_accounts.csv", "Actual_gl_detail.csv"):
            path = pack / name
            # Keep the filename unstamped so source_file matches pack rows and
            # does not fork a second July copy under CSV · … · 2026-07.
            res = load_demo_csv_core(db, org, path.read_bytes(), filename=path.name, as_of_period=period)
            if res.header_error or res.integrity_error:
                db.rollback()
                raise RuntimeError(f"{name}: {res.header_error or res.integrity_error}")
            db.commit()
            print("LOADED", name, "rows=", res.rows_upserted)

        rows = db.execute(
            text(
                """
                select account_number, sum(amount::numeric) amt, count(*) n
                from gl_actuals
                where organization_id = :org
                  and lower(version) = 'actual'
                  and to_char(period, 'YYYY-MM') = :p
                  and account_number in ('5040', '6140', '3311')
                group by 1
                order by 1
                """
            ),
            {"org": str(org), "p": period},
        ).mappings()
        print("DB after load:")
        for row in rows:
            print(" ", dict(row))

        print("Compiling", period, "...")
        out = compile_close_month(db, org, period)
        print("compile wrote=", out.get("wrote"))
    finally:
        db.close()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reload-july", action="store_true", help="Load patched July into DATABASE_URL")
    parser.add_argument("--database-url", default=None, help="Optional override DATABASE_URL for reload")
    args = parser.parse_args()

    months = sorted(
        path.name
        for path in ROOT.iterdir()
        if path.is_dir() and path.name >= "2026-07" and (path / "Actual_gl_detail.csv").exists()
    )
    for period in months:
        patch_month(period)
    if args.reload_july:
        print("Reloading July into warehouse...")
        reload_july(args.database_url)
    else:
        print("Packs patched. Re-run with --reload-july to load July into the DB.")


if __name__ == "__main__":
    main()
