"""Customer ARR history for the demo company: every movement in the Actual ARR waterfall lands on a customer.

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
  * Revenue weights (recurring services schedule) follow the history: a customer is billed only while it
    has ARR. Budget weights hold Dec 2025 ARR and Forecast weights hold Jun 2026 ARR (their own customer
    movements are not modeled yet).
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_v5_dataset import ZERO, Dataset, allocate, num, padd, pidx, prange, q, stable_unit, write  # noqa: E402

FIRST = "2024-01"
LAST_PRE_2026 = "2025-12"
CLOSE = "2026-06"
PRE_FROM = "2023-07"
WINBACK_WINDOW = 6
WINBACK_SHARE = Decimal("0.20")
RETURNING_NEW = 2
HISTORY_FILE = "Actual_customer_arr_history.csv"
HISTORY_FIELDS = ["organization_id", "version", "period", "customer_id", "customer_name", "segment", "movement_type",
                  "beginning_arr", "movement_arr", "ending_arr", "waterfall_column", "opportunity_id", "note"]
COLUMN = {"New Business": "new_business_arr", "Expansion": "expansion_arr", "Reactivation": "reactivation_arr",
          "Contraction": "contraction_arr", "Churn": "churn_arr", "Pause": "churn_arr", "Opening balance": ""}
WF_COLUMNS = ("new_business_arr", "expansion_arr", "reactivation_arr", "contraction_arr", "churn_arr")
WEIGHT_SOURCE = "Actual_customer_arr_history.csv (ARR after the month's movements)"


def u(key: str) -> Decimal:
    return stable_unit(key)


def pick(cands: list[str], n: int, key: str, weight) -> list[str]:
    """Deterministic weighted sample without replacement (Efraimidis-Spirakis)."""
    def score(c: str) -> float:
        w = float(weight(c)) or 1e-9
        return (float(u(f"{key}|{c}")) + 1e-6) ** (1.0 / w)
    return sorted(cands, key=lambda c: (-score(c), c))[:n]


class History:
    def __init__(self, org: str):
        self.org = org
        self.arr: dict[str, Decimal] = defaultdict(lambda: ZERO)
        self.rows: list[dict] = []
        self.info: dict[str, dict[str, str]] = {}
        self.eop: dict[str, dict[str, Decimal]] = {}
        self.moved: dict[str, set[str]] = defaultdict(set)

    def move(self, p: str, cid: str, kind: str, amount: Decimal, opp: str = "", note: str = "") -> None:
        begin = self.arr[cid]
        delta = -amount if kind in ("Contraction", "Churn", "Pause") else amount
        end = begin + delta
        if amount <= 0 or end < 0:
            raise ValueError(f"{p} {cid} {kind} {amount}: ARR {begin} would become {end}")
        if kind in ("Churn", "Pause") and end != 0:
            raise ValueError(f"{p} {cid} {kind} leaves {end}")
        if kind in ("New Business", "Reactivation") and begin != 0:
            raise ValueError(f"{p} {cid} {kind} while active ({begin})")
        if cid in self.moved[p]:
            raise ValueError(f"{p} {cid}: second movement in the month")
        self.moved[p].add(cid)
        self.arr[cid] = end
        i = self.info[cid]
        self.rows.append({"organization_id": self.org, "version": "Actual", "period": p, "customer_id": cid,
                          "customer_name": i["customer_name"], "segment": i["segment"], "movement_type": kind,
                          "beginning_arr": begin, "movement_arr": delta, "ending_arr": end,
                          "waterfall_column": COLUMN[kind], "opportunity_id": opp, "note": note})

    def open(self, cid: str, amount: Decimal) -> None:
        self.arr[cid] = amount
        i = self.info[cid]
        self.rows.append({"organization_id": self.org, "version": "Actual", "period": padd(FIRST, -1), "customer_id": cid,
                          "customer_name": i["customer_name"], "segment": i["segment"],
                          "movement_type": "Opening balance", "beginning_arr": amount, "movement_arr": ZERO,
                          "ending_arr": amount, "waterfall_column": "", "opportunity_id": "",
                          "note": f"ARR at the start of the ARR waterfall ({FIRST})"})

    def close_month(self, p: str) -> None:
        self.eop[p] = {c: a for c, a in self.arr.items() if a > 0}


def build(src: str, dst: str) -> list[str]:
    if os.path.exists(dst):
        raise SystemExit(f"{dst} exists; pick a new folder")
    ds = Dataset(src)
    notes: list[str] = []
    master_fields, master = ds.get("Actual_customers.csv")
    org = master[0]["organization_id"]
    wf = {r["period"][:7]: r for r in ds.rows("Actual_MRR_Waterfall.csv")}
    months = sorted(wf)
    if months[0] != FIRST or months[-1] != CLOSE:
        raise ValueError(f"Actual waterfall runs {months[0]}..{months[-1]}, expected {FIRST}..{CLOSE}")
    W = {p: {k: num(wf[p][k]) for k in (*WF_COLUMNS, "beginning_arr", "ending_arr")} for p in months}
    opp_fields, opps = ds.get("Actual_opportunities.csv")
    opp_of = {o["opportunity_id"]: o for o in opps}
    region_of = {}
    for v in ("Actual", "Budget", "Forecast"):
        for r in ds.rows(f"{v}_opportunities.csv"):
            region_of[r["customer_state"]] = r["region"]
    renewal_ids = {r["customer_id"] for r in ds.rows("Actual_renewal_pipeline.csv")}
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

    h = History(org)
    mrow = {r["customer_id"]: r for r in master}
    for r in master:
        h.info[r["customer_id"]] = {"customer_name": r["customer_name"], "segment": r["segment"]}
    start = {r["customer_id"]: r["customer_start_date"][:7] for r in master}
    jan26 = {r["customer_id"]: num(r["starting_arr_jan_2026"]) for r in master}
    logos = {o["customer_id"]: o for o in opps if o["opportunity_type"] == "New Business" and o["close_status"] == "Closed Won"}
    for cid, o in logos.items():
        h.info[cid] = {"customer_name": o["customer_name"], "segment": o["segment"]}

    # ---- former customers (not in the master): new records
    prefixes = sorted({re.sub(r"\s+\d+$", "", r["customer_name"]) for r in master})
    industries = sorted({r["industry"] for r in master})
    states = sorted({r["billing_state"] for r in master})
    terms = [r["billing_terms"] for r in master]
    cadences = [r["billing_cadence"] for r in master]
    next_no = max(int(c.split("-")[1]) for c in mrow) + 1
    new_rows: list[dict] = []

    def new_customer(tag: str, arr_hint: Decimal, departs: str, like: dict | None = None) -> str:
        """A former customer. ``like`` is the 2026 opportunity it will carry: the customer takes the deal's
        segment, industry, state, cadence and terms so the deal keeps its region (and so its owner)."""
        nonlocal next_no
        cid = f"CUST-{next_no:04d}"
        next_no += 1
        k = f"former|{cid}"
        seg = "SMB" if arr_hint < 50000 else "Mid-Market" if arr_hint < 150000 else "Enterprise"
        latest = min(pidx(departs) - 7, pidx("2023-06"))
        s = padd("2019-01", int(u(k + "|start") * (latest - pidx("2019-01") + 1)))
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

    flagged = sorted(c for c in opening_masters if mrow[c]["status"] == "Churned" and c not in renewal_ids)
    no_renewal = [c for c in opening_masters if c not in renewal_ids and c not in flagged]
    if len(flagged) > len(churn_opps):
        raise ValueError("more churned customers in the master than 2026 churn opportunities")
    pinned: dict[str, Decimal] = {}
    assign: dict[str, str] = {}
    for c in flagged:
        o = next((o for o in churn_opps if o["opportunity_id"] not in assign and o["region"] == region(c)),
                 next(o for o in churn_opps if o["opportunity_id"] not in assign))
        assign[o["opportunity_id"]] = c
    for o in churn_opps:
        if o["opportunity_id"] not in assign:
            cands = [c for c in no_renewal if c not in assign.values()]
            if not cands:
                raise ValueError("not enough customers without renewals to carry the 2026 churn")
            assign[o["opportunity_id"]] = pick(in_region(cands, o), 1, f"churn2026|{o['opportunity_id']}",
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

    # ---- returners: 2024-2025 returns are master customers; 2026 returns are former customers
    departures: dict[str, list[tuple[str, str, Decimal, str]]] = defaultdict(list)
    returning: dict[str, list[tuple[str, Decimal, str, str]]] = defaultdict(list)
    pre_departures: list[tuple[str, str, Decimal, str]] = []
    opening: dict[str, Decimal] = {}
    pool = [c for c in early_masters if c not in used]
    for r in returns:
        if r["period"] <= LAST_PRE_2026:
            c = pick([x for x in pool if x not in used], 1, f"ret|{r['key']}", lambda c: Decimal(1))[0]
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

    # ---- formers: the rest of each month's churn
    for p in prange(FIRST, LAST_PRE_2026):
        rem = W[p]["churn_arr"] - sum((x[2] for x in departures[p]), ZERO)
        if rem <= 0:
            raise ValueError(f"{p}: returners' departures {W[p]['churn_arr'] - rem} exceed churn {W[p]['churn_arr']}")
        n = max(1, int((rem / Decimal(85000)).to_integral_value()))
        for key, a in sorted(allocate(rem, [(f"{p}#{i}", Decimal("0.5") + u(f"csplit|{p}|{i}")) for i in range(n)]).items()):
            pause = p >= "2025-07" and u(f"pause|{key}") < Decimal("0.15")
            c = new_customer("former", a, p)
            opening[c] = a
            departures[p].append((c, "Pause" if pause else "Churn", a, ""))

    # ---- opening balances
    for c in churners + contractors:
        opening[c] = pinned[c]
    free_open = [c for c in opening_masters if c not in opening and c not in {r["customer"] for r in returns}]
    rest = W[FIRST]["beginning_arr"] - sum(opening.values(), ZERO)
    if rest <= 0:
        raise ValueError("pinned opening ARR exceeds the waterfall's opening ARR")
    for c, a in allocate(rest, [(c, jan26[c] * (Decimal("0.6") + Decimal("0.4") * u(f"open|{c}"))) for c in free_open]).items():
        opening[c] = a
    for c in sorted(opening):
        h.open(c, opening[c])
    for d, c, b, kind in sorted(pre_departures):
        h.rows.append({"organization_id": org, "version": "Actual", "period": d, "customer_id": c,
                       "customer_name": h.info[c]["customer_name"], "segment": h.info[c]["segment"], "movement_type": kind,
                       "beginning_arr": b, "movement_arr": -b, "ending_arr": ZERO, "waterfall_column": "",
                       "opportunity_id": "", "note": f"before the ARR waterfall starts ({FIRST}); ARR left with"})
    notes.append(f"opening {padd(FIRST, -1)}: {len(opening)} customers, ARR {sum(opening.values(), ZERO):,.2f}; "
                 f"{len(pre_departures)} returners left before {FIRST}")

    flat = set(churners) | set(contractors)
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
    exp_assigned: dict[str, str] = {}
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
                assign[oid] = exp_assigned[oid] = c
                h.move(p, c, "Expansion", a, oid)
        h.close_month(p)

    # ---- ties: every month, every column, ending ARR
    by = defaultdict(lambda: defaultdict(lambda: ZERO))
    for r in h.rows:
        if r["waterfall_column"]:
            by[r["period"]][r["waterfall_column"]] += abs(r["movement_arr"])
    bad = []
    wf_rounding = worst_end = ZERO
    for p in months:
        for col in WF_COLUMNS:
            if by[p][col] != W[p][col]:
                bad.append(f"{p} {col} {by[p][col]} vs {W[p][col]}")
        w = W[p]
        own = w["ending_arr"] - (w["beginning_arr"] + w["new_business_arr"] + w["expansion_arr"] + w["reactivation_arr"]
                                 - w["contraction_arr"] - w["churn_arr"])
        wf_rounding = max(wf_rounding, abs(own))
        diff = abs(sum(h.eop[p].values(), ZERO) - w["ending_arr"])
        worst_end = max(worst_end, diff)
        if abs(own) > Decimal("0.05") or diff > Decimal("0.05"):
            bad.append(f"{p} ending {sum(h.eop[p].values(), ZERO)} vs {w['ending_arr']} (waterfall's own rounding {own})")
    opening_sum = sum((r["ending_arr"] for r in h.rows if r["movement_type"] == "Opening balance"), ZERO)
    if opening_sum != W[FIRST]["beginning_arr"]:
        bad.append(f"opening {opening_sum} vs {W[FIRST]['beginning_arr']}")
    if bad:
        raise ValueError("history does not tie to the waterfall: " + "; ".join(bad[:10]))
    notes.append(f"ties: {len(months)} months x 5 movement columns and opening ARR to the cent; ending ARR within "
                 f"{worst_end} (the waterfall's own ending ARR differs from beginning + movements by up to {wf_rounding})")

    dec = h.eop[LAST_PRE_2026]
    masters = [r["customer_id"] for r in master]
    if any(dec.get(c, ZERO) <= 0 for c in masters) or sum((dec[c] for c in masters), ZERO) != sum(jan26.values(), ZERO):
        raise ValueError("master customers at Dec 2025 don't keep their count and total ARR")
    notes.append(f"master: {len(masters)} customers active at Dec 2025, ARR {sum((dec[c] for c in masters), ZERO):,.2f} "
                 f"(unchanged total); {len(new_rows)} former customers added")

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

    shutil.copytree(src, dst)
    for v in ("Actual", "Budget", "Forecast"):
        write(os.path.join(dst, f"{v}_customers.csv"), master_fields, out_master)
    h.rows.sort(key=lambda r: (r["period"], r["customer_id"], r["movement_type"]))
    write(os.path.join(dst, HISTORY_FILE), HISTORY_FIELDS, h.rows)

    info = {c: mrow[c] for c in mrow}

    def repoint(rows: list[dict]) -> int:
        n = 0
        for r in rows:
            c = assign.get(r["opportunity_id"])
            if not c:
                continue
            m = info[c]
            r.update({"customer_id": c, "customer_name": m["customer_name"], "segment": m["segment"],
                      "industry": m["industry"], "customer_state": m["billing_state"],
                      "region": region_of[m["billing_state"]], "billing_terms": m["billing_terms"],
                      "opportunity_name": f"{m['customer_name']} - {r['opportunity_type']} - {r['period'][:7]}"})
            n += 1
        return n

    n_opp = repoint(opps)
    write(os.path.join(dst, "Actual_opportunities.csv"), opp_fields, opps)
    mv_fields, mv = ds.get("Actual_opportunity_movements.csv")
    n_mv = repoint(mv)
    opp_by_id = {o["opportunity_id"]: o for o in opps}
    adjusted = {c.split()[0] for c in cents}
    for r in mv:
        o = opp_by_id.get(r["opportunity_id"])
        if o and r["opportunity_id"] in adjusted and r["close_status"] == o["close_status"]:
            r["amount_arr"], r["weighted_arr"] = o["amount_arr"], o["weighted_arr"]
    write(os.path.join(dst, "Actual_opportunity_movements.csv"), mv_fields, mv)
    notes.append(f"opportunities: {n_opp} pointed at customers in the history (churn, contraction, expansion, "
                 f"reactivation, {RETURNING_NEW} returning new business); {n_mv} matching opportunity movement rows")

    sched_fields = ds.fields("Actual_recurring_services_schedule.csv")
    for v, src_months, holding in (("Actual", months, None), ("Budget", None, LAST_PRE_2026), ("Forecast", None, CLOSE)):
        periods = src_months or sorted({r["period"] for r in ds.rows(f"{v}_recurring_services_schedule.csv")})
        rows = []
        for p in periods:
            snap = h.eop[holding or p]
            for c in sorted(snap):
                rows.append({"organization_id": org, "version": v, "period": p, "customer_id": c,
                             "customer_name": h.info[c]["customer_name"], "segment": h.info[c]["segment"],
                             "weight_source": WEIGHT_SOURCE if not holding else f"{WEIGHT_SOURCE}, held at {holding}",
                             "customer_arr": snap[c]})
        write(os.path.join(dst, f"{v}_recurring_services_schedule.csv"), sched_fields, rows)
    notes.append("revenue weights: Actual from the history each month; Budget held at Dec 2025; Forecast held at Jun 2026")

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
