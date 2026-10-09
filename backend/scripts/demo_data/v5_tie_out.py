"""Tie-out report for the v5/v6 dataset: every file against the GL and against each other.

  python v5_tie_out.py <prior_folder> <dataset_folder> <gl_folder> [report.md] [--prior-gl <prior_gl_folder>]

Each check is PASS or FAIL; gaps that are known and accepted are listed as FLAG with the number.
Columns added on purpose (ADDED_COLUMNS) are allowed in the schema check. When the dataset has
<version>_commission_schedule.csv, the ASC 340-40 commission section recomputes the schedule,
rollforward, amortization and GL postings independently. When the prior dataset has no commission
schedule, a change-scope section checks that nothing else moved (GL accounts need --prior-gl).
Exit code 1 if any check fails.
"""

from __future__ import annotations

import calendar
import csv
import datetime as dt
import os
import sys
from collections import Counter, defaultdict
from decimal import ROUND_HALF_UP, Decimal

ZERO = Decimal("0")
CLOSE = "2026-06"
VERSIONS = ("Actual", "Budget", "Forecast")
CHAIN_FROM_ACTUAL = {"Budget": "2026-01", "Forecast": "2026-07"}
CASH_FLOOR = Decimal("10000000")
DEFERRED_REVENUE_CAP = Decimal("10000000")
CENTS = Decimal("0.02")
REVENUE_ACCOUNTS = {"4000": "Subscription", "4100": "Implementation & Onboarding", "4200": "Recurring Services"}
BS_ACCOUNTS = {"1000": ("cash", 1), "1100": ("accounts_receivable", 1), "1200": ("prepaids_and_other_current", 1),
               "1250": ("deferred_commissions_current", 1), "1500": ("ppe_net", 1),
               "1550": ("deferred_commissions_noncurrent", 1), "2000": ("accounts_payable", -1),
               "2100": ("deferred_revenue", -1), "2500": ("debt", -1), "2600": ("other_liabilities", -1)}
ADDED_COLUMNS = {
    "_commission_plans.csv": ("capitalize", "amortization_months", "payout_basis", "payout_lag_months",
                              "capitalize_payroll_taxes"),
    "_balance_sheet.csv": ("deferred_commissions_current", "deferred_commissions_noncurrent"),
    "_cash_flow_statement.csv": ("change_in_deferred_commissions",),
    "_commission_payouts.csv": ("commission_base_arr",),
    "_Employees.csv": ("cost_center", "termination_type", "pay_plan", "bonus_target_pct", "retirement_deferral_pct"),
}
PAYROLL_REGISTER_SUFFIX = "_payroll_register.csv"
REGISTER_ACCOUNTS = {"regular_wages": "6100", "bonus": "6105", "employer_payroll_tax": "6110", "retirement_match": "6115",
                     "health_benefits": "6120", "severance": "6125"}
COGS_PAYROLL = {"SUP-TIER1": "5010", "CS-IMPL": "5020"}
PAYROLL_ACCOUNTS = set(REGISTER_ACCOUNTS.values()) | set(COGS_PAYROLL.values())
EXPENSE_LINES = {"Sales": "S&M", "Marketing": "S&M", "Customer Success": "S&M", "Engineering": "R&D", "Product": "R&D",
                 "Finance": "G&A", "G&A": "G&A", "Support": "G&A"}
REGISTER_WINDOW = {"Actual": ("2024-01", CLOSE), "Budget": ("2026-01", "2026-12"), "Forecast": ("2026-07", "2026-12")}
HISTORY_FILE = "Actual_customer_arr_history.csv"
WINBACK_WINDOW = 6
SEGMENT_FLOORS = (("Enterprise", Decimal(500000)), ("Mid-Market", Decimal(100000)), ("SMB", ZERO))
IMPLEMENTATION_FEE = {"SMB": Decimal(2000), "Mid-Market": Decimal(3500), "Enterprise": Decimal(5000)}
COMMISSION_SOURCE_SUFFIX = "_deferred_commissions_rollforward.csv"
TERRITORIES = ("Central", "East", "South", "West")
TEAM_DEPARTMENTS = ("Sales", "Customer Success")
BOOKINGS_ROLES = ("Account Executive", "Senior Account Executive")
PIPELINE_ROLES = ("Sales Development Rep",)
CSM_ROLES = ("Customer Success Manager", "Senior Customer Success Manager")
PERSON_COLUMNS = {"rep_id": "id", "employee_id": "id", "owner_id": "id", "csm_id": "id", "rep_name": "name",
                  "owner": "name", "customer_success_manager": "name"}
NON_VENDOR_CATEGORIES = {"revenue", "d&a", "interest", "taxes", "tax"}
NON_VENDOR_EXPENSE_TYPES = {"salaries and wages", "bonus", "payroll taxes", "retirement match", "benefits", "severance",
                            "labor", "commissions"}


def is_vendor_expense(r: dict[str, str]) -> bool:
    return (r["statement"] != "Balance Sheet" and r["account_group"] != "D&A"
            and r["statement_category"].strip().lower() not in NON_VENDOR_CATEGORIES
            and (r["expense_type"] or "").strip().lower() not in NON_VENDOR_EXPENSE_TYPES)


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


def cents(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), ROUND_HALF_UP)


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


