"""Rebuild the Board demo seed (TS_DATA) from the GL detail files that are loaded into gl_actuals.

The demo seed must show the same statements as the database. This runs the same GL statement
builders the API uses (income statement, balance sheet, cash flow, Budget / Forecast chained from
Actual) over the ``<Version>_gl_detail.csv`` files and writes the result into TS_DATA in the Board
page. Months follow the existing seed: Actual through close, Budget Jan–Dec, Forecast after close.

Usage:
  python build_demo_seed_from_gl.py <gl_dir> <board_html> [<board_html> ...] [--write]

Default is a dry run that prints old vs new and the tie checks. ``--write`` replaces the TS_DATA
line in each Board page; then run ``node frontend/scripts/extract-demo-seed.mjs``.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.services.reporting.gl_balance_sheet import build_balance_sheet_and_cash_flow, chain_rows  # noqa: E402
from app.services.reporting.gl_income_statement import (  # noqa: E402
    build_income_statement_rows,
    build_marketing_program_rows,
    build_opex_detail_rows,
)

VERSIONS = ("Actual", "Budget", "Forecast")
TS_LINE = re.compile(r"^(\s*var TS_DATA=)(\{.*\})(;?\s*)$")

IS_KEYS = ["revenue", "sub_rev", "svc_rev", "cogs", "gross_profit", "gm_pct", "sm", "rd", "ga", "total_opex",
           "ebitda", "da", "interest", "op_income", "pretax", "tax", "net_income", "impl_rev", "rec_svc_rev"]
BS_KEYS = {
    "cash": "cash",
    "ar": "accounts_receivable",
    "prepaids": "prepaids_and_other_current_assets",
    "ppe": "property_and_equipment_net",
    "total_assets": "total_assets",
    "ap": "accounts_payable",
    "deferred_rev": "deferred_revenue",
    "debt": "debt",
    "total_liabilities": "total_liabilities",
    "equity": "equity",
    "total_le": "total_liabilities_and_equity",
}
CFS_KEYS = {
    "beginning_cash": "beginning_cash",
    "net_income": "net_income",
    "da": "depreciation_and_amortization",
    "sbc": "stock_based_compensation",
    "chg_ar": "change_in_accounts_receivable",
    "chg_dr": "change_in_deferred_revenue",
    "chg_ap": "change_in_accounts_payable",
    "chg_prepaids": "change_in_prepaids",
    "cfo": "net_cash_from_operating_activities",
    "capex": "capital_expenditures",
    "cfi": "net_cash_from_investing_activities",
    "debt": "debt_issuance_repayment",
    "cff": "net_cash_from_financing_activities",
    "net_change": "net_change_in_cash",
    "ending_cash": "ending_cash",
}
# Carried in the GL statements but not in the seed's named lines; reported so CFO / totals still explain.
BS_EXTRA = {"other_liabilities": "other_liabilities", "other_assets": "other_assets"}
CFS_EXTRA = ["other_non_cash", "change_in_other_liabilities", "change_in_other_assets", "equity_issuance", "unclassified"]


def _read(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _split(rows: list[dict[str, str]]) -> tuple[list[dict], list[dict]]:
    bs, pl = [], []
    for r in rows:
        row = dict(r)
        row["period"] = (row.get("period") or "")[:7]
        row["amount"] = float((row.get("amount") or "0").replace(",", "") or 0)
        (bs if "balance" in (row.get("statement") or "").lower() else pl).append(row)
    return bs, pl


def _r(v) -> float:
    return round(float(v or 0.0), 2)


def build(gl_dir: str, old_ts: dict) -> tuple[dict, list[str]]:
    gl = {v: _split(_read(os.path.join(gl_dir, f"{v}_gl_detail.csv"))) for v in VERSIONS}
    actual_bs, actual_pl = gl["Actual"]
    notes: list[str] = []
    out: dict = {}
    for v in VERSIONS:
        old = old_ts.get(v) or {}
        periods = list(old.get("periods") or sorted((old.get("is") or {}).keys()))
        if v == "Actual":
            bs_rows, pl_rows, start = actual_bs, actual_pl, None
        else:
            bs_rows, pl_rows, start = chain_rows(v, actual_bs, actual_pl, *gl[v])
        version_pl = gl[v][1] if v != "Actual" else actual_pl
        income = build_income_statement_rows(version_pl)
        opex_detail = build_opex_detail_rows(version_pl)
        programs = build_marketing_program_rows(version_pl)
        balance, cash_flow = build_balance_sheet_and_cash_flow(bs_rows, pl_rows)
        block = {k: val for k, val in old.items() if k not in ("is", "bs", "cfs", "gl_opex", "gl_programs")}
        block["periods"] = periods
        block["is"], block["bs"], block["cfs"], block["gl_opex"], block["gl_programs"] = {}, {}, {}, {}, {}
        for p in periods:
            detail = {k: _r(a) for k, a in sorted((opex_detail.get(p) or {}).items()) if abs(a) >= 0.005}
            block["gl_opex"][p] = detail
            block["gl_programs"][p] = {k: _r(a) for k, a in sorted((programs.get(p) or {}).items()) if abs(a) >= 0.005}
            for k, a in block["gl_programs"][p].items():
                if abs(detail.get(k, 0.0) - a) > 1:
                    notes.append(f"FAIL {v} {p} program account {k} {a:,.2f} vs opex detail {detail.get(k, 0.0):,.2f}")
            for ln in ("sm", "rd", "ga"):
                tot = sum(a for k, a in detail.items() if k.split("|")[0] == ln)
                if abs(tot - float(income.get(p, {}).get(ln, 0.0))) > 1:
                    notes.append(f"FAIL {v} {p} opex detail {ln} {tot:,.2f} vs income statement {income.get(p, {}).get(ln, 0.0):,.2f}")
            i, b, c = income.get(p), balance.get(p), cash_flow.get(p)
            if i is None or b is None or c is None:
                raise SystemExit(f"{v} {p}: missing GL statement (is={i is not None} bs={b is not None} cfs={c is not None})")
            block["is"][p] = {k: _r(i.get(k)) for k in IS_KEYS}
            brow = {k: _r(b.get(src)) for k, src in BS_KEYS.items()}
            for k, src in BS_EXTRA.items():
                if abs(b.get(src, 0.0)) >= 0.005:
                    brow[k] = _r(b.get(src))
            block["bs"][p] = brow
            crow = {k: _r(c.get(src)) for k, src in CFS_KEYS.items()}
            for k in CFS_EXTRA:
                if abs(c.get(k, 0.0)) >= 0.005:
                    crow[k] = _r(c.get(k))
            block["cfs"][p] = crow
            if abs(b.get("balance_check", 0.0)) > 1:
                notes.append(f"FAIL {v} {p} balance sheet off by {b['balance_check']:,.2f}")
            if abs(c.get("cash_check", 0.0)) > 1:
                notes.append(f"FAIL {v} {p} cash flow ending cash vs balance sheet cash off by {c['cash_check']:,.2f}")
            if abs(i.get("net_income", 0.0) - c.get("net_income", 0.0)) > 1:
                notes.append(f"FAIL {v} {p} income statement NI {i['net_income']:,.2f} vs cash flow NI {c['net_income']:,.2f}")
        out[v] = block
    return out, notes


def _load_ts(html_path: str) -> tuple[list[str], int, dict]:
    with open(html_path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    for idx, line in enumerate(lines):
        m = TS_LINE.match(line)
        if m:
            return lines, idx, json.loads(m.group(2))
    raise SystemExit(f"TS_DATA line not found in {html_path}")


def main(argv: list[str]) -> int:
    write = "--write" in argv
    args = [a for a in argv if a != "--write"]
    if len(args) < 2:
        print(__doc__)
        return 2
    gl_dir, pages = args[0], args[1:]
    _, _, old_ts = _load_ts(pages[0])
    new_ts, notes = build(gl_dir, old_ts)

    def line(v, sec, p, keys):
        o = (old_ts.get(v, {}).get(sec, {}) or {}).get(p, {})
        n = new_ts[v][sec][p]
        return f"  {v:8} {p} {sec:3} " + "  ".join(f"{k} {o.get(k, 0):,.0f} -> {n.get(k, 0):,.0f}" for k in keys)

    for v, p in (("Actual", new_ts["Actual"]["periods"][-1]), ("Budget", "2026-12"), ("Forecast", new_ts["Forecast"]["periods"][-1])):
        print(line(v, "is", p, ["revenue", "sub_rev", "rec_svc_rev", "impl_rev", "net_income"]))
        print(line(v, "bs", p, ["cash", "ar", "prepaids", "ppe", "deferred_rev", "equity", "total_assets"]))
        print(line(v, "cfs", p, ["net_income", "chg_dr", "cfo", "net_change", "ending_cash"]))
    extras = sorted({k for v in VERSIONS for sec in ("bs", "cfs") for r in new_ts[v][sec].values()
                     for k in r if k in BS_EXTRA or k in CFS_EXTRA})
    print("extra lines carried:", ", ".join(extras) or "none")
    for n in notes:
        print(n)
    if notes:
        print("== checks FAILED; nothing written")
        return 1
    print("== all checks passed (balance sheet balances, cash flow ties to balance sheet cash, NI ties)")
    if not write:
        print("== dry run; nothing written")
        return 0
    payload = json.dumps(new_ts, separators=(",", ":"))
    for page in pages:
        lines, idx, _ = _load_ts(page)
        m = TS_LINE.match(lines[idx])
        lines[idx] = m.group(1) + payload + m.group(3)
        with open(page, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(lines))
        print("wrote", page)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
