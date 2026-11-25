"""Repair July close spine: SBC reclass, dedupe tieout, recompile.

July packs posted Cr 3311 with a +total_sbc cash plug so the file foots without
P&L stock-comp. ``_fix_july_forward_sbc`` then added Dr 5040/6140 on top,
breaking the TB and cash_check. The durable fix is:

  * Keep Cr 3311 + the cash plug (demo BS identity)
  * Keep Dr 5040/6140 for MoM
  * Credit Labor by total_sbc so SBC is a P&L reclass, not an orphan expense
  * Dedupe Close Tieout Foot (keep one AP↔Accrued ±11829.77 pair)
  * Exclude non-cash from vendor purchases in compile (code change)

Also restores a prior mistaken cash-unwind if present.
"""
from __future__ import annotations

import csv
import os
import shutil
import uuid
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

NEON_ENV = Path(
    r"C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence\frontend\.env.neon-production.local"
)
PACK_GL = Path(r"C:\Users\mattj\Downloads\SMPL-actuals\2026-07\Actual_gl_detail.csv")
ORG = uuid.UUID("8571e520-0687-4516-bdee-379f37c58c1f")
PERIOD = "2026-07"
SBC_TOTAL = Decimal("75400.00")
TIEOUT_DROP_SOURCE_FILE = "tieout_july_vendor_reclass"
TIEOUT_KEEP_SOURCE_FILE = "july-vendor-reclass"
RECLASS_SOURCE_FILE = "july-sbc-labor-reclass"
RECLASS_SOURCE_SYSTEM = "Close SBC Reclass"
LABOR_ACCT = "6100"
LABOR_NAME = "Base Salaries"


def q(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _engine():
    load_dotenv(NEON_ENV, override=True)
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    os.environ["DATABASE_URL"] = url
    from app.core import config as config_mod

    config_mod.get_settings.cache_clear()
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 30})


def _restore_cash_if_unwound(db, org: str) -> None:
    """Undo a prior cash-plug unwind so BS cash matches the operational bridge."""
    rows = db.execute(
        text(
            """
            select amount::numeric as amount, coalesce(source_record_id,'') as rec,
                   coalesce(notes,'') as notes
            from gl_actuals
            where organization_id=:org and lower(version)='actual'
              and to_char(period,'YYYY-MM')=:p
              and account_number='1000'
              and coalesce(source_file,'')='Actual_gl_detail.csv'
            order by abs(amount::numeric) desc
            """
        ),
        {"org": org, "p": PERIOD},
    ).mappings().all()
    if not rows:
        return
    target = rows[0]
    if "unwind SBC cash plug" not in str(target["notes"]):
        print("Neon cash 1000: no unwind note; leaving", target["amount"])
        return
    old_amt = q(Decimal(str(target["amount"])))
    new_amt = q(old_amt + SBC_TOTAL)
    updated = db.execute(
        text(
            """
            update gl_actuals
            set amount = :amt,
                notes = replace(coalesce(notes,''), :needle, :repl)
            where organization_id=:org and lower(version)='actual'
              and to_char(period,'YYYY-MM')=:p
              and account_number='1000'
              and coalesce(source_file,'')='Actual_gl_detail.csv'
              and amount::numeric = :old_amt
              and coalesce(source_record_id,'') = :rec
            """
        ),
        {
            "amt": f"{new_amt:.2f}",
            "needle": f" | unwind SBC cash plug -{SBC_TOTAL:.2f}",
            "repl": " | cash plug restored; SBC via labor reclass",
            "org": org,
            "p": PERIOD,
            "old_amt": f"{old_amt:.2f}",
            "rec": target["rec"],
        },
    )
    print(f"Neon cash 1000 restored: {old_amt} -> {new_amt} (rows={updated.rowcount})")