def main(v4: str, v5: str, gl_dir: str, prior_gl: str | None = None) -> Report:
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
    rep.section("Warehouse schema (columns = prior dataset, plus columns added on purpose)")
    v4_files = {n for n in os.listdir(v4) if n.endswith(".csv")}
    v5_files = {n for n in os.listdir(v5) if n.endswith(".csv")}
    header_diffs, blank_org, added = [], [], []
    for n in sorted(v4_files & v5_files):
        h4, r4 = read(os.path.join(v4, n))
        h5, r5 = read(os.path.join(v5, n))
        allowed = next((cols for suffix, cols in ADDED_COLUMNS.items() if n.endswith(suffix)), ())
        new_cols = [c for c in h5 if c not in h4]
        if [c for c in h5 if c not in allowed] != [c for c in h4 if c not in allowed] or any(c not in allowed for c in new_cols):
            header_diffs.append(n)
        elif new_cols:
            added.append(f"{n} (+{', '.join(new_cols)})")
        if "organization_id" in h5 and all(r.get("organization_id") for r in r4) and any(not r.get("organization_id") for r in r5):
            blank_org.append(n)
    rep.check("same columns in every file", header_diffs, f"{len(v4_files & v5_files)} files")
    rep.check("organization_id filled wherever the prior dataset had it", blank_org)
    if added:
        rep.info(f"columns added on purpose: {'; '.join(added)}")
    rep.info(f"removed: {sorted(v4_files - v5_files) or 'none'}")
    rep.info(f"new files: {sorted(v5_files - v4_files) or 'none'}")

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
                if name not in r and bs_line(v, p, name) == 0:
                    continue
                if abs(num(r.get(name)) - bs_line(v, p, name)) > CENTS:
                    diffs.append(f"{p} {name}: file {money(num(r.get(name)))} vs GL {money(bs_line(v, p, name))}")
            listed = sum((num(r.get(name)) for _, (name, sign) in BS_ACCOUNTS.items() if sign > 0), ZERO)
            if abs(listed - num(r["total_assets"])) > CENTS:
                diffs.append(f"{p}: asset lines add to {money(listed)}, total assets {money(num(r['total_assets']))}")
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
                d_dc = sum((bs_line(v, p, k) - bs_line(v, prior(p), k)
                            for k in ("deferred_commissions_current", "deferred_commissions_noncurrent")), ZERO)
                if abs(num(r.get("change_in_deferred_commissions")) + d_dc) > CENTS:
                    diffs.append(f"{p}: change in deferred commissions {money(num(r.get('change_in_deferred_commissions')))} "
                                 f"vs GL {money(-d_dc)}")
        rep.check(f"{v} cash flow statement adds up and ties to GL cash, net income and working capital", diffs)

        cc = {r["period"][:7]: r for r in f(f"{v}_cash_collections.csv")}
        ar = {r["period"][:7]: r for r in f(f"{v}_accounts_receivable_rollforward.csv")}
        diffs = [p for p in ms if abs(num(cc[p]["cash_collections"]) - num(ar[p]["cash_collections"])) > CENTS
                 or abs(num(cc[p]["ending_cash"]) - bs_line(v, p, "cash")) > CENTS]
        rep.check(f"{v} cash collections file = AR collections and GL cash", diffs)

        ap_by = {r["period"][:7]: r for r in f(f"{v}_accounts_payable_rollforward.csv")}
        prepaid = {r["period"][:7]: r for r in f(f"{v}_Prepaids_Rollforward.csv")}
        spend = sums(gl[v], "period", "amount", is_vendor_expense)
        diffs = []
        for p in ms:
            if p == cutoff:
                continue
            r = ap_by.get(p)
            if r is None:
                diffs.append(f"{p}: no AP rollforward row")
                continue
            begin, end = bs_line(v, prior(p), "accounts_payable"), bs_line(v, p, "accounts_payable")
            invoiced = spend.get(p, ZERO) + movement[source(v, p)][p].get("3311", ZERO) \
                - num(prepaid.get(p, {}).get("prepaid_amortization"))
            for label, got, want in (("beginning", r["beginning_accounts_payable"], begin),
                                     ("invoices", r["vendor_expense_accruals"], invoiced),
                                     ("payments", r["vendor_cash_payments_n30"], begin),
                                     ("ending", r["ending_accounts_payable"], end)):
                if abs(num(got) - want) > CENTS:
                    diffs.append(f"{p} {label} {money(num(got))} vs {money(want)}")
        rep.check(f"{v} AP rollforward = GL: invoices = non-payroll expense less stock comp and prepaid amortization; "
                  f"paid net 30 (payments = opening AP)", diffs, f"{len([p for p in ms if p != cutoff])} months")

        path = os.path.join(v5, f"{v}_cash_flow_bridge.csv")
        if os.path.exists(path):
            br = read(path)[1]
            tax = sums(gl[v], "period", "amount", lambda r: r["statement_category"] in ("Taxes", "Tax"))
            interest = sums(gl[v], "period", "amount", lambda r: r["statement_category"] == "Interest")
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
                if p == cutoff:
                    continue
                if abs(num(r["vendor_cash_out_n30"]) - num(ap_by.get(p, {}).get("vendor_cash_payments_n30"))) > CENTS:
                    diffs.append(f"{p} vendor cash vs AP payments")
                if abs(num(r["tax_cash_out"]) - tax.get(p, ZERO)) > CENTS or \
                        abs(num(r["interest_cash_out"]) - interest.get(p, ZERO)) > CENTS:
                    diffs.append(f"{p} tax or interest cash vs GL expense")
                others.append(num(r["other_operating_cash_out"]))
            rep.check(f"{v} cash bridge adds up to GL cash; collections = AR rollforward; vendor cash = AP payments; "
                      f"tax and interest cash = GL expense", diffs, f"{len(br)} months")
            neg = [o for o in others if o < 0]
            if neg:
                rep.flag(f"{v} cash bridge other operating cash out is negative in {len(neg)} of {len(others)} months "
                         f"({money(min(others))} to {money(max(others))})")
            elif others:
                rep.info(f"{v} cash bridge other operating cash out {money(min(others))} to {money(max(others))} a month "
                         f"(prepaid purchases, payroll tax on commission payouts, billing timing)")

    # ------------------------------------------------------------------ cash path and caps
    rep.section("Cash path and deferred revenue level")
    for v, p in (("Actual", "2024-01"), ("Actual", "2024-12"), ("Actual", "2025-12"), ("Actual", CLOSE),
                 ("Budget", "2026-12"), ("Forecast", "2026-12")):
        rep.info(f"{v} {p}: cash {money(bs_line(v, p, 'cash'))}, AR {money(bs_line(v, p, 'accounts_receivable'))}, "
                 f"deferred revenue {money(bs_line(v, p, 'deferred_revenue'))}")
    for notes_name in sorted(n for n in os.listdir(v5) if n.endswith("_build_notes.txt")):
        with open(os.path.join(v5, notes_name), encoding="utf-8") as fh:
            for line in fh:
                if "unrecognized invoice amounts" in line:
                    rep.info("build check, rollforward vs open invoices: " + line.strip())
                elif notes_name.startswith("v6") and line.strip():
                    rep.info(f"{notes_name}: {line.strip()}")
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
    rep.section("Sales team: employees, quotas, opportunities, commissions")
    emps = {v: f(f"{v}_Employees.csv") for v in VERSIONS}
    team = {v: [e for e in emps[v] if e["department"] in TEAM_DEPARTMENTS] for v in VERSIONS}
    sales = {v: {e["employee_id"]: e for e in emps[v] if e["department"] == "Sales"} for v in VERSIONS}
    diffs = [f"{v} {e['employee_id']}: region {e['region']}" for v in VERSIONS for e in team[v] if e["region"] not in TERRITORIES]
    seen: dict[str, tuple] = {}
    for v in VERSIONS:
        for e in emps[v]:
            key = tuple(e[k] for k in ("employee_name", "department", "role", "region", "hire_date"))
            if seen.setdefault(e["employee_id"], key) != key:
                diffs.append(f"{v} {e['employee_id']}: name, role, territory or hire date differs from another version")
        diffs += [f"{v}: {n} used {c} times" for n, c in Counter(e["employee_name"] for e in emps[v]).items() if c > 1]
        diffs += [f"{v} {e['employee_id']}: quota_carrying {e['quota_carrying']} for {e['role']}" for e in sales[v].values()
                  if (e["quota_carrying"] == "Yes") != (e["role"] in BOOKINGS_ROLES + PIPELINE_ROLES)]
    rep.check("employees: Sales and Customer Success work a CRM territory; an ID has one name, role, territory and hire "
              "date in every version; names unique; quota-carrying = AE, Senior AE, SDR", diffs,
              "; ".join(f"{v} " + ", ".join(f"{t} {n}" for t, n in sorted(Counter(e["region"] for e in team[v]).items()))
                        for v in VERSIONS))

    curve: dict[int, dict[int, Decimal]] = defaultdict(dict)
    for r in f("Hiring_Ramp_Assumptions.csv"):
        curve[int(r["ramp_months"])][int(r["month_after_start"])] = num(r["productivity_pct"])

    def ramp(e: dict[str, str], p: str) -> Decimal:
        k = _pidx(p) - _pidx(e["hire_date"][:7]) + 1
        return ZERO if k < 1 else curve.get(int(e["productivity_ramp_months"] or 0), {}).get(k, Decimal(1))

    def on_staff(e: dict[str, str], p: str) -> bool:
        return e["hire_date"][:7] <= p and (not e["termination_date"] or e["termination_date"][:7] > p)

    quota_files = {"Actual": f("Actual_Sales_Quotas.csv"), "Budget": f("Budget_Sales_Quotas.csv")}
    for v, rows in quota_files.items():
        months_q = sorted({r["period"][:7] for r in rows})
        end = CLOSE if v == "Actual" else "2026-12"
        diffs = [] if months_q and (months_q[0], months_q[-1]) == ("2026-01", end) else [f"months {months_q[:1]}..{months_q[-1:]}"]
        got: dict[str, set[str]] = defaultdict(set)
        for r in rows:
            p = r["period"][:7]
            got[p].add(r["employee_id"])
            e = sales[v].get(r["employee_id"])
            if e is None:
                diffs.append(f"{p} {r['employee_id']}: not a {v} Sales employee")
                continue
            kind = ("Bookings ARR" if e["role"] in BOOKINGS_ROLES else
                    "Pipeline ARR" if e["role"] in PIPELINE_ROLES else "Non-Quota")
            annual = num(e["annual_quota_arr"]) if kind != "Non-Quota" else ZERO
            pct = ramp(e, p) if kind != "Non-Quota" else Decimal(1)
            if (r["rep_name"], r["role"], r["region"], r["hire_period"], r["quota_type"], r["productivity_ramp_months"]) != \
                    (e["employee_name"], e["role"], e["region"], e["hire_date"][:7], kind, e["productivity_ramp_months"]) \
                    or num(r["annual_quota_arr"]) != annual or num(r["ramp_pct"]) != pct \
                    or abs(num(r["ramped_monthly_quota_arr"]) - cents(cents(annual / 12) * pct)) > CENTS:
                diffs.append(f"{p} {r['employee_id']}: not its employee row or ramp")
        for p in months_q:
            want = {i for i, e in sales[v].items() if on_staff(e, p)}
            if got[p] != want:
                diffs.append(f"{p}: {len(got[p])} quota rows vs {len(want)} Sales employees on staff")
        rep.check(f"{v} quotas = the {v} Sales employees on staff each month (name, role, territory, hire month, quota; "
                  f"ramp from Hiring_Ramp_Assumptions.csv)", diffs, f"{len(rows)} rows {months_q[0]}..{months_q[-1]}")

    diffs = []
    for v in VERSIONS:
        reps = {r["rep_id"]: r for r in f(f"{v}_sales_reps.csv")}
        if set(reps) != set(sales[v]):
            diffs.append(f"{v}: {len(reps)} reps vs {len(sales[v])} Sales employees")
        diffs += [f"{v} {i}" for i, r in reps.items() if i in sales[v] and (r["rep_name"], r["role"], r["region"], r["hire_date"])
                  != tuple(sales[v][i][k] for k in ("employee_name", "role", "region", "hire_date"))]
    rep.check("sales_reps files = each version's Sales employees (ID, name, role, territory, hire date)", diffs)

    diffs, local = [], Counter()
    for v in VERSIONS:
        closers = {e["employee_name"]: e for e in sales[v].values() if e["role"] in BOOKINGS_ROLES}
        v_opps = f(f"{v}_opportunities.csv")
        owner_of = {o["opportunity_id"]: o["owner"] for o in v_opps}
        for o in v_opps:
            e, p = closers.get(o["owner"]), o["period"][:7]
            if e is None or not on_staff(e, p) or ramp(e, p) == 0:
                diffs.append(f"{v} {o['opportunity_id']}: owner {o['owner']} is not a ramped AE on staff in {p}")
            else:
                local[(v, e["region"] == o["region"])] += 1
        for r in f(f"{v}_opportunity_movements.csv"):
            if r["opportunity_id"] in owner_of and r["owner"] != owner_of[r["opportunity_id"]]:
                diffs.append(f"{v} movement {r['opportunity_id']}: owner differs from its opportunity")
            elif r["owner"] not in closers:
                diffs.append(f"{v} movement {r['opportunity_id']}: owner {r['owner']} is not a {v} AE")
    rep.check("opportunity owners are ramped AEs or Senior AEs on staff in the deal month (each version's own team); "
              "movements carry their deal's owner", diffs,
              ", ".join(f"{v} {local[(v, True)] / max(1, local[(v, True)] + local[(v, False)]):.0%} in the rep's territory"
                        for v in VERSIONS))

    quotas = quota_files["Actual"]
    roster = {i: e["employee_name"] for i, e in sales["Actual"].items()}
    by_name = {n: i for i, n in roster.items()}
    q_months = sorted({r["period"][:7] for r in quotas})
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
        elif abs(num(r.get("commission_base_arr") or r["booked_arr"]) * num(r["commission_rate"]) - num(r["commission_amount"])) > CENTS:
            diffs.append(f"{r['commission_id']}: amount != commission base x rate")
    by_p = sums(pay, "period", "commission_amount")
    rep.check("commission payouts: rep IDs on the roster, owner and amount from the opportunity, "
              "amount = commission base x rate", diffs,
              f"{len(pay)} payouts, " + ", ".join(f"{p} {money(a)}" for p, a in sorted(by_p.items())))
    plans = {r["plan_id"]: r for r in f("Actual_commission_plans.csv")}
    diffs = [f"{r['commission_id']}: rate {r['commission_rate']} not the plan's base or accelerated rate"
             for r in pay + f("Actual_renewal_commissions.csv")
             if r["plan_id"] in plans and num(r["commission_rate"]) not in
             (num(plans[r["plan_id"]]["base_commission_rate"]), num(plans[r["plan_id"]]["accelerated_rate"]))]
    rep.check("every payout rate is its plan's base or accelerated rate", diffs)

    hist = f(HISTORY_FILE) if os.path.exists(os.path.join(v5, HISTORY_FILE)) else None
    plan_hists = {}
    if hist is not None:
        history_section(rep, f, hist, a_mrr)
        a_eop = snapshots(hist, list(a_mrr), min(a_mrr))
        for v in ("Budget", "Forecast"):
            if os.path.exists(os.path.join(v5, f"{v}_customer_arr_history.csv")):
                plan_history_section(rep, f, v, hist, a_eop)
                plan_hists[v] = f(f"{v}_customer_arr_history.csv")
        segment_section(rep, f, hist)
    if os.path.exists(os.path.join(v5, "Actual_commission_schedule.csv")):
        commission_section(rep, f, gl, months, chain_months, source, bs_line, a_mrr, hist, plan_hists)
        if not os.path.exists(os.path.join(v4, "Actual_commission_schedule.csv")):
            change_scope_section(rep, v4, v5, gl_dir, prior_gl)
    else:
        gl6200 = defaultdict(Decimal)
        for r in gl["Actual"]:
            if r["account_number"] == "6200":
                gl6200[r["period"][:7]] += num(r["amount"])
        rep.flag("GL 6200 Sales Commissions vs payouts: " + ", ".join(
            f"{p} {money(gl6200[p])} vs {money(by_p.get(p, ZERO))}" for p in q_months)
                 + " (commission expense is not in the GL; the GL expense is not the cash paid)")

    state_region = {o["customer_state"]: o["region"] for v in VERSIONS for o in f(f"{v}_opportunities.csv")}
    cust_region = {c["customer_id"]: state_region.get(c["billing_state"], "") for v in VERSIONS for c in f(f"{v}_customers.csv")}
    diffs, csm_of = [], {}
    for v in ("Actual", "Forecast"):
        csms = {e["employee_name"]: e for e in team[v] if e["role"] in CSM_ROLES}
        for r in f(f"{v}_renewal_pipeline.csv"):
            e, p = csms.get(r["customer_success_manager"]), r["renewal_period"][:7]
            if e is None or not on_staff(e, p):
                diffs.append(f"{v} {r['renewal_id']}: {r['customer_success_manager']} is not a CSM on staff in {p}")
            elif csm_of.setdefault(r["customer_id"], e["employee_id"]) != e["employee_id"]:
                diffs.append(f"{v} {r['renewal_id']}: {r['customer_id']} has another CSM")
            elif e["region"] != cust_region.get(r["customer_id"]) and any(
                    x["region"] == cust_region.get(r["customer_id"]) and on_staff(x, p) for x in csms.values()):
                diffs.append(f"{v} {r['renewal_id']}: CSM outside the customer's territory")
    csm_ids = {e["employee_id"]: e["employee_name"] for e in team["Actual"] if e["role"] in CSM_ROLES}
    diffs += [f"{r['commission_id']}: {r['rep_id']} {r['rep_name']} is not an Actual CSM"
              for r in f("Actual_renewal_commissions.csv") if csm_ids.get(r["rep_id"]) != r["rep_name"]]
    rep.check("renewal CSMs are CSM employees on staff, in the customer's territory where it has one, one CSM per "
              "customer; renewal commissions are paid to the CSM's employee ID", diffs,
              f"{len(set(csm_of.values()))} CSMs, {len(csm_of)} customers, up to "
              f"{max(Counter(csm_of.values()).values(), default=0)} accounts each")

    nb = defaultdict(Decimal)
    for v, status, col in (("Actual", "Closed Won", "amount_arr"), ("Forecast", "Open", "weighted_arr")):
        for o in f(f"{v}_opportunities.csv"):
            if o["opportunity_type"] == "New Business" and o["close_status"] == status:
                nb[(o["period"][:7], o["region"])] += num(o[col])
    cap = f("Forecast_quota_capacity.csv")
    diffs = [f"{p}: {n} rows" for p, n in Counter(r["period"][:7] for r in cap).items() if n != len(TERRITORIES)]
    for r in cap:
        p, t = r["period"][:7], r["region"]
        mine = [e for e in sales["Forecast"].values() if e["role"] in BOOKINGS_ROLES and on_staff(e, p) and e["region"] == t]
        if num(r["quota_carrying_reps"]) != len(mine) or num(r["quota_capacity_arr"]) != sum((num(e["annual_quota_arr"]) for e in mine), ZERO) \
                or abs(num(r["expected_bookings_arr"]) - nb[(p, t)]) > CENTS:
            diffs.append(f"{p} {t}: {r['quota_carrying_reps']} reps {r['quota_capacity_arr']} vs {len(mine)} AEs on staff")
    last_cap = max((r["period"][:7] for r in cap), default="")
    rep.check("Forecast quota capacity by territory = Forecast AEs and Senior AEs on staff (count, annual quota); expected "
              "bookings = the month's new business (Actual closed won through the close, Forecast weighted ARR after)", diffs,
              f"{last_cap}: {money(sum((num(r['quota_capacity_arr']) for r in cap if r['period'][:7] == last_cap), ZERO))} "
              f"annual quota across {len(TERRITORIES)} territories")

    ids = {e["employee_id"] for v in VERSIONS for e in emps[v]}
    names = {e["employee_name"] for v in VERSIONS for e in emps[v]}
    stray = defaultdict(set)
    for n in sorted(v5_files):
        h, rows = read(os.path.join(v5, n))
        for col, kind in PERSON_COLUMNS.items():
            if col in h:
                stray[n].update(r[col] for r in rows if r[col] and r[col] not in (ids if kind == "id" else names))
    rep.check("every rep, owner, CSM and employee ID or name in any file is an employee",
              [f"{n} ({len(vals)}): {', '.join(sorted(vals)[:4])}" for n, vals in sorted(stray.items()) if vals])

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
    for v in VERSIONS:
        diffs, hp_months, backcast = [], set(), defaultdict(list)
        for r in f(f"{v}_Headcount_Plan.csv"):
            p = r["period"][:7]
            act = [e for e in emps[v] if e["department"] == r["department"] and on_staff(e, p)]
            if f"{v}_Employees" not in r["source"]:
                backcast[r["department"]].append((p, int(num(r["headcount_ending"])), len(act)))
                continue
            hp_months.add(p)
            quota = sum((num(e["annual_quota_arr"]) for e in act if e["quota_carrying"] == "Yes"), ZERO)
            if int(num(r["headcount_ending"])) != len(act) or abs(num(r["quota_capacity_arr"]) - quota) > 1:
                diffs.append(f"{p} {r['department']}: {r['headcount_ending']} heads {money(num(r['quota_capacity_arr']))} "
                             f"vs {len(act)} employees {money(quota)}")
        rep.check(f"{v} headcount plan = employees on staff, every department (heads; quota capacity incl. SDR pipeline "
                  f"quota)", diffs, f"{len(hp_months)} months from {v}_Employees.csv")
        if backcast:
            rows = [x for d in backcast.values() for x in d]
            rep.flag(f"{v} headcount plan {min(x[0] for x in rows)}..{max(x[0] for x in rows)} is a backcast the employee "
                     f"file does not reproduce (no hires before 2024, no leavers): " + ", ".join(
                         f"{d} {xs[0][0]} {xs[0][1]} planned vs {xs[0][2]} employees" for d, xs in sorted(backcast.items())
                         if d in TEAM_DEPARTMENTS))
    rep.check("Hiring_Ramp_Assumptions.csv present (loader expands it for every role)",
              [] if os.path.exists(os.path.join(v5, "Hiring_Ramp_Assumptions.csv")) else ["missing"])
    if os.path.exists(os.path.join(v5, f"Actual{PAYROLL_REGISTER_SUFFIX}")):
        payroll_section(rep, f, gl, emps, on_staff, ramp)

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


