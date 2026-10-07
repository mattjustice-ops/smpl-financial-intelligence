"""Rewrite the v5 statement and cash files from the rebuilt GL so every file shows the GL's numbers.

  python sync_v5_statements.py <v5_folder> <gl_folder>

Files rewritten in <v5_folder> (same columns as before):
  * <version>_balance_sheet.csv: every line from the GL balances; equity is total equity
    (paid-in capital + stock comp + retained earnings).
  * <version>_cash_flow_statement.csv: indirect method from the GL: net income, D&A, stock comp,
    working capital changes, capex (PP&E change plus D&A), financing as booked.
  * <version>_cash_collections.csv: beginning and ending cash from the GL.
  * <version>_cash_flow_bridge.csv: collections from the AR rollforward, commission cash from
    <version>_commission_schedule.csv (all plans) when it exists, else the Actual commission
    payouts; other lines as loaded; other operating cash is what is left so the bridge ends on
    GL cash.
  * Deferred commissions (when the balance sheet has the columns): current and noncurrent from
    the GL; their change is an operating line (change_in_deferred_commissions).
  * <version>_Working_Capital_Driver_Summary.csv, <version>_cash_flow_driver_assumptions.csv,
    Forecast_working_capital_metrics.csv, Forecast_revenue_schedule.csv: AR, AP, deferred
    revenue, revenue, billings, collections and DSO from the GL and the billing files.
  * Marketing spend (<version>_marketing_pipeline.csv, Actual_marketing_spend_by_channel.csv,
    Forecast_marketing_pipeline_summary.csv): each month's total equals GL marketing program
    spend; channels keep their mix; per-dollar metrics move with spend.
Old validation summaries that described the v4 numbers are removed.
"""

from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_gl_balance_sheet import CHAIN_FROM_ACTUAL, balances, is_da, is_pl  # noqa: E402

CENT = Decimal("0.01")
ZERO = Decimal("0")
VERSIONS = ("Actual", "Budget", "Forecast")
DAYS_PER_MONTH = Decimal("30.4")
STALE_VALIDATION_FILES = (
    "cash_alignment_validation.csv", "cash_ar_forecast_validation_summary.csv",
    "cash_collections_nonzero_validation.csv", "cash_flow_bridge_validation_summary.csv",
    "cash_forecast_validation_summary.csv", "cash_logic_validation.csv", "cash_rollforward_validation.csv",
    "cash_statement_alignment_validation.csv", "collections_billings_alignment_validation.csv",
    "financial_statement_flow_validation_summary.csv", "financial_statement_validation_summary.csv",
    "full_alignment_validation_summary.csv", "income_statement_revenue_validation_summary.csv",
    "statement_validation_summary.csv", "working_capital_refresh_validation_summary.csv",
    "mrr_waterfall_validation_summary.csv", "marketing_spend_update_validation_summary.csv",
)


def num(value) -> Decimal:
    text = str(value if value is not None else "").replace(",", "").strip()
    return Decimal(text or "0")


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
        for r in rows:
            w.writerow({k: (f"{r[k]:.2f}" if isinstance(r.get(k), Decimal) else r.get(k, "")) for k in fields})