def _upsert_labor_reclass(db, org: str) -> None:
    db.execute(
        text(
            """
            delete from gl_actuals
            where organization_id=:org and lower(version)='actual'
              and to_char(period,'YYYY-MM')=:p
              and coalesce(source_file,'')=:sf
            """
        ),
        {"org": org, "p": PERIOD, "sf": RECLASS_SOURCE_FILE},
    )
    # Sample labor row for department / cost center
    sample = db.execute(
        text(
            """
            select department, cost_center, currency, subsidiary
            from gl_actuals
            where organization_id=:org and lower(version)='actual'
              and to_char(period,'YYYY-MM')=:p
              and account_number=:acct
              and amount::numeric > 0
            order by amount::numeric desc
            limit 1
            """
        ),
        {"org": org, "p": PERIOD, "acct": LABOR_ACCT},
    ).mappings().first()
    dept = (sample or {}).get("department") or "Corporate"
    cc = (sample or {}).get("cost_center") or ""
    currency = (sample or {}).get("currency") or "USD"
    sub = (sample or {}).get("subsidiary") or ""
    db.execute(
        text(
            """
            insert into gl_actuals (
              organization_id, version, period, statement, account_group, expense_type,
              account_number, account_name, department, amount, currency, subsidiary,
              source_system, source_record_id, cost_center, sub_department, vendor_id,
              source_file, notes
            ) values (
              :org, 'Actual', (:p || '-01')::date, 'Income Statement', 'Labor', 'Labor',
              :acct, :name, :dept, :amt, :currency, :sub,
              :src, :rec, :cc, '', '',
              :sf,
              :notes
            )
            """
        ),
        {
            "org": org,
            "p": PERIOD,
            "acct": LABOR_ACCT,
            "name": LABOR_NAME,
            "dept": dept,
            "amt": f"{-SBC_TOTAL:.2f}",
            "currency": currency,
            "sub": sub,
            "src": RECLASS_SOURCE_SYSTEM,
            "rec": f"{RECLASS_SOURCE_FILE}-{LABOR_ACCT}",
            "cc": cc,
            "sf": RECLASS_SOURCE_FILE,
            "notes": (
                f"Reclass {SBC_TOTAL:.2f} Base Salaries to SBC 5040/6140 so stock-comp "
                "is a P&L reclass (keeps TB/cash plug identity; non-cash)."
            ),
        },
    )
    print(f"Neon labor reclass credited {LABOR_ACCT} by {-SBC_TOTAL}")


def repair_neon(db) -> None:
    org = str(ORG)
    _restore_cash_if_unwound(db, org)
    _upsert_labor_reclass(db, org)

    deleted = db.execute(
        text(
            """
            delete from gl_actuals
            where organization_id=:org and lower(version)='actual'
              and to_char(period,'YYYY-MM')=:p
              and coalesce(source_file,'')=:sf
            """
        ),
        {"org": org, "p": PERIOD, "sf": TIEOUT_DROP_SOURCE_FILE},
    )
    print(f"Neon deleted duplicate tieout ({TIEOUT_DROP_SOURCE_FILE}):", deleted.rowcount)
    kept = db.execute(
        text(
            """
            select count(*) from gl_actuals
            where organization_id=:org and lower(version)='actual'
              and to_char(period,'YYYY-MM')=:p
              and coalesce(source_file,'')=:sf
            """
        ),
        {"org": org, "p": PERIOD, "sf": TIEOUT_KEEP_SOURCE_FILE},
    ).scalar()
    print(f"Neon kept tieout ({TIEOUT_KEEP_SOURCE_FILE}):", kept)

    month_sum = db.execute(
        text(
            """
            select coalesce(sum(amount::numeric),0) from gl_actuals
            where organization_id=:org and lower(version)='actual'
              and to_char(period,'YYYY-MM')=:p
            """
        ),
        {"org": org, "p": PERIOD},
    ).scalar()
    print("Neon July month sum after repair:", month_sum)
    db.commit()


