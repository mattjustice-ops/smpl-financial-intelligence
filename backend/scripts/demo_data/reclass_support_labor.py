"""Reallocate Tier 1 support labor from cost of revenue to R&D (Engineering).

Writes a new folder only (never touches the database):
  python reclass_support_labor.py <source_folder> <output_folder>

The output is a copy of the source with {V}_income_statement.csv, Actual_gl_detail.csv and Budget_gl_detail.csv
replaced, plus support_labor_reclass_log.csv (one row per version and month).

Rules (agreed with Matt, Oct 8 2026):
  * The summary income statements are fixed shares of revenue (cost of revenue 29-30%, R&D 16%, G&A 11%). Booked
    from a roster, that mix staffs Support with 84 people and Engineering with 42; a SaaS company of this size
    runs a gross margin of 72-78% and R&D of 20-25% of revenue.
  * 60% of 5010 Customer Support Labor COGS, as rebuild_gl_to_summary books it from the summary, moves to R&D in
    every month of every version: cost of revenue falls and R&D rises by the same amount, so gross profit rises
    and EBITDA, net income, cash and the balance sheet do not change.
  * The source GL carries the same share so the rebuild's account mix books it: each month's 5010 rows keep 40%
    and the cut is added to that month's Engineering 6100 rows. The Forecast GL is built from June actuals.
"""

from __future__ import annotations

import csv
import os
import shutil
import sys
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rebuild_gl_to_summary import forecast_seed, rebuild  # noqa: E402

CENT = Decimal("0.01")
ZERO = Decimal("0")
VERSIONS = ("Actual", "Budget", "Forecast")
SHARE = Decimal("0.60")
FROM_ACCOUNT = "5010"
TO_DEPARTMENT, TO_ACCOUNT = "Engineering", "6100"
SOURCE_GL_VERSIONS = ("Actual", "Budget")
LOG_FIELDS = ["version", "period", "support_labor_cogs_before", "moved_to_rd", "cost_of_revenue_before",
              "cost_of_revenue_after", "research_and_development_before", "research_and_development_after",
              "gross_margin_before", "gross_margin_after"]


def num(value) -> Decimal:
    return Decimal(str(value if value is not None else "").replace(",", "").strip() or "0")


def q(x: Decimal) -> Decimal:
    return x.quantize(CENT, ROUND_HALF_UP)


