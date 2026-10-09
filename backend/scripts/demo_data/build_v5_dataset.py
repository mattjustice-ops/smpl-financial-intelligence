"""Build the v5 demo dataset from v4: one billing model, June close completed, reps from the employee files.

Writes a new folder only (never touches the database):
  python build_v5_dataset.py <v4_folder> <v5_folder> [--opening-equity-adjustment AMOUNT]

Then rebuild the GL (rebuild_gl_to_summary.py <v5_folder> <gl_folder>) and sync the statement
files to it (sync_v5_statements.py <v5_folder> <gl_folder>).

Rules (agreed with Matt, Oct 6 2026):
  * Revenue: total revenue is the income statement summary. Implementation fees come from
    the implementation schedule; recurring services are 10% of subscription; subscription is
    the rest. Each month's subscription and recurring services are spread across that
    month's customers by ARR. New logos won in 2026 (Actual closed-won new business) are
    customers from their close month, in the customer master and in the per-customer revenue.
  * Billing: no annual billing. About 60% of ARR bills monthly, invoiced on the 1st of the
    service month. The rest bills quarterly in advance on the customer's anniversary,
    invoiced on the 1st of the month before the quarter (about 30 days ahead). Recurring
    services bill on the same invoice as subscription. Implementation fees bill at signing
    and are recognized in that month (implementation schedule).
  * Collections (Oct 9 2026, collections_model.py): Actual invoices are paid on each customer's payment habit;
    the collections cases (no-starts and non-payment churn from the ARR history, one late payer recovered after
    escalation, one dispute open at the close) go unpaid and are written off, or are paid late. Budget and
    Forecast invoices are collected at the customer's terms (Net 15/30/45/60) plus 7 days.
  * Deferred revenue = billed but not yet recognized. AR = billed but not yet collected or written off; the
    balance sheet shows it net of the allowance for doubtful accounts (opening equity carries the opening
    allowance, so opening cash does not move).
    Budget continues from the Actual balances at Dec 2025, Forecast from Jun 2026.
  * Opening balance sheet (Jan 2024 month end): AR and deferred revenue come from the
    billing model; equity is the v4 opening equity less --opening-equity-adjustment; cash
    balances it.
  * June close: ARR waterfall rates and renewal ARR are calculated from the movements;
    quotas run through June; quota attainment is the closed-won new business each rep owns;
    commission payouts are rebuilt from closed-won deals at the plan rates and paid to
    roster reps.
  * Sales team: each version's roster is its Sales employees (sales_team.py), month by month with the
    employee's quota and the Hiring_Ramp_Assumptions.csv ramp: sales_reps, Actual and Budget quotas,
    Forecast quota capacity by territory, and the owners of that version's opportunities and movements. When Actual_customer_arr_history.csv exists (build_customer_history.py), the
    commission base follows the return policy (onboarding 7.21-7.24): a winback or restart
    earns only on ARR above what the customer left with, expansion first recovers earlier
    contraction, and a customer back more than 6 months after churning is new business.
    Revenue weights and the customer master then come from that history. Budget-only and Forecast-only new
    logos come from their version's customer file and are billed in that version only. The 7 forecast hires
    that were due to start in June move to July because the June roster has no June hires.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import os
import shutil
import sys
from collections import Counter, defaultdict
from decimal import ROUND_HALF_UP, Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collections_model import (BUCKETS, activity_rows, aging_rows, allowance_rollforward, case_rows,  # noqa: E402
                               is_open, payment_rows, plan_cases, settle, write_off_month)
from customer_buckets import (CUSTOMER_SUCCESS_BEGINNING, LINES, NEW_BUSINESS_TOTAL,  # noqa: E402
                              WATERFALL_BUCKET_FIELDS, bucket_waterfall)
from sales_team import BOOKINGS_ROLES, REP_SEGMENT, TERRITORIES, active, quota_type  # noqa: E402

CENT = Decimal("0.01")
ZERO = Decimal("0")
VERSIONS = ("Actual", "Budget", "Forecast")
CLOSE = "2026-06"
CHAIN_FROM_ACTUAL = {"Budget": "2026-01", "Forecast": "2026-07"}
RSVC_RATE = Decimal("0.10")
MONTHLY_SHARE = Decimal("0.60")
COLLECTION_LAG_DAYS = 7
TERMS_DAYS = {"Net 15": 15, "Net 30": 30, "Net 45": 45, "Net 60": 60}
PRE_PERIOD_START = "2023-09"
QUOTA_FROM = "2026-01"
PLAN_END = "2026-12"
REMOVED_FILES = ("Actual_deferred_revenue_waterfall_SUPPORTING_ONLY.csv",)
LETTER = {"Actual": "A", "Budget": "B", "Forecast": "F"}


def num(value) -> Decimal:
    text = str(value if value is not None else "").replace(",", "").strip()
    return Decimal(text or "0")


def q(x: Decimal) -> Decimal:
    return x.quantize(CENT, ROUND_HALF_UP)


def read(path: str) -> tuple[list[str], list[dict[str, str]]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        rows = list(r)
        return list(r.fieldnames or []), rows


def write(path: str, fields: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else (f"{r[k]:.2f}" if isinstance(r[k], Decimal) else r[k])) for k in fields})


def pidx(p: str) -> int:
    return int(p[:4]) * 12 + int(p[5:7]) - 1


def padd(p: str, n: int) -> str:
    i = pidx(p) + n
    return f"{i // 12}-{i % 12 + 1:02d}"


def prange(a: str, b: str) -> list[str]:
    return [padd(a, i) for i in range(pidx(b) - pidx(a) + 1)]


def first_day(p: str) -> dt.date:
    return dt.date(int(p[:4]), int(p[5:7]), 1)


def last_day(p: str) -> dt.date:
    return first_day(padd(p, 1)) - dt.timedelta(days=1)


def month_of(d: dt.date) -> str:
    return f"{d.year}-{d.month:02d}"


def allocate(total: Decimal, weights: list[tuple[str, Decimal]]) -> dict[str, Decimal]:
    """Spread ``total`` (cents) by weight; rounding goes to the largest weight."""
    wsum = sum((w for _, w in weights), ZERO)
    if not weights or wsum == 0:
        return {}
    out = {k: q(total * w / wsum) for k, w in weights}
    big = max(weights, key=lambda kw: kw[1])[0]
    out[big] += total - sum(out.values(), ZERO)
    return out


def stable_unit(key: str) -> Decimal:
    h = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)
    return Decimal(h % 10000) / Decimal(10000)


HISTORY_FILE = "Actual_customer_arr_history.csv"
HISTORY_ORDER = {"Opening balance": 0, "Churn": 1, "Pause": 1, "Contraction": 2, "Reactivation": 3,
                 "New Business": 3, "Expansion": 4}


def commission_bases(history: list[dict[str, str]]) -> list[dict]:
    """Each movement's commissionable ARR under the commission policy (onboarding 7.21-7.24, agreed with Matt):
    a return (winback or restart) earns only on ARR above what the customer left with; expansion earns only
    above the customer's prior level (it first recovers earlier contractions or a return below the prior
    ARR); new business, including a customer back more than 6 months after churning, earns on all of it.

    Expected-value rows (Forecast: ``probability`` and ``opportunity_arr``) earn probability x the base on the full
    opportunity ARR; a churn that leaves ARR (an expected lapse) is not a departure."""
    out = []
    state: dict[str, dict] = defaultdict(lambda: {"left_with": None, "unrecovered": ZERO})
    for r in sorted(history, key=lambda r: (r["customer_id"], r["period"], HISTORY_ORDER[r["movement_type"]])):
        s, kind = state[r["customer_id"]], r["movement_type"]
        amount = abs(num(r["movement_arr"]))
        prob = num(r["probability"]) if r.get("probability") else Decimal(1)
        full = num(r["opportunity_arr"]) if r.get("probability") else amount
        base = None
        if kind in ("Churn", "Pause"):
            if num(r["ending_arr"]) == 0:
                s["left_with"], s["unrecovered"] = num(r["beginning_arr"]), ZERO
        elif kind == "Contraction":
            s["unrecovered"] += amount
        elif kind == "Reactivation":
            if s["left_with"] is None:
                raise ValueError(f"{r['period']} {r['customer_id']}: return without a recorded departure")
            base = prob * max(ZERO, full - s["left_with"])
            s["unrecovered"], s["left_with"] = max(ZERO, s["left_with"] - full), None
        elif kind == "Expansion":
            recovered = min(s["unrecovered"], full)
            s["unrecovered"] -= recovered
            base = prob * (full - recovered)
        elif kind == "New Business":
            s["left_with"], s["unrecovered"] = None, ZERO
            base = prob * full
        if base is not None:
            out.append({"period": r["period"], "customer_id": r["customer_id"], "movement_type": kind,
                        "opportunity_id": r["opportunity_id"], "arr": amount, "base": base})
    return out


class Dataset:
    def __init__(self, src: str):
        self.src = src
        self.cache: dict[str, tuple[list[str], list[dict[str, str]]]] = {}

    def get(self, name: str) -> tuple[list[str], list[dict[str, str]]]:
        if name not in self.cache:
            self.cache[name] = read(os.path.join(self.src, name))
        return self.cache[name]

    def rows(self, name: str) -> list[dict[str, str]]:
        return self.get(name)[1]

    def fields(self, name: str) -> list[str]:
        return self.get(name)[0]

    def exists(self, name: str) -> bool:
        return os.path.exists(os.path.join(self.src, name))


# ----------------------------------------------------------------------------- customers


def new_logos(ds: Dataset) -> dict[str, dict[str, str]]:
    """Actual closed-won new business: customer id -> opportunity row."""
    out = {}
    for r in ds.rows("Actual_opportunities.csv"):
        if r["opportunity_type"] == "New Business" and r["close_status"] == "Closed Won":
            out[r["customer_id"]] = r
    return out


def plan_logos(ds: Dataset, master: list[dict[str, str]], logos: dict[str, dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    """Budget and Forecast new logos that are not Actual customers (in that version's customer file)."""
    known = {r["customer_id"] for r in master} | set(logos)
    return {v: [r for r in ds.rows(f"{v}_customers.csv") if r["customer_id"] not in known] for v in ("Budget", "Forecast")}


def no_annual(cadence: str) -> str:
    return "Quarterly" if cadence in ("Annual", "Quarterly") else "Monthly"


def assign_cadence(master: list[dict[str, str]], logos: dict[str, dict[str, str]]) -> tuple[dict[str, str], dict[str, int]]:
    cadence = {r["customer_id"]: no_annual(r["billing_cadence"]) for r in master}
    for cid, o in logos.items():
        cadence[cid] = no_annual(o["billing_cadence"])
    arr = {r["customer_id"]: num(r["starting_arr_jan_2026"]) for r in master}
    total = sum(arr.values(), ZERO)

    def monthly_share() -> Decimal:
        return sum((a for c, a in arr.items() if cadence[c] == "Monthly"), ZERO) / total

    for cid in sorted((c for c in arr if cadence[c] == "Quarterly"), key=lambda c: (arr[c], c)):
        if monthly_share() >= MONTHLY_SHARE:
            break
        cadence[cid] = "Monthly"
    for cid in sorted((c for c in arr if cadence[c] == "Monthly"), key=lambda c: (-arr[c], c)):
        if monthly_share() <= MONTHLY_SHARE + Decimal("0.01"):
            break
        cadence[cid] = "Quarterly"
    anniv = {r["customer_id"]: int(r["customer_start_date"][5:7]) for r in master}
    for cid, o in logos.items():
        anniv[cid] = int(o["period"][5:7])
    return cadence, anniv


# ----------------------------------------------------------------------------- revenue


class Revenue:
    """Per customer-month subscription and recurring services for one version."""

    def __init__(self, ds: Dataset, version: str, logos: dict[str, dict[str, str]]):
        self.version = version
        summary = {r["period"][:7]: num(r["revenue"]) for r in ds.rows(f"{version}_income_statement.csv")}
        impl: dict[str, Decimal] = defaultdict(Decimal)
        for r in ds.rows(f"{version}_implementation_schedule.csv"):
            impl[r["period"][:7]] += num(r["implementation_fee"])
        self.impl = impl
        sched = ds.rows(f"{version}_recurring_services_schedule.csv")
        members: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
        for r in sched:
            members[r["period"][:7]][r["customer_id"]] = r
        self.months = sorted(members)
        self.sub: dict[str, Decimal] = {}
        self.rsvc: dict[str, Decimal] = {}
        self.by_cust: dict[str, dict[str, tuple[Decimal, Decimal]]] = defaultdict(dict)
        self.meta: dict[tuple[str, str], dict[str, str]] = {}
        for p in self.months:
            people = {cid: {"customer_name": r["customer_name"], "segment": r["segment"],
                            "weight_source": r["weight_source"], "customer_arr": num(r["customer_arr"])}
                      for cid, r in members[p].items()}
            if version in ("Actual", "Forecast"):
                for cid, o in logos.items():
                    if o["period"][:7] <= p and cid not in people:
                        people[cid] = {"customer_name": o["customer_name"], "segment": o["segment"],
                                       "weight_source": "Actual_opportunities.csv (closed-won new business ARR)",
                                       "customer_arr": num(o["amount_arr"])}
            base = summary[p] - impl.get(p, ZERO)
            sub = q(base / (1 + RSVC_RATE))
            rsvc = base - sub
            self.sub[p], self.rsvc[p] = sub, rsvc
            weights = sorted(((cid, m["customer_arr"]) for cid, m in people.items()), key=lambda kw: kw[0])
            sa, ra = allocate(sub, weights), allocate(rsvc, weights)
            for cid in sa:
                self.by_cust[cid][p] = (sa[cid], ra[cid])
                self.meta[(cid, p)] = people[cid]

    def recurring(self, cid: str, p: str) -> Decimal:
        s = self.by_cust.get(cid, {}).get(p)
        return s[0] + s[1] if s else ZERO

    def split(self, cid: str, p: str) -> tuple[Decimal, Decimal]:
        return self.by_cust.get(cid, {}).get(p, (ZERO, ZERO))


# ----------------------------------------------------------------------------- billing


class Invoice:
    """``paid`` / ``written_off``: dates (or None). Plan invoices are paid on the plan rule; the Actual invoices get
    their payment record from collections_model.settle."""
    __slots__ = ("id", "version", "customer_id", "customer_name", "cadence", "terms", "issue", "invoice_date",
                 "due_date", "service", "amount", "kind", "paid", "written_off")

    def __init__(self, **kw):
        self.paid = self.written_off = None
        for k, v in kw.items():
            setattr(self, k, v)

    @property
    def collection(self) -> str:
        return month_of(self.paid) if self.paid else ""


class World:
    """One version's billing: invoices it issues plus the Actual invoices it carries."""

    def __init__(self, version: str, months: list[str]):
        self.version = version
        self.months = months
        self.own: list[Invoice] = []
        self.carried: list[Invoice] = []
        self.begin_ar = ZERO
        self.begin_dr = ZERO


def bill_customers(version: str, issue_months: list[str], customers: list[str], cadence: dict[str, str],
                   anniv: dict[str, int], terms: dict[str, str], names: dict[str, str], recurring) -> list[Invoice]:
    out = []
    for cid in customers:
        for i in issue_months:
            if cadence[cid] == "Monthly":
                service = [i]
            else:
                start = padd(i, 1)
                if (int(start[5:7]) - anniv[cid]) % 3:
                    # A restart mid-quarter is billed from the restart month to the end of its quarter.
                    if not recurring(cid, start) or recurring(cid, i):
                        continue
                    service = [start]
                    while (int(padd(service[-1], 1)[5:7]) - anniv[cid]) % 3:
                        service.append(padd(service[-1], 1))
                else:
                    service = [start, padd(start, 1), padd(start, 2)]
                run = []
                for s in service:
                    if not recurring(cid, s):
                        break
                    run.append(s)
                service = run
            amounts = {s: recurring(cid, s) for s in service}
            amounts = {s: a for s, a in amounts.items() if a}
            if not amounts:
                continue
            inv_date = first_day(i)
            due = inv_date + dt.timedelta(days=TERMS_DAYS[terms[cid]])
            out.append(Invoice(
                id=f"INV-{LETTER[version]}-{i.replace('-', '')}-{cid}", version=version, customer_id=cid,
                customer_name=names[cid], cadence=cadence[cid], terms=terms[cid], issue=i, invoice_date=inv_date,
                due_date=due, paid=due + dt.timedelta(days=COLLECTION_LAG_DAYS),
                service=amounts, amount=sum(amounts.values(), ZERO), kind="recurring"))
    return out


def implementation_invoices(ds: Dataset, version: str) -> list[Invoice]:
    out = []
    for r in ds.rows(f"{version}_implementation_schedule.csv"):
        p = r["period"][:7]
        fee = num(r["implementation_fee"])
        due, cp = dt.date.fromisoformat(r["due_date"]), r["collection_period"][:7]
        out.append(Invoice(
            id=r["invoice_id"], version=version, customer_id=r["customer_id"], customer_name=r["customer_name"],
            cadence="One-time", terms="", issue=p, invoice_date=dt.date.fromisoformat(r["invoice_date"]),
            due_date=due, paid=min(max(due, first_day(cp)), last_day(cp)),
            service={p: fee}, amount=fee, kind="implementation"))
    return out


def rollforward(world: World, revenue_by_month: dict[str, Decimal]) -> dict[str, dict[str, Decimal]]:
    billed: dict[str, Decimal] = defaultdict(Decimal)
    for inv in world.own:
        billed[inv.issue] += inv.amount
    collected: dict[str, Decimal] = defaultdict(Decimal)
    written: dict[str, Decimal] = defaultdict(Decimal)
    for inv in world.own + world.carried:
        collected[inv.collection] += inv.amount
        written[write_off_month(inv)] += inv.amount
    out = {}
    ar, dr = world.begin_ar, world.begin_dr
    for p in world.months:
        row = {"begin_ar": ar, "billings": billed[p], "collections": collected[p], "write_offs": written[p],
               "begin_dr": dr, "revenue": revenue_by_month[p]}
        ar = ar + billed[p] - collected[p] - written[p]
        dr = dr + billed[p] - revenue_by_month[p]
        row["end_ar"], row["end_dr"] = ar, dr
        out[p] = row
    return out


def open_balances(invoices: list[Invoice], month_end: str) -> tuple[Decimal, Decimal]:
    """(AR, deferred revenue) at ``month_end`` from invoices issued by then."""
    ar = dr = ZERO
    for inv in invoices:
        if inv.issue > month_end:
            continue
        if is_open(inv, last_day(month_end)):
            ar += inv.amount
        dr += sum((a for s, a in inv.service.items() if s > month_end), ZERO)
    return ar, dr


# ----------------------------------------------------------------------------- main build


def build(src: str, dst: str, opening_equity_adjustment: Decimal) -> list[str]:
    notes: list[str] = []
    if os.path.exists(dst):
        raise SystemExit(f"{dst} exists; pick a new folder")
    shutil.copytree(src, dst)
    for name in REMOVED_FILES:
        if os.path.exists(os.path.join(dst, name)):
            os.remove(os.path.join(dst, name))
            notes.append(f"removed {name} (old supporting schedule that did not tie)")
    ds = Dataset(src)
    org = ds.rows("Actual_customers.csv")[0]["organization_id"]

    master_fields, master = ds.get("Actual_customers.csv")
    logos = new_logos(ds)
    cadence, anniv = assign_cadence(master, logos)
    terms = {r["customer_id"]: r["billing_terms"] for r in master}
    names = {r["customer_id"]: r["customer_name"] for r in master}
    for cid, o in logos.items():
        terms[cid], names[cid] = o["billing_terms"], o["customer_name"]
    plan_only = plan_logos(ds, master, logos)
    billing = {"Actual": (cadence, anniv, terms, names)}
    for v, rows in plan_only.items():
        billing[v] = ({**cadence, **{r["customer_id"]: no_annual(r["billing_cadence"]) for r in rows}},
                      {**anniv, **{r["customer_id"]: int(r["customer_start_date"][5:7]) for r in rows}},
                      {**terms, **{r["customer_id"]: r["billing_terms"] for r in rows}},
                      {**names, **{r["customer_id"]: r["customer_name"] for r in rows}})

    rev = {v: Revenue(ds, v, logos) for v in VERSIONS}

    def recurring_actual_world(cid: str, p: str) -> Decimal:
        if p < rev["Actual"].months[0]:
            return rev["Actual"].recurring(cid, rev["Actual"].months[0])
        if p <= CLOSE:
            return rev["Actual"].recurring(cid, p)
        f = rev["Forecast"]
        return f.recurring(cid, min(p, f.months[-1]))

    def recurring_in(version: str):
        r = rev[version]

        def fn(cid: str, p: str) -> Decimal:
            return r.recurring(cid, min(p, r.months[-1]))
        return fn

    all_customers = sorted(set(cadence))
    worlds: dict[str, World] = {}
    a = World("Actual", rev["Actual"].months)
    a.own = bill_customers("Actual", prange(PRE_PERIOD_START, CLOSE), all_customers, cadence, anniv, terms, names,
                           recurring_actual_world) + implementation_invoices(ds, "Actual")
    history = ds.rows("Actual_customer_arr_history.csv") if ds.exists("Actual_customer_arr_history.csv") else []
    cases = plan_cases(history, a.own, cadence, terms)
    settle(a.own, cases)
    notes.append("collections cases: " + "; ".join(
        f"{c.kind} {c.customer_id} ({len(c.invoices)} invoices, {sum((i.amount for i in c.invoices), ZERO):,.2f})"
        for c in cases))
    pre = [inv for inv in a.own if inv.issue < a.months[0]]
    a.own = [inv for inv in a.own if inv.issue >= a.months[0]]
    a.carried = pre
    a.begin_ar, a.begin_dr = open_balances(pre, padd(a.months[0], -1))
    worlds["Actual"] = a
    for v in ("Budget", "Forecast"):
        start = CHAIN_FROM_ACTUAL[v]
        w = World(v, rev[v].months)
        v_cadence, v_anniv, v_terms, v_names = billing.get(v, billing["Actual"])
        w.own = bill_customers(v, w.months, sorted(set(v_cadence)), v_cadence, v_anniv, v_terms, v_names,
                               recurring_in(v)) + implementation_invoices(ds, v)
        w.carried = [inv for inv in a.carried + a.own if inv.issue < start]
        w.begin_ar, w.begin_dr = open_balances(w.carried, padd(start, -1))
        worlds[v] = w

    gl_revenue = {v: {p: rev[v].sub[p] + rev[v].rsvc[p] + rev[v].impl.get(p, ZERO) for p in rev[v].months} for v in VERSIONS}
    roll = {v: rollforward(worlds[v], gl_revenue[v]) for v in VERSIONS}
    allowance = {v: {r["period"]: r for r in allowance_rollforward(worlds[v].carried + worlds[v].own, cases,
                                                                   worlds[v].months)} for v in VERSIONS}
    for v in VERSIONS:
        for p, x in roll[v].items():
            al = allowance[v][p]
            if al["gross_accounts_receivable"] != x["end_ar"]:
                raise ValueError(f"{v} {p}: aged AR {al['gross_accounts_receivable']} != AR rollforward {x['end_ar']}")
            if al["write_offs"] != x["write_offs"]:
                raise ValueError(f"{v} {p}: allowance write-offs {al['write_offs']} != AR write-offs {x['write_offs']}")
        start = CHAIN_FROM_ACTUAL.get(v)
        if start and allowance[v][start]["beginning_allowance"] != allowance["Actual"][padd(start, -1)]["ending_allowance"]:
            raise ValueError(f"{v}: opening allowance does not continue from the Actual {padd(start, -1)}")

    for v in VERSIONS:
        w = worlds[v]
        end = w.months[-1]
        ar_inv, dr_inv = open_balances(w.carried + w.own, end)
        notes.append(f"{v}: invoices {len(w.own)}; ending AR {roll[v][end]['end_ar']:,.2f} (open invoices {ar_inv:,.2f}); "
                     f"ending deferred revenue {roll[v][end]['end_dr']:,.2f} (unrecognized invoice amounts {dr_inv:,.2f})")
        neg = [p for p in w.months if roll[v][p]["end_dr"] < 0]
        if neg:
            notes.append(f"{v}: deferred revenue below zero in {neg}")

    write_income_statement_totals(ds, dst, notes)
    write_customers(ds, dst, master_fields, master, logos, cadence, org, plan_only)
    write_billing_files(ds, dst, org, worlds, roll, rev)
    write_collections_files(ds, dst, org, worlds, cases, allowance, master, logos, notes)
    write_chart_of_accounts(ds, dst)
    write_balance_sheet_inputs(ds, dst, roll, allowance, opening_equity_adjustment, notes)
    write_mrr(ds, dst, notes)
    rosters = write_rosters(ds, dst, notes)
    write_opportunities(ds, dst, rosters, notes)
    write_quota_capacity(ds, dst, rosters, notes)
    write_commissions(ds, dst, rosters["Actual"], notes)

    share = {}
    for p in ("2024-01", CLOSE, "2026-12"):
        v = "Forecast" if p > CLOSE else "Actual"
        v_cadence = billing.get(v, billing["Actual"])[0]
        tot = mon = ZERO
        for (cid, mp), m in rev[v].meta.items():
            if mp == p:
                tot += m["customer_arr"]
                mon += m["customer_arr"] if v_cadence[cid] == "Monthly" else ZERO
        share[p] = mon / tot if tot else ZERO
    notes.append("monthly-billed share of ARR: " + ", ".join(f"{p} {s:.1%}" for p, s in share.items()))
    with open(os.path.join(dst, "v5_build_notes.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(notes) + "\n")
    return notes


def write_income_statement_totals(ds, dst, notes):
    """Gross profit, EBITDA and net income recalculated from the lines (v4 stated totals carried rounding)."""
    opex = ("sales_and_marketing", "research_and_development", "general_and_administrative")
    below = ("depreciation_and_amortization", "interest_expense", "tax_expense")
    for v in VERSIONS:
        fields, rows = ds.get(f"{v}_income_statement.csv")
        out, changed = [], 0
        for r in rows:
            nr = dict(r)
            gp = num(r["revenue"]) - num(r["cost_of_revenue"])
            ebitda = gp - sum((num(r[k]) for k in opex), ZERO)
            ni = ebitda - sum((num(r[k]) for k in below if k in r), ZERO)
            new = {"gross_profit": gp, "ebitda": ebitda, "net_income": ni}
            new = {k: x for k, x in new.items() if k in fields}
            if any(num(r[k]) != x for k, x in new.items()):
                changed += 1
            nr.update({k: f"{x:.2f}" for k, x in new.items()})
            out.append(nr)
        write(os.path.join(dst, f"{v}_income_statement.csv"), fields, out)
        notes.append(f"{v} income statement: gross profit, EBITDA, net income recalculated from the lines ({changed} of {len(rows)} months changed)")


def write_customers(ds, dst, fields, master, logos, cadence, org, plan_only):
    rows = []
    for r in master:
        nr = dict(r)
        nr["billing_cadence"] = cadence[r["customer_id"]]
        rows.append(nr)
    in_master = {r["customer_id"] for r in master}
    for cid, o in sorted(logos.items()):
        if cid in in_master:
            continue
        digits = "".join(ch for ch in cid if ch.isdigit())
        rows.append({
            "organization_id": org, "customer_id": cid, "customer_name": o["customer_name"], "segment": o["segment"],
            "industry": o["industry"], "status": "Active", "customer_start_date": o["contract_start_date"],
            "first_mrr_date": f"{o['period'][:7]}-01",
            "contract_start_date": o["contract_start_date"], "billing_cadence": cadence[cid],
            "billing_terms": o["billing_terms"], "billing_state": o["customer_state"], "source_crm": "Salesforce",
            "netsuite_customer_id": f"NS-{cid}", "stripe_customer_id": f"cus_demo_{digits}",
            "starting_mrr_jan_2026": "0", "starting_arr_jan_2026": "0", "currency": "USD"})
    for v in VERSIONS:
        extra = [{**r, "billing_cadence": no_annual(r["billing_cadence"])} for r in plan_only.get(v, [])]
        write(os.path.join(dst, f"{v}_customers.csv"), fields, rows + extra)


def write_billing_files(ds, dst, org, worlds, roll, rev):
    for v in VERSIONS:
        w, r = worlds[v], rev[v]
        months = set(w.months)
        own = sorted((inv for inv in w.own if inv.issue in months), key=lambda i: (i.issue, i.kind, i.customer_id))
        inv_fields = list(ds.fields(f"{v}_invoices.csv"))
        if "payment_date" not in inv_fields:
            inv_fields.insert(inv_fields.index("payment_status") + 1, "payment_date")
        close = last_day(CLOSE)
        inv_rows, sched_rows = [], []
        carrier: dict[tuple[str, str], Invoice] = {}
        for inv in w.carried + w.own:
            if inv.kind == "recurring":
                for s in inv.service:
                    carrier[(inv.customer_id, s)] = inv
        for inv in own:
            svc = sorted(inv.service)
            paid = v == "Actual" and inv.paid is not None and inv.paid <= close
            if v != "Actual":
                status = "Forecast"
            elif inv.written_off and inv.written_off <= close:
                status = "Written Off"
            else:
                status = "Paid" if paid else "Open"
            inv_rows.append({
                "organization_id": org, "version": v, "invoice_id": inv.id, "customer_id": inv.customer_id,
                "customer_name": inv.customer_name, "invoice_period": inv.issue,
                "service_period_start": first_day(svc[0]).isoformat(), "service_period_end": last_day(svc[-1]).isoformat(),
                "invoice_date": inv.invoice_date.isoformat(), "due_date": inv.due_date.isoformat(),
                "invoice_amount": inv.amount, "payment_status": status,
                "payment_date": inv.paid.isoformat() if paid else "", "billing_cadence": inv.cadence,
                "billing_terms": inv.terms or "Net 30", "currency": "USD"})
            driver = {"recurring": f"{inv.cadence} subscription + recurring services",
                      "implementation": "Implementation fee at signing"}[inv.kind]
            sched_rows.append({
                "organization_id": org, "version": v, "period": inv.issue, "invoice_id": inv.id,
                "customer_id": inv.customer_id, "customer_name": inv.customer_name,
                "invoice_date": inv.invoice_date.isoformat(), "due_date": inv.due_date.isoformat(),
                "billing_terms": inv.terms or "Net 30", "billings": inv.amount, "collection_period": inv.collection,
                "driver": driver})
        write(os.path.join(dst, f"{v}_invoices.csv"), inv_fields, inv_rows)
        sched_fields = ds.fields("Actual_invoice_billing_schedule.csv")
        write(os.path.join(dst, f"{v}_invoice_billing_schedule.csv"), sched_fields, sched_rows)

        rs_fields = ds.fields(f"{v}_recurring_services_schedule.csv")
        rs_rows, rr_rows = [], []
        for p in r.months:
            for cid in sorted(c for c in r.by_cust if p in r.by_cust[c]):
                sub, rsvc = r.by_cust[cid][p]
                m = r.meta[(cid, p)]
                inv = carrier.get((cid, p))
                rs_rows.append({
                    "organization_id": org, "version": v, "period": p, "customer_id": cid,
                    "customer_name": m["customer_name"], "segment": m["segment"], "weight_source": m["weight_source"],
                    "customer_arr": q(m["customer_arr"]), "month_subscription_revenue": r.sub[p], "rate": f"{RSVC_RATE:.2f}",
                    "recurring_services_revenue": rsvc, "invoice_id": inv.id if inv else "",
                    "invoice_date": inv.invoice_date.isoformat() if inv else "",
                    "due_date": inv.due_date.isoformat() if inv else "", "collection_period": inv.collection if inv else ""})
                rr_rows.append({"organization_id": org, "version": v, "period": p, "customer_id": cid,
                                "customer_name": m["customer_name"], "recognized_revenue": sub,
                                "recognized_arr": q(m["customer_arr"]), "revenue_type": "Subscription"})
                rr_rows.append({"organization_id": org, "version": v, "period": p, "customer_id": cid,
                                "customer_name": m["customer_name"], "recognized_revenue": rsvc,
                                "recognized_arr": "0", "revenue_type": "Recurring Services"})
        for row in ds.rows(f"{v}_implementation_schedule.csv"):
            rr_rows.append({"organization_id": org, "version": v, "period": row["period"][:7],
                            "customer_id": row["customer_id"], "customer_name": row["customer_name"],
                            "recognized_revenue": num(row["implementation_fee"]), "recognized_arr": "0",
                            "revenue_type": "Implementation & Onboarding"})
        write(os.path.join(dst, f"{v}_recurring_services_schedule.csv"), rs_fields, rs_rows)
        write(os.path.join(dst, f"{v}_revenue_recognition.csv"), ds.fields("Actual_revenue_recognition.csv"), rr_rows)

        dr_rows, ar_rows, cc_rows = [], [], []
        ar_fields = list(ds.fields("Actual_accounts_receivable_rollforward.csv"))
        if "write_offs" not in ar_fields:
            ar_fields.insert(ar_fields.index("cash_collections") + 1, "write_offs")
        driver = ("Customer payments received (Actual_customer_payments.csv)" if v == "Actual" else
                  "Invoices collected: customer terms + 7 days; Actual invoices as paid")
        for p in w.months:
            x = roll[v][p]
            dr_rows.append({"organization_id": org, "version": v, "period": p, "beginning_deferred_revenue": x["begin_dr"],
                            "new_billings": x["billings"], "revenue_recognized": x["revenue"],
                            "ending_deferred_revenue": x["end_dr"], "waterfall_check": "0.00"})
            ar_rows.append({"organization_id": org, "version": v, "period": p, "beginning_accounts_receivable": x["begin_ar"],
                            "new_billings": x["billings"], "cash_collections": x["collections"],
                            "write_offs": x["write_offs"],
                            "ending_accounts_receivable": x["end_ar"], "rollforward_check": "0.00"})
            cc_rows.append({"organization_id": org, "version": v, "period": p, "cash_collections": x["collections"],
                            "beginning_cash": "", "ending_cash": "", "driver": driver})
        write(os.path.join(dst, f"{v}_deferred_revenue_waterfall.csv"), ds.fields("Actual_deferred_revenue_waterfall.csv"), dr_rows)
        write(os.path.join(dst, f"{v}_accounts_receivable_rollforward.csv"), ar_fields, ar_rows)
        write(os.path.join(dst, f"{v}_cash_collections.csv"), ds.fields("Actual_cash_collections.csv"), cc_rows)


ALLOWANCE_FIELDS = ["organization_id", "version", "period", "beginning_allowance", "provision_for_credit_losses",
                    "write_offs", "ending_allowance", "gross_accounts_receivable", "net_accounts_receivable",
                    *(f"reserve_{b}" for b in BUCKETS), "specific_reserve"]
NEW_ACCOUNTS = (
    {"account_number": "1110", "account_name": "Allowance for Doubtful Accounts", "statement": "Balance Sheet",
     "statement_category": "Assets", "account_group": "AR", "expense_type": "Accounts Receivable",
     "description": "Contra AR: open invoices not expected to be collected, by age and for customers in collections "
                    "(<version>_allowance_for_doubtful_accounts.csv)"},
    {"account_number": "6560", "account_name": "Bad Debt Expense", "statement": "Income Statement",
     "statement_category": "Operating Expense", "account_group": "G&A Expense", "expense_type": "Bad Debt",
     "description": "Provision for credit losses: change in the allowance for doubtful accounts plus write-offs"},
)


def write_collections_files(ds, dst, org, worlds, cases, allowance, master, logos, notes):
    """The allowance rollforward per version; the Actual payments, AR aging, dunning log and collections cases;
    the Actual implementation schedule's collection period from the payment record."""
    for v in VERSIONS:
        rows = [{"organization_id": org, "version": v, **r} for _, r in sorted(allowance[v].items())]
        write(os.path.join(dst, f"{v}_allowance_for_doubtful_accounts.csv"), ALLOWANCE_FIELDS, rows)
    a = worlds["Actual"]
    invoices = a.carried + a.own
    first, close = first_day(a.months[0]), last_day(CLOSE)
    segment = {r["customer_id"]: r["segment"] for r in master}
    segment.update({cid: o["segment"] for cid, o in logos.items()})
    names = {inv.customer_id: inv.customer_name for inv in invoices}
    finance = [e for e in ds.rows("Actual_Employees.csv") if e["department"] == "Finance"]
    files = {
        "Actual_customer_payments.csv": [r for r in payment_rows(org, invoices, close, segment) if r["period"] >= a.months[0]],
        "Actual_AR_Aging.csv": aging_rows(org, invoices, a.months, names),
        "Actual_collections_activity.csv": [r for r in activity_rows(org, invoices, cases, close, finance)
                                            if r["activity_date"] >= first.isoformat()],
        "Actual_collections_cases.csv": case_rows(org, cases, close),
    }
    for name, rows in files.items():
        write(os.path.join(dst, name), list(rows[0]), rows)
    paid_by: dict[str, Decimal] = defaultdict(Decimal)
    for r in files["Actual_customer_payments.csv"]:
        paid_by[r["period"]] += r["amount"]
    imp_fields, imp = read(os.path.join(dst, "Actual_implementation_schedule.csv"))
    by_id = {inv.id: inv for inv in invoices if inv.kind == "implementation"}
    for r in imp:
        r["collection_period"] = by_id[r["invoice_id"]].collection
    write(os.path.join(dst, "Actual_implementation_schedule.csv"), imp_fields, imp)
    end = allowance["Actual"][CLOSE]
    notes.append(f"collections: {len(files['Actual_customer_payments.csv'])} customer payments "
                 f"({sum(paid_by.values(), ZERO):,.2f}), {len(files['Actual_collections_activity.csv'])} dunning "
                 f"steps, {len(cases)} cases; write-offs "
                 f"{sum((r['write_offs'] for r in allowance['Actual'].values()), ZERO):,.2f}; allowance at {CLOSE} "
                 f"{end['ending_allowance']:,.2f} on gross AR {end['gross_accounts_receivable']:,.2f}")


def write_chart_of_accounts(ds, dst):
    for v in VERSIONS:
        fields, rows = read(os.path.join(dst, f"{v}_chart_of_accounts.csv"))
        have = {r["account_number"] for r in rows}
        for acct in NEW_ACCOUNTS:
            if acct["account_number"] not in have:
                at = next((i for i, r in enumerate(rows) if r["account_number"] > acct["account_number"]), len(rows))
                rows.insert(at, {k: acct.get(k, "") for k in fields})
        write(os.path.join(dst, f"{v}_chart_of_accounts.csv"), fields, rows)


def write_balance_sheet_inputs(ds, dst, roll, allowance, opening_equity_adjustment, notes):
    """AR is net of the allowance for doubtful accounts."""
    for v in VERSIONS:
        fields, rows = ds.get(f"{v}_balance_sheet.csv")
        out = []
        for r in rows:
            p = r["period"][:7]
            nr = dict(r)
            if p in roll[v]:
                nr["accounts_receivable"] = f"{roll[v][p]['end_ar'] - allowance[v][p]['ending_allowance']:.2f}"
                nr["deferred_revenue"] = f"{roll[v][p]['end_dr']:.2f}"
            out.append(nr)
        if v == "Actual":
            o = out[0]
            a0 = allowance[v][o["period"][:7]]["ending_allowance"]
            liab = sum((num(o[k]) for k in ("accounts_payable", "deferred_revenue", "debt", "other_liabilities")), ZERO)
            equity = num(o["equity"]) - opening_equity_adjustment - a0
            cash = liab + equity - sum((num(o[k]) for k in ("accounts_receivable", "ppe_net", "prepaids_and_other_current")), ZERO)
            notes.append(f"opening {o['period']}: AR {num(o['accounts_receivable']):,.2f} (net of a "
                         f"{a0:,.2f} allowance), deferred revenue {num(o['deferred_revenue']):,.2f}, equity "
                         f"{equity:,.2f} (v4 {num(rows[0]['equity']):,.2f} less {opening_equity_adjustment:,.2f} and "
                         f"the allowance), cash {cash:,.2f} (v4 {num(rows[0]['cash']):,.2f})")
            o["equity"], o["cash"] = f"{equity:.2f}", f"{cash:.2f}"
            o["total_liabilities"] = f"{liab:.2f}"
            o["total_assets"] = o["total_liabilities_and_equity"] = f"{liab + equity:.2f}"
            o["balance_check"] = "0"
        write(os.path.join(dst, f"{v}_balance_sheet.csv"), fields, out)


def write_mrr(ds, dst, notes):
    for v in VERSIONS:
        fields, rows = ds.get(f"{v}_MRR_Waterfall.csv")
        fields = [*fields, *(f for f in WATERFALL_BUCKET_FIELDS if f not in fields)]
        buckets = bucket_waterfall(ds.rows(f"{v}_customer_arr_history.csv"), [r["period"][:7] for r in rows])
        out, changed = [], 0
        for r in rows:
            nr = dict(r)
            bop, nb, ex = num(r["beginning_arr"]), num(r["new_business_arr"]), num(r["expansion_arr"])
            co, ch, re_ = num(r["contraction_arr"]), num(r["churn_arr"]), num(r.get("reactivation_arr"))
            net = nb + ex + re_ - co - ch
            if abs(bop + net - num(r["ending_arr"])) > 1:
                notes.append(f"{v} MRR {r['period']}: ending ARR {r['ending_arr']} != beginning + movements {bop + net:,.2f}")
            b = buckets[r["period"][:7]]
            cs = {k: b[LINES[k][1]] for k in ("expansion", "contraction", "churn", "reactivation")}
            moved = b[NEW_BUSINESS_TOTAL] + cs["expansion"] + cs["reactivation"] - cs["contraction"] - cs["churn"]
            if moved != net:
                raise ValueError(f"{v} {r['period']}: customer bucket lines {moved} != waterfall movements {net}")
            base = b[CUSTOMER_SUCCESS_BEGINNING]
            kept = base - cs["contraction"] - cs["churn"]
            new = {"renewal_arr": f"{bop - co - ch:.2f}", "net_new_arr": f"{net:.2f}",
                   "gross_retention_rate": f"{kept / base:.4f}",
                   "net_dollar_retention_rate": f"{(kept + cs['expansion'] + cs['reactivation']) / base:.4f}",
                   "waterfall_check": "0"}
            if any(num(nr.get(k)) != num(val) for k, val in new.items() if k != "waterfall_check"):
                changed += 1
            nr.update(new)
            nr.update({k: f"{x:.2f}" for k, x in b.items()})
            out.append(nr)
        write(os.path.join(dst, f"{v}_MRR_Waterfall.csv"), fields, out)
        notes.append(f"{v} MRR: New Business and Customer Success bucket lines from the customer history; GRR and NRR on "
                     f"customers 12 months and older; renewal ARR and net new ARR from the movements "
                     f"({changed} of {len(rows)} months changed)")


# ----------------------------------------------------------------------------- reps, quotas, commissions


def ramp_curve(ds) -> dict[int, dict[int, Decimal]]:
    curve: dict[int, dict[int, Decimal]] = defaultdict(dict)
    for r in ds.rows("Hiring_Ramp_Assumptions.csv"):
        curve[int(r["ramp_months"])][int(r["month_after_start"])] = num(r["productivity_pct"])
    return curve


def ramp_pct(curve, ramp_months: int, hire: str, p: str) -> Decimal:
    k = pidx(p) - pidx(hire) + 1
    if k < 1:
        return ZERO
    return curve.get(ramp_months, {}).get(k, Decimal("1"))


def write_rosters(ds, dst, notes):
    """Per version, the Sales employees month by month: quota from the employee file, ramp
    from Hiring_Ramp_Assumptions.csv. Writes each version's sales_reps and the Budget quotas; Actual quotas are
    written with attainment by write_opportunities."""
    curve = ramp_curve(ds)
    fields = ds.fields("Actual_Sales_Quotas.csv")
    reps_fields = ds.fields("Actual_sales_reps.csv")
    org = ds.rows("Actual_sales_reps.csv")[0]["organization_id"]
    rosters = {}
    for v in VERSIONS:
        emps = sorted((e for e in read(os.path.join(dst, f"{v}_Employees.csv"))[1] if e["department"] == "Sales"),
                      key=lambda e: e["employee_id"])
        bad = [e["employee_id"] for e in emps if (e["quota_carrying"] == "Yes") != (quota_type(e["role"]) != "Non-Quota")
               or e["region"] not in TERRITORIES]
        if bad:
            raise ValueError(f"{v}_Employees.csv: quota_carrying disagrees with the role, or no territory: {bad}")
        by_period: dict[str, list[dict[str, str]]] = {}
        for p in prange(QUOTA_FROM, CLOSE if v == "Actual" else PLAN_END):
            by_period[p] = []
            for e in emps:
                if not active(e, p):
                    continue
                kind = quota_type(e["role"])
                annual = num(e["annual_quota_arr"]) if kind != "Non-Quota" else ZERO
                pct = (ramp_pct(curve, int(e["productivity_ramp_months"] or 0), e["hire_date"][:7], p)
                       if kind != "Non-Quota" else Decimal("1"))
                monthly = q(annual / 12)
                by_period[p].append({
                    "period": p, "version": v, "employee_id": e["employee_id"], "rep_name": e["employee_name"],
                    "quota_status": "Open Req" if e["employment_status"] == "Planned" else "Filled", "role": e["role"],
                    "sub_department": e["sub_department"], "department": e["department"], "region": e["region"],
                    "manager": e["manager"], "quota_type": kind, "hire_period": e["hire_date"][:7],
                    "annual_quota_arr": f"{annual:.2f}", "monthly_quota_arr": f"{monthly:.2f}",
                    "productivity_ramp_months": e["productivity_ramp_months"], "ramp_pct": f"{pct}",
                    "ramped_monthly_quota_arr": f"{q(monthly * pct):.2f}", "quota_attainment_actual_arr": "",
                    "quota_attainment_pct": "",
                    "source": f"{v}_Employees.csv (quota, ramp months); ramp from Hiring_Ramp_Assumptions.csv"})
        rosters[v] = {"names": {e["employee_id"]: e["employee_name"] for e in emps}, "by_period": by_period, "fields": fields}
        write(os.path.join(dst, f"{v}_sales_reps.csv"), reps_fields, [
            {"organization_id": org, "rep_id": e["employee_id"], "rep_name": e["employee_name"], "role": e["role"],
             "segment": REP_SEGMENT.get(e["sub_department"], "All"), "region": e["region"], "manager_id": e["manager"],
             "hire_date": e["hire_date"], "quota_eligible": e["quota_carrying"],
             "status": e["employment_status"]} for e in emps])
        last = max(by_period)
        notes.append(f"{v} sales team: {len(emps)} Sales employees; {last}: " + ", ".join(
            f"{k} {n}" for k, n in sorted(Counter(r["quota_type"] for r in by_period[last]).items()))
            + f"; quota months {min(by_period)}..{last}")
    write(os.path.join(dst, "Budget_Sales_Quotas.csv"), fields,
          [r for p in sorted(rosters["Budget"]["by_period"]) for r in rosters["Budget"]["by_period"][p]])
    return rosters


def assign_owners(opps: list[dict[str, str]], roster, balance: bool = True) -> dict[str, str]:
    """opportunity id -> rep id, from the bookings reps on the version's roster that month with ramped quota.
    New business (closed won at its ARR; open Forecast deals at weighted ARR) goes to the in-region rep furthest
    below quota (scaled by a fixed per-rep performance factor); other deals go round-robin in region."""
    owner: dict[str, str] = {}
    attained: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    rr: dict[tuple[str, str], int] = defaultdict(int)
    for o in sorted(opps, key=lambda x: (x["period"][:7], x["opportunity_id"])):
        p = o["period"][:7]
        if p not in roster["by_period"]:
            raise ValueError(f"{o['opportunity_id']}: no roster for {p}")
        pool = [r for r in roster["by_period"][p] if r["role"] in BOOKINGS_ROLES and num(r["ramped_monthly_quota_arr"]) > 0]
        if not pool:
            raise ValueError(f"{p}: no ramped bookings rep")
        local = [r for r in pool if r["region"] == o["region"]] or pool
        if balance and o["opportunity_type"] == "New Business" and o["close_status"] in ("Closed Won", "Open"):
            def load(r):
                factor = Decimal("0.75") + stable_unit(r["employee_id"]) / 2
                return attained[(p, r["employee_id"])] / (num(r["ramped_monthly_quota_arr"]) * factor)
            pick = min(local, key=lambda r: (load(r), r["employee_id"]))
            attained[(p, pick["employee_id"])] += num(o["amount_arr"] if o["close_status"] == "Closed Won" else o["weighted_arr"])
        else:
            key = (p, o["region"])
            pick = local[rr[key] % len(local)]
            rr[key] += 1
        owner[o["opportunity_id"]] = pick["employee_id"]
    return owner


def write_opportunities(ds, dst, rosters, notes):
    """Owners from each version's own roster; movement rows take their deal's owner, and pipeline-only deals
    (movements without an opportunity row) go round-robin in region from their first movement month."""
    for v in VERSIONS:
        roster = rosters[v]
        names = roster["names"]
        fields, rows = ds.get(f"{v}_opportunities.csv")
        owner = assign_owners(rows, roster)
        mv_fields, mv = ds.get(f"{v}_opportunity_movements.csv")
        first: dict[str, dict[str, str]] = {}
        for r in sorted(mv, key=lambda r: r["period"]):
            if r["opportunity_id"] not in owner:
                first.setdefault(r["opportunity_id"], r)
        owner.update(assign_owners(list(first.values()), roster, balance=False))
        out = []
        for r in rows:
            nr = dict(r)
            nr["owner"] = names[owner[r["opportunity_id"]]]
            nr["billing_cadence"] = no_annual(r["billing_cadence"])
            out.append(nr)
        write(os.path.join(dst, f"{v}_opportunities.csv"), fields, out)
        write(os.path.join(dst, f"{v}_opportunity_movements.csv"), mv_fields,
              [{**r, "owner": names[owner[r["opportunity_id"]]]} for r in mv])
        roster["owner"] = owner
        roster["opps"] = rows
        notes.append(f"{v} opportunities: {len(rows)} deals and {len(first)} pipeline-only deals owned by "
                     f"{len({owner[o['opportunity_id']] for o in rows})} reps on the {v} roster")
    notes.append("opportunities: new business balanced against ramped quota in region; no annual billing cadence")
    roster = rosters["Actual"]
    roster["actual_owner"], roster["actual_opps"] = roster["owner"], roster["opps"]

    attained: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for o in roster["actual_opps"]:
        if o["opportunity_type"] == "New Business" and o["close_status"] == "Closed Won":
            attained[(o["period"][:7], roster["actual_owner"][o["opportunity_id"]])] += num(o["amount_arr"])
    outbound = {r["period"][:7]: num(r["pipeline_arr_created"]) for r in ds.rows("Actual_marketing_pipeline.csv")
                if r["marketing_channel"] == "Outbound"}
    out = []
    for p in sorted(roster["by_period"]):
        rs = roster["by_period"][p]
        sdrs = [r for r in rs if r["quota_type"] == "Pipeline ARR" and num(r["ramped_monthly_quota_arr"]) > 0]
        sdr_alloc = allocate(outbound.get(p, ZERO), [(r["employee_id"], num(r["ramped_monthly_quota_arr"]) *
                                                      (Decimal("0.8") + stable_unit(r["employee_id"] + p) * Decimal("0.4")))
                                                     for r in sdrs])
        for r in rs:
            nr = dict(r)
            ramped = num(r["ramped_monthly_quota_arr"])
            if r["quota_type"] == "Bookings ARR":
                a = attained.get((p, r["employee_id"]), ZERO)
            elif r["quota_type"] == "Pipeline ARR":
                a = sdr_alloc.get(r["employee_id"], ZERO)
            else:
                nr["quota_attainment_actual_arr"] = nr["quota_attainment_pct"] = ""
                out.append(nr)
                continue
            nr["quota_attainment_actual_arr"] = f"{a:.2f}"
            nr["quota_attainment_pct"] = f"{a / ramped:.4f}" if ramped else ""
            nr["source"] = ("Closed-won new business in Actual_opportunities.csv owned by the rep"
                            if r["quota_type"] == "Bookings ARR" else
                            "Outbound pipeline created in Actual_marketing_pipeline.csv, split across SDRs")
            out.append(nr)
        roster["by_period"][p] = [x for x in out if x["period"] == p]
    write(os.path.join(dst, "Actual_Sales_Quotas.csv"), roster["fields"], out)
    notes.append("quotas: bookings attainment = closed-won new business by owner; SDR attainment = outbound pipeline created")


def write_quota_capacity(ds, dst, rosters, notes):
    """Forecast_quota_capacity.csv by territory: bookings reps on the Forecast roster and their annual quota, and the
    month's new business (Actual closed won through the close, Forecast weighted ARR after)."""
    fields, rows = ds.get("Forecast_quota_capacity.csv")
    org = rows[0]["organization_id"]
    nb: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for v, status, col in (("Actual", "Closed Won", "amount_arr"), ("Forecast", "Open", "weighted_arr")):
        for o in rosters[v]["opps"]:
            if o["opportunity_type"] == "New Business" and o["close_status"] == status:
                nb[(o["period"][:7], o["region"])] += num(o[col])
    out = []
    for p in sorted({r["period"][:7] for r in rows}):
        reps = [r for r in rosters["Forecast"]["by_period"][p] if r["quota_type"] == "Bookings ARR"]
        for t in TERRITORIES:
            mine = [r for r in reps if r["region"] == t]
            out.append({"organization_id": org, "version": "Forecast", "period": p, "region": t,
                        "quota_carrying_reps": str(len(mine)),
                        "quota_capacity_arr": sum((num(r["annual_quota_arr"]) for r in mine), ZERO),
                        "expected_bookings_arr": nb[(p, t)]})
    write(os.path.join(dst, "Forecast_quota_capacity.csv"), fields, out)
    notes.append(f"Forecast_quota_capacity.csv: {len(out)} rows by territory from the Forecast roster (was the company "
                 f"total repeated in every region); expected_bookings_arr is the month's new business")


def write_commissions(ds, dst, roster, notes):
    plans = {r["plan_id"]: r for r in ds.rows("Actual_commission_plans.csv")}
    fields = ds.fields("Actual_commission_payouts.csv")
    pct = {(r["period"], r["employee_id"]): num(r["quota_attainment_pct"]) for p in roster["by_period"]
           for r in roster["by_period"][p] if r["quota_attainment_pct"]}
    base_of = None
    if ds.exists(HISTORY_FILE):
        base_of = {b["opportunity_id"]: b["base"] for b in commission_bases(ds.rows(HISTORY_FILE)) if b["opportunity_id"]}
        fields = fields[:fields.index("booked_arr") + 1] + ["commission_base_arr"] + fields[fields.index("booked_arr") + 1:]
    rows, n, skipped = [], 0, []
    plan_for = {"New Business": "PLAN-AE-NEW", "Reactivation": "PLAN-AE-NEW", "Expansion": "PLAN-AM-EXP"}
    for o in sorted(roster["actual_opps"], key=lambda x: (x["period"], x["opportunity_id"])):
        if o["close_status"] != "Closed Won" or o["opportunity_type"] not in plan_for:
            continue
        plan = plans[plan_for[o["opportunity_type"]]]
        p = o["period"][:7]
        rep = roster["actual_owner"][o["opportunity_id"]]
        hit = pct.get((p, rep), ZERO) >= num(plan["accelerator_threshold"])
        rate = num(plan["accelerated_rate"] if hit else plan["base_commission_rate"])
        booked = num(o["amount_arr"])
        if base_of is None:
            base = booked
        elif o["opportunity_id"] not in base_of:
            raise ValueError(f"{o['opportunity_id']} is not in {HISTORY_FILE}")
        else:
            base = base_of[o["opportunity_id"]]
        if base <= 0:
            skipped.append(o["opportunity_id"])
            continue
        n += 1
        rows.append({"organization_id": o["organization_id"], "version": "Actual", "commission_id": f"COMM-{n:06d}",
                     "period": p, "rep_id": rep, "rep_name": roster["names"][rep], "opportunity_id": o["opportunity_id"],
                     "customer_id": o["customer_id"], "booked_arr": booked, "commission_base_arr": base,
                     "commission_rate": f"{rate}", "commission_amount": q(base * rate),
                     "payout_date": last_day(p).isoformat(), "clawback_flag": "No", "plan_id": plan["plan_id"]})
    write(os.path.join(dst, "Actual_commission_payouts.csv"), fields, rows)
    if base_of is not None:
        reduced = sum(1 for r in rows if r["commission_base_arr"] < r["booked_arr"])
        notes.append(f"commission payouts follow {HISTORY_FILE}: {reduced} paid on less than booked ARR "
                     f"(return or expansion above the customer's prior level only); no payout for {skipped or 'none'}")
    by_p: dict[str, Decimal] = defaultdict(Decimal)
    for r in rows:
        by_p[r["period"]] += r["commission_amount"]
    roster["payouts_by_period"] = dict(by_p)
    notes.append("commission payouts: " + ", ".join(f"{p} {v:,.2f}" for p, v in sorted(by_p.items())))


if __name__ == "__main__":
    adj = Decimal("0")
    args = list(sys.argv[1:])
    if "--opening-equity-adjustment" in args:
        i = args.index("--opening-equity-adjustment")
        adj = Decimal(args[i + 1])
        del args[i:i + 2]
    for line in build(args[0], args[1], adj):
        print(line)