def _first(p: str) -> dt.date:
    return dt.date(int(p[:4]), int(p[5:7]), 1)


def _last(p: str) -> dt.date:
    return dt.date(int(p[:4]), int(p[5:7]), calendar.monthrange(int(p[:4]), int(p[5:7]))[1])


def _months(a: str, b: str) -> list[str]:
    return [_padd(a, i) for i in range(_pidx(b) - _pidx(a) + 1)]


def _register_line(e: dict[str, str], p: str, pol: dict[str, list[dict[str, str]]], as_of: dt.date):
    """One employee-month of payroll from the employee file and the payroll policies, or None when not employed."""
    hire = dt.date.fromisoformat(e["hire_date"])
    exit_ = dt.date.fromisoformat(e["termination_date"]) if e["termination_date"] else None
    start, end = max(hire, _first(p)), min(exit_ or _last(p), _last(p))
    days = (end - start).days + 1
    if days <= 0:
        return None
    value = {k: num(rows[0]["value"]) for k, rows in pol.items() if len(rows) == 1 and k != "bonus_payout"
             and rows[0]["value"].replace(".", "").isdigit()}
    merit_month = int(pol["merit_increase_pct"][0]["effective_from"][5:7])

    def raises(d: dt.date) -> int:
        return sum(1 for y in range(hire.year + 1, d.year + 1) if dt.date(y, merit_month, 1) <= d)

    salary = cents(num(e["base_salary"]) / (1 + value["merit_increase_pct"]) ** (raises(as_of) - raises(end)))
    share = Decimal(days) / Decimal(calendar.monthrange(int(p[:4]), int(p[5:7]))[1])
    wages = cents(salary / 12 * share)
    annual = (cents(salary * num(e["bonus_target_pct"])) if e["pay_plan"] == "Bonus"
              else num(e["variable_comp"]) if e["pay_plan"] == "Incentive" else ZERO)
    bonus = cents(annual / 12 * share)
    severance = ZERO
    if e["termination_type"] == "Involuntary" and exit_ and exit_.strftime("%Y-%m") == p:
        weeks = min(max(int(value["severance_weeks_per_year"]) * ((exit_ - hire).days // 365),
                        int(value["severance_min_weeks"])), int(value["severance_max_weeks"]))
        severance = cents(salary / 52 * weeks)
    health = next(num(r["value"]) for r in pol["health_benefits_monthly"] if r["effective_from"][:4] == p[:4]) \
        if hire <= _first(p) and (exit_ is None or exit_ >= _first(p)) else ZERO
    match = cents((wages + bonus) * min(num(e["retirement_deferral_pct"]), value["retirement_match_cap_pct"])
                  * value["retirement_match_rate"])
    return {"days_employed": Decimal(days), "regular_wages": wages, "bonus": bonus, "severance": severance,
            "employer_payroll_tax": cents((wages + bonus + severance) * value["employer_payroll_tax_rate"]),
            "health_benefits": health, "retirement_match": match}


def payroll_section(rep: Report, f, gl, emps, on_staff, ramp) -> None:
    """The payroll register recomputed from the employee files and the payroll policies; GL payroll, headcount-plan
    payroll and cash-bridge payroll = the register; each P&L line keeps positive non-payroll spend; the chart of
    accounts covers the GL; managers, requisitions and the Budget's opening roster come from the employee files."""
    rep.section("Payroll register, GL payroll, chart of accounts")
    reg = {v: f(f"{v}{PAYROLL_REGISTER_SUFFIX}") for v in VERSIONS}
    tol = Decimal("0.02")
    for v in VERSIONS:
        pol: dict[str, list[dict[str, str]]] = defaultdict(list)
        for r in f(f"{v}_payroll_policies.csv"):
            pol[r["policy"]].append(r)
        plan_end = _last(CLOSE if v == "Actual" else "2026-12")
        want = {}
        for e in emps[v]:
            exit_ = dt.date.fromisoformat(e["termination_date"]) if e["termination_date"] else None
            as_of = dt.date.fromisoformat(e["hire_date"]) if e["employment_status"] == "Planned" else min(exit_ or plan_end, plan_end)
            for p in _months(*REGISTER_WINDOW[v]):
                line = _register_line(e, p, pol, as_of)
                if line:
                    want[(p, e["employee_id"])] = line
        got = {(r["period"], r["employee_id"]): r for r in reg[v]}
        by_id = {e["employee_id"]: e for e in emps[v]}
        diffs = [f"{p} {i}: missing from the register" for p, i in sorted(set(want) - set(got))]
        diffs += [f"{p} {i}: on the register, not employed" for p, i in sorted(set(got) - set(want))]
        worst = ZERO
        for k in sorted(set(want) & set(got)):
            r, w, e = got[k], want[k], by_id[k[1]]
            if (r["employee_name"], r["department"], r["cost_center"]) != (e["employee_name"], e["department"], e["cost_center"]):
                diffs.append(f"{k[0]} {k[1]}: name, department or cost center differs from the employee file")
            for col, x in w.items():
                worst = max(worst, abs(num(r[col]) - x))
                if abs(num(r[col]) - x) > tol:
                    diffs.append(f"{k[0]} {k[1]} {col}: register {r[col]} vs {x}")
            if num(r["total_payroll_cost"]) != sum((num(r[c]) for c in REGISTER_ACCOUNTS), ZERO):
                diffs.append(f"{k[0]} {k[1]}: total is not the sum of its components")
        rep.check(f"{v} payroll register = the employee file under the payroll policies (days employed, wages, bonus, "
                  f"severance, payroll tax, benefits, 401(k) match)", diffs,
                  f"{len(got)} employee-months, largest difference {money(worst)} (salary restated from the close)")

        exp: dict[tuple[str, str, str], Decimal] = defaultdict(Decimal)
        for r in reg[v]:
            if r["cost_center"] in COGS_PAYROLL:
                exp[(r["period"], r["cost_center"], COGS_PAYROLL[r["cost_center"]])] += num(r["total_payroll_cost"])
            else:
                for col, acct in REGISTER_ACCOUNTS.items():
                    exp[(r["period"], r["cost_center"], acct)] += num(r[col])
        posted: dict[tuple[str, str, str], Decimal] = defaultdict(Decimal)
        stray = []
        for r in gl[v]:
            if r["statement"] == "Balance Sheet" or r["account_number"] not in PAYROLL_ACCOUNTS \
                    or r["source_file"].endswith(COMMISSION_SOURCE_SUFFIX):
                continue
            if r["source_file"] != f"{v}{PAYROLL_REGISTER_SUFFIX}":
                stray.append(f"{r['period'][:7]} {r['account_number']} {r['cost_center']} from {r['source_file']}")
            posted[(r["period"][:7], r["cost_center"], r["account_number"])] += num(r["amount"])
        diffs = stray + [f"{p} {cc} {a}: GL {money(posted.get((p, cc, a), ZERO))} vs register {money(x)}"
                         for (p, cc, a), x in sorted(exp.items()) if abs(posted.get((p, cc, a), ZERO) - x) > CENTS / 2]
        diffs += [f"{k}: GL only" for k in sorted(set(posted) - set(exp)) if posted[k]]
        rep.check(f"{v} GL payroll accounts ({', '.join(sorted(PAYROLL_ACCOUNTS))}) = the payroll register by month, cost "
                  f"center and account, to the cent (commission payroll tax rows aside)", diffs,
                  f"{money(sum(exp.values(), ZERO))}")

        hp_reg: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
        for r in reg[v] + (reg["Actual"] if v == "Forecast" else []):
            hp_reg[(r["period"], r["department"])] += num(r["total_payroll_cost"])
        diffs = [f"{r['period'][:7]} {r['department']}: {r['monthly_cash_payroll_cost']} vs {money(hp_reg[(r['period'][:7], r['department'])])}"
                 for r in f(f"{v}_Headcount_Plan.csv")
                 if abs(num(r["monthly_cash_payroll_cost"]) - hp_reg[(r["period"][:7], r["department"])]) > CENTS]
        rep.check(f"{v} headcount plan cash payroll = the payroll register by department", diffs)

        by_p = sums(reg[v], "period", "total_payroll_cost")
        bridge = [r for r in f(f"{v}_cash_flow_bridge.csv") if r["period"][:7] in by_p]
        diffs = [f"{r['period'][:7]}: {r['payroll_cash_out']} vs {money(by_p[r['period'][:7]])}" for r in bridge
                 if abs(num(r["payroll_cash_out"]) - by_p[r["period"][:7]]) > CENTS]
        rep.check(f"{v} cash bridge payroll = the payroll register (paid in the month)", diffs, f"{len(bridge)} months")

        other: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
        accounts: dict[tuple[str, str, str], Decimal] = defaultdict(Decimal)
        for r in gl[v]:
            cat = r["statement_category"]
            if r["statement"] == "Balance Sheet" or cat not in ("Operating Expense", "Cost of Revenue"):
                continue
            if r["source_file"] == f"{v}{PAYROLL_REGISTER_SUFFIX}" or r["source_file"].endswith(COMMISSION_SOURCE_SUFFIX):
                continue
            line = "COGS" if cat == "Cost of Revenue" else EXPENSE_LINES[r["department"]]
            other[(r["period"][:7], line)] += num(r["amount"])
            accounts[(r["period"][:7], line, r["account_number"])] += num(r["amount"])
        neg = [f"{p} {line} {a}: {money(x)}" for (p, line, a), x in sorted(accounts.items()) if x < 0]
        low = {line: min((x, p) for (p, l_), x in other.items() if l_ == line) for line in sorted({l_ for _, l_ in other})}
        rep.check(f"{v} every P&L line keeps positive non-payroll spend (each account, every month)", neg,
                  "lowest month: " + ", ".join(f"{line} {money(x)} ({p})" for line, (x, p) in low.items()))

        coa = {r["account_number"]: r["account_name"] for r in f(f"{v}_chart_of_accounts.csv")}
        used = {(r["account_number"], r["account_name"]) for r in gl[v]}
        diffs = [f"{a} {n}: not in the chart of accounts" for a, n in sorted(used) if a not in coa]
        diffs += [f"{a}: GL '{n}' vs chart '{coa[a]}'" for a, n in sorted(used) if a in coa and coa[a] != n]
        rep.check(f"{v} chart of accounts covers every GL account under the same name", diffs, f"{len(coa)} accounts")

        ids = {e["employee_id"]: e for e in emps[v]}
        diffs = []
        for e in emps[v]:
            exit_ = dt.date.fromisoformat(e["termination_date"]) if e["termination_date"] else None
            d = dt.date.fromisoformat(e["hire_date"]) if e["employment_status"] == "Planned" else min(exit_ or plan_end, plan_end)
            m = ids.get(e["manager"])
            if not e["manager"]:
                if e["role"] != "Chief Executive Officer":
                    diffs.append(f"{e['employee_id']}: no manager")
            elif m is None or m["employee_id"] == e["employee_id"]:
                diffs.append(f"{e['employee_id']}: manager {e['manager']} is not another {v} employee")
            elif not (m["hire_date"] <= d.isoformat() and (not m["termination_date"] or m["termination_date"] >= d.isoformat())):
                diffs.append(f"{e['employee_id']}: manager {e['manager']} not employed on {d}")
        rep.check(f"{v} managers are employees employed alongside the employee; only the CEO has none", diffs)

        reqs = f(f"{v}_Open_Requisitions.csv")
        planned = [e for e in emps[v] if e["employment_status"] == "Planned"]
        open_ids = {r["source"].split()[0] for r in reqs if r["status"] == "Open"}
        if v == "Actual":
            hires = {e["employee_id"] for e in emps[v] if e["hire_date"] >= "2024-01-01"}
            filled = {r["source"].split()[0] for r in reqs if r["status"] == "Filled"}
            diffs = [f"{len(hires ^ filled)} hires without a filled requisition or the reverse"] if hires != filled else []
            forecast_planned = {e["employee_id"] for e in emps["Forecast"] if e["employment_status"] == "Planned"}
            if open_ids != forecast_planned:
                diffs.append(f"open requisitions {len(open_ids)} vs Forecast planned hires {len(forecast_planned)}")
        else:
            diffs = [] if open_ids == {e["employee_id"] for e in planned} else [
                f"open requisitions {len(open_ids)} vs planned hires {len(planned)}"]
            diffs += [f"{e['employee_id']}: source names no requisition" for e in planned if "REQ-" not in e["source"]]
        rep.check(f"{v} requisitions = hires (filled since Jan 2024, open = the Forecast's planned hires)" if v == "Actual"
                  else f"{v} requisitions = planned hires, one each", diffs, f"{len(reqs)} requisitions")

    dec = "2025-12-31"
    a_open = {e["employee_id"]: e for e in emps["Actual"] if e["hire_date"] <= dec
              and (not e["termination_date"] or e["termination_date"] > dec)}
    b_open = {e["employee_id"]: e for e in emps["Budget"] if e["employment_status"] != "Planned"}
    diffs = [f"{len(set(a_open) ^ set(b_open))} employees differ"] if set(a_open) != set(b_open) else []
    diffs += [f"{i}: role or cost center" for i in set(a_open) & set(b_open)
              if (a_open[i]["role"], a_open[i]["cost_center"]) != (b_open[i]["role"], b_open[i]["cost_center"])]
    rep.check("Budget opening roster = Actual employees on staff at Dec 31, 2025 (Budget plans no exits)", diffs,
              f"{len(b_open)} employees")

    heads = Counter(e["department"] for e in emps["Actual"] if on_staff(e, CLOSE))
    rep.info(f"Actual employees on staff at the {CLOSE} close: {sum(heads.values())} (" +
             ", ".join(f"{d} {n}" for d, n in sorted(heads.items())) + ")")
    h1 = _months("2026-01", CLOSE)
    quotas = [r for r in f("Actual_Sales_Quotas.csv") if r["quota_type"] == "Bookings ARR" and r["period"][:7] in h1]
    won = sum((num(r["quota_attainment_actual_arr"]) for r in quotas), ZERO)
    cap = sum((num(r["ramped_monthly_quota_arr"]) for r in quotas), ZERO)
    exp_arr = sum((num(o["amount_arr"]) for o in f("Actual_opportunities.csv") if o["opportunity_type"] == "Expansion"
                   and o["close_status"] == "Closed Won" and o["period"][:7] in h1), ZERO)
    csm_cap = sum((num(e["annual_quota_arr"]) / 12 * ramp(e, p) for e in emps["Actual"] if e["role"] in CSM_ROLES
                   for p in h1 if on_staff(e, p)), ZERO)
    rep.info(f"H1 2026 attainment: AEs and Senior AEs {won / cap:.0%} of ramped quota (new business {money(won)}); "
             f"CSMs {exp_arr / csm_cap:.0%} of ramped quota (expansion {money(exp_arr)})")


def _pidx(p: str) -> int:
    return int(p[:4]) * 12 + int(p[5:7]) - 1


def _padd(p: str, n: int) -> str:
    i = _pidx(p) + n
    return f"{i // 12}-{i % 12 + 1:02d}"


def _cum_amortization(cohorts: dict[str, list[tuple[Decimal, int]]], through: str, paid_through: str | None = None) -> Decimal:
    total = ZERO
    for p, layers in cohorts.items():
        if paid_through and p > paid_through:
            continue
        age = _pidx(through) - _pidx(p) + 1
        if age <= 0:
            continue
        for amt, n in layers:
            total += amt * min(age, n) / n
    return total.quantize(Decimal("0.01"))


HISTORY_ORDER = {"Opening balance": 0, "Churn": 1, "Pause": 1, "Contraction": 2, "Reactivation": 3,
                 "New Business": 3, "Expansion": 4}
OPP_TYPE = {"New Business": ("New Business", "Closed Won"), "Expansion": ("Expansion", "Closed Won"),
            "Reactivation": ("Reactivation", "Closed Won"), "Contraction": ("Contraction", "Contraction"),
            "Churn": ("Churn", "Churn")}


def history_bases(hist: list[dict[str, str]]) -> list[dict]:
    """Commissionable ARR per movement, recomputed as a high-water level per customer: reset to the ARR a
    customer leaves with, raised by every increase; a return or expansion earns only above it.

    Expected-value rows (Forecast, with ``probability``) are measured on contract ARR: the deal's full opportunity
    ARR moves it, an expected lapse or churn that leaves ARR does not, and the base is probability x the
    commissionable part."""
    level: dict[str, Decimal] = {}
    contract: dict[str, Decimal] = {}
    out = []
    for r in sorted(hist, key=lambda r: (r["customer_id"], r["period"], HISTORY_ORDER[r["movement_type"]])):
        c, kind = r["customer_id"], r["movement_type"]
        old, new = num(r["beginning_arr"]), num(r["ending_arr"])
        hw = level.get(c, ZERO)
        base = None
        if not r.get("probability"):
            if kind == "Opening balance":
                level[c] = new
            elif kind in ("Churn", "Pause"):
                level[c] = old
            elif kind == "Contraction":
                level[c] = max(hw, old)
            elif kind == "New Business":
                base, level[c] = new, new
            else:
                base = max(ZERO, new - max(hw, old))
                level[c] = max(hw, new)
            contract[c] = new
        else:
            prob, full = num(r["probability"]), num(r["opportunity_arr"])
            cur = contract.get(c, old)
            if kind in ("Churn", "Pause") and new == 0:
                level[c], contract[c] = old, ZERO
            elif kind == "Contraction":
                level[c], contract[c] = max(hw, cur), cur - abs(num(r["movement_arr"]))
            elif kind == "New Business":
                base, level[c], contract[c] = prob * full, full, full
            elif kind in ("Reactivation", "Expansion"):
                after = cur + full
                base = prob * max(ZERO, after - max(hw, cur))
                level[c], contract[c] = max(hw, after), after
        if base is not None:
            out.append({"period": r["period"], "kind": kind, "opportunity_id": r["opportunity_id"],
                        "arr": new - old, "base": base})
    return out


def snapshots(rows: list[dict[str, str]], months: list[str], first: str) -> dict[str, dict[str, Decimal]]:
    """Customer ARR at each month end (rows before ``first`` count only as opening balances)."""
    arr: dict[str, Decimal] = defaultdict(Decimal)
    by_period = defaultdict(list)
    for r in sorted(rows, key=lambda r: (r["period"], r["customer_id"], HISTORY_ORDER[r["movement_type"]])):
        by_period[r["period"]].append(r)
    eop = {}
    for p in sorted(set(by_period) | set(months)):
        for r in by_period[p]:
            if p >= first or r["movement_type"] == "Opening balance":
                arr[r["customer_id"]] = num(r["ending_arr"])
        eop[p] = {c: a for c, a in arr.items() if a > 0}
    return eop


def renewals_due(eop: dict[str, dict[str, Decimal]], months: list[str], anniv: dict[str, str],
                 starts: dict[str, list[str]], skip: dict[str, set[str]]) -> dict[tuple[str, str], Decimal]:
    """(month, customer) -> renewal ARR: active at the prior month end, anniversary month, 12+ months since it last
    started (customer start, new business or a return)."""
    out = {}
    for p in months:
        for c, a in eop[_padd(p, -1)].items():
            last = max((s for s in starts.get(c, []) if s < p), default="")
            if anniv.get(c) == p[5:7] and last and _pidx(last) <= _pidx(p) - 12 and c not in skip.get(p, set()):
                out[(p, c)] = a
    return out


def history_section(rep: Report, f, hist: list[dict[str, str]], a_mrr) -> None:
    """Customer ARR history: ties to the waterfall, the opportunities, the master, revenue, invoices and payouts."""
    rep.section("Customer ARR history (every waterfall movement on a customer)")
    first = min(a_mrr)
    cols = ("new_business_arr", "expansion_arr", "reactivation_arr", "contraction_arr", "churn_arr")
    by = defaultdict(lambda: defaultdict(Decimal))
    arr: dict[str, Decimal] = defaultdict(Decimal)
    eop: dict[str, dict[str, Decimal]] = {}
    diffs, chain = [], []
    rows = sorted(hist, key=lambda r: (r["period"], r["customer_id"], HISTORY_ORDER[r["movement_type"]]))
    seen = set()
    for r in rows:
        c, p, kind = r["customer_id"], r["period"], r["movement_type"]
        b, m, e = num(r["beginning_arr"]), num(r["movement_arr"]), num(r["ending_arr"])
        if (p, c) in seen:
            chain.append(f"{p} {c}: two movements in a month")
        seen.add((p, c))
        if b + m != e or e < 0 or (kind in ("Churn", "Pause") and e) or (kind in ("New Business", "Reactivation") and b):
            chain.append(f"{p} {c} {kind}: {b} + {m} = {e}")
        if kind != "Opening balance" and p >= first and arr[c] != b:
            chain.append(f"{p} {c}: begins {b}, prior ending {arr[c]}")
        if p >= first or kind == "Opening balance":
            arr[c] = e
        if r["waterfall_column"]:
            by[p][r["waterfall_column"]] += abs(m)
    eop.update(snapshots(rows, list(a_mrr), first))
    opening = sum((num(r["ending_arr"]) for r in rows if r["movement_type"] == "Opening balance"), ZERO)
    if opening != num(a_mrr[first]["beginning_arr"]):
        diffs.append(f"opening {money(opening)} vs {money(num(a_mrr[first]['beginning_arr']))}")
    worst = ZERO
    for p, w in sorted(a_mrr.items()):
        for col in cols:
            if by[p][col] != num(w[col]):
                diffs.append(f"{p} {col} {money(by[p][col])} vs {money(num(w[col]))}")
        d = abs(sum(eop[p].values(), ZERO) - num(w["ending_arr"]))
        worst = max(worst, d)
        if d > Decimal("0.05"):
            diffs.append(f"{p} ending ARR {money(sum(eop[p].values(), ZERO))} vs {money(num(w['ending_arr']))}")
    rep.check("history = Actual ARR waterfall: opening ARR, each movement column every month (to the cent), ending ARR",
              diffs, f"{len(a_mrr)} months; ending ARR within {money(worst)} (the waterfall's own rounding)")
    rep.check("each customer's history chains: beginning = prior ending, ending = beginning + movement, never negative; "
              "churn and pause end at zero; new business and returns start from zero; one movement a month", chain,
              f"{len({r['customer_id'] for r in rows})} customers, {len(rows)} rows")

    diffs, kinds = [], defaultdict(int)
    last: dict[str, tuple[str, str]] = {}
    for r in sorted(rows, key=lambda r: (r["customer_id"], r["period"], HISTORY_ORDER[r["movement_type"]])):
        c, p, kind = r["customer_id"], r["period"], r["movement_type"]
        if kind in ("Churn", "Pause"):
            last[c] = (kind, p)
        elif kind in ("Reactivation", "New Business") and c in last:
            dep, when = last.pop(c)
            away = _pidx(p) - _pidx(when)
            if kind == "Reactivation":
                kinds["restart" if dep == "Pause" else "winback"] += 1
                if dep == "Churn" and away > WINBACK_WINDOW:
                    diffs.append(f"{p} {c}: reactivation {away} months after churning (new business after {WINBACK_WINDOW})")
            else:
                kinds["back as new business"] += 1
                if dep != "Churn" or away <= WINBACK_WINDOW:
                    diffs.append(f"{p} {c}: new business {away} months after a {dep.lower()}")
        elif kind == "Reactivation":
            diffs.append(f"{p} {c}: reactivation without a departure")
    rep.check(f"returns follow the policy: restart after a pause (any time), winback within {WINBACK_WINDOW} months of "
              f"churning, later than that is new business", diffs, ", ".join(f"{k} {n}" for k, n in sorted(kinds.items())))

    opps = f("Actual_opportunities.csv")
    want = {}
    for o in opps:
        for kind, (t, status) in OPP_TYPE.items():
            if o["opportunity_type"] == t and o["close_status"] == status:
                want[o["opportunity_id"]] = (o["period"][:7], o["customer_id"], kind, num(o["amount_arr"]))
    got = {r["opportunity_id"]: (r["period"], r["customer_id"], r["movement_type"], abs(num(r["movement_arr"])))
           for r in rows if r["opportunity_id"]}
    diffs = [f"{oid}: opportunity {want.get(oid)} vs history {got.get(oid)}" for oid in sorted(set(want) | set(got))
             if want.get(oid) != got.get(oid)]
    diffs += [f"{r['period']} {r['customer_id']} {r['movement_type']}: no opportunity" for r in rows
              if r["period"] in {p for p in a_mrr if p >= "2026-01"} and not r["opportunity_id"]]
    rep.check("every booked Actual opportunity is one history movement (customer, month, type, amount) and every "
              "2026 movement has its opportunity", diffs, f"{len(want)} opportunities")

    master = {r["customer_id"]: r for r in f("Actual_customers.csv")}
    diffs, region_of = [], defaultdict(set)
    for o in opps:
        region_of[o["customer_state"]].add(o["region"])
        m = master.get(o["customer_id"])
        if m is None:
            continue
        for of, mf in (("customer_name", "customer_name"), ("segment", "segment"), ("industry", "industry"),
                       ("customer_state", "billing_state")):
            if o[of] != m[mf]:
                diffs.append(f"{o['opportunity_id']} {o['customer_id']}: {of} {o[of]} vs master {m[mf]}")
    diffs += [f"state {s} in regions {sorted(r)}" for s, r in sorted(region_of.items()) if len(r) > 1]
    rep.check("Actual opportunities on master customers carry the customer's name, segment, industry and state; "
              "each state is in one region (owners are assigned by region)", diffs,
              f"{sum(1 for o in opps if o['customer_id'] in master)} of {len(opps)} opportunities on master customers")
    close = max(a_mrr)
    dec = eop["2025-12"]
    diffs = [c for c in {r["customer_id"] for r in rows} if c not in master]
    for c, m in master.items():
        status = "Active" if eop[close].get(c, ZERO) > 0 else ("Paused" if last.get(c, ("",))[0] == "Pause" else "Churned")
        if c in arr and m["status"] != status:
            diffs.append(f"{c}: status {m['status']} vs history {status}")
        if c in arr and abs(num(m["starting_arr_jan_2026"]) - dec.get(c, ZERO)) > CENTS:
            diffs.append(f"{c}: Jan 2026 ARR {m['starting_arr_jan_2026']} vs history {dec.get(c, ZERO)}")
    summary = {r["metric"]: num(r["value"]) for r in f("Actual_dataset_summary.csv")
               if r["metric"] in ("Customers", "Starting January 2026 ARR")}
    active = [c for c in master if dec.get(c, ZERO) > 0]
    if len(active) != summary.get("Customers") or sum((dec[c] for c in active), ZERO) != summary.get("Starting January 2026 ARR"):
        diffs.append(f"Dec 2025: {len(active)} customers {money(sum((dec[c] for c in active), ZERO))} vs dataset summary")
    rep.check("customer master: every history customer present; status at the close and Jan 2026 ARR from the history; "
              "dataset summary customers and Jan 2026 ARR", diffs,
              ", ".join(f"{k} {n}" for k, n in sorted(defaultdict(int, {s: sum(1 for m in master.values() if m['status'] == s)
                                                                          for s in {m['status'] for m in master.values()}}).items())))

    sched = defaultdict(dict)
    for r in f("Actual_recurring_services_schedule.csv"):
        sched[r["period"]][r["customer_id"]] = num(r["customer_arr"])
    diffs = [f"{p}: revenue weights differ from history ARR" for p in sorted(a_mrr) if sched.get(p) != eop[p]]
    rep.check("Actual revenue weights (recurring services schedule) = history ARR each month", diffs)
    billed, quarterly = defaultdict(set), set()
    for r in f("Actual_invoices.csv"):
        if r["billing_cadence"] in ("Monthly", "Quarterly"):
            if r["billing_cadence"] == "Quarterly":
                quarterly.add(r["customer_id"])
            s, e = r["service_period_start"][:7], r["service_period_end"][:7]
            p = s
            while p <= e:
                billed[r["customer_id"]].add(p)
                p = _padd(p, 1)
    first_quarter = sorted(a_mrr)[:3]
    diffs, pre_billed = [], 0
    for p in sorted(a_mrr):
        for c in billed:
            if p in billed[c] and eop[p].get(c, ZERO) <= 0:
                diffs.append(f"{p} {c}: billed without ARR")
        for c in eop[p]:
            if p in billed.get(c, set()):
                continue
            # Quarterly invoices issued before the first Actual month are not in the invoice file; they are
            # the opening AR and deferred revenue.
            if c in quarterly and p in first_quarter and p < min(billed[c]):
                pre_billed += 1
                continue
            diffs.append(f"{p} {c}: ARR without a subscription invoice")
    rep.check("subscription invoices cover exactly the months each customer has ARR", diffs,
              f"{pre_billed} customer-months in {first_quarter[0]} to {first_quarter[-1]} billed quarterly before "
              f"{first_quarter[0]} (opening deferred revenue)")
    anniv = {c: m["customer_start_date"][5:7] for c, m in master.items()}
    starts = defaultdict(list)
    for c, m in master.items():
        starts[c].append(m["customer_start_date"][:7])
    for r in rows:
        if r["movement_type"] in ("New Business", "Reactivation"):
            starts[r["customer_id"]].append(r["period"])
    churning = defaultdict(set)
    for o in opps:
        if o["opportunity_type"] == "Churn" and o["close_status"] == "Churn":
            churning[o["period"][:7]].add(o["customer_id"])
    pipeline = f("Actual_renewal_pipeline.csv")
    ren_months = sorted(p for p in a_mrr if p >= "2026-01")
    want = renewals_due(eop, ren_months, anniv, starts, churning)
    got = {(r["renewal_period"][:7], r["customer_id"]): num(r["renewal_arr"]) for r in pipeline}
    diffs = [f"{k}: pipeline {got.get(k)} vs due {want.get(k)}" for k in sorted(set(want) | set(got)) if got.get(k) != want.get(k)]
    diffs += [f"{r['renewal_id']}: expected post-renewal ARR {r['expected_post_renewal_arr']} vs renewal ARR"
              for r in pipeline if num(r["expected_post_renewal_arr"]) != num(r["renewal_arr"]) * (1 + num(r["expected_uplift_pct"]))]
    rep.check("Actual renewal pipeline = customers due in their anniversary month (12+ months since they last started, "
              "not churning that month) at their ARR at the prior month end", diffs,
              f"{len(pipeline)} renewals {ren_months[0]}..{ren_months[-1]}, renewal ARR "
              f"{money(sum(got.values(), ZERO))}")
    plans = {r["plan_id"]: r for r in f("Actual_commission_plans.csv")}
    rate = num(plans["PLAN-RENEWAL"]["base_commission_rate"])
    by_opp = {f"OPP-{r['renewal_id']}": r for r in pipeline}
    com = f("Actual_renewal_commissions.csv")
    diffs = []
    for r in com:
        ren = by_opp.pop(r["opportunity_id"], None)
        if ren is None or ren["customer_id"] != r["customer_id"] or ren["renewal_period"][:7] != r["period"][:7] \
                or num(r["booked_arr"]) != num(ren["renewal_arr"]) or ren["customer_success_manager"] != r["rep_name"]:
            diffs.append(f"{r['commission_id']}: not its renewal (customer, month, ARR, CSM)")
        elif num(r["commission_amount"]) != cents(num(r["booked_arr"]) * rate):
            diffs.append(f"{r['commission_id']}: {r['commission_amount']} vs {rate} x {r['booked_arr']}")
    diffs += [f"{oid}: renewal without a commission" for oid in sorted(by_opp)]
    rep.check(f"Actual renewal commissions: one per renewal, its customer, month, renewal ARR and CSM, at {rate}", diffs,
              f"{len(com)} commissions {money(sum((num(r['commission_amount']) for r in com), ZERO))}")

    bases = history_bases(hist)
    base_of = {b["opportunity_id"]: b["base"] for b in bases if b["opportunity_id"]}
    diffs = []
    paid = {r["opportunity_id"]: r for r in f("Actual_commission_payouts.csv")}
    for oid, base in sorted(base_of.items()):
        r = paid.get(oid)
        if base > 0 and (r is None or abs(num(r["commission_base_arr"]) - base) > CENTS):
            diffs.append(f"{oid}: commission base {r['commission_base_arr'] if r else 'no payout'} vs {money(base)}")
        if base <= 0 and r is not None:
            diffs.append(f"{oid}: paid {r['commission_amount']} on no ARR above the prior level")
    tot = defaultdict(Decimal)
    for b in bases:
        tot[(b["kind"], "arr")] += b["arr"]
        tot[(b["kind"], "base")] += b["base"]
    rep.check("commission base on each payout = ARR above the customer's prior level (returns: above the ARR they left "
              "with; expansion: above their level before contractions), recomputed as a high-water level", diffs,
              f"reactivation {tot[('Reactivation', 'base')] / tot[('Reactivation', 'arr')]:.2%} commissionable, "
              f"expansion {tot[('Expansion', 'base')] / tot[('Expansion', 'arr')]:.2%}")
    wb = sum((num(r["movement_arr"]) for r in rows if r["movement_type"] == "Reactivation"
              and r["note"].startswith("winback")), ZERO)
    re_ = sum((num(r["movement_arr"]) for r in rows if r["movement_type"] == "Reactivation"), ZERO)
    rep.info(f"winbacks {money(wb)} of {money(re_)} reactivation ARR ({wb / re_:.1%}); the rest are restarts after a pause")


def plan_history_section(rep: Report, f, v: str, actual: list[dict[str, str]], a_eop) -> None:
    """Budget or Forecast customer ARR history: the plan's waterfall, its deals, renewals, revenue and customers."""
    rep.section(f"{v} customer ARR history")
    rows = f(f"{v}_customer_arr_history.csv")
    mrr = {r["period"][:7]: r for r in f(f"{v}_MRR_Waterfall.csv")}
    months = sorted(mrr)
    first, open_p = months[0], _padd(months[0], -1)
    expected = v == "Forecast"
    cols = ("new_business_arr", "expansion_arr", "reactivation_arr", "contraction_arr", "churn_arr")
    ordered = sorted(rows, key=lambda r: (r["period"], r["customer_id"], HISTORY_ORDER[r["movement_type"]]))
    by, arr, chain, seen = defaultdict(lambda: defaultdict(Decimal)), {}, [], set()
    for r in ordered:
        c, p, kind = r["customer_id"], r["period"], r["movement_type"]
        b, m, e = num(r["beginning_arr"]), num(r["movement_arr"]), num(r["ending_arr"])
        if r["version"] != v or (p, c) in seen:
            chain.append(f"{p} {c}: version {r['version']} or two movements in a month")
        seen.add((p, c))
        if b + m != e or e < 0 or (kind in ("New Business", "Reactivation") and b) \
                or (kind in ("Churn", "Pause") and e and not expected):
            chain.append(f"{p} {c} {kind}: {b} + {m} = {e}")
        if kind == "Opening balance":
            if p != open_p:
                chain.append(f"{p} {c}: opening balance not at {open_p}")
        elif arr.get(c, ZERO) != b:
            chain.append(f"{p} {c}: begins {b}, prior ending {arr.get(c, ZERO)}")
        arr[c] = e
        if r["waterfall_column"]:
            by[p][r["waterfall_column"]] += abs(m)
    eop = snapshots(rows, months, first)
    opening = {r["customer_id"]: num(r["ending_arr"]) for r in rows if r["movement_type"] == "Opening balance"}
    diffs = [f"{c}: opening {opening.get(c)} vs Actual {a_eop[open_p].get(c)}"
             for c in sorted(set(opening) | set(a_eop[open_p])) if opening.get(c) != a_eop[open_p].get(c)]
    worst = ZERO
    for p in months:
        w = mrr[p]
        diffs += [f"{p} {col} {money(by[p][col])} vs {money(num(w[col]))}" for col in cols if by[p][col] != num(w[col])]
        end = num(w["ending_arr"])
        d = abs(sum(eop[p].values(), ZERO) - end)
        worst = max(worst, d)
        if d > (Decimal("0.99") if end == end.to_integral_value() else Decimal("0.05")):
            diffs.append(f"{p} ending ARR {money(sum(eop[p].values(), ZERO))} vs {money(end)}")
    rep.check(f"{v} history = {v} ARR waterfall: opening = each customer's Actual ARR at {open_p}, each movement column "
              f"every month (to the cent), ending ARR", diffs,
              f"{len(months)} months; ending ARR within {money(worst)} (the waterfall's own rounding)")
    rep.check(f"{v} history chains per customer: beginning = prior ending, ending = beginning + movement, never "
              f"negative; new business and returns start from zero; one movement a month"
              + ("" if expected else "; churn and pause end at zero"), chain,
              f"{len({r['customer_id'] for r in rows})} customers, {len(rows)} rows")

    pipeline = f("Forecast_renewal_pipeline.csv") if expected else []
    ren_ids = {r["renewal_id"] for r in pipeline}
    opps = f(f"{v}_opportunities.csv")
    want, diffs, off = {}, [], []
    for o in opps:
        if o["period"][:7] not in mrr:
            diffs.append(f"{o['opportunity_id']}: {o['period'][:7]} is outside the {v} months")
            continue
        pr, amt, wt = num(o["probability"]), num(o["amount_arr"]), num(o["weighted_arr"])
        kind = o["opportunity_type"]
        if expected:
            want[o["opportunity_id"]] = (o["period"][:7], o["customer_id"], kind, wt, pr, amt)
        else:
            want[o["opportunity_id"]] = (o["period"][:7], o["customer_id"], kind, amt)
        if expected and kind == "Churn":
            off.append(wt / amt - pr)
        elif abs(wt - amt * pr) > CENTS:
            diffs.append(f"{o['opportunity_id']}: weighted {wt} vs amount x probability")
    got, begins = {}, {}
    for r in rows:
        if not r["opportunity_id"] or r["opportunity_id"] in ren_ids:
            continue
        key = (r["period"], r["customer_id"], r["movement_type"], abs(num(r["movement_arr"])))
        got[r["opportunity_id"]] = key + ((num(r["probability"]), num(r["opportunity_arr"])) if expected else ())
        begins[r["opportunity_id"]] = num(r["beginning_arr"])
    diffs += [f"{oid}: opportunity {want.get(oid)} vs history {got.get(oid)}" for oid in sorted(set(want) | set(got))
              if want.get(oid) != got.get(oid)]
    diffs += [f"{oid}: churn deal {want[oid][5]} vs the customer's ARR {begins.get(oid)}" for oid in want
              if expected and want[oid][2] == "Churn" and want[oid][5] != begins.get(oid)]
    diffs += [f"{r['period']} {r['customer_id']} {r['movement_type']}: no opportunity" for r in rows
              if r["movement_type"] != "Opening balance" and not r["opportunity_id"]]
    rep.check(f"every {v} opportunity is one history movement (customer, month, type, "
              + ("weighted ARR, probability, full ARR; a churn deal is the customer's whole ARR" if expected else "amount")
              + "), weighted = amount x probability, and every movement has its deal", diffs,
              f"{len(want)} opportunities" + (f"; churn deals weighted at {min(off):+.3f}..{max(off):+.3f} of probability "
                                              f"x ARR (the month's last churn deal takes the cents)" if off else ""))

    combined = [r for r in actual if r["period"] < first] + [r for r in rows if r["movement_type"] != "Opening balance"]
    diffs, kinds, last = [], defaultdict(int), {}
    for r in sorted(combined, key=lambda r: (r["customer_id"], r["period"], HISTORY_ORDER[r["movement_type"]])):
        c, p, kind = r["customer_id"], r["period"], r["movement_type"]
        if kind in ("Churn", "Pause") and num(r["ending_arr"]) == 0:
            last[c] = (kind, p)
        elif kind in ("Reactivation", "New Business") and c in last:
            dep, when = last.pop(c)
            away = _pidx(p) - _pidx(when)
            if p >= first:
                if kind == "Reactivation":
                    kinds["restart" if dep == "Pause" else "winback"] += 1
                if (kind == "Reactivation" and dep == "Churn" and away > WINBACK_WINDOW) or \
                        (kind == "New Business" and (dep != "Churn" or away <= WINBACK_WINDOW)):
                    diffs.append(f"{p} {c}: {kind} {away} months after a {dep.lower()}")
        elif kind == "Reactivation":
            diffs.append(f"{p} {c}: reactivation without a departure")
    rep.check(f"{v} returns follow the policy (restart after a pause, winback within {WINBACK_WINDOW} months)", diffs,
              ", ".join(f"{k} {n}" for k, n in sorted(kinds.items())))

    customers = {r["customer_id"]: r for r in f(f"{v}_customers.csv")}
    if expected:
        anniv = {c: m["customer_start_date"][5:7] for c, m in customers.items()}
        starts = defaultdict(list)
        for c, m in customers.items():
            starts[c].append(m["customer_start_date"][:7])
        skip = defaultdict(set)
        churn_deals = {o["opportunity_id"] for o in opps if o["opportunity_type"] == "Churn"}
        for r in combined:
            if r["movement_type"] in ("New Business", "Reactivation"):
                starts[r["customer_id"]].append(r["period"])
            if r["period"] >= first and (r["opportunity_id"] in churn_deals or r["movement_type"] == "Reactivation"):
                for p in months:
                    if p > r["period"] or (p == r["period"] and r["opportunity_id"] in churn_deals):
                        skip[p].add(r["customer_id"])
        want = renewals_due(eop, months, anniv, starts, skip)
        got = {(r["renewal_period"][:7], r["customer_id"]): num(r["renewal_arr"]) for r in pipeline}
        diffs = [f"{k}: pipeline {got.get(k)} vs due {want.get(k)}" for k in sorted(set(want) | set(got)) if got.get(k) != want.get(k)]
        lapse = {r["opportunity_id"]: r for r in rows if r["opportunity_id"] in ren_ids}
        for r in pipeline:
            x, prob = lapse.get(r["renewal_id"]), num(r["renewal_probability"])
            amt = cents(num(r["renewal_arr"]) * (1 - prob))
            if x is None or x["customer_id"] != r["customer_id"] or x["period"] != r["renewal_period"][:7] \
                    or x["movement_type"] != "Churn" or num(x["movement_arr"]) != -amt \
                    or num(x["probability"]) != 1 - prob or num(x["opportunity_arr"]) != num(r["renewal_arr"]):
                diffs.append(f"{r['renewal_id']}: no matching lapse row (renewal ARR x (1 - {prob}) = {amt})")
        rep.check("Forecast renewal pipeline = customers due in their anniversary month at expected ARR, and each renewal's "
                  "expected lapse (renewal ARR x (1 - probability)) is one churn row in the history", diffs,
                  f"{len(pipeline)} renewals, renewal ARR {money(sum(got.values(), ZERO))}, expected lapse "
                  f"{money(sum((-num(x['movement_arr']) for x in lapse.values()), ZERO))}")

    sched = defaultdict(dict)
    for r in f(f"{v}_recurring_services_schedule.csv"):
        sched[r["period"]][r["customer_id"]] = num(r["customer_arr"])
    diffs = [f"{p}: revenue weights differ from history ARR" for p in months if sched.get(p) != eop[p]]
    rep.check(f"{v} revenue weights (recurring services schedule) = history ARR each month", diffs)
    diffs = [f"{c}: in the history, not in {v}_customers.csv" for c in sorted({r["customer_id"] for r in rows}) if c not in customers]
    for o in opps:
        m = customers.get(o["customer_id"])
        if m is None:
            diffs.append(f"{o['opportunity_id']}: customer {o['customer_id']} not in {v}_customers.csv")
            continue
        if o["opportunity_type"] == "New Business" and o["customer_id"] not in a_eop[CLOSE]:
            continue
        for of, mf in (("customer_name", "customer_name"), ("segment", "segment"), ("industry", "industry"),
                       ("customer_state", "billing_state")):
            if o[of] != m[mf]:
                diffs.append(f"{o['opportunity_id']} {o['customer_id']}: {of} {o[of]} vs {m[mf]}")
    rep.check(f"{v} customers file has every history and opportunity customer; deals on existing customers carry the "
              f"customer's name, segment, industry and state", diffs,
              f"{len(customers)} customers, {sum(1 for c in customers if c not in a_eop[open_p] and c not in a_eop[CLOSE])} "
              f"not active in Actual at {' or '.join(sorted({open_p, CLOSE}))}")


def segment_section(rep: Report, f, hist: list[dict[str, str]]) -> None:
    """Segment = ARR at signing in every file that carries it; implementation fee = the segment's fee."""
    rep.section("Customer segment (ARR at signing)")

    def band(a: Decimal) -> str:
        return next(name for name, floor in SEGMENT_FLOORS if a >= floor)

    signing: dict[str, Decimal] = {}
    for r in sorted(hist, key=lambda r: r["period"]):
        if r["customer_id"] not in signing:
            departed = r["movement_type"] in ("Churn", "Pause")
            signing[r["customer_id"]] = num(r["beginning_arr"] if departed else r["ending_arr"])
    for v in VERSIONS:
        opps = f(f"{v}_opportunities.csv")
        seg = {c: band(a) for c, a in signing.items()}
        deals = opps + f(f"{v}_opportunity_movements.csv")
        for o in sorted(deals, key=lambda o: (o["period"], o["opportunity_id"])):
            if o["customer_id"] not in seg and o["opportunity_type"] == "New Business":
                seg[o["customer_id"]] = band(num(o["amount_arr"]))
        diffs: list[str] = []
        files = [f"{v}_customers.csv", f"{v}_opportunities.csv", f"{v}_opportunity_movements.csv",
                 f"{v}_customer_arr_history.csv", f"{v}_recurring_services_schedule.csv"]
        for name in files:
            for r in f(name):
                want = seg.get(r["customer_id"])
                if r["segment"] != want:
                    diffs.append(f"{name} {r['customer_id']}: {r['segment']} vs {want or 'no signing ARR'}")
        by_opp = {o["opportunity_id"]: o for o in opps}
        imp = f(f"{v}_implementation_schedule.csv")
        for r in imp:
            want = seg.get(r["customer_id"])
            if r["segment"] != want:
                diffs.append(f"implementation {r['invoice_id']} {r['customer_id']}: {r['segment']} vs {want}")
                continue
            fee = cents(IMPLEMENTATION_FEE[want] * num(r["win_probability"]))
            if num(r["implementation_fee"]) != fee:
                diffs.append(f"implementation {r['invoice_id']}: fee {r['implementation_fee']} vs {fee}")
            o = by_opp.get(r["source_record_id"])
            if r["source"] == f"{v}_opportunities.csv" and (o is None or o["customer_id"] != r["customer_id"]):
                diffs.append(f"implementation {r['invoice_id']}: customer {r['customer_id']} vs its deal "
                             f"{r['source_record_id']} {o['customer_id'] if o else 'missing'}")
        counts = defaultdict(int)
        for r in f(f"{v}_customers.csv"):
            counts[r["segment"]] += 1
        rep.check(f"{v} segment = ARR at signing in customers, opportunities, movements, history and revenue schedules; "
                  f"implementation fee = segment fee x win probability, on its deal's customer", diffs[:20] + (
                      [f"... {len(diffs) - 20} more"] if len(diffs) > 20 else []),
                  ", ".join(f"{k} {n}" for k, n in sorted(counts.items())) + f"; {len(imp)} implementation fees")


def commission_section(rep: Report, f, gl, months, chain_months, source, bs_line, a_mrr, hist=None,
                       plan_hists: dict[str, list[dict[str, str]]] | None = None) -> None:
    """ASC 340-40: plans -> schedule -> rollforward -> GL -> statements -> cash bridge, each recomputed."""
    rep.section("Sales commissions (ASC 340-40)")
    detail_files = {"Actual_commission_payouts.csv": "commission_amount", "Actual_renewal_commissions.csv": "commission_amount"}
    detail, detail_base, detail_paid = defaultdict(Decimal), defaultdict(Decimal), defaultdict(Decimal)
    renewal_booked, renewal_months = ZERO, set()
    for name in detail_files:
        for r in f(name):
            detail[(r["period"][:7], r["plan_id"])] += num(r["commission_amount"])
            detail_base[r["plan_id"]] += num(r.get("commission_base_arr") or r["booked_arr"])
            detail_paid[r["plan_id"]] += num(r["commission_amount"])
            if "renewal" in name:
                renewal_booked += num(r["booked_arr"])
                renewal_months.add(r["period"][:7])
    renew_share = renewal_booked / sum((num(a_mrr[p]["beginning_arr"]) for p in renewal_months), ZERO)
    eff = {plan: (detail_paid[plan] / detail_base[plan]) for plan in detail_base}
    ren_span = f"{min(renewal_months)}..{max(renewal_months)}"
    hb_rows = {}
    if hist is not None:
        hb_rows["Actual"] = hist
        for v, rows in (plan_hists or {}).items():
            start = CHAIN_FROM_ACTUAL[v]
            hb_rows[v] = [r for r in hist if r["period"] < start] + [r for r in rows if r["movement_type"] != "Opening balance"]
    hb_new, hb_exp = defaultdict(lambda: defaultdict(Decimal)), defaultdict(lambda: defaultdict(Decimal))
    for v, rows in hb_rows.items():
        for b in history_bases(rows):
            (hb_exp if b["kind"] == "Expansion" else hb_new)[v][b["period"]] += b["base"]
    expected_ren = defaultdict(Decimal)
    if "Forecast" in hb_rows:
        for r in f("Forecast_renewal_pipeline.csv"):
            expected_ren[r["renewal_period"][:7]] += num(r["renewal_arr"]) * num(r["renewal_probability"])

    plans_by_v, sched, roll = {}, {}, {}
    for v in VERSIONS:
        plans_by_v[v] = {r["plan_id"]: r for r in f(f"{v}_commission_plans.csv")}
        sched[v] = f(f"{v}_commission_schedule.csv")
        roll[v] = {r["period"][:7]: r for r in f(f"{v}{COMMISSION_SOURCE_SUFFIX}")}

    diffs = []
    for v, plans in plans_by_v.items():
        for pid, r in plans.items():
            cap, months_ = r.get("capitalize"), r.get("amortization_months")
            if cap not in ("Y", "N") or not months_ or not r.get("payout_basis") or r.get("payout_lag_months") in (None, "") \
                    or r.get("capitalize_payroll_taxes") not in ("Y", "N"):
                diffs.append(f"{v} {pid}: policy columns incomplete")
            elif (cap == "Y") != (int(months_) > 0):
                diffs.append(f"{v} {pid}: capitalize {cap} with amortization_months {months_}")
            elif r.get("payout_lag_months") != "0":
                diffs.append(f"{v} {pid}: payout lag {r['payout_lag_months']} needs an accrued commissions liability (not modeled)")
        used = {r["plan_id"] for r in sched[v]} | ({k[1] for k in detail} if v == "Actual" else set())
        diffs += [f"{v}: plan {pid} used but not in {v}_commission_plans.csv" for pid in sorted(used - set(plans))]
    rep.check("commission plans carry a complete policy (capitalize, amortization months, payout basis and lag, "
              "payroll tax treatment) and cover every plan paid", diffs,
              "; ".join(f"{pid} capitalize {r['capitalize']} over {r['amortization_months']} months"
                        for pid, r in plans_by_v["Actual"].items()))

    diffs, est_months = [], defaultdict(set)
    scheduled = {(r["period"][:7], r["plan_id"]) for r in sched["Actual"]}
    diffs += [f"Actual {p} {pid}: payout detail {money(a)} has no schedule row" for (p, pid), a in sorted(detail.items())
              if (p, pid) not in scheduled]
    first = min(a_mrr)
    growth = (num(a_mrr["2025-12"]["ending_arr"]) / num(a_mrr[first]["beginning_arr"])) ** (
        Decimal(12) / Decimal(_pidx("2025-12") - _pidx(first) + 1))
    first_pay = {r["plan_id"]: num(r["commission_payout"]) for r in sched["Actual"] if r["period"][:7] == first}
    ladder = 0
    for v in VERSIONS:
        wf = {r["period"][:7]: r for r in f(f"{v}_MRR_Waterfall.csv")}
        plans = plans_by_v[v]
        for r in sched[v]:
            p, pid, amt = r["period"][:7], r["plan_id"], num(r["commission_payout"])
            if p < first:
                ladder += 1
                k = _pidx(first) - _pidx(p)
                want = (first_pay.get(pid, ZERO) / growth ** (Decimal(k) / 12)).quantize(Decimal("0.01"))
                if v != "Actual" or r["capitalize"] != "Y" or abs(amt - want) > CENTS \
                        or num(r["capitalized_amount"]) != amt:
                    diffs.append(f"{v} {p} {pid}: opening ladder {money(amt)} vs {money(want)}")
                continue
            cap_flag = plans[pid]["capitalize"] if pid in plans else "?"
            if r["capitalize"] != cap_flag:
                diffs.append(f"{v} {p} {pid}: schedule capitalize {r['capitalize']} vs plan {cap_flag}")
            if abs(num(r["capitalized_amount"]) + num(r["expensed_amount"]) - amt) > CENTS or \
                    (r["capitalize"] == "Y" and num(r["expensed_amount"])) or (r["capitalize"] == "N" and num(r["capitalized_amount"])):
                diffs.append(f"{v} {p} {pid}: capitalized + expensed != payout, or split against policy")
            if v == "Actual" and (p, pid) in detail:
                if abs(detail[(p, pid)] - amt) > CENTS:
                    diffs.append(f"Actual {p} {pid}: schedule {money(amt)} vs payout detail {money(detail[(p, pid)])}")
                continue
            if r["commission_base_arr"] == "":
                continue
            est_months[v].add(p)
            w = wf[p]
            if v in hb_rows:
                new, exp = hb_new[v][p], hb_exp[v][p]
            else:
                new, exp = num(w["new_business_arr"]) + num(w["reactivation_arr"]), num(w["expansion_arr"])
            ren = expected_ren[p] if v == "Forecast" and expected_ren else num(w["beginning_arr"]) * renew_share
            base = {"PLAN-AE-NEW": new, "PLAN-AM-EXP": exp, "PLAN-RENEWAL": ren}[pid]
            rate = eff[pid] if pid != "PLAN-RENEWAL" else num(plans[pid]["base_commission_rate"])
            if abs(num(r["commission_base_arr"]) - base) > CENTS or abs(amt - (base * rate).quantize(Decimal("0.01"))) > CENTS:
                diffs.append(f"{v} {p} {pid}: {money(amt)} vs base {money(base)} x {rate:.5f}")
    rep.check("commission schedule = payout detail where it exists (every detail line scheduled), else the commission "
              "base x the 2026 effective rate: each version's customer ARR history where it has one (ARR above the "
              "customer's prior level; Forecast probability-weighted), else its ARR waterfall; renewals: Forecast "
              f"renewal pipeline ARR x probability, else beginning ARR x the {ren_span} renewal share, x plan rate; "
              "capitalized/expensed per plan; opening ladder recomputes", diffs,
              f"effective rates {', '.join(f'{k} {e:.5f}' for k, e in sorted(eff.items()))}; renewal share {renew_share:.4%}; "
              f"{ladder} pre-{first} opening-ladder rows = {first} payout / {growth:.4f} annual ARR growth")
    rep.flag(f"payout detail exists only for Actual Jan-Jun 2026 (renewals {ren_span}); estimated months: "
             + "; ".join(f"{v} {min(ms)}..{max(ms)} ({len(ms)})" for v, ms in est_months.items() if ms))

    diffs = []
    for v in VERSIONS:
        cohorts: dict[str, list[tuple[Decimal, int]]] = defaultdict(list)
        start = CHAIN_FROM_ACTUAL.get(v)
        rows = [r for r in sched["Actual"] if not start or r["period"][:7] < start] + (sched[v] if v != "Actual" else [])
        for r in rows:
            if num(r["capitalized_amount"]):
                cohorts[r["period"][:7]].append((num(r["capitalized_amount"]), int(r["amortization_months"])))
        cap_by = sums(rows, "period", "capitalized_amount")
        exp_by = sums(rows, "period", "expensed_amount")
        prev_end = num(roll["Actual"][_padd(start, -1)]["ending_deferred_commissions"]) if start else None
        tax_rates = set()
        for p in sorted(roll[v]):
            r = roll[v][p]
            begin, cap, amort, end = (num(r[k]) for k in ("beginning_deferred_commissions", "capitalized_commissions",
                                                          "commission_amortization", "ending_deferred_commissions"))
            if abs(begin + cap - amort - end) > CENTS:
                diffs.append(f"{v} {p}: rollforward does not roll")
            if prev_end is not None and abs(begin - prev_end) > CENTS:
                diffs.append(f"{v} {p}: beginning {money(begin)} vs prior ending {money(prev_end)}")
            prev_end = end
            if abs(cap - cap_by.get(p, ZERO)) > CENTS or abs(num(r["expensed_commissions"]) - exp_by.get(p, ZERO)) > CENTS:
                diffs.append(f"{v} {p}: rollforward capitalized/expensed vs schedule")
            if abs(cap + num(r["expensed_commissions"]) - num(r["total_commission_payouts"])) > CENTS:
                diffs.append(f"{v} {p}: total payouts != capitalized + expensed")
            if abs(num(r["current_portion"]) + num(r["noncurrent_portion"]) - end) > CENTS:
                diffs.append(f"{v} {p}: current + noncurrent != ending")
            want_amort = _cum_amortization(cohorts, p) - _cum_amortization(cohorts, _padd(p, -1))
            want_end = sum((a for q_, layers in cohorts.items() if q_ <= p for a, _ in layers), ZERO) - _cum_amortization(cohorts, p)
            want_cur = _cum_amortization(cohorts, _padd(p, 12), paid_through=p) - _cum_amortization(cohorts, p)
            if abs(amort - want_amort) > CENTS or abs(end - want_end) > CENTS or abs(num(r["current_portion"]) - want_cur) > CENTS:
                diffs.append(f"{v} {p}: amortization {money(amort)} / ending {money(end)} / current "
                             f"{money(num(r['current_portion']))} vs recomputed {money(want_amort)} / {money(want_end)} / {money(want_cur)}")
            total = num(r["total_commission_payouts"])
            if total:
                tax_rates.add((num(r["payroll_tax_on_commissions"]) / total).quantize(Decimal("0.0001")))
        if len(tax_rates) > 1:
            diffs.append(f"{v}: payroll tax on commissions is not one rate ({sorted(tax_rates)})")
    rep.check("deferred commissions rollforward rolls, chains (Budget from Actual Dec 2025, Forecast from Jun 2026), "
              "matches the schedule, and amortization / ending / current portion recompute from the payout cohorts", diffs)

    diffs = []
    for v in VERSIONS:
        gl_by = defaultdict(lambda: defaultdict(Decimal))
        for r in gl[v]:
            p = r["period"][:7]
            if r["account_number"] == "6200":
                gl_by[p]["6200"] += num(r["amount"])
                if not r["source_file"].endswith(COMMISSION_SOURCE_SUFFIX):
                    gl_by[p]["stray"] += num(r["amount"])
            elif r["account_number"] == "6210":
                gl_by[p]["6210"] += num(r["amount"])
            elif r["account_number"] == "6110" and r["source_file"].endswith(COMMISSION_SOURCE_SUFFIX):
                gl_by[p]["tax"] += num(r["amount"])
        for p in months[v]:
            r = roll[v][p]
            for key, col in (("6200", "commission_amortization"), ("6210", "expensed_commissions"),
                             ("tax", "payroll_tax_on_commissions")):
                if abs(gl_by[p][key] - num(r[col])) > CENTS:
                    diffs.append(f"{v} {p} GL {key} {money(gl_by[p][key])} vs rollforward {col} {money(num(r[col]))}")
            if gl_by[p]["stray"]:
                diffs.append(f"{v} {p}: 6200 rows not from the rollforward {money(gl_by[p]['stray'])}")
            for k, col in (("deferred_commissions_current", "current_portion"),
                           ("deferred_commissions_noncurrent", "noncurrent_portion")):
                if abs(bs_line(v, p, k) - num(r[col])) > CENTS:
                    diffs.append(f"{v} {p} GL {k} {money(bs_line(v, p, k))} vs rollforward {money(num(r[col]))}")
    rep.check("GL 6200 = amortization, 6210 = expensed commissions, 6110 commission rows = payroll tax on payouts, "
              "1250/1550 = current/noncurrent deferred commissions, every month", diffs)

    diffs = []
    for v in VERSIONS:
        br = {r["period"][:7]: r for r in f(f"{v}_cash_flow_bridge.csv")}
        for p in months[v]:
            if p in br and abs(num(br[p]["commission_cash_out"]) - num(roll[v][p]["total_commission_payouts"])) > CENTS:
                diffs.append(f"{v} {p}: bridge {money(num(br[p]['commission_cash_out']))} vs payouts "
                             f"{money(num(roll[v][p]['total_commission_payouts']))}")
    rep.check("cash bridge commission cash = total commission payouts (all plans)", diffs)

    diffs = []
    for v in VERSIONS:
        capitalizes = any(r["capitalize"] == "Y" for r in plans_by_v[v].values())
        has_asset = all(bs_line(v, p, "deferred_commissions_current") + bs_line(v, p, "deferred_commissions_noncurrent") > 0
                        for p in months[v])
        if capitalizes != has_asset:
            diffs.append(f"{v}: policy capitalize={capitalizes} but GL deferred commissions asset present={has_asset}")
    rep.check("policy and books agree: plans that capitalize have a deferred commissions asset in the GL every month", diffs)

    for v in VERSIONS:
        tot = defaultdict(lambda: defaultdict(Decimal))
        for p, r in roll[v].items():
            for k in ("total_commission_payouts", "capitalized_commissions", "commission_amortization",
                      "expensed_commissions", "payroll_tax_on_commissions"):
                tot[p[:4]][k] += num(r[k])
        last = max(roll[v])
        rep.info(f"{v}: " + "; ".join(
            f"{y} paid {money(t['total_commission_payouts'])} (capitalized {money(t['capitalized_commissions'])}, "
            f"renewals expensed {money(t['expensed_commissions'])}), amortized {money(t['commission_amortization'])}, "
            f"payroll tax {money(t['payroll_tax_on_commissions'])}" for y, t in sorted(tot.items()))
                 + f"; deferred commissions {last} {money(num(roll[v][last]['ending_deferred_commissions']))}")


COMMISSION_BUILD_ACCOUNTS = {"1000", "1250", "1550", "3000", "6110", "6200", "6210"}
COMMISSION_BUILD_FILES = ("_balance_sheet.csv", "_cash_collections.csv", "_cash_flow_bridge.csv",
                          "_cash_flow_statement.csv", "_commission_plans.csv", "_income_statement.csv",
                          "_commission_schedule.csv", COMMISSION_SOURCE_SUFFIX)


def change_scope_section(rep: Report, prior_dir: str, data_dir: str, gl_dir: str, prior_gl_dir: str | None) -> None:
    """The commission build may only change commission, payroll tax, cash and equity: every other GL
    account and every other file must be identical to the prior dataset, to the cent."""
    rep.section("Change scope vs the prior dataset (the commission build touches nothing else)")
    changed = []
    for n in sorted(os.listdir(data_dir)):
        if not n.endswith(".csv"):
            continue
        old = os.path.join(prior_dir, n)
        with open(os.path.join(data_dir, n), "rb") as fh:
            new_bytes = fh.read()
        if os.path.exists(old):
            with open(old, "rb") as fh:
                if fh.read() == new_bytes:
                    continue
        if not n.endswith(COMMISSION_BUILD_FILES):
            changed.append(n)
    rep.check("only statement, cash and commission files differ from the prior dataset", changed)

    if not prior_gl_dir:
        rep.flag("prior GL folder not given (--prior-gl); GL account scope not checked")
        return
    for v in VERSIONS:
        def by_key(folder: str) -> dict[tuple[str, str], Decimal]:
            out: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
            for r in read(os.path.join(folder, f"{v}_gl_detail.csv"))[1]:
                out[(r["period"][:7], r["account_number"])] += num(r["amount"])
            return out

        old, new = by_key(prior_gl_dir), by_key(gl_dir)
        delta = {k: new.get(k, ZERO) - old.get(k, ZERO) for k in set(old) | set(new)}
        stray = [f"{p} {a} {money(d)}" for (p, a), d in sorted(delta.items()) if d and a not in COMMISSION_BUILD_ACCOUNTS]
        rep.check(f"{v} GL: no account outside {', '.join(sorted(COMMISSION_BUILD_ACCOUNTS))} changed", stray)

        roll = {r["period"][:7]: r for r in read(os.path.join(data_dir, f"{v}{COMMISSION_SOURCE_SUFFIX}"))[1]}
        diffs = []
        for p, r in sorted(roll.items()):
            if delta.get((p, "6110"), ZERO) != num(r["payroll_tax_on_commissions"]):
                diffs.append(f"{p}: 6110 change {money(delta.get((p, '6110'), ZERO))} vs payroll tax on payouts "
                             f"{money(num(r['payroll_tax_on_commissions']))}")
            want = num(r["commission_amortization"]) + num(r["expensed_commissions"]) - old.get((p, "6200"), ZERO)
            got = delta.get((p, "6200"), ZERO) + delta.get((p, "6210"), ZERO)
            if got != want:
                diffs.append(f"{p}: 6200+6210 change {money(got)} vs amortization + expensed - prior 6200 {money(want)}")
        rep.check(f"{v} GL: payroll tax and commission accounts changed by exactly the rollforward, to the cent", diffs)


KNOWN_GAPS = [
    "Implementation fees are billed and recognized at signing (not spread over the implementation period).",
    "Budget deferred revenue differs from the unrecognized amount on its invoices (see the build check line above): "
    "Budget recognizes Budget revenue against invoices billed before 2026 at Actual amounts.",
    "Sales and Customer Success employees work the CRM territory with the most Actual opportunities per head in "
    "their role group when hired; other departments have an office region.",
    "Headcount plan quota capacity includes SDR pipeline quota alongside AE bookings quota.",
    "Headcount follows the plan (build_workforce.HEADCOUNT_PLAN): ~250 at the June 2026 close, "
    "straight-line between plan points; each P&L line's non-payroll accounts take the rest of the line (mostly "
    "marketing programs in S&M). R&D and G&A heads are limited by their P&L lines.",
    "The summary P&L is fixed shares of revenue; 60% of Tier 1 support labor (5010) was reallocated to R&D in every "
    "month and version (support_labor_reclass_log.csv): gross margin and R&D moved, EBITDA did not.",
    "Bonus and the SDR incentive are paid monthly at target with payroll (no accrued bonus liability); Tier 1 Support "
    "and Implementation post fully loaded payroll (incl. bonus, 401(k), severance) to 5010 / 5020.",
    "The SBC schedule is still 1% of revenue (not the roster's equity grants); the headcount plan's SBC is the roster's.",
    "AP is one month of vendor invoices (net 30) from Feb 2024; the Jan 2024 opening AP from the balance sheet file "
    "is paid in Feb 2024. Vendor invoices carry no line or vendor detail.",
    "Cost center SALES-AM has no roles (expansion is owned by AEs and CSMs).",
    "CSMs are on the Commission pay plan (target in commission_target); their renewal commissions come from the "
    "renewal commission files, not the target.",
    "Budget-only and Forecast-only new logos are in their own version's customer file, not the Actual master.",
    "renewal_arr redefined as beginning ARR less contraction and churn.",
    "Commission payout detail exists only for Actual Jan-Jun 2026; every other month is estimated at the 2026 "
    "effective rates on each version's customer ARR history (Forecast probability-weighted), and pre-2024 cohorts "
    "are an opening ladder.",
    "Forecast customer ARR is expected value (each deal moves its customer by probability x amount, each renewal by "
    "its expected lapse), so Forecast customer ARR is not a contract amount.",
    "Customer segment is ARR at signing; customers that signed before Jan 2024 use their Dec 2023 ARR (the earliest "
    "on record). A rep's segment is the HRIS sub-department (Enterprise Sales, Mid-Market Sales; others All); owners "
    "are assigned by territory, not segment.",
    "Commissions are paid in the booking month (payout lag 0), so there is no accrued commissions liability.",
    "Deferred tax on deferred commissions (book/tax difference) is not modeled.",
    "Budget and Forecast bookings_summary does not tie to their ARR waterfalls; commissions use the waterfall.",
]

METHODS = [
    "Budget renewal commissions: the Budget has no renewal pipeline (by design). Each month is Budget beginning ARR "
    "x the Jan-Jun 2026 Actual renewal share (renewal ARR / beginning ARR, a month) x the 2% renewal rate, built "
    "in the dataset and stored in the warehouse as the Budget commission schedule.",
]


if __name__ == "__main__":
    argv = sys.argv[1:]
    prior_gl = None
    if "--prior-gl" in argv:
        i = argv.index("--prior-gl")
        prior_gl = argv[i + 1]
        del argv[i:i + 2]
    v4_dir, v5_dir, gl = argv[:3]
    name = os.path.basename(os.path.normpath(v5_dir))
    out = argv[3] if len(argv) > 3 else os.path.join(v5_dir, "tie_out_report.md")
    report = main(v4_dir, v5_dir, gl, prior_gl)
    text = [f"# {name} tie-out", "", f"prior dataset: {v4_dir}", f"dataset: {v5_dir}", f"GL: {gl}",
            f"prior GL: {prior_gl or 'not given'}",
            "", f"**{report.failures} failing checks**"] + report.lines + ["\n## Methods (estimates by design)\n"] + \
           [f"- {m}" for m in METHODS] + ["\n## Known gaps (not fixed in this dataset)\n"] + [f"- {g}" for g in KNOWN_GAPS]
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(text) + "\n")
    print("\n".join(text))
    sys.exit(1 if report.failures else 0)