def repair_pack() -> None:
    if not PACK_GL.exists():
        print("pack missing", PACK_GL)
        return
    bak = PACK_GL.with_suffix(".csv.bak_pre_close_spine")
    if not bak.exists():
        shutil.copy2(PACK_GL, bak)
        print("wrote", bak.name)

    with PACK_GL.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        rows = list(reader)

    before = len(rows)
    rows = [
        r
        for r in rows
        if (r.get("source_file") or "") not in {TIEOUT_DROP_SOURCE_FILE, RECLASS_SOURCE_FILE}
    ]
    print(f"Pack dropped tieout/reclass rows: {before - len(rows)}")

    # Restore cash if previously unwound
    cash_idxs = [
        i
        for i, r in enumerate(rows)
        if (r.get("account_number") or "").strip() == "1000"
        and (r.get("source_file") or "") == "Actual_gl_detail.csv"
    ]
    cash_idxs.sort(
        key=lambda i: abs(Decimal(str(rows[i].get("amount") or "0") or "0")),
        reverse=True,
    )
    if cash_idxs:
        i = cash_idxs[0]
        note = (rows[i].get("notes") or "")
        amt = q(Decimal(str(rows[i].get("amount") or "0") or "0"))
        if "unwind SBC cash plug" in note or amt == q(Decimal("3131830.65")):
            rows[i]["amount"] = f"{q(amt + SBC_TOTAL):.2f}" if "unwind" in note or amt < Decimal("3200000") else f"{amt:.2f}"
            # If amount is the unwound value, restore
            if amt == q(Decimal("3131830.65")):
                rows[i]["amount"] = "3207230.65"
            rows[i]["notes"] = (
                note.replace(f" | unwind SBC cash plug -{SBC_TOTAL:.2f}", "")
                + " | cash plug kept; SBC via labor reclass"
            ).strip(" |")
            print("Pack cash 1000 restored/kept at", rows[i]["amount"])

    # Append labor reclass credit
    template = next(
        (
            r
            for r in rows
            if (r.get("account_number") or "").strip() == LABOR_ACCT
            and Decimal(str(r.get("amount") or "0") or "0") > 0
        ),
        None,
    )
    if template is None:
        template = next(r for r in rows if (r.get("period") or "")[:7] == PERIOD)
    reclass = {k: "" for k in fields}
    reclass.update(
        {
            "organization_id": template.get("organization_id") or str(ORG),
            "version": template.get("version") or "Actual",
            "period": PERIOD,
            "statement": "Income Statement",
            "account_group": "Labor",
            "expense_type": "Labor",
            "account_number": LABOR_ACCT,
            "account_name": LABOR_NAME,
            "department": template.get("department") or "Corporate",
            "cost_center": template.get("cost_center") or "",
            "amount": f"{-SBC_TOTAL:.2f}",
            "currency": template.get("currency") or "USD",
            "subsidiary": template.get("subsidiary") or "",
            "source_file": RECLASS_SOURCE_FILE,
            "source_system": RECLASS_SOURCE_SYSTEM,
            "source_record_id": f"{RECLASS_SOURCE_FILE}-{LABOR_ACCT}",
            "notes": (
                f"Reclass {SBC_TOTAL:.2f} Base Salaries to SBC 5040/6140 "
                "(P&L reclass; non-cash)."
            ),
        }
    )
    rows.append(reclass)
    print(f"Pack appended labor reclass {-SBC_TOTAL}")

    total = sum((q(Decimal(str(r.get("amount") or "0") or "0")) for r in rows), Decimal("0"))
    print("Pack July total after repair:", total)

    with PACK_GL.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print("wrote", PACK_GL)


def recompile(db) -> None:
    from app.services.warehouse.compile_schedules import compile_close_month
    from app.services.warehouse.cash_bridge_residual import (
        cash_bridge_mapping_candidates,
        read_bridge_residual,
    )
    from app.services.reporting.gl_balance_sheet import (
        build_balance_sheet_and_cash_flow,
        fetch_gl_bs_rows,
    )
    from app.services.reporting.gl_income_statement import fetch_gl_pl_rows

    bal, cf = build_balance_sheet_and_cash_flow(
        fetch_gl_bs_rows(db, ORG, "Actual"),
        fetch_gl_pl_rows(db, ORG, "Actual"),
    )
    july_bs = bal.get(PERIOD) or {}
    july_cf = cf.get(PERIOD) or {}
    print(
        "BS/CFS",
        "cash",
        july_bs.get("cash"),
        "balance_check",
        july_bs.get("balance_check"),
        "cash_check",
        july_cf.get("cash_check"),
        "sbc",
        july_cf.get("stock_based_compensation"),
    )

    out = compile_close_month(db, ORG, PERIOD)
    print("compile wrote", out.get("wrote"))
    residual = read_bridge_residual(db, ORG, PERIOD)
    print("bridge_check", residual)
    cands = cash_bridge_mapping_candidates(db, ORG, PERIOD, residual=residual)
    print("mapping candidates", len(cands))
    for c in cands[:10]:
        print(
            " ",
            c.get("account_number"),
            c.get("name"),
            c.get("statement_hint"),
            c.get("reason"),
        )


def main() -> None:
    repair_pack()
    eng = _engine()
    db = sessionmaker(bind=eng)()
    try:
        repair_neon(db)
        recompile(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
