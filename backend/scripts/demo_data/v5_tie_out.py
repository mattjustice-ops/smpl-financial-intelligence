"""Tie-out report for the v5 dataset: every file against the GL and against each other.

  python v5_tie_out.py <v4_folder> <v5_folder> <gl_folder> [report.md]

Each check is PASS or FAIL; gaps that are known and accepted are listed as FLAG with the number.
Exit code 1 if any check fails.
"""

from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict
from decimal import Decimal

ZERO = Decimal("0")
CLOSE = "2026-06"
VERSIONS = ("Actual", "Budget", "Forecast")
CHAIN_FROM_ACTUAL = {"Budget": "2026-01", "Forecast": "2026-07"}
CASH_FLOOR = Decimal("10000000")
DEFERRED_REVENUE_CAP = Decimal("10000000")
CENTS = Decimal("0.02")
REVENUE_ACCOUNTS = {"4000": "Subscription", "4100": "Implementation & Onboarding", "4200": "Recurring Services"}
BS_ACCOUNTS = {"1000": ("cash", 1), "1100": ("accounts_receivable", 1), "1200": ("prepaids_and_other_current", 1),
               "1500": ("ppe_net", 1), "2000": ("accounts_payable", -1), "2100": ("deferred_revenue", -1),
               "2500": ("debt", -1), "2600": ("other_liabilities", -1)}


def num(value) -> Decimal:
    text = str(value if value is not None else "").replace(",", "").strip()
    return Decimal(text or "0")