def prior(p: str) -> str:
    y, m = int(p[:4]), int(p[5:7])
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def by_period(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {r["period"][:7]: r for r in rows}


def allocate(total: Decimal, weights: list[tuple[int, Decimal]]) -> dict[int, Decimal]:
    wsum = sum((w for _, w in weights), ZERO)
    if not weights:
        return {}
    if wsum == 0:
        weights = [(k, Decimal("1")) for k, _ in weights]
        wsum = Decimal(len(weights))
    out = {k: q(total * w / wsum) for k, w in weights}
    big = max(weights, key=lambda kw: kw[1])[0]
    out[big] += total - sum(out.values(), ZERO)
    return out


def main(src: str, gl_dir: str) -> list[str]:
    notes: list[str] = []
    gl = {v: read(os.path.join(gl_dir, f"{v}_gl_detail.csv"))[1] for v in VERSIONS}
    bs_rows = {v: [r for r in rows if r["statement"] == "Balance Sheet"] for v, rows in gl.items()}
    bal = balances(bs_rows, gl)

    pl = {v: defaultdict(lambda: defaultdict(Decimal)) for v in VERSIONS}
    for v, rows in gl.items():
        for r in rows:
            p = r["period"][:7]
            amt = num(r["amount"])
            if is_pl(r):
                pl[v][p]["net_income"] -= amt
                if r["statement_category"] == "Revenue":
                    pl[v][p]["revenue"] -= amt
                if is_da(r):
                    pl[v][p]["da"] += amt
                if (r["expense_type"] or "").strip().lower() == "marketing programs" or \
                        (r["account_group"] or "").strip().lower() == "marketing programs":
                    pl[v][p]["programs"] += amt
            elif r["account_number"] == "3311":
                pl[v][p]["sbc"] -= amt

    def pl_for(v: str, p: str, key: str) -> Decimal:
        chain = CHAIN_FROM_ACTUAL.get(v)
        source = "Actual" if chain and p < chain else v
        return pl[source][p][key]

    def line(v: str, p: str) -> dict[str, Decimal] | None:
        return bal[v].get(p)

    for v in VERSIONS:
        bs_fields, bs_file = read(os.path.join(src, f"{v}_balance_sheet.csv"))
        cf_fields, cf_file = read(os.path.join(src, f"{v}_cash_flow_statement.csv"))
        cf_by = by_period(cf_file)
        ar = by_period(read(os.path.join(src, f"{v}_accounts_receivable_rollforward.csv"))[1])
        dr = by_period(read(os.path.join(src, f"{v}_deferred_revenue_waterfall.csv"))[1])
        ap = by_period(read(os.path.join(src, f"{v}_accounts_payable_rollforward.csv"))[1])
        pp = by_period(read(os.path.join(src, f"{v}_Prepaids_Rollforward.csv"))[1])
        dc_path = os.path.join(src, f"{v}_deferred_commissions_rollforward.csv")
        dc = by_period(read(dc_path)[1]) if os.path.exists(dc_path) else {}
        months = [r["period"][:7] for r in bs_file]

        bs_out = []
        for r in bs_file:
            p = r["period"][:7]
            b = line(v, p)
            nr = dict(r)
            if "deferred_commissions_current" in bs_fields:
                nr["deferred_commissions_current"] = q(b["deferred_commissions_current"])
                nr["deferred_commissions_noncurrent"] = q(b["deferred_commissions_noncurrent"])
            assets = b["cash"] + b["accounts_receivable"] + b["prepaids_and_other_current"] + b["ppe_net"] \
                + b["deferred_commissions_current"] + b["deferred_commissions_noncurrent"]
            liabs = b["accounts_payable"] + b["deferred_revenue"] + b["debt"] + b["other_liabilities"]
            nr.update({"cash": q(b["cash"]), "accounts_receivable": q(b["accounts_receivable"]),
                       "ppe_net": q(b["ppe_net"]), "prepaids_and_other_current": q(b["prepaids_and_other_current"]),
                       "total_assets": q(assets), "accounts_payable": q(b["accounts_payable"]),
                       "deferred_revenue": q(b["deferred_revenue"]), "debt": q(b["debt"]),
                       "other_liabilities": q(b["other_liabilities"]), "total_liabilities": q(liabs),
                       "equity": q(b["total_equity"]), "total_liabilities_and_equity": q(liabs + b["total_equity"]),
                       "balance_check": q(assets - liabs - b["total_equity"])})
            bs_out.append(nr)
        write(os.path.join(src, f"{v}_balance_sheet.csv"), bs_fields, bs_out)

        cf_out, cash_by = [], {}
        for p in months:
            b = line(v, p)
            src_cf = cf_by.get(p, {})
            prev = line(v, prior(p))
            ni = pl_for(v, p, "net_income")
            da = pl_for(v, p, "da")
            sbc = pl_for(v, p, "sbc")
            if prev is None:
                prev = {"accounts_receivable": num(ar[p]["beginning_accounts_receivable"]),
                        "deferred_revenue": num(dr[p]["beginning_deferred_revenue"]),
                        "accounts_payable": num(ap[p]["beginning_accounts_payable"]),
                        "prepaids_and_other_current": num(pp[p]["beginning_prepaid_balance"]),
                        "ppe_net": b["ppe_net"] + num(src_cf.get("capital_expenditures")) - da,
                        "other_liabilities": b["other_liabilities"], "debt": b["debt"],
                        "deferred_commissions": num(dc[p]["beginning_deferred_commissions"]) if p in dc
                        else b["deferred_commissions_current"] + b["deferred_commissions_noncurrent"]}
            else:
                prev = {**prev, "deferred_commissions": prev["deferred_commissions_current"] + prev["deferred_commissions_noncurrent"]}
            b = {**b, "deferred_commissions": b["deferred_commissions_current"] + b["deferred_commissions_noncurrent"]}
            chg = {k: b[k] - prev[k] for k in ("accounts_receivable", "deferred_revenue", "accounts_payable",
                                               "prepaids_and_other_current", "ppe_net", "other_liabilities",
                                               "deferred_commissions")}
            cfo = ni + da + sbc - chg["accounts_receivable"] + chg["accounts_payable"] + chg["deferred_revenue"] \
                - chg["prepaids_and_other_current"] + chg["other_liabilities"] - chg["deferred_commissions"]
            capex = -(chg["ppe_net"] + da)
            cff = num(src_cf.get("debt_issuance_repayment"))
            net = cfo + capex + cff
            begin = b["cash"] - net
            if line(v, prior(p)) is not None and abs(begin - line(v, prior(p))["cash"]) > Decimal("0.02"):
                notes.append(f"{v} {p}: cash flow does not tie to GL cash ({begin - line(v, prior(p))['cash']:,.2f})")
            if chg["other_liabilities"]:
                notes.append(f"{v} {p}: other liabilities moved {chg['other_liabilities']:,.2f}; in operating cash flow")
            row = dict(src_cf)
            row.update({"period": p, "net_income": q(ni), "depreciation_and_amortization": q(da),
                        "stock_based_compensation": q(sbc), "change_in_accounts_receivable": q(-chg["accounts_receivable"]),
                        "change_in_accounts_payable": q(chg["accounts_payable"]),
                        "change_in_deferred_revenue": q(chg["deferred_revenue"]),
                        "change_in_prepaids": q(-chg["prepaids_and_other_current"]),
                        "change_in_deferred_commissions": q(-chg["deferred_commissions"]),
                        "net_cash_from_operating_activities": q(cfo), "capital_expenditures": q(capex),
                        "net_cash_from_investing_activities": q(capex), "debt_issuance_repayment": q(cff),
                        "net_cash_from_financing_activities": q(cff), "net_change_in_cash": q(net),
                        "beginning_cash": q(begin), "ending_cash": q(b["cash"])})
            cf_out.append(row)
            cash_by[p] = (begin, b["cash"], cfo, capex, cff)
        write(os.path.join(src, f"{v}_cash_flow_statement.csv"), cf_fields, cf_out)

        cc_fields, cc = read(os.path.join(src, f"{v}_cash_collections.csv"))
        for r in cc:
            begin, end, *_ = cash_by[r["period"][:7]]
            r["beginning_cash"], r["ending_cash"] = q(begin), q(end)
        write(os.path.join(src, f"{v}_cash_collections.csv"), cc_fields, cc)

        bridge_path = os.path.join(src, f"{v}_cash_flow_bridge.csv")
        if os.path.exists(bridge_path):
            payouts: dict[str, Decimal] = defaultdict(Decimal)
            schedule_path = os.path.join(src, f"{v}_commission_schedule.csv")
            if os.path.exists(schedule_path):
                for r in read(schedule_path)[1]:
                    payouts[r["period"][:7]] += num(r["commission_payout"])
            elif v == "Actual":
                for r in read(os.path.join(src, "Actual_commission_payouts.csv"))[1]:
                    payouts[r["period"][:7]] += num(r["commission_amount"])
            bf, brows = read(bridge_path)
            out = []
            for r in brows:
                p = r["period"][:7]
                if p not in cash_by:
                    continue
                begin, end, cfo, capex, cff = cash_by[p]
                coll = num(ar[p]["cash_collections"]) if p in ar else num(r.get("cash_collections_from_invoices"))
                nr = dict(r)
                if p in payouts:
                    nr["commission_cash_out"] = q(payouts[p])
                outflows = sum((num(nr.get(k)) for k in ("payroll_cash_out", "commission_cash_out", "vendor_cash_out_n30",
                                                          "tax_cash_out", "interest_cash_out")), ZERO)
                financing_key = "financing_to_maintain_cash_floor" if "financing_to_maintain_cash_floor" in bf else "financing"
                other = begin + coll - outflows - (-capex) + cff - end
                nr.update({"beginning_cash": q(begin), "cash_collections_from_invoices": q(coll), "capex": q(-capex),
                           financing_key: q(cff), "other_operating_cash_out": q(other), "ending_cash": q(end),
                           "bridge_check": "0.00"})
                for alias in ("cash_collections", "collections"):
                    if alias in bf:
                        nr[alias] = q(coll)
                out.append(nr)
            write(bridge_path, bf, out)

        for name in (f"{v}_Working_Capital_Driver_Summary.csv", f"{v}_cash_flow_driver_assumptions.csv"):
            path = os.path.join(src, name)
            if not os.path.exists(path):
                continue
            f_, rows = read(path)
            for r in rows:
                p = r["period"][:7]
                b = line(v, p)
                rev = pl_for(v, p, "revenue")
                if b is None or not rev:
                    continue
                r["dso_days"] = f"{b['accounts_receivable'] / rev * DAYS_PER_MONTH:.1f}"
                if "ending_accounts_receivable" in f_:
                    r["ending_accounts_receivable"] = q(b["accounts_receivable"])
                    r["ending_accounts_payable"] = q(b["accounts_payable"])
                    r["net_working_capital"] = q(b["accounts_receivable"] - b["accounts_payable"])
                    r["revenue"] = q(rev)
            write(path, f_, rows)

    fwm = os.path.join(src, "Forecast_working_capital_metrics.csv")
    frs = os.path.join(src, "Forecast_revenue_schedule.csv")
    ar_f = {**by_period(read(os.path.join(src, "Actual_accounts_receivable_rollforward.csv"))[1]),
            **by_period(read(os.path.join(src, "Forecast_accounts_receivable_rollforward.csv"))[1])}
    for path in (fwm, frs):
        f_, rows = read(path)
        for r in rows:
            p = r["period"][:7]
            b = line("Forecast", p)
            rev = pl_for("Forecast", p, "revenue")
            dso = b["accounts_receivable"] / rev * DAYS_PER_MONTH
            if path == fwm:
                r.update({"dso": f"{dso:.1f}", "accounts_receivable": q(b["accounts_receivable"]),
                          "deferred_revenue": q(b["deferred_revenue"])})
            else:
                r.update({"recognized_revenue": q(rev), "billings": q(num(ar_f[p]["new_billings"])),
                          "deferred_revenue_ending": q(b["deferred_revenue"]), "historical_dso": f"{dso:.1f}",
                          "expected_collections": q(num(ar_f[p]["cash_collections"]))})
        write(path, f_, rows)

    for v in VERSIONS:
        path = os.path.join(src, f"{v}_marketing_pipeline.csv")
        f_, rows = read(path)
        months = sorted({r["period"][:7] for r in rows})
        spend_by: dict[tuple[str, str], Decimal] = {}
        for p in months:
            idx = [i for i, r in enumerate(rows) if r["period"][:7] == p]
            target = pl_for(v, p, "programs")
            old = sum((num(rows[i]["marketing_spend"]) for i in idx), ZERO)
            if not target:
                notes.append(f"{v} {p}: no GL marketing program spend; marketing spend left as loaded")
                continue
            new = allocate(target, [(i, num(rows[i]["marketing_spend"])) for i in idx])
            for i in idx:
                r = rows[i]
                was = num(r["marketing_spend"])
                factor = new[i] / was if was else Decimal("1")
                r["marketing_spend"] = new[i]
                for k in ("cost_per_mql", "cost_per_sql", "marketing_cac_proxy"):
                    if k in f_ and r.get(k) not in (None, ""):
                        r[k] = q(num(r[k]) * factor)
                if "pipeline_per_dollar_spend" in f_ and new[i]:
                    r["pipeline_per_dollar_spend"] = f"{num(r['pipeline_arr_created']) / new[i]:.4f}"
                spend_by[(p, r["marketing_channel"])] = new[i]
            if p in (months[0], months[-1]):
                notes.append(f"{v} {p}: marketing spend {old:,.2f} -> {target:,.2f} (GL programs)")
        write(path, f_, rows)
        if v == "Actual":
            sp = os.path.join(src, "Actual_marketing_spend_by_channel.csv")
            sf, srows = read(sp)
            for r in srows:
                key = (r["period"][:7], r["marketing_channel"])
                if key not in spend_by:
                    continue
                was = num(r["marketing_spend"])
                factor = spend_by[key] / was if was else Decimal("1")
                r["marketing_spend"] = spend_by[key]
                for k in ("cost_per_sql", "marketing_cac_proxy"):
                    if r.get(k) not in (None, ""):
                        r[k] = q(num(r[k]) * factor)
                if spend_by[key]:
                    r["pipeline_per_dollar_spend"] = f"{num(r['pipeline_arr_created']) / spend_by[key]:.4f}"
            write(sp, sf, srows)
    summ = os.path.join(src, "Forecast_marketing_pipeline_summary.csv")
    if os.path.exists(summ):
        f_, rows = read(summ)
        for r in rows:
            p = r["period"][:7]
            target = pl_for("Forecast", p, "programs")
            if not target:
                continue
            r["forecast_marketing_spend"] = q(target)
            pipe, won = num(r["forecast_marketing_pipeline_arr"]), num(r["forecast_marketing_sourced_closed_won_arr"])
            r["spend_as_percent_of_pipeline"] = f"{target / pipe:.4f}" if pipe else ""
            r["marketing_spend_as_percent_of_closed_won_arr"] = f"{target / won:.4f}" if won else ""
        write(summ, f_, rows)

    for name in STALE_VALIDATION_FILES:
        path = os.path.join(src, name)
        if os.path.exists(path):
            os.remove(path)
    notes.append(f"removed {len(STALE_VALIDATION_FILES)} old validation summaries (they described v4 numbers)")
    return notes


if __name__ == "__main__":
    for n in main(sys.argv[1], sys.argv[2]):
        print(n)