def read(path: str) -> tuple[list[str], list[dict[str, str]]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        return list(r.fieldnames or []), list(r)


def write(path: str, fields: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def booked_5010(folder: str) -> dict[str, dict[str, Decimal]]:
    """{version: {period: 5010}} as the GL rebuild books it from the folder's summary and GL."""
    out: dict[str, dict[str, Decimal]] = {}
    actual_rows: list[dict[str, str]] = []
    for v in VERSIONS:
        gl = forecast_seed(actual_rows) if v == "Forecast" else read(os.path.join(folder, f"{v}_gl_detail.csv"))[1]
        rows, _ = rebuild(v, gl, read(os.path.join(folder, f"{v}_income_statement.csv"))[1], {})
        rows = [r for r in rows if r["statement"] != "Balance Sheet"]
        if v == "Actual":
            actual_rows = rows
        amounts: dict[str, Decimal] = defaultdict(Decimal)
        for r in rows:
            if r["account_number"] == FROM_ACCOUNT:
                amounts[r["period"][:7]] += num(r["amount"])
        out[v] = amounts
    return out


def move_in_source_gl(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], int]:
    """Each month: 5010 rows keep (1 - SHARE); the cut is spread over the Engineering 6100 rows by size."""
    by_period: dict[str, list[int]] = defaultdict(list)
    targets: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        if r["statement"] == "Balance Sheet":
            continue
        if r["account_number"] == FROM_ACCOUNT:
            by_period[r["period"][:7]].append(i)
        elif (r["account_number"], r["department"], r["statement_category"]) == (TO_ACCOUNT, TO_DEPARTMENT,
                                                                                 "Operating Expense"):
            targets[r["period"][:7]].append(i)
    out = [dict(r) for r in rows]
    months = 0
    for p, idx in by_period.items():
        if not targets[p]:
            raise ValueError(f"{p}: 5010 rows but no {TO_DEPARTMENT} {TO_ACCOUNT} rows to receive the reclass")
        cut = ZERO
        for i in idx:
            old = num(rows[i]["amount"])
            new = q(old * (1 - SHARE))
            out[i]["amount"] = f"{new:.2f}"
            cut += old - new
        base = sum((num(rows[i]["amount"]) for i in targets[p]), ZERO)
        adds = [q(cut * num(rows[i]["amount"]) / base) for i in targets[p]]
        adds[max(range(len(adds)), key=lambda k: abs(adds[k]))] += cut - sum(adds, ZERO)
        for i, add in zip(targets[p], adds):
            out[i]["amount"] = f"{num(rows[i]['amount']) + add:.2f}"
        months += 1
    return out, months


def build(src: str, dst: str) -> list[str]:
    if os.path.exists(dst):
        raise SystemExit(f"{dst} exists; pick a new folder")
    before = booked_5010(src)
    shutil.copytree(src, dst)
    notes: list[str] = []
    log: list[dict[str, str]] = []
    for v in VERSIONS:
        fields, rows = read(os.path.join(src, f"{v}_income_statement.csv"))
        out = []
        for r in rows:
            p = r["period"][:7]
            moved = q(before[v].get(p, ZERO) * SHARE)
            rev, cogs, rd = num(r["revenue"]), num(r["cost_of_revenue"]), num(r["research_and_development"])
            nr = dict(r)
            nr["cost_of_revenue"] = f"{cogs - moved:.2f}"
            nr["research_and_development"] = f"{rd + moved:.2f}"
            nr["gross_profit"] = f"{num(r['gross_profit']) + moved:.2f}"
            out.append(nr)
            log.append({"version": v, "period": p, "support_labor_cogs_before": f"{before[v].get(p, ZERO):.2f}",
                        "moved_to_rd": f"{moved:.2f}", "cost_of_revenue_before": f"{cogs:.2f}",
                        "cost_of_revenue_after": f"{cogs - moved:.2f}", "research_and_development_before": f"{rd:.2f}",
                        "research_and_development_after": f"{rd + moved:.2f}",
                        "gross_margin_before": f"{(rev - cogs) / rev:.4f}" if rev else "",
                        "gross_margin_after": f"{(rev - cogs + moved) / rev:.4f}" if rev else ""})
        write(os.path.join(dst, f"{v}_income_statement.csv"), fields, out)
        total = sum((num(x["moved_to_rd"]) for x in log if x["version"] == v), ZERO)
        notes.append(f"{v}: {len(out)} months; {total:,.2f} moved from cost of revenue (5010) to R&D")
    for v in SOURCE_GL_VERSIONS:
        fields, rows = read(os.path.join(src, f"{v}_gl_detail.csv"))
        moved_rows, months = move_in_source_gl(rows)
        write(os.path.join(dst, f"{v}_gl_detail.csv"), fields, moved_rows)
        notes.append(f"{v}_gl_detail.csv: {months} months of 5010 rows cut to {1 - SHARE:.0%}, the cut added to "
                     f"{TO_DEPARTMENT} {TO_ACCOUNT}")
    write(os.path.join(dst, "support_labor_reclass_log.csv"), LOG_FIELDS, log)
    notes.extend(check(src, dst, before, log))
    with open(os.path.join(dst, "support_labor_reclass_notes.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(notes) + "\n")
    return notes


def check(src: str, dst: str, before, log) -> list[str]:
    """EBITDA and net income unchanged to the cent; the rebuild books 5010 at (1 - SHARE) of before."""
    for v in VERSIONS:
        a = {r["period"]: r for r in read(os.path.join(src, f"{v}_income_statement.csv"))[1]}
        for r in read(os.path.join(dst, f"{v}_income_statement.csv"))[1]:
            o = a[r["period"]]
            for k in ("revenue", "sales_and_marketing", "general_and_administrative", "ebitda", "net_income"):
                if num(r[k]) != num(o[k]):
                    raise ValueError(f"{v} {r['period']} {k} changed: {o[k]} -> {r[k]}")
            if num(r["cost_of_revenue"]) + num(r["research_and_development"]) != \
                    num(o["cost_of_revenue"]) + num(o["research_and_development"]):
                raise ValueError(f"{v} {r['period']}: cost of revenue + R&D changed")
    after = booked_5010(dst)
    moved = {(x["version"], x["period"]): num(x["moved_to_rd"]) for x in log}
    worst = ZERO
    for v in VERSIONS:
        for p, amt in before[v].items():
            worst = max(worst, abs(after[v].get(p, ZERO) - (amt - moved[(v, p)])))
    if worst > Decimal("1.00"):
        raise ValueError(f"rebuilt 5010 off the reclass by up to {worst}")
    return [f"check: revenue, S&M, G&A, EBITDA and net income unchanged in every month; cost of revenue + R&D "
            f"unchanged; rebuilt 5010 = before less the reclass within {worst} per month"]


if __name__ == "__main__":
    for line in build(sys.argv[1], sys.argv[2]):
        print(line)