def read(path: str) -> tuple[list[str], list[dict[str, str]]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        return list(r.fieldnames or []), list(r)


def prior(p: str) -> str:
    y, m = int(p[:4]), int(p[5:7])
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def money(x: Decimal) -> str:
    return f"${x:,.2f}"


class Report:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.failures = 0

    def section(self, title: str) -> None:
        self.lines.append(f"\n## {title}\n")

    def check(self, name: str, diffs: list[str], detail: str = "") -> None:
        if diffs:
            self.failures += 1
            shown = "; ".join(diffs[:5]) + (f"; ... {len(diffs) - 5} more" if len(diffs) > 5 else "")
            self.lines.append(f"- FAIL {name}: {shown}")
        else:
            self.lines.append(f"- PASS {name}" + (f" ({detail})" if detail else ""))

    def flag(self, text: str) -> None:
        self.lines.append(f"- FLAG {text}")

    def info(self, text: str) -> None:
        self.lines.append(f"- {text}")


def compare(label: str, a: dict[str, Decimal], b: dict[str, Decimal], periods, tol: Decimal = CENTS) -> list[str]:
    return [f"{label} {p}: {money(a.get(p, ZERO))} vs {money(b.get(p, ZERO))}"
            for p in periods if abs(a.get(p, ZERO) - b.get(p, ZERO)) > tol]


def sums(rows, key: str, value: str, where=lambda r: True) -> dict[str, Decimal]:
    out: dict[str, Decimal] = defaultdict(Decimal)
    for r in rows:
        if where(r):
            out[r[key][:7]] += num(r[value])
    return out


def main(v4: str, v5: str, gl_dir: str) -> Report:
    rep = Report()

    def f(name: str) -> list[dict[str, str]]:
        return read(os.path.join(v5, name))[1]

    # ------------------------------------------------------------------ GL
    gl = {v: f_ for v, f_ in ((v, read(os.path.join(gl_dir, f"{v}_gl_detail.csv"))[1]) for v in VERSIONS)}
    months = {v: sorted({r["period"][:7] for r in gl[v]}) for v in VERSIONS}
    movement = {v: defaultdict(lambda: defaultdict(Decimal)) for v in VERSIONS}
    pl = {v: defaultdict(lambda: defaultdict(Decimal)) for v in VERSIONS}
    cutoff = months["Actual"][0]
    for v in VERSIONS:
        for r in gl[v]:
            p, amt, acct = r["period"][:7], num(r["amount"]), r["account_number"]
            if r["statement"] == "Balance Sheet":
                movement[v][p]["__all__"] += amt
                movement[v][p][acct] += amt
            else:
                if p > cutoff:
                    movement[v][p]["__all__"] += amt
                pl[v][p]["net_income"] -= amt
                if acct in REVENUE_ACCOUNTS:
                    pl[v][p][acct] -= amt
                    pl[v][p]["revenue"] -= amt
                if "marketing programs" in ((r["expense_type"] or "") + "|" + (r["account_group"] or "")).lower():
                    pl[v][p]["programs"] += amt

    def chain_months(v: str) -> list[str]:
        start = CHAIN_FROM_ACTUAL.get(v)
        if not start:
            return months[v]
        return [p for p in months["Actual"] if p < start] + months[v]

    def source(v: str, p: str) -> str:
        start = CHAIN_FROM_ACTUAL.get(v)
        return "Actual" if start and p < start else v

    balance = {}
    for v in VERSIONS:
        run: dict[str, Decimal] = defaultdict(Decimal)
        balance[v] = {}
        for p in chain_months(v):
            for acct, amt in movement[source(v, p)][p].items():
                run[acct] += amt
            balance[v][p] = dict(run)

    def bs_line(v: str, p: str, field: str) -> Decimal:
        for acct, (name, sign) in BS_ACCOUNTS.items():
            if name == field:
                return balance[v][p].get(acct, ZERO) * sign
        raise KeyError(field)

    # ------------------------------------------------------------------ schema
    rep.section("Warehouse schema (v5 columns = v4 columns)")
    v4_files = {n for n in os.listdir(v4) if n.endswith(".csv")}
    v5_files = {n for n in os.listdir(v5) if n.endswith(".csv")}
    header_diffs, blank_org = [], []
    for n in sorted(v4_files & v5_files):
        h4, r4 = read(os.path.join(v4, n))
        h5, r5 = read(os.path.join(v5, n))
        if h4 != h5:
            header_diffs.append(n)
        if "organization_id" in h5 and all(r.get("organization_id") for r in r4) and any(not r.get("organization_id") for r in r5):
            blank_org.append(n)
    rep.check("same columns in every file", header_diffs, f"{len(v4_files & v5_files)} files")
    rep.check("organization_id filled wherever v4 had it", blank_org)
    rep.info(f"removed in v5: {sorted(v4_files - v5_files) or 'none'}")
    rep.info(f"new in v5: {sorted(v5_files - v4_files) or 'none'}")

    # ------------------------------------------------------------------ double entry + balance sheet
    rep.section("General ledger and balance sheet")
    for v in VERSIONS:
        tb = [f"{p}: {money(balance[v][p].get('__all__', ZERO))}" for p in chain_months(v)
              if abs(balance[v][p].get("__all__", ZERO)) > CENTS]
        rep.check(f"{v} GL debits = credits every month (trial balance nets to zero; the {cutoff} opening "
                  f"balances are month-end, so {cutoff} P&L is inside opening equity)", tb)
        bs = {r["period"][:7]: r for r in f(f"{v}_balance_sheet.csv")}
        diffs = []
        for p in months[v]:
            r = bs.get(p)
            if r is None:
                diffs.append(f"{p}: missing from balance sheet file")
                continue
            for _, (name, _) in BS_ACCOUNTS.items():
                if abs(num(r[name]) - bs_line(v, p, name)) > CENTS:
                    diffs.append(f"{p} {name}: file {money(num(r[name]))} vs GL {money(bs_line(v, p, name))}")
            if abs(num(r["total_assets"]) - num(r["total_liabilities"]) - num(r["equity"])) > CENTS:
                diffs.append(f"{p}: assets != liabilities + equity")
        rep.check(f"{v} balance sheet file = GL balances and balances every month", diffs)

    # ------------------------------------------------------------------ revenue
    rep.section("Revenue")
    for v in VERSIONS:
        ms = months[v]
        rr = f(f"{v}_revenue_recognition.csv")
        diffs = []
        for acct, rtype in REVENUE_ACCOUNTS.items():
            diffs += compare(f"GL {acct} vs revenue recognition {rtype}", {p: pl[v][p][acct] for p in ms},
                             sums(rr, "period", "recognized_revenue", lambda r, t=rtype: r["revenue_type"] == t), ms)
        diffs += compare("GL 4100 vs implementation schedule", {p: pl[v][p]["4100"] for p in ms},
                         sums(f(f"{v}_implementation_schedule.csv"), "period", "implementation_fee"), ms)
        diffs += compare("GL 4200 vs recurring services schedule", {p: pl[v][p]["4200"] for p in ms},
                         sums(f(f"{v}_recurring_services_schedule.csv"), "period", "recurring_services_revenue"), ms)
        rep.check(f"{v} GL revenue by account = revenue recognition = schedules", diffs)

        is_rows = {r["period"][:7]: r for r in f(f"{v}_income_statement.csv")}
        diffs = compare("revenue", {p: pl[v][p]["revenue"] for p in ms}, {p: num(is_rows[p]["revenue"]) for p in ms if p in is_rows}, ms)
        diffs += compare("net income", {p: pl[v][p]["net_income"] for p in ms}, {p: num(is_rows[p]["net_income"]) for p in ms if p in is_rows},
                         ms, Decimal("0.005"))
        rep.check(f"{v} GL total revenue and net income = income statement", diffs)
        diffs = []
        for p, r in sorted(is_rows.items()):
            gp = num(r["revenue"]) - num(r["cost_of_revenue"])
            ebitda = gp - num(r["sales_and_marketing"]) - num(r["research_and_development"]) - num(r["general_and_administrative"])
            ni = ebitda - num(r["depreciation_and_amortization"]) - num(r["interest_expense"]) - num(r["tax_expense"])
            if (num(r["gross_profit"]), num(r["ebitda"]), num(r["net_income"])) != (gp, ebitda, ni):
                diffs.append(p)
        rep.check(f"{v} income statement gross profit, EBITDA and net income = sum of the lines", diffs)

        worst = max((abs(pl[v][p]["4200"] - pl[v][p]["4000"] / 10) for p in ms), default=ZERO)
        rep.check(f"{v} recurring services = 10% of subscription", [] if worst <= 1 else [f"largest gap {money(worst)}"],
                  f"largest monthly rounding gap {money(worst)}")

    # ------------------------------------------------------------------ billings, deferred revenue, AR
    rep.section("Billings, deferred revenue, accounts receivable")
    sched_all = {v: f(f"{v}_invoice_billing_schedule.csv") for v in VERSIONS}
    for v in VERSIONS:
        ms = months[v]
        dr = {r["period"][:7]: r for r in f(f"{v}_deferred_revenue_waterfall.csv")}
        ar = {r["period"][:7]: r for r in f(f"{v}_accounts_receivable_rollforward.csv")}
        inv = sums(f(f"{v}_invoices.csv"), "invoice_period", "invoice_amount")
        sch = sums(sched_all[v], "period", "billings")
        diffs = compare("invoices vs billing schedule", inv, sch, ms)
        diffs += compare("billing schedule vs AR rollforward", sch, {p: num(ar[p]["new_billings"]) for p in ms}, ms)
        diffs += compare("billing schedule vs deferred revenue waterfall", sch, {p: num(dr[p]["new_billings"]) for p in ms}, ms)
        rep.check(f"{v} billings: invoices = billing schedule = AR rollforward = deferred revenue waterfall", diffs,
                  f"{money(sum((sch.get(p, ZERO) for p in ms), ZERO))} billed")

        diffs = []
        prev_dr = prev_ar = None
        start = CHAIN_FROM_ACTUAL.get(v)
        if start:
            prev_dr = num({r["period"][:7]: r for r in f("Actual_deferred_revenue_waterfall.csv")}[prior(start)]["ending_deferred_revenue"])
            prev_ar = num({r["period"][:7]: r for r in f("Actual_accounts_receivable_rollforward.csv")}[prior(start)]["ending_accounts_receivable"])
        for p in ms:
            d, a = dr[p], ar[p]
            if abs(num(d["beginning_deferred_revenue"]) + num(d["new_billings"]) - num(d["revenue_recognized"]) - num(d["ending_deferred_revenue"])) > CENTS:
                diffs.append(f"{p}: deferred revenue waterfall does not roll")
            if abs(num(a["beginning_accounts_receivable"]) + num(a["new_billings"]) - num(a["cash_collections"]) - num(a["ending_accounts_receivable"])) > CENTS:
                diffs.append(f"{p}: AR rollforward does not roll")
            if prev_dr is not None and abs(num(d["beginning_deferred_revenue"]) - prev_dr) > CENTS:
                diffs.append(f"{p}: deferred revenue beginning {money(num(d['beginning_deferred_revenue']))} vs prior ending {money(prev_dr)}")
            if prev_ar is not None and abs(num(a["beginning_accounts_receivable"]) - prev_ar) > CENTS:
                diffs.append(f"{p}: AR beginning {money(num(a['beginning_accounts_receivable']))} vs prior ending {money(prev_ar)}")
            prev_dr, prev_ar = num(d["ending_deferred_revenue"]), num(a["ending_accounts_receivable"])
        rep.check(f"{v} rollforwards roll month to month" + (f" and pick up Actual {prior(start)}" if start else ""), diffs)

        diffs = compare("deferred revenue waterfall vs GL 2100", {p: num(dr[p]["ending_deferred_revenue"]) for p in ms},
                        {p: bs_line(v, p, "deferred_revenue") for p in ms}, ms)
        diffs += compare("waterfall revenue vs GL revenue", {p: num(dr[p]["revenue_recognized"]) for p in ms},
                         {p: pl[v][p]["revenue"] for p in ms}, ms)
        diffs += compare("AR rollforward vs GL 1100", {p: num(ar[p]["ending_accounts_receivable"]) for p in ms},
                         {p: bs_line(v, p, "accounts_receivable") for p in ms}, ms)
        rep.check(f"{v} deferred revenue and AR ending balances = GL", diffs)

        carried = [r for r in sched_all["Actual"] if not start or r["period"][:7] < start] if v != "Actual" else []
        collect = sums(sched_all[v] + carried, "collection_period", "billings")
        check_ms = [p for p in ms if p >= "2024-03"]
        diffs = compare("collections vs invoices due", {p: num(ar[p]["cash_collections"]) for p in check_ms}, collect, check_ms)
        rep.check(f"{v} cash collections = invoices by collection month (due date + 7 days)", diffs)
        if v == "Actual":
            pre = sum((num(ar[p]["cash_collections"]) - collect.get(p, ZERO) for p in ms if p < "2024-03"), ZERO)
            opening = num(ar[ms[0]]["beginning_accounts_receivable"])
            rep.check("Actual Jan-Feb 2024 collections of invoices issued before 2024 = opening AR",
                      [] if abs(pre - opening) <= CENTS else [f"{money(pre)} vs {money(opening)}"], money(opening))

    # ------------------------------------------------------------------ cash flow
    rep.section("Cash flow statement, cash collections, cash bridge")
    for v in VERSIONS:
        ms = months[v]
        cf = {r["period"][:7]: r for r in f(f"{v}_cash_flow_statement.csv")}
        diffs = []
        for p in ms:
            r = cf[p]
            net = num(r["net_cash_from_operating_activities"]) + num(r["net_cash_from_investing_activities"]) + num(r["net_cash_from_financing_activities"])
            if abs(net - num(r["net_change_in_cash"])) > CENTS:
                diffs.append(f"{p}: sections do not add to net change")
            if abs(num(r["beginning_cash"]) + net - num(r["ending_cash"])) > CENTS:
                diffs.append(f"{p}: beginning + net change != ending")
            if abs(num(r["ending_cash"]) - bs_line(v, p, "cash")) > CENTS:
                diffs.append(f"{p}: ending cash {money(num(r['ending_cash']))} vs GL {money(bs_line(v, p, 'cash'))}")
            if p in balance[v] and prior(p) in balance[v] and abs(num(r["beginning_cash"]) - bs_line(v, prior(p), "cash")) > CENTS:
                diffs.append(f"{p}: beginning cash vs GL prior month")
            if abs(num(r["net_income"]) - pl[source(v, p)][p]["net_income"]) > CENTS:
                diffs.append(f"{p}: net income vs GL")
            if prior(p) in balance[v]:
                d_dr = bs_line(v, p, "deferred_revenue") - bs_line(v, prior(p), "deferred_revenue")
                d_ar = bs_line(v, p, "accounts_receivable") - bs_line(v, prior(p), "accounts_receivable")
                if abs(num(r["change_in_deferred_revenue"]) - d_dr) > CENTS or abs(num(r["change_in_accounts_receivable"]) + d_ar) > CENTS:
                    diffs.append(f"{p}: working capital changes vs GL")
        rep.check(f"{v} cash flow statement adds up and ties to GL cash, net income and working capital", diffs)

        cc = {r["period"][:7]: r for r in f(f"{v}_cash_collections.csv")}
        ar = {r["period"][:7]: r for r in f(f"{v}_accounts_receivable_rollforward.csv")}
        diffs = [p for p in ms if abs(num(cc[p]["cash_collections"]) - num(ar[p]["cash_collections"])) > CENTS
                 or abs(num(cc[p]["ending_cash"]) - bs_line(v, p, "cash")) > CENTS]
        rep.check(f"{v} cash collections file = AR collections and GL cash", diffs)

        path = os.path.join(v5, f"{v}_cash_flow_bridge.csv")
        if os.path.exists(path):
            br = read(path)[1]
            diffs, others = [], []
            fin_key = "financing_to_maintain_cash_floor" if "financing_to_maintain_cash_floor" in br[0] else "financing"
            for r in br:
                p = r["period"][:7]
                out = sum((num(r[k]) for k in ("payroll_cash_out", "commission_cash_out", "vendor_cash_out_n30", "tax_cash_out",
                                               "interest_cash_out", "other_operating_cash_out", "capex")), ZERO)
                end = num(r["beginning_cash"]) + num(r["cash_collections_from_invoices"]) - out + num(r[fin_key])
                if abs(end - num(r["ending_cash"])) > CENTS or abs(num(r["ending_cash"]) - bs_line(v, p, "cash")) > CENTS:
                    diffs.append(p)
                if abs(num(r["cash_collections_from_invoices"]) - num(ar[p]["cash_collections"])) > CENTS:
                    diffs.append(f"{p} collections")
                others.append(num(r["other_operating_cash_out"]))
            rep.check(f"{v} cash bridge adds up to GL cash; collections = AR rollforward", diffs, f"{len(br)} months")
            neg = [o for o in others if o < 0]
            if neg:
                rep.flag(f"{v} cash bridge other operating cash out is negative in {len(neg)} of {len(others)} months "
                         f"({money(min(others))} to {money(max(others))}): payroll and commission lines are larger than "
                         f"the GL implies (headcount-plan payroll and commission payouts do not tie to GL expense)")

    # ------------------------------------------------------------------ cash path and caps
    rep.section("Cash path and deferred revenue level")
    for v, p in (("Actual", "2024-01"), ("Actual", "2024-12"), ("Actual", "2025-12"), ("Actual", CLOSE),
                 ("Budget", "2026-12"), ("Forecast", "2026-12")):
        rep.info(f"{v} {p}: cash {money(bs_line(v, p, 'cash'))}, AR {money(bs_line(v, p, 'accounts_receivable'))}, "
                 f"deferred revenue {money(bs_line(v, p, 'deferred_revenue'))}")
    notes_path = os.path.join(v5, "v5_build_notes.txt")
    if os.path.exists(notes_path):
        with open(notes_path, encoding="utf-8") as fh:
            for line in fh:
                if "unrecognized invoice amounts" in line:
                    rep.info("build check, rollforward vs open invoices: " + line.strip())
    for v in VERSIONS:
        low = min(months[v], key=lambda p: bs_line(v, p, "cash"))
        rep.check(f"{v} cash stays above the {money(CASH_FLOOR)} floor",
                  [] if bs_line(v, low, "cash") >= CASH_FLOOR else [f"{low} {money(bs_line(v, low, 'cash'))}"],
                  f"lowest {low} {money(bs_line(v, low, 'cash'))}")
        high = max(months[v], key=lambda p: bs_line(v, p, "deferred_revenue"))
        rep.check(f"{v} deferred revenue under the {money(DEFERRED_REVENUE_CAP)} cap",
                  [] if bs_line(v, high, "deferred_revenue") <= DEFERRED_REVENUE_CAP else [f"{high}"],
                  f"highest {high} {money(bs_line(v, high, 'deferred_revenue'))}")

    # ------------------------------------------------------------------ billing mix
    rep.section("Billing terms")
    cad = defaultdict(int)
    for r in f("Actual_customers.csv"):
        cad[r["billing_cadence"]] += 1
    annual_opps = sum(1 for v in VERSIONS for r in f(f"{v}_opportunities.csv") if r["billing_cadence"] == "Annual")
    rep.check("no annual billing (customers and opportunities)",
              [f"customers {dict(cad)}"] * ("Annual" in cad) + ([f"{annual_opps} opportunities"] if annual_opps else []),
              f"customers by cadence {dict(cad)}")
    monthly_due = [r["invoice_id"] for v in VERSIONS for r in f(f"{v}_invoices.csv")
                   if r["billing_cadence"] == "Monthly" and r["invoice_date"][8:10] != "01"]
    rep.check("monthly invoices dated the 1st", monthly_due)
    q_bad = []
    for v in VERSIONS:
        for r in f(f"{v}_invoices.csv"):
            if r["billing_cadence"] == "Quarterly":
                start, inv_date = r["service_period_start"][:7], r["invoice_date"][:7]
                if prior(start) != inv_date:
                    q_bad.append(r["invoice_id"])
    rep.check("quarterly invoices issued the month before the quarter starts (about 30 days ahead)", q_bad)

    # ------------------------------------------------------------------ MRR
    rep.section("ARR waterfall")
    for v in VERSIONS:
        rows = f(f"{v}_MRR_Waterfall.csv")
        diffs, prev_end = [], None
        for r in rows:
            bop, nb, ex = num(r["beginning_arr"]), num(r["new_business_arr"]), num(r["expansion_arr"])
            co, ch, re_ = num(r["contraction_arr"]), num(r["churn_arr"]), num(r["reactivation_arr"])
            p = r["period"][:7]
            if abs(bop + nb + ex + re_ - co - ch - num(r["ending_arr"])) > 1:
                diffs.append(f"{p}: ending ARR")
            if abs(num(r["net_new_arr"]) - (nb + ex + re_ - co - ch)) > 1 or abs(num(r["renewal_arr"]) - (bop - co - ch)) > 1:
                diffs.append(f"{p}: net new or renewal")
            if abs(num(r["gross_retention_rate"]) - (bop - co - ch) / bop) > Decimal("0.0001"):
                diffs.append(f"{p}: GRR {r['gross_retention_rate']}")
            if abs(num(r["net_dollar_retention_rate"]) - (bop + ex + re_ - co - ch) / bop) > Decimal("0.0001"):
                diffs.append(f"{p}: NRR {r['net_dollar_retention_rate']}")
            if prev_end is not None and abs(bop - prev_end) > 1:
                diffs.append(f"{p}: beginning ARR vs prior ending")
            prev_end = num(r["ending_arr"])
        rep.check(f"{v} ARR waterfall: movements, renewal, GRR and NRR computed from components; months chain", diffs,
                  f"{len(rows)} months")
    a_mrr = {r["period"][:7]: r for r in f("Actual_MRR_Waterfall.csv")}
    if "2026-06" in a_mrr:
        r = a_mrr["2026-06"]
        rep.info(f"Actual June 2026 GRR {r['gross_retention_rate']}, NRR {r['net_dollar_retention_rate']}")

    # ------------------------------------------------------------------ sales
    rep.section("Sales: roster, quotas, opportunities, commissions")
    quotas = f("Actual_Sales_Quotas.csv")
    roster = {r["employee_id"]: r["rep_name"] for r in quotas}
    by_name = {n: i for i, n in roster.items()}
    q_months = sorted({r["period"][:7] for r in quotas})
    in_close = {r["employee_id"] for r in quotas if r["period"][:7] == CLOSE}
    rep.check("quotas run through the June close for every rep",
              [] if q_months and q_months[-1] == CLOSE and in_close == set(roster)
              else [f"months {q_months[0]}..{q_months[-1]}; {len(in_close)} of {len(roster)} reps in {CLOSE}"],
              f"{len(roster)} reps, {q_months[0]}..{q_months[-1]}; reps hired in 2026 start at their hire month")
    budget_q = f("Budget_Sales_Quotas.csv")
    rep.flag(f"Budget_Sales_Quotas.csv is a separate planning roster ({len({r['employee_id'] for r in budget_q})} "
             f"BSALES IDs with placeholder names); not mapped to the Actual roster")
    reps_files = [n for v in VERSIONS for n in [f"{v}_sales_reps.csv"]
                  if {r["rep_id"]: r["rep_name"] for r in f(n)} != roster]
    rep.check("sales_reps files = quota roster (IDs and names)", reps_files)
    opp_owner_bad = sorted({r["owner"] for v in VERSIONS for r in f(f"{v}_opportunities.csv") if r["owner"] not in by_name})
    rep.check("every opportunity owner is a roster rep", opp_owner_bad)
    opps = f("Actual_opportunities.csv")
    won_nb = defaultdict(Decimal)
    for o in opps:
        if o["opportunity_type"] == "New Business" and o["close_status"] == "Closed Won":
            won_nb[(o["period"][:7], by_name[o["owner"]])] += num(o["amount_arr"])
    diffs = []
    for r in quotas:
        if r["quota_type"] != "Bookings ARR":
            continue
        a = won_nb.get((r["period"][:7], r["employee_id"]), ZERO)
        if abs(num(r["quota_attainment_actual_arr"]) - a) > CENTS:
            diffs.append(f"{r['period']} {r['employee_id']}: {r['quota_attainment_actual_arr']} vs closed-won {a:.2f}")
        ramped = num(r["ramped_monthly_quota_arr"])
        if ramped and abs(num(r["quota_attainment_pct"]) - a / ramped) > Decimal("0.0001"):
            diffs.append(f"{r['period']} {r['employee_id']}: attainment %")
    rep.check("AE quota attainment = closed-won new business owned by the rep", diffs)
    nb_by_p = defaultdict(Decimal)
    for (p, _), a in won_nb.items():
        nb_by_p[p] += a
    rep.info("team attainment by month: " + ", ".join(
        f"{p} {sum(num(x['quota_attainment_actual_arr']) for x in quotas if x['period'][:7] == p and x['quota_type'] == 'Bookings ARR') / sum(num(x['ramped_monthly_quota_arr']) for x in quotas if x['period'][:7] == p and x['quota_type'] == 'Bookings ARR'):.0%}"
        for p in q_months))
    mrr_nb = {p: num(a_mrr[p]["new_business_arr"]) for p in q_months if p in a_mrr}
    gap = {p: nb_by_p[p] - mrr_nb[p] for p in mrr_nb}
    if any(abs(g) > 1 for g in gap.values()):
        rep.flag("closed-won new business (opportunities) vs ARR waterfall new business, by month: "
                 + ", ".join(f"{p} {money(nb_by_p[p])} vs {money(mrr_nb[p])}" for p in sorted(gap)))
    else:
        rep.check("closed-won new business = ARR waterfall new business", [])

    pay = f("Actual_commission_payouts.csv")
    opp_by_id = {o["opportunity_id"]: o for o in opps}
    diffs = []
    for r in pay:
        o = opp_by_id.get(r["opportunity_id"])
        if r["rep_id"] not in roster or roster[r["rep_id"]] != r["rep_name"]:
            diffs.append(f"{r['commission_id']}: rep {r['rep_id']} {r['rep_name']}")
        elif o is None or o["owner"] != r["rep_name"] or abs(num(o["amount_arr"]) - num(r["booked_arr"])) > CENTS:
            diffs.append(f"{r['commission_id']}: opportunity owner or amount")
        elif abs(num(r["booked_arr"]) * num(r["commission_rate"]) - num(r["commission_amount"])) > CENTS:
            diffs.append(f"{r['commission_id']}: amount != booked x rate")
    by_p = sums(pay, "period", "commission_amount")
    rep.check("commission payouts: rep IDs on the roster, owner and amount from the opportunity, amount = ARR x rate", diffs,
              f"{len(pay)} payouts, " + ", ".join(f"{p} {money(a)}" for p, a in sorted(by_p.items())))
    gl6200 = defaultdict(Decimal)
    for r in gl["Actual"]:
        if r["account_number"] == "6200":
            gl6200[r["period"][:7]] += num(r["amount"])
    rep.flag("GL 6200 Sales Commissions vs payouts: " + ", ".join(
        f"{p} {money(gl6200[p])} vs {money(by_p.get(p, ZERO))}" for p in q_months)
             + " (capitalized commissions are not modeled; the GL expense is not the cash paid)")

    stray = defaultdict(set)
    for n in sorted(v5_files):
        h, rows = read(os.path.join(v5, n))
        for col in ("rep_id", "employee_id", "owner_id", "csm_id", "rep_name"):
            if col in h and n not in ("Actual_Sales_Quotas.csv", "Budget_Sales_Quotas.csv") and not n.endswith("_sales_reps.csv"):
                for r in rows:
                    val = r[col]
                    if col == "rep_name":
                        if val and val not in by_name:
                            stray[n].add(val)
                    elif val.startswith(("REP-", "ASALES-")) and val not in roster:
                        stray[n].add(val)
    for n, vals in sorted(stray.items()):
        rep.flag(f"{n} has rep IDs/names not on the quota roster ({len(vals)}): {', '.join(sorted(vals)[:6])}")

    # ------------------------------------------------------------------ workforce
    rep.section("Workforce")
    reqs = read(os.path.join(v5, "Forecast_Open_Requisitions.csv"))[1]
    early = [r["req_id"] for r in reqs if r["status"] == "Open" and r["planned_start_date"][:7] <= CLOSE]
    rep.check("no open requisition starts on or before the June close", early, f"{sum(1 for r in reqs if r['status'] == 'Open')} open reqs")
    a_hp = {(r["period"][:7], r["department"]): r for r in f("Actual_Headcount_Plan.csv")}
    f_hp = {(r["period"][:7], r["department"]): r for r in f("Forecast_Headcount_Plan.csv")}
    diffs = [f"{d}: Actual {a_hp[(CLOSE, d)]['headcount_ending']} vs Forecast {f_hp[(CLOSE, d)]['headcount_ending']}"
             for (p, d) in a_hp if p == CLOSE and (CLOSE, d) in f_hp
             and a_hp[(CLOSE, d)]["headcount_ending"] != f_hp[(CLOSE, d)]["headcount_ending"]]
    rep.check("Forecast headcount at June = Actual headcount at June, by department", diffs)
    rep.check("Hiring_Ramp_Assumptions.csv present (loader expands it for every role)",
              [] if os.path.exists(os.path.join(v5, "Hiring_Ramp_Assumptions.csv")) else ["missing"])

    # ------------------------------------------------------------------ marketing
    rep.section("Marketing")
    for v in VERSIONS:
        mp = f(f"{v}_marketing_pipeline.csv")
        spend = sums(mp, "period", "marketing_spend")
        ms = [p for p in sorted(spend) if pl[source(v, p)][p]["programs"]]
        diffs = compare("pipeline spend vs GL programs", spend, {p: pl[source(v, p)][p]["programs"] for p in ms}, ms)
        missing = [p for p in sorted(spend) if not pl[source(v, p)][p]["programs"]]
        rep.check(f"{v} marketing spend = GL marketing program accounts", diffs,
                  f"{len(ms)} months" + (f"; no GL program spend in {missing}" if missing else ""))
    ch = sums(f("Actual_marketing_spend_by_channel.csv"), "period", "marketing_spend")
    a_mp = sums(f("Actual_marketing_pipeline.csv"), "period", "marketing_spend")
    rep.check("Actual marketing spend by channel = marketing pipeline", compare("by channel", ch, a_mp, sorted(ch)))
    fs = {r["period"][:7]: num(r["forecast_marketing_spend"]) for r in f("Forecast_marketing_pipeline_summary.csv")}
    rep.check("Forecast marketing pipeline summary spend = GL programs",
              compare("summary", fs, {p: pl[source("Forecast", p)][p]["programs"] for p in fs}, sorted(fs)))
    return rep


KNOWN_GAPS = [
    "Implementation fees are billed and recognized at signing (not spread over the implementation period).",
    "Budget deferred revenue differs from the unrecognized amount on its invoices (see the build check line above): "
    "Budget recognizes Budget revenue against invoices billed before 2026 at Actual amounts.",
    "Renewal commissions and the renewal pipeline still use CSM rep IDs and run only to May 2026.",
    "Employees (EMP IDs) are not linked to the ASALES quota roster; sales_reps manager_id holds the manager title.",
    "FY24/FY25 headcount-plan payroll does not tie to GL payroll (GL detail for those months is cloned from Jan 2026).",
    "Budget and Forecast 2026 new logos are not in the customer master; Budget implementation invoices reference them.",
    "Roster region EMEA renamed South; renewal_arr redefined as beginning ARR less contraction and churn.",
    "Budget Engine still assumes 0.16 months of revenue deferred; reading it from data is a later code change.",
]


if __name__ == "__main__":
    v4_dir, v5_dir, gl = sys.argv[1:4]
    out = sys.argv[4] if len(sys.argv) > 4 else os.path.join(v5_dir, "v5_tie_out_report.md")
    report = main(v4_dir, v5_dir, gl)
    text = ["# v5 dataset tie-out", "", f"source v4: {v4_dir}", f"v5: {v5_dir}", f"GL: {gl}",
            "", f"**{report.failures} failing checks**"] + report.lines + ["\n## Known gaps (not fixed in v5)\n"] + \
           [f"- {g}" for g in KNOWN_GAPS]
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(text) + "\n")
    print("\n".join(text))
    sys.exit(1 if report.failures else 0)
