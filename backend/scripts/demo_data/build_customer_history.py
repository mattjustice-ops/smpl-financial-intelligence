"""Customer ARR history for the demo company: every movement in the Actual, Budget and Forecast ARR waterfalls
lands on a customer.

Writes a new folder only (never touches the database):
  python build_customer_history.py <v4_folder> <out_folder>

Then build v5 from <out_folder> (build_v5_dataset.py) and continue the usual pipeline.

Rules (agreed with Matt, Oct 7 2026):
  * The company ARR waterfall is the source: each month's new business, expansion, reactivation, contraction
    and churn split across customers to the cent, and customer ARR adds up to ending ARR every month.
  * Jan-Jun 2026 movements are the Actual opportunities, one customer each. Churn, contraction, expansion and
    reactivation opportunities pointed at customer IDs that were not in the customer master; they now point
    at customers whose history matches the amount, in the deal's own region where one fits (owners are
    assigned by region, so deals stay with their reps). Opportunity cents move to the waterfall.
  * Customers in the master at Jan 2026 keep their count (700) and total ARR ($75M); their individual ARR is
    where their history lands. Customers who left before 2026 are added to the master (Churned or Paused).
  * Returns: a pause is in the churn bucket when it starts. A restart after a pause (no time limit) and a
    winback within 6 months of churning are reactivation; a customer back more than 6 months after churning
    is new business. About 20% of reactivation ARR is winbacks and 80% restarts.
  * Some returns come back above the ARR they left with, some below, some equal; some customers contract and
    later expand. That is what the commission policy (7.21-7.24) measures.
  * Customers leave at renewal: a former customer's anniversary (start month) is the month it left, and churn
    deals go to customers whose anniversary is that month where one fits.
  * Budget and Forecast customer histories (customer_history_plans.py) start from the Actual close they plan
    from (Dec 2025, Jun 2026). Budget churn customers hold flat Actual ARR through Dec 2025.
  * Renewal pipelines (Actual Jan-Jun 2026, Forecast Jul-Dec 2026) are the customers due in their anniversary
    month at their ARR; Actual renewal commissions are 2% of each renewal, paid to its CSM.
  * Revenue weights (recurring services schedule) follow each version's history: a customer is billed only
    while it has ARR (Forecast: expected ARR).
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_v5_dataset import ZERO, Dataset, allocate, last_day, num, padd, pidx, prange, q, write  # noqa: E402
from customer_history_plans import (EXPECTED_FIELDS, HISTORY_FIELDS, WINBACK_SHARE, WINBACK_WINDOW,  # noqa: E402
                                    FORECAST_RENEWAL_PROBABILITY, History, actual_renewals, forecast_deals, pick,
                                    renewal_commissions, renewal_rows, simulate_budget, simulate_forecast, tie,
                                    tie_budget_deals, u, waterfall)

FIRST = "2024-01"
LAST_PRE_2026 = "2025-12"
CLOSE = "2026-06"
PRE_FROM = "2023-07"
RETURNING_NEW = 2
PAUSE_FROM = "2024-04"
PAUSE_SHARE = Decimal("0.5")
RENEWAL_RATE = Decimal("0.02")
HISTORY_FILE = "Actual_customer_arr_history.csv"


def weight_source(v: str) -> str:
    what = "expected ARR" if v == "Forecast" else "ARR"
    return f"{v}_customer_arr_history.csv ({what} after the month's movements)"


def build(src: str, dst: str) -> list[str]:
    if os.path.exists(dst):
        raise SystemExit(f"{dst} exists; pick a new folder")
    ds = Dataset(src)
    notes: list[str] = []
    master_fields, master = ds.get("Actual_customers.csv")
    org = master[0]["organization_id"]
    W = waterfall(ds.rows("Actual_MRR_Waterfall.csv"))
    months = sorted(W)
    if months[0] != FIRST or months[-1] != CLOSE:
        raise ValueError(f"Actual waterfall runs {months[0]}..{months[-1]}, expected {FIRST}..{CLOSE}")
    opp_fields, opps = ds.get("Actual_opportunities.csv")
    opp_of = {o["opportunity_id"]: o for o in opps}
    region_of = {}
    for v in ("Actual", "Budget", "Forecast"):
        for r in ds.rows(f"{v}_opportunities.csv"):
            region_of[r["customer_state"]] = r["region"]
    booked = {"New Business": "Closed Won", "Expansion": "Closed Won", "Reactivation": "Closed Won",
              "Contraction": "Contraction", "Churn": "Churn"}
    col_of = {"New Business": "new_business_arr", "Expansion": "expansion_arr", "Reactivation": "reactivation_arr",
              "Contraction": "contraction_arr", "Churn": "churn_arr"}
    cents: list[str] = []
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for o in opps:
        if booked.get(o["opportunity_type"]) == o["close_status"]:
            groups[(o["period"][:7], o["opportunity_type"])].append(o)
    for (p, t), rows in sorted(groups.items()):
        diff = W[p][col_of[t]] - sum((num(o["amount_arr"]) for o in rows), ZERO)
        if diff and abs(diff) <= Decimal("0.05"):
            top = max(rows, key=lambda o: (num(o["amount_arr"]), o["opportunity_id"]))
            top["amount_arr"] = f"{num(top['amount_arr']) + diff:.2f}"
            top["weighted_arr"] = f"{num(top['weighted_arr']) + diff:.2f}" if top.get("weighted_arr") else top.get("weighted_arr", "")
            cents.append(f"{top['opportunity_id']} {diff:+}")
        elif diff:
            raise ValueError(f"{p} {t}: opportunities differ from the waterfall by {diff}")
    notes.append("opportunity cents moved to the waterfall (largest deal of the type and month): " + (", ".join(cents) or "none"))

    b_fields, b_opps = ds.get("Budget_opportunities.csv")
    WB = waterfall(ds.rows("Budget_MRR_Waterfall.csv"))
    tie_budget_deals(b_opps, WB, notes)
    f_fields, f_all = ds.get("Forecast_opportunities.csv")
    WF = waterfall(ds.rows("Forecast_MRR_Waterfall.csv"))
    f_opps = forecast_deals(f_all, WF, padd(CLOSE, 1), notes)

    h = History(org)
    mrow = {r["customer_id"]: r for r in master}
    for r in master:
        h.info[r["customer_id"]] = {"customer_name": r["customer_name"], "segment": r["segment"]}
    start = {r["customer_id"]: r["customer_start_date"][:7] for r in master}
    jan26 = {r["customer_id"]: num(r["starting_arr_jan_2026"]) for r in master}
    logos = {o["customer_id"]: o for o in opps if o["opportunity_type"] == "New Business" and o["close_status"] == "Closed Won"}
    for cid, o in logos.items():
        h.info[cid] = {"customer_name": o["customer_name"], "segment": o["segment"]}
        start[cid] = o["period"][:7]

    def anniv(c: str) -> str:
        return start[c][5:7]

    # ---- former customers (not in the master): new records
    prefixes = sorted({re.sub(r"\s+\d+$", "", r["customer_name"]) for r in master})
    industries = sorted({r["industry"] for r in master})
    states = sorted({r["billing_state"] for r in master})
    terms = [r["billing_terms"] for r in master]
    cadences = [r["billing_cadence"] for r in master]
    next_no = max(int(c.split("-")[1]) for c in mrow) + 1
    new_rows: list[dict] = []

    def new_customer(tag: str, arr_hint: Decimal, departs: str, like: dict | None = None) -> str:
        """A former customer whose anniversary is the month it leaves. ``like`` is the 2026 opportunity it will
        carry: the customer takes the deal's segment, industry, state, cadence and terms so the deal keeps its
        region (and so its owner)."""
        nonlocal next_no
        cid = f"CUST-{next_no:04d}"
        next_no += 1
        k = f"former|{cid}"
        seg = "SMB" if arr_hint < 50000 else "Mid-Market" if arr_hint < 150000 else "Enterprise"
        latest = min(pidx(departs) - 7, pidx("2023-06"))
        s = padd("2019-01", int(u(k + "|start") * (latest - pidx("2019-01") + 1)))
        s = f"{s[:4]}-{departs[5:7]}"
        if pidx(s) > latest:
            s = padd(s, -12)
        row = {"organization_id": org, "customer_id": cid,
               "customer_name": f"{prefixes[int(u(k + '|name') * len(prefixes))]} {next_no - 1}",
               "segment": seg, "industry": industries[int(u(k + "|ind") * len(industries))], "status": "",
               "customer_start_date": f"{s}-01", "contract_start_date": f"{s}-01",
               "billing_cadence": cadences[int(u(k + "|cad") * len(cadences))],
               "billing_terms": terms[int(u(k + "|terms") * len(terms))],
               "billing_state": states[int(u(k + "|state") * len(states))], "source_crm": "Salesforce",
               "netsuite_customer_id": f"NS-{cid}", "stripe_customer_id": f"cus_demo_{cid.split('-')[1]}",
               "starting_mrr_jan_2026": "0", "starting_arr_jan_2026": "0", "currency": "USD", "_tag": tag}
        if like:
            seg = like["segment"]
            row.update({"segment": seg, "industry": like["industry"], "billing_state": like["customer_state"],
                        "billing_cadence": like["billing_cadence"], "billing_terms": like["billing_terms"]})
        new_rows.append(row)
        mrow[cid] = row
        start[cid] = s
        h.info[cid] = {"customer_name": row["customer_name"], "segment": seg}
        return cid

    # ---- returns: every month's reactivation ARR, 2024-2025 split 1-2 ways, 2026 = the opportunities
    returns: list[dict] = []
    for p in prange(FIRST, LAST_PRE_2026):
        total = W[p]["reactivation_arr"]
        n = 1 if total < 40000 else 2
        amts = allocate(total, [(f"{p}#{i}", Decimal(1) + u(f"rsplit|{p}|{i}")) for i in range(n)])
        for key, a in sorted(amts.items()):
            returns.append({"period": p, "amount": a, "key": key, "opp": ""})
    for o in sorted(opps, key=lambda o: (o["period"], o["opportunity_id"])):
        if o["opportunity_type"] == "Reactivation" and o["close_status"] == "Closed Won":
            returns.append({"period": o["period"][:7], "amount": num(o["amount_arr"]), "key": o["opportunity_id"],
                            "opp": o["opportunity_id"]})
    wb = tot = ZERO
    for r in returns:
        tot += r["amount"]
        r["kind"] = "winback" if wb + r["amount"] <= WINBACK_SHARE * tot + Decimal("15000") and wb < WINBACK_SHARE * tot else "restart"
        if r["kind"] == "winback":
            wb += r["amount"]
        p, key = r["period"], r["key"]
        lo = max(1 if r["kind"] == "winback" else 2, pidx(p) - pidx(LAST_PRE_2026))
        hi = WINBACK_WINDOW if r["kind"] == "winback" else 14
        hi = max(lo, min(hi, pidx(p) - pidx(PRE_FROM)))
        r["months_away"] = lo + int(u(f"away|{key}") * (hi - lo + 1))
        r["departed"] = padd(p, -r["months_away"])
        x, y = u(f"base|{key}"), u(f"base2|{key}")
        a = r["amount"]
        if x < Decimal("0.4"):
            r["baseline"] = q(a / (Decimal("1.05") + Decimal("0.25") * y))
        elif x < Decimal("0.6"):
            r["baseline"] = q(a * (Decimal("1.05") + Decimal("0.25") * y))
        else:
            r["baseline"] = a
    notes.append(f"returns: {len(returns)} (${tot:,.2f}); winbacks {sum(1 for r in returns if r['kind'] == 'winback')} "
                 f"(${wb:,.2f}, {wb / tot:.1%} of reactivation ARR); restarts {sum(1 for r in returns if r['kind'] == 'restart')}")

    # ---- 2026 opportunities pinned to flat-ARR customers
    used: set[str] = set()
    opening_masters = sorted(c for c in mrow if start[c] < FIRST)
    early_masters = [c for c in opening_masters if start[c] < PRE_FROM]
    churn_opps = sorted((o for o in opps if o["opportunity_type"] == "Churn"), key=lambda o: (o["period"], o["opportunity_id"]))
    con_opps = sorted((o for o in opps if o["opportunity_type"] == "Contraction"), key=lambda o: (o["period"], o["opportunity_id"]))
    # Opportunity owners are assigned by region, so each deal goes to a customer in its own region where one fits.
    def region(c: str) -> str:
        return region_of.get(mrow[c]["billing_state"], "")

    def in_region(cands: list[str], o: dict) -> list[str]:
        return [c for c in cands if region(c) == o["region"]] or cands

    def at_renewal(cands: list[str], o: dict) -> list[str]:
        return [c for c in cands if anniv(c) == o["period"][5:7]] or cands

    flagged = sorted(c for c in opening_masters if mrow[c]["status"] == "Churned")
    if len(flagged) > len(churn_opps):
        raise ValueError("more churned customers in the master than 2026 churn opportunities")
    pinned: dict[str, Decimal] = {}
    assign: dict[str, str] = {}
    for c in flagged:
        free_opps = [o for o in churn_opps if o["opportunity_id"] not in assign]
        local = [o for o in free_opps if o["region"] == region(c)] or free_opps
        o = next((o for o in local if o["period"][5:7] == anniv(c)), local[0])
        assign[o["opportunity_id"]] = c
    for o in churn_opps:
        if o["opportunity_id"] not in assign:
            cands = [c for c in opening_masters if c not in assign.values()]
            assign[o["opportunity_id"]] = pick(at_renewal(in_region(cands, o), o), 1, f"churn2026|{o['opportunity_id']}",
                                               lambda c: jan26[c])[0]
    churners = [assign[o["opportunity_id"]] for o in churn_opps]
    for o, c in zip(churn_opps, churners):
        pinned[c] = num(o["amount_arr"])
        used.add(c)
    big = [c for c in opening_masters if c not in used and mrow[c]["segment"] == "Enterprise"]
    contractors = []
    for o in con_opps:
        cands = [c for c in big if c not in contractors]
        contractors += pick(in_region(cands, o), 1, f"con2026|{o['opportunity_id']}", lambda c: jan26[c])
    for o, c in zip(con_opps, contractors):
        share = Decimal("0.25") + Decimal("0.15") * u(f"conshare|{o['opportunity_id']}")
        assign[o["opportunity_id"]] = c
        pinned[c] = q(num(o["amount_arr"]) / share)
        used.add(c)
    # Budget churn customers hold their Dec 2025 ARR (= the Budget churn deal) flat in the Actual history.
    budget_pins: dict[str, str] = {}
    for o in sorted((o for o in b_opps if o["opportunity_type"] == "Churn"), key=lambda o: (o["period"], o["opportunity_id"])):
        cands = [c for c in opening_masters if c not in used]
        c = pick(at_renewal(in_region(cands, o), o), 1, f"bchurn|{o['opportunity_id']}", lambda c: jan26[c])[0]
        budget_pins[o["opportunity_id"]] = c
        pinned[c] = num(o["amount_arr"])
        used.add(c)
    budget_churners = list(budget_pins.values())

    # ---- returners: 2024-2025 returns are master customers; 2026 returns are former customers
    departures: dict[str, list[tuple[str, str, Decimal, str]]] = defaultdict(list)
    returning: dict[str, list[tuple[str, Decimal, str, str]]] = defaultdict(list)
    pre_departures: list[tuple[str, str, Decimal, str]] = []
    opening: dict[str, Decimal] = {}
    pool = [c for c in early_masters if c not in used]
    for r in returns:
        if r["period"] <= LAST_PRE_2026:
            cands = [x for x in pool if x not in used]
            cands = [x for x in cands if anniv(x) == r["departed"][5:7]] or cands
            c = pick(cands, 1, f"ret|{r['key']}", lambda c: Decimal(1))[0]
        else:
            c = new_customer("returner", r["baseline"], r["departed"], opp_of[r["opp"]])
        used.add(c)
        r["customer"] = c
        kind = "Churn" if r["kind"] == "winback" else "Pause"
        note = f"{'winback' if kind == 'Churn' else 'restart'} after {r['months_away']} months away"
        if r["departed"] >= FIRST:
            opening[c] = r["baseline"]
            departures[r["departed"]].append((c, kind, r["baseline"], ""))
        else:
            pre_departures.append((r["departed"], c, r["baseline"], kind))
        returning[r["period"]].append((c, r["amount"], r["opp"], note))
        if r["opp"]:
            assign[r["opp"]] = c

    # ---- returning as new business (back more than 6 months after churning): 2026 new business opportunities
    nb2026 = sorted((o for o in opps if o["opportunity_type"] == "New Business" and o["close_status"] == "Closed Won"),
                    key=lambda o: o["opportunity_id"])
    back_new = pick([o["opportunity_id"] for o in nb2026], RETURNING_NEW, "backnew", lambda c: Decimal(1))
    nb_by_id = {o["opportunity_id"]: o for o in nb2026}
    for oid in sorted(back_new):
        o = nb_by_id[oid]
        a = num(o["amount_arr"])
        away = 9 + int(u(f"backaway|{oid}") * 12)
        d = padd(o["period"][:7], -away)
        b = q(a * (Decimal("0.8") + Decimal("0.4") * u(f"backbase|{oid}")))
        c = new_customer("returning new business", b, d, o)
        opening[c] = b
        departures[d].append((c, "Churn", b, f"back as new business {o['period'][:7]} ({away} months later)"))
        assign[oid] = c
        used.add(c)

    # ---- formers: the rest of each month's churn; about half of those leaving from PAUSE_FROM pause
    for p in prange(FIRST, LAST_PRE_2026):
        rem = W[p]["churn_arr"] - sum((x[2] for x in departures[p]), ZERO)
        if rem <= 0:
            raise ValueError(f"{p}: returners' departures {W[p]['churn_arr'] - rem} exceed churn {W[p]['churn_arr']}")
        n = max(1, int((rem / Decimal(85000)).to_integral_value()))
        for key, a in sorted(allocate(rem, [(f"{p}#{i}", Decimal("0.5") + u(f"csplit|{p}|{i}")) for i in range(n)]).items()):
            pause = p >= PAUSE_FROM and u(f"pause|{key}") < PAUSE_SHARE
            c = new_customer("former", a, p)
            opening[c] = a
            departures[p].append((c, "Pause" if pause else "Churn", a, ""))

    # ---- opening balances
    for c in churners + contractors + budget_churners:
        opening[c] = pinned[c]
    free_open = [c for c in opening_masters if c not in opening and c not in {r["customer"] for r in returns}]
    rest = W[FIRST]["beginning_arr"] - sum(opening.values(), ZERO)
    if rest <= 0:
        raise ValueError("pinned opening ARR exceeds the waterfall's opening ARR")
    for c, a in allocate(rest, [(c, jan26[c] * (Decimal("0.6") + Decimal("0.4") * u(f"open|{c}"))) for c in free_open]).items():
        opening[c] = a
    for c in sorted(opening):
        h.open(c, opening[c], padd(FIRST, -1), f"ARR at the start of the ARR waterfall ({FIRST})")
    for d, c, b, kind in sorted(pre_departures):
        h.rows.append({"organization_id": org, "version": "Actual", "period": d, "customer_id": c,
                       "customer_name": h.info[c]["customer_name"], "segment": h.info[c]["segment"], "movement_type": kind,
                       "beginning_arr": b, "movement_arr": -b, "ending_arr": ZERO, "waterfall_column": "",
                       "opportunity_id": "", "note": f"before the ARR waterfall starts ({FIRST}); ARR left with"})
    notes.append(f"opening {padd(FIRST, -1)}: {len(opening)} customers, ARR {sum(opening.values(), ZERO):,.2f}; "
                 f"{len(pre_departures)} returners left before {FIRST}")

    flat = set(churners) | set(contractors) | set(budget_churners)
    leaves = {c: d for d, items in departures.items() for c, *_ in items}

    def free(c: str, p: str) -> bool:
        """Can take an expansion or contraction in ``p``: active, not pinned to an amount it must leave with."""
        return c not in flat and h.arr[c] > 0 and c not in h.moved[p] and (c not in leaves or leaves[c] < p)

    # ---- 2024-2025 month by month
    for p in prange(FIRST, LAST_PRE_2026):
        for c, kind, b, note in departures[p]:
            if h.arr[c] != b:
                raise ValueError(f"{p} {c}: leaves with {h.arr[c]}, planned {b}")
            h.move(p, c, kind, b, note=note)
        for c, a, _, note in returning[p]:
            h.move(p, c, "Reactivation", a, note=note)
        starters = sorted(c for c in mrow if start[c] == p and c in jan26)
        if not starters:
            raise ValueError(f"{p}: new business {W[p]['new_business_arr']} but no customer starts")
        for c, a in allocate(W[p]["new_business_arr"], [(c, jan26[c] * (Decimal("0.6") + Decimal("0.4") * u(f"nb|{c}")))
                                                       for c in starters]).items():
            h.move(p, c, "New Business", a)
        for kind, col, size, cap, floor in (("Contraction", "contraction_arr", 18000, Decimal("0.5"), Decimal(30000)),
                                            ("Expansion", "expansion_arr", 45000, Decimal("1.0"), ZERO)):
            total = W[p][col]
            elig = [c for c in sorted(h.arr) if free(c, p) and h.arr[c] >= floor]
            n = max(1, int((total / Decimal(size)).to_integral_value()))
            while True:
                chosen = pick(elig, n, f"{kind}|{p}", lambda c: h.arr[c])
                amts = allocate(total, [(c, h.arr[c] * (Decimal("0.5") + u(f"{kind}amt|{p}|{c}"))) for c in chosen])
                if all(a <= h.arr[c] * cap and a > 0 for c, a in amts.items()):
                    break
                n += 1
                if n > len(elig):
                    raise ValueError(f"{p}: can't place {kind} {total}")
            for c, a in sorted(amts.items()):
                h.move(p, c, kind, a)
        h.close_month(p)

    # ---- Jan-Jun 2026: the Actual opportunities
    for p in prange("2026-01", CLOSE):
        month = sorted((o for o in opps if o["period"][:7] == p), key=lambda o: o["opportunity_id"])
        for o in month:
            t, a, oid = o["opportunity_type"], num(o["amount_arr"]), o["opportunity_id"]
            if t == "Churn":
                h.move(p, assign[oid], "Churn", a, oid)
            elif t == "Contraction":
                h.move(p, assign[oid], "Contraction", a, oid)
        for c, a, oid, note in returning.get(p, []):
            h.move(p, c, "Reactivation", a, oid, note)
        for o in month:
            if o["opportunity_type"] == "New Business" and o["close_status"] == "Closed Won":
                oid = o["opportunity_id"]
                c = assign.get(oid, o["customer_id"])
                h.move(p, c, "New Business", num(o["amount_arr"]), oid,
                       "back as new business more than 6 months after churning" if oid in assign else "")
        for o in month:
            if o["opportunity_type"] == "Expansion" and o["close_status"] == "Closed Won":
                a, oid = num(o["amount_arr"]), o["opportunity_id"]
                elig = [c for c in sorted(h.arr) if free(c, p) and h.arr[c] >= a and c not in logos]
                c = pick(in_region(elig, o), 1, f"exp2026|{oid}", lambda c: h.arr[c])[0]
                assign[oid] = c
                h.move(p, c, "Expansion", a, oid)
        h.close_month(p)

    opening_sum = sum((r["ending_arr"] for r in h.rows if r["movement_type"] == "Opening balance"), ZERO)
    notes.append(tie(h, W, months, opening_sum))

    dec = h.eop[LAST_PRE_2026]
    masters = [r["customer_id"] for r in master]
    if any(dec.get(c, ZERO) <= 0 for c in masters) or sum((dec[c] for c in masters), ZERO) != sum(jan26.values(), ZERO):
        raise ValueError("master customers at Dec 2025 don't keep their count and total ARR")
    notes.append(f"master: {len(masters)} customers active at Dec 2025, ARR {sum((dec[c] for c in masters), ZERO):,.2f} "
                 f"(unchanged total); {len(new_rows)} former customers added "
                 f"({sum(1 for x in departures.values() for _, k, *_ in x if k == 'Pause')} paused)")

    # ---- Budget and Forecast
    taken = {int(c.split("-")[1]) for c in list(mrow) + list(logos)}
    for v_opps in (b_opps, f_all):
        taken |= {int(o["customer_id"].split("-")[1]) for o in v_opps}
    next_logo = max(taken) + 1
    renamed: dict[str, tuple[str, str]] = {}
    seen: set[str] = set()
    for o in sorted(f_opps, key=lambda o: (o["period"], o["opportunity_id"])):
        cid = o["customer_id"]
        if o["opportunity_type"] != "New Business":
            continue
        if cid in mrow or h.eop[CLOSE].get(cid, ZERO) > 0 or cid in seen:
            new, name = f"CUST-{next_logo:05d}", re.sub(r"\d+$", str(next_logo), o["customer_name"])
            next_logo += 1
            renamed[o["opportunity_id"]] = (new, name)
            o.update({"customer_id": new, "customer_name": name,
                      "opportunity_name": f"{name} - New Business - {o['period'][:7]}"})
        seen.add(o["customer_id"])
    for o in b_opps:
        if o["opportunity_type"] == "New Business" and (o["customer_id"] in mrow or dec.get(o["customer_id"], ZERO) > 0):
            raise ValueError(f"Budget new business {o['opportunity_id']} on a customer active at Dec 2025")
    plan_logos: dict[str, dict[str, dict]] = {"Budget": {}, "Forecast": {}}
    for v, v_opps in (("Budget", b_opps), ("Forecast", f_opps)):
        for o in v_opps:
            if o["opportunity_type"] == "New Business":
                cid = o["customer_id"]
                plan_logos[v][cid] = o
                start.setdefault(cid, o["period"][:7])
                h.info.setdefault(cid, {"customer_name": o["customer_name"], "segment": o["segment"]})
    notes.append(f"Forecast new business on a customer already active at the Actual close or already won earlier in the "
                 f"Forecast is a new logo: {', '.join(f'{a} -> {b[0]} {b[1]}' for a, b in renamed.items()) or 'none'}")

    def plan_region(c: str) -> str:
        return region(c) if c in mrow else region_of.get((plan_logos["Budget"].get(c) or plan_logos["Forecast"].get(c)
                                                          or logos[c])["customer_state"], "")

    hb, b_assign = simulate_budget(org, h.info, dec, LAST_PRE_2026, h.rows, b_opps, WB, budget_pins, plan_region, anniv,
                                   start, notes)
    hf, f_assign, f_due = simulate_forecast(org, h.info, h.eop[CLOSE], CLOSE, h.rows, f_opps, WF, plan_region, anniv,
                                            start, notes)

    # ---- renewal pipelines and renewal commissions
    churn_by_month: dict[str, set[str]] = defaultdict(set)
    for o in churn_opps:
        churn_by_month[o["period"][:7]].add(assign[o["opportunity_id"]])
    a_due = actual_renewals(h, prange("2026-01", CLOSE), anniv, start, churn_by_month)
    ren_fields, old_ren = ds.get("Actual_renewal_pipeline.csv")
    old_by_customer = {r["customer_id"]: r for r in sorted(old_ren, key=lambda r: r["renewal_period"])}
    a_ren = renewal_rows(org, "Actual", a_due, old_ren, old_by_customer, h.info)
    by_customer = {r["customer_id"]: r for r in a_ren}
    by_customer.update({c: r for c, r in old_by_customer.items() if c not in by_customer})
    f_ren = renewal_rows(org, "Forecast", f_due, old_ren, by_customer, h.info,
                         {"renewal_probability": f"{FORECAST_RENEWAL_PROBABILITY}", "renewal_stage": "Commit"})
    com_fields, old_com = ds.get("Actual_renewal_commissions.csv")
    rep_of = {r["rep_name"]: r["rep_id"] for r in old_com}
    missing_rep = sorted({r["customer_success_manager"] for r in a_ren} - set(rep_of))
    if missing_rep:
        raise ValueError(f"CSMs without a rep ID in the renewal commissions: {missing_rep}")
    a_com = renewal_commissions(org, a_ren, rep_of, RENEWAL_RATE, last_day)
    notes.append(f"renewal pipeline: Actual {len(a_ren)} renewals Jan-Jun 2026 (renewal ARR "
                 f"{sum((num(r['renewal_arr']) for r in a_ren), ZERO):,.2f}), Forecast {len(f_ren)} Jul-Dec 2026; "
                 f"renewal commissions {len(a_com)} at {RENEWAL_RATE} "
                 f"({sum((num(r['commission_amount']) for r in a_com), ZERO):,.2f})")

    # ---- customer master
    last_kind = {}
    for r in sorted(h.rows, key=lambda r: r["period"]):
        if r["movement_type"] in ("Churn", "Pause"):
            last_kind[r["customer_id"]] = r["movement_type"]
    final = h.eop[CLOSE]

    def status(c: str) -> str:
        return "Active" if final.get(c, ZERO) > 0 else ("Paused" if last_kind.get(c) == "Pause" else "Churned")

    out_master = []
    for r in master + new_rows:
        nr = {k: v for k, v in r.items() if not k.startswith("_")}
        c = r["customer_id"]
        nr["status"] = status(c)
        a = dec.get(c, ZERO)
        nr["starting_arr_jan_2026"] = f"{a:.2f}"
        nr["starting_mrr_jan_2026"] = f"{q(a / 12):.2f}"
        out_master.append(nr)
    notes.append("status at " + CLOSE + ": " + ", ".join(f"{k} {n}" for k, n in sorted(Counter(r["status"] for r in out_master).items()))
                 + f" (plus {sum(1 for o in logos.values() if o['opportunity_id'] not in assign)} 2026 new logos "
                 f"added by the v5 build; {len(back_new)} returning customers booked as new business)")

    def logo_row(o: dict) -> dict:
        cid = o["customer_id"]
        return {"organization_id": org, "customer_id": cid, "customer_name": o["customer_name"], "segment": o["segment"],
                "industry": o["industry"], "status": "Active", "customer_start_date": o["contract_start_date"],
                "contract_start_date": o["contract_start_date"], "billing_cadence": o["billing_cadence"],
                "billing_terms": o["billing_terms"], "billing_state": o["customer_state"], "source_crm": "Salesforce",
                "netsuite_customer_id": f"NS-{cid}", "stripe_customer_id": f"cus_demo_{cid.split('-')[1]}",
                "starting_mrr_jan_2026": "0", "starting_arr_jan_2026": "0", "currency": "USD"}

    shutil.copytree(src, dst)
    write(os.path.join(dst, "Actual_customers.csv"), master_fields, out_master)
    for v in ("Budget", "Forecast"):
        extra = [logo_row(o) for cid, o in sorted(plan_logos[v].items()) if cid not in logos]
        write(os.path.join(dst, f"{v}_customers.csv"), master_fields, out_master + extra)
        notes.append(f"{v}_customers.csv: the Actual customer master plus {len(extra)} {v}-only new logos (Active)")
    for name, fields, hist in ((HISTORY_FILE, HISTORY_FIELDS, h), ("Budget_customer_arr_history.csv", HISTORY_FIELDS, hb),
                               ("Forecast_customer_arr_history.csv", EXPECTED_FIELDS, hf)):
        hist.rows.sort(key=lambda r: (r["period"], r["customer_id"], r["movement_type"]))
        write(os.path.join(dst, name), fields, hist.rows)
    write(os.path.join(dst, "Actual_renewal_pipeline.csv"), ren_fields, a_ren)
    write(os.path.join(dst, "Forecast_renewal_pipeline.csv"), ren_fields, f_ren)
    write(os.path.join(dst, "Actual_renewal_commissions.csv"), com_fields, a_com)

    info = {c: mrow[c] for c in mrow}
    for cid, o in logos.items():
        info.setdefault(cid, {"customer_name": o["customer_name"], "segment": o["segment"], "industry": o["industry"],
                              "billing_state": o["customer_state"], "billing_terms": o["billing_terms"]})

    def repoint(rows: list[dict], to: dict[str, str]) -> int:
        n = 0
        for r in rows:
            c = to.get(r["opportunity_id"])
            if not c or c not in info:
                continue
            m = info[c]
            r.update({"customer_id": c, "customer_name": m["customer_name"], "segment": m["segment"],
                      "industry": m["industry"], "customer_state": m["billing_state"],
                      "region": region_of[m["billing_state"]], "billing_terms": m["billing_terms"],
                      "opportunity_name": f"{m['customer_name']} - {r['opportunity_type']} - {r['period'][:7]}"})
            n += 1
        return n

    moved_region: dict[str, int] = {}
    for v, fields, v_opps, to, keep in (("Actual", opp_fields, opps, assign, None),
                                        ("Budget", b_fields, b_opps, b_assign, None),
                                        ("Forecast", f_fields, f_opps, f_assign, {o["opportunity_id"] for o in f_opps})):
        before = {o["opportunity_id"]: o["region"] for o in v_opps}
        n_opp = repoint(v_opps, to)
        moved_region[v] = sum(1 for o in v_opps if o["region"] != before[o["opportunity_id"]])
        write(os.path.join(dst, f"{v}_opportunities.csv"), fields, v_opps)
        mv_fields, mv = ds.get(f"{v}_opportunity_movements.csv")
        if keep is not None:
            dropped = {o["opportunity_id"] for o in f_all} - keep
            mv = [r for r in mv if r["opportunity_id"] not in dropped]
        if keep is not None:
            for r in mv:
                if r["opportunity_id"] in renamed:
                    new, name = renamed[r["opportunity_id"]]
                    r.update({"customer_id": new, "customer_name": name,
                              "opportunity_name": f"{name} - New Business - {r['period'][:7]}"})
        n_mv = repoint(mv, to)
        by_id = {o["opportunity_id"]: o for o in v_opps}
        for r in mv:
            o = by_id.get(r["opportunity_id"])
            if o and r["close_status"] == o["close_status"]:
                r["amount_arr"], r["weighted_arr"] = o["amount_arr"], o["weighted_arr"]
        write(os.path.join(dst, f"{v}_opportunity_movements.csv"), mv_fields, mv)
        notes.append(f"{v} opportunities: {n_opp} pointed at customers in the {v} history; {n_mv} matching movement rows; "
                     f"{moved_region[v]} changed region (no in-region customer fit)")
    imp_fields, imp = ds.get("Forecast_implementation_schedule.csv")
    for r in imp:
        if r["source_record_id"] in renamed:
            r["customer_id"], r["customer_name"] = renamed[r["source_record_id"]]
    write(os.path.join(dst, "Forecast_implementation_schedule.csv"), imp_fields, imp)

    sched_fields = ds.fields("Actual_recurring_services_schedule.csv")
    for v, hist in (("Actual", h), ("Budget", hb), ("Forecast", hf)):
        periods = months if v == "Actual" else sorted({r["period"] for r in ds.rows(f"{v}_recurring_services_schedule.csv")})
        rows = []
        for p in periods:
            snap = hist.eop[p]
            for c in sorted(snap):
                rows.append({"organization_id": org, "version": v, "period": p, "customer_id": c,
                             "customer_name": h.info[c]["customer_name"], "segment": h.info[c]["segment"],
                             "weight_source": weight_source(v), "customer_arr": snap[c]})
        write(os.path.join(dst, f"{v}_recurring_services_schedule.csv"), sched_fields, rows)
    notes.append("revenue weights: each version's customer ARR history, month by month (Forecast: expected ARR)")

    rets = [r for r in h.rows if r["movement_type"] == "Reactivation"]
    above = sum(1 for r in returns if r["amount"] > r["baseline"])
    below = sum(1 for r in returns if r["amount"] < r["baseline"])
    notes.append(f"returns vs ARR left with: {above} above, {below} below, {len(rets) - above - below} equal")
    with open(os.path.join(dst, "customer_history_notes.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(notes) + "\n")
    return notes


if __name__ == "__main__":
    for line in build(sys.argv[1], sys.argv[2]):
        print(line)
