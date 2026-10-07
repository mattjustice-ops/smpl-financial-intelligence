"""Build the v5 demo dataset from v4: one billing model, June close completed, reps on one roster.

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
  * Collections: the customer's terms (Net 15/30/45/60) plus 7 days.
  * Deferred revenue = billed but not yet recognized. AR = billed but not yet collected.
    Budget continues from the Actual balances at Dec 2025, Forecast from Jun 2026.
  * Opening balance sheet (Jan 2024 month end): AR and deferred revenue come from the
    billing model; equity is the v4 opening equity less --opening-equity-adjustment; cash
    balances it.
  * June close: ARR waterfall rates and renewal ARR are calculated from the movements;
    quotas run through June; quota attainment is the closed-won new business each rep owns;
    commission payouts are rebuilt from closed-won deals at the plan rates and paid to
    roster reps; the 7 forecast hires that were due to start in June move to July because
    the June roster has no June hires.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import os
import shutil
import sys
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

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
ROSTER_REGION_RENAME = {"EMEA": "South"}
BOOKINGS_ROLES = {"Senior Account Executive", "Account Executive"}
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
                    if o["period"][:7] <= p:
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
    __slots__ = ("id", "version", "customer_id", "customer_name", "cadence", "terms", "issue", "invoice_date",
                 "due_date", "collection", "service", "amount", "kind")

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


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
                    continue
                service = [start, padd(start, 1), padd(start, 2)]
            amounts = {s: recurring(cid, s) for s in service}
            amounts = {s: a for s, a in amounts.items() if a}
            if not amounts:
                continue
            inv_date = first_day(i)
            due = inv_date + dt.timedelta(days=TERMS_DAYS[terms[cid]])
            out.append(Invoice(
                id=f"INV-{LETTER[version]}-{i.replace('-', '')}-{cid}", version=version, customer_id=cid,
                customer_name=names[cid], cadence=cadence[cid], terms=terms[cid], issue=i, invoice_date=inv_date,
                due_date=due, collection=month_of(due + dt.timedelta(days=COLLECTION_LAG_DAYS)),
                service=amounts, amount=sum(amounts.values(), ZERO), kind="recurring"))
    return out


def implementation_invoices(ds: Dataset, version: str) -> list[Invoice]:
    out = []
    for r in ds.rows(f"{version}_implementation_schedule.csv"):
        p = r["period"][:7]
        fee = num(r["implementation_fee"])
        out.append(Invoice(
            id=r["invoice_id"], version=version, customer_id=r["customer_id"], customer_name=r["customer_name"],
            cadence="One-time", terms="", issue=p, invoice_date=dt.date.fromisoformat(r["invoice_date"]),
            due_date=dt.date.fromisoformat(r["due_date"]), collection=r["collection_period"][:7],
            service={p: fee}, amount=fee, kind="implementation"))
    return out


def rollforward(world: World, revenue_by_month: dict[str, Decimal]) -> dict[str, dict[str, Decimal]]:
    billed: dict[str, Decimal] = defaultdict(Decimal)
    for inv in world.own:
        billed[inv.issue] += inv.amount
    collected: dict[str, Decimal] = defaultdict(Decimal)
    for inv in world.own + world.carried:
        collected[inv.collection] += inv.amount
    out = {}
    ar, dr = world.begin_ar, world.begin_dr
    for p in world.months:
        row = {"begin_ar": ar, "billings": billed[p], "collections": collected[p],
               "begin_dr": dr, "revenue": revenue_by_month[p]}
        ar = ar + billed[p] - collected[p]
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
        if inv.collection > month_end:
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
    pre = [inv for inv in a.own if inv.issue < a.months[0]]
    a.own = [inv for inv in a.own if inv.issue >= a.months[0]]
    a.carried = pre
    a.begin_ar, a.begin_dr = open_balances(pre, padd(a.months[0], -1))
    worlds["Actual"] = a
    for v in ("Budget", "Forecast"):
        start = CHAIN_FROM_ACTUAL[v]
        w = World(v, rev[v].months)
        w.own = bill_customers(v, w.months, all_customers, cadence, anniv, terms, names, recurring_in(v)) \
            + implementation_invoices(ds, v)
        w.carried = [inv for inv in a.carried + a.own if inv.issue < start]
        w.begin_ar, w.begin_dr = open_balances(w.carried, padd(start, -1))
        worlds[v] = w

    gl_revenue = {v: {p: rev[v].sub[p] + rev[v].rsvc[p] + rev[v].impl.get(p, ZERO) for p in rev[v].months} for v in VERSIONS}
    roll = {v: rollforward(worlds[v], gl_revenue[v]) for v in VERSIONS}

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
    write_customers(ds, dst, master_fields, master, logos, cadence, org)
    write_billing_files(ds, dst, org, worlds, roll, rev)
    write_balance_sheet_inputs(ds, dst, roll, opening_equity_adjustment, notes)
    write_mrr(ds, dst, notes)
    roster = write_roster_and_quotas(ds, dst, notes)
    write_opportunities(ds, dst, roster, notes)
    write_commissions(ds, dst, roster, notes)
    write_workforce(ds, dst, notes)

    share = {}
    for p in ("2024-01", CLOSE, "2026-12"):
        v = "Forecast" if p > CLOSE else "Actual"
        tot = mon = ZERO
        for (cid, mp), m in rev[v].meta.items():
            if mp == p:
                tot += m["customer_arr"]
                mon += m["customer_arr"] if cadence[cid] == "Monthly" else ZERO
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


def write_customers(ds, dst, fields, master, logos, cadence, org):
    rows = []
    for r in master:
        nr = dict(r)
        nr["billing_cadence"] = cadence[r["customer_id"]]
        rows.append(nr)
    for cid, o in sorted(logos.items()):
        digits = "".join(ch for ch in cid if ch.isdigit())
        rows.append({
            "organization_id": org, "customer_id": cid, "customer_name": o["customer_name"], "segment": o["segment"],
            "industry": o["industry"], "status": "Active", "customer_start_date": o["contract_start_date"],
            "contract_start_date": o["contract_start_date"], "billing_cadence": cadence[cid],
            "billing_terms": o["billing_terms"], "billing_state": o["customer_state"], "source_crm": "Salesforce",
            "netsuite_customer_id": f"NS-{cid}", "stripe_customer_id": f"cus_demo_{digits}",
            "starting_mrr_jan_2026": "0", "starting_arr_jan_2026": "0", "currency": "USD"})
    for v in VERSIONS:
        write(os.path.join(dst, f"{v}_customers.csv"), fields, rows)


def write_billing_files(ds, dst, org, worlds, roll, rev):
    for v in VERSIONS:
        w, r = worlds[v], rev[v]
        months = set(w.months)
        own = sorted((inv for inv in w.own if inv.issue in months), key=lambda i: (i.issue, i.kind, i.customer_id))
        inv_fields = ds.fields(f"{v}_invoices.csv")
        inv_rows, sched_rows = [], []
        carrier: dict[tuple[str, str], Invoice] = {}
        for inv in w.carried + w.own:
            if inv.kind == "recurring":
                for s in inv.service:
                    carrier[(inv.customer_id, s)] = inv
        for inv in own:
            svc = sorted(inv.service)
            status = ("Paid" if inv.collection <= CLOSE else "Open") if v == "Actual" else "Forecast"
            inv_rows.append({
                "organization_id": org, "version": v, "invoice_id": inv.id, "customer_id": inv.customer_id,
                "customer_name": inv.customer_name, "invoice_period": inv.issue,
                "service_period_start": first_day(svc[0]).isoformat(), "service_period_end": last_day(svc[-1]).isoformat(),
                "invoice_date": inv.invoice_date.isoformat(), "due_date": inv.due_date.isoformat(),
                "invoice_amount": inv.amount, "payment_status": status, "billing_cadence": inv.cadence,
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
        for p in w.months:
            x = roll[v][p]
            dr_rows.append({"organization_id": org, "version": v, "period": p, "beginning_deferred_revenue": x["begin_dr"],
                            "new_billings": x["billings"], "revenue_recognized": x["revenue"],
                            "ending_deferred_revenue": x["end_dr"], "waterfall_check": "0.00"})
            ar_rows.append({"organization_id": org, "version": v, "period": p, "beginning_accounts_receivable": x["begin_ar"],
                            "new_billings": x["billings"], "cash_collections": x["collections"],
                            "ending_accounts_receivable": x["end_ar"], "rollforward_check": "0.00"})
            cc_rows.append({"organization_id": org, "version": v, "period": p, "cash_collections": x["collections"],
                            "beginning_cash": "", "ending_cash": "",
                            "driver": "Invoices collected: customer terms + 7 days"})
        write(os.path.join(dst, f"{v}_deferred_revenue_waterfall.csv"), ds.fields("Actual_deferred_revenue_waterfall.csv"), dr_rows)
        write(os.path.join(dst, f"{v}_accounts_receivable_rollforward.csv"), ds.fields("Actual_accounts_receivable_rollforward.csv"), ar_rows)
        write(os.path.join(dst, f"{v}_cash_collections.csv"), ds.fields("Actual_cash_collections.csv"), cc_rows)


def write_balance_sheet_inputs(ds, dst, roll, opening_equity_adjustment, notes):
    for v in VERSIONS:
        fields, rows = ds.get(f"{v}_balance_sheet.csv")
        out = []
        for r in rows:
            p = r["period"][:7]
            nr = dict(r)
            if p in roll[v]:
                nr["accounts_receivable"] = f"{roll[v][p]['end_ar']:.2f}"
                nr["deferred_revenue"] = f"{roll[v][p]['end_dr']:.2f}"
            out.append(nr)
        if v == "Actual":
            o = out[0]
            liab = sum((num(o[k]) for k in ("accounts_payable", "deferred_revenue", "debt", "other_liabilities")), ZERO)
            equity = num(o["equity"]) - opening_equity_adjustment
            cash = liab + equity - sum((num(o[k]) for k in ("accounts_receivable", "ppe_net", "prepaids_and_other_current")), ZERO)
            notes.append(f"opening {o['period']}: AR {num(o['accounts_receivable']):,.2f}, deferred revenue "
                         f"{num(o['deferred_revenue']):,.2f}, equity {equity:,.2f} (v4 {num(rows[0]['equity']):,.2f} less "
                         f"{opening_equity_adjustment:,.2f}), cash {cash:,.2f} (v4 {num(rows[0]['cash']):,.2f})")
            o["equity"], o["cash"] = f"{equity:.2f}", f"{cash:.2f}"
            o["total_liabilities"] = f"{liab:.2f}"
            o["total_assets"] = o["total_liabilities_and_equity"] = f"{liab + equity:.2f}"
            o["balance_check"] = "0"
        write(os.path.join(dst, f"{v}_balance_sheet.csv"), fields, out)


def write_mrr(ds, dst, notes):
    for v in VERSIONS:
        fields, rows = ds.get(f"{v}_MRR_Waterfall.csv")
        out, changed = [], 0
        for r in rows:
            nr = dict(r)
            bop, nb, ex = num(r["beginning_arr"]), num(r["new_business_arr"]), num(r["expansion_arr"])
            co, ch, re_ = num(r["contraction_arr"]), num(r["churn_arr"]), num(r.get("reactivation_arr"))
            net = nb + ex + re_ - co - ch
            if abs(bop + net - num(r["ending_arr"])) > 1:
                notes.append(f"{v} MRR {r['period']}: ending ARR {r['ending_arr']} != beginning + movements {bop + net:,.2f}")
            new = {"renewal_arr": f"{bop - co - ch:.2f}", "net_new_arr": f"{net:.2f}",
                   "gross_retention_rate": f"{(bop - co - ch) / bop:.4f}",
                   "net_dollar_retention_rate": f"{(bop + ex + re_ - co - ch) / bop:.4f}", "waterfall_check": "0"}
            if any(num(nr.get(k)) != num(val) for k, val in new.items() if k != "waterfall_check"):
                changed += 1
            nr.update(new)
            out.append(nr)
        write(os.path.join(dst, f"{v}_MRR_Waterfall.csv"), fields, out)
        notes.append(f"{v} MRR: renewal ARR, net new ARR, GRR and NRR recalculated from the movements ({changed} of {len(rows)} months changed)")


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


def write_roster_and_quotas(ds, dst, notes):
    fields, rows = ds.get("Actual_Sales_Quotas.csv")
    name_pool = list(dict.fromkeys(r["rep_name"] for r in ds.rows("Actual_sales_reps.csv")))
    ids = sorted({r["employee_id"] for r in rows})
    rep_name = {rid: name_pool[i] for i, rid in enumerate(ids)}
    curve = ramp_curve(ds)
    by_period: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        nr = dict(r)
        nr["rep_name"] = rep_name[r["employee_id"]]
        nr["region"] = ROSTER_REGION_RENAME.get(r["region"], r["region"])
        by_period[r["period"]].append(nr)
    last = max(by_period)
    for p in prange(padd(last, 1), CLOSE):
        for r in by_period[last]:
            nr = dict(r)
            nr["period"] = p
            by_period[p].append(nr)
    mismatches = 0
    for p, rs in by_period.items():
        for r in rs:
            pct = ramp_pct(curve, int(r["productivity_ramp_months"]), r["hire_period"], p) if r["quota_type"] != "Non-Quota" else Decimal("1")
            if p <= last and r["quota_type"] != "Non-Quota" and num(r["ramp_pct"]) != pct:
                mismatches += 1
            r["ramp_pct"] = f"{pct}"
            r["ramped_monthly_quota_arr"] = f"{q(num(r['monthly_quota_arr']) * pct):.2f}" if r["quota_type"] != "Non-Quota" else "0.0"
    notes.append(f"quotas: roster {len(ids)} reps; months {min(by_period)}..{max(by_period)}; "
                 f"ramp from Hiring_Ramp_Assumptions.csv ({mismatches} loaded ramp values differed and were recalculated)")
    roster = {"names": rep_name, "by_period": by_period, "fields": fields}
    reps_fields = ds.fields("Actual_sales_reps.csv")
    org = ds.rows("Actual_sales_reps.csv")[0]["organization_id"]
    seg = {}
    for i, rid in enumerate(ids):
        role = next(r["role"] for r in rows if r["employee_id"] == rid)
        seg[rid] = {"Senior Account Executive": "Enterprise", "Account Executive": "Mid-Market" if i % 2 else "SMB"}.get(role, "All")
    reps_rows = []
    for rid in ids:
        r = next(x for x in by_period[CLOSE] if x["employee_id"] == rid)
        reps_rows.append({"organization_id": org, "rep_id": rid, "rep_name": rep_name[rid], "role": r["role"], "segment": seg[rid],
                          "region": r["region"], "manager_id": r["manager"], "hire_date": f"{r['hire_period']}-01",
                          "quota_eligible": "No" if r["quota_type"] == "Non-Quota" else "Yes", "status": "Active"})
    for v in VERSIONS:
        write(os.path.join(dst, f"{v}_sales_reps.csv"), reps_fields, reps_rows)
    return roster


def assign_owners(opps: list[dict[str, str]], roster, period_of) -> dict[str, str]:
    """opportunity id -> rep id. New business goes to the in-region rep furthest below quota (scaled by a
    fixed per-rep performance factor); other deal types go round-robin in region."""
    owner: dict[str, str] = {}
    attained: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    rr: dict[tuple[str, str], int] = defaultdict(int)
    fallback_p = max(roster["by_period"])
    for o in sorted(opps, key=lambda x: (period_of(x), x["opportunity_id"])):
        p = period_of(o)
        reps = roster["by_period"].get(p) or roster["by_period"][fallback_p]
        pool = [r for r in reps if r["role"] in BOOKINGS_ROLES and num(r["ramped_monthly_quota_arr"]) > 0]
        local = [r for r in pool if r["region"] == o["region"]] or pool
        if o["opportunity_type"] == "New Business" and o["close_status"] == "Closed Won":
            def load(r):
                factor = Decimal("0.75") + stable_unit(r["employee_id"]) / 2
                return attained[(p, r["employee_id"])] / (num(r["ramped_monthly_quota_arr"]) * factor)
            pick = min(local, key=lambda r: (load(r), r["employee_id"]))
            attained[(p, pick["employee_id"])] += num(o["amount_arr"])
        else:
            key = (p, o["region"])
            pick = sorted(local, key=lambda r: r["employee_id"])[rr[key] % len(local)]
            rr[key] += 1
        owner[o["opportunity_id"]] = pick["employee_id"]
    return owner


def write_opportunities(ds, dst, roster, notes):
    names = roster["names"]
    for v in VERSIONS:
        fields, rows = ds.get(f"{v}_opportunities.csv")
        owner = assign_owners(rows, roster, lambda o: o["period"][:7])
        out = []
        for r in rows:
            nr = dict(r)
            nr["owner"] = names[owner[r["opportunity_id"]]]
            nr["billing_cadence"] = no_annual(r["billing_cadence"])
            out.append(nr)
        write(os.path.join(dst, f"{v}_opportunities.csv"), fields, out)
        if v == "Actual":
            roster["actual_owner"] = owner
            roster["actual_opps"] = rows
    notes.append("opportunities: owners are roster reps (new business balanced against quota in region); no annual billing cadence")

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


def write_commissions(ds, dst, roster, notes):
    plans = {r["plan_id"]: r for r in ds.rows("Actual_commission_plans.csv")}
    fields = ds.fields("Actual_commission_payouts.csv")
    pct = {(r["period"], r["employee_id"]): num(r["quota_attainment_pct"]) for p in roster["by_period"]
           for r in roster["by_period"][p] if r["quota_attainment_pct"]}
    rows, n = [], 0
    plan_for = {"New Business": "PLAN-AE-NEW", "Reactivation": "PLAN-AE-NEW", "Expansion": "PLAN-AM-EXP"}
    for o in sorted(roster["actual_opps"], key=lambda x: (x["period"], x["opportunity_id"])):
        if o["close_status"] != "Closed Won" or o["opportunity_type"] not in plan_for:
            continue
        plan = plans[plan_for[o["opportunity_type"]]]
        p = o["period"][:7]
        rep = roster["actual_owner"][o["opportunity_id"]]
        hit = pct.get((p, rep), ZERO) >= num(plan["accelerator_threshold"])
        rate = num(plan["accelerated_rate"] if hit else plan["base_commission_rate"])
        n += 1
        rows.append({"organization_id": o["organization_id"], "version": "Actual", "commission_id": f"COMM-{n:06d}",
                     "period": p, "rep_id": rep, "rep_name": roster["names"][rep], "opportunity_id": o["opportunity_id"],
                     "customer_id": o["customer_id"], "booked_arr": num(o["amount_arr"]), "commission_rate": f"{rate}",
                     "commission_amount": q(num(o["amount_arr"]) * rate), "payout_date": last_day(p).isoformat(),
                     "clawback_flag": "No", "plan_id": plan["plan_id"]})
    write(os.path.join(dst, "Actual_commission_payouts.csv"), fields, rows)
    by_p: dict[str, Decimal] = defaultdict(Decimal)
    for r in rows:
        by_p[r["period"]] += r["commission_amount"]
    roster["payouts_by_period"] = dict(by_p)
    notes.append("commission payouts: " + ", ".join(f"{p} {v:,.2f}" for p, v in sorted(by_p.items())))


# ----------------------------------------------------------------------------- workforce


def write_workforce(ds, dst, notes):
    curve = ramp_curve(ds)
    req_fields, reqs = ds.get("Forecast_Open_Requisitions.csv")
    moved = []
    new_reqs = []
    for r in reqs:
        nr = dict(r)
        if r["status"] == "Open" and r["planned_start_date"][:7] <= CLOSE:
            nxt = padd(CLOSE, 1)
            nr["planned_start_date"] = nr["scenario_start_date"] = f"{nxt}-01"
            if nr.get("target_hire_date"):
                d = dt.date.fromisoformat(nr["target_hire_date"])
                nr["target_hire_date"] = (d + dt.timedelta(days=30)).isoformat()
            nr["source"] = f"{r.get('source', '')}; start moved from {r['planned_start_date']}: not filled by the {CLOSE} close".strip("; ")
            moved.append((r["department"], r["role"]))
        new_reqs.append(nr)
    write(os.path.join(dst, "Forecast_Open_Requisitions.csv"), req_fields, new_reqs)

    emp_fields, emps = ds.get("Forecast_Employees.csv")
    new_emps = []
    pending = list(moved)
    for e in emps:
        ne = dict(e)
        if e["employment_status"] == "Planned" and e["hire_date"][:7] <= CLOSE and (e["department"], e["role"]) in pending:
            pending.remove((e["department"], e["role"]))
            ne["hire_date"] = f"{padd(CLOSE, 1)}-01"
        new_emps.append(ne)
    if pending:
        notes.append(f"workforce: no planned employee found for moved reqs {pending}")
    write(os.path.join(dst, "Forecast_Employees.csv"), emp_fields, new_emps)

    hp_fields, hp = ds.get("Forecast_Headcount_Plan.csv")

    def active(emp_rows, dept, p):
        return [e for e in emp_rows if e["department"] == dept and e["hire_date"][:7] <= p
                and (not e["termination_date"] or e["termination_date"][:7] > p)]

    def plan_row(emp_rows, req_rows, base, p):
        dept = base["department"]
        act = active(emp_rows, dept, p)
        prev = active(emp_rows, dept, padd(p, -1))
        quota = [e for e in act if e["quota_carrying"] == "Yes"]
        ramped = sum((num(e["annual_quota_arr"]) * ramp_pct(curve, int(e["productivity_ramp_months"] or 0), e["hire_date"][:7], p)
                      for e in quota), ZERO)
        return {
            "headcount_beginning": str(len(prev)), "new_hires": str(sum(1 for e in act if e["hire_date"][:7] == p)),
            "headcount_ending": str(len(act)),
            "open_requisitions": str(sum(1 for r in req_rows if r["department"] == dept and r["status"] == "Open"
                                         and r["planned_start_date"][:7] > p)),
            "monthly_cash_payroll_cost": f"{q(sum((num(e['fully_loaded_cash_cost']) for e in act), ZERO) / 12):.2f}",
            "monthly_gaap_payroll_cost": f"{q(sum((num(e['fully_loaded_gaap_cost']) for e in act), ZERO) / 12):.2f}",
            "monthly_sbc": f"{q(sum((num(e['equity_sbc_annual']) for e in act), ZERO) / 12):.2f}",
            "quota_capacity_arr": f"{sum((num(e['annual_quota_arr']) for e in quota), ZERO):.2f}",
            "ramped_quota_capacity_arr": f"{q(ramped):.2f}",
        }

    diffs = defaultdict(int)
    out = []
    for r in hp:
        before = plan_row(emps, reqs, r, r["period"])
        after = plan_row(new_emps, new_reqs, r, r["period"])
        nr = dict(r)
        for k in before:
            if num(before[k]) != num(r[k]):
                diffs[k] += 1
            delta = num(after[k]) - num(before[k])
            if delta:
                val = num(r[k]) + delta
                nr[k] = str(int(val)) if k in ("headcount_beginning", "new_hires", "headcount_ending", "open_requisitions") else f"{val:.2f}"
        if any(nr[k] != r[k] for k in before):
            nr["source"] = f"{r['source']}; June starts moved to July"
        out.append(nr)
    write(os.path.join(dst, "Forecast_Headcount_Plan.csv"), hp_fields, out)
    notes.append(f"workforce: {len(moved)} forecast reqs/hires moved from June to July ({moved}); "
                 f"Forecast_Headcount_Plan.csv adjusted by the roster change "
                 f"(formula check against v4 cells it does not reproduce: {dict(diffs) or 'none'})")


if __name__ == "__main__":
    adj = Decimal("0")
    args = list(sys.argv[1:])
    if "--opening-equity-adjustment" in args:
        i = args.index("--opening-equity-adjustment")
        adj = Decimal(args[i + 1])
        del args[i:i + 2]
    for line in build(args[0], args[1], adj):
        print(line)
