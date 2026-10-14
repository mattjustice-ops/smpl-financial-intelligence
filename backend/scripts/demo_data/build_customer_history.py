"""Customer ARR history for the demo company: every movement in the Actual, Budget and Forecast ARR waterfalls
lands on a customer.

Writes a new folder only (never touches the database):
  python build_customer_history.py <v4_folder> <out_folder>

Then build v5 from <out_folder> (build_v5_dataset.py) and continue the usual pipeline.

Rules (agreed with Matt, Oct 7 and Oct 14 2026):
  * 2024-2025: the company ARR waterfall is the source. Each month's new business, expansion, reactivation,
    contraction and churn split across customers to the cent, and customer ARR adds up to ending ARR every month.
  * Jan-Jun 2026 is built customer by customer at the rates the 2025 history shows (customer_history_actuals.py):
    renewal departures, returns, contraction and expansion on the customers themselves, and new business from
    each closing team's ramped quota at its 2025 attainment. The Actual ARR waterfall's 2026 months are the sum of
    those movements, and each movement is one Actual opportunity (a pause is a Churn opportunity). Every version's
    pipeline waterfall closes its own ARR movements at the measured Actual rates (pipeline_waterfalls.py): Actual
    2026 from the Dec 2025 pipeline, the Forecast from the June close, the Budget from Dec 2025. New logos are new
    customers in the deal's territory;
    a New Business deal goes to the channel furthest behind its expected new business (each month's new business
    split by marketing spend x the channel's win rate on the CRM deals); other deals are Customer Success. Created
    dates are
    drawn from the CRM's recorded days from creation to close for the deal type. The Forecast ARR waterfall starts
    from the new June close (its movements stay).
  * Customers in the master at Jan 2026 keep their count (700) and total ARR ($75M); their individual ARR is
    where their history lands. Customers who left before 2026 are added to the master (Churned or Paused).
  * Returns: a pause is in the churn bucket when it starts. A customer back after a pause (any length) or
    within 6 months of cancelling is a Reactivation movement; a customer back more than 6 months after
    cancelling is new business. In 2024-2025 about 20% of reactivation ARR is customers back after cancelling and
    80% after a pause.
  * Some returns come back above the ARR they left with, some below, some equal; some customers contract and
    later expand. That is what the commission policy (7.21-7.24) measures.
  * Customers leave at renewal: a former customer's anniversary (start month) is the month it left.
  * Budget and Forecast customer histories (customer_history_plans.py) start from the Actual close they plan
    from (Dec 2025, Jun 2026). Budget churn customers hold flat Actual ARR through Dec 2025.
  * Renewal pipelines (Actual Jan-Jun 2026, Forecast Jul-Dec 2026) are the customers due in their anniversary
    month at their ARR; Actual renewal commissions are the renewal plan rate x each renewal, paid to its CSM. The
    rate pays the Actual CSMs their commission targets (prorated for the months employed) on the Jan-Jun 2026
    renewals, to the basis point; PLAN-RENEWAL is added to each version's commission plans at that rate.
  * The sales and customer success team is the employee files (sales_team.py): employees are named, Sales and
    Customer Success work CRM territories, and each customer's CSM is an employee CSM in its territory.
  * Revenue weights (recurring services schedule) follow each version's history: a customer is billed only
    while it has ARR (Forecast: expected ARR). Revenue follows that ARR (revenue_from_arr.py) in the simulated
    Actual months and every Budget and Forecast month.
  * Segment is the customer's ARR at signing (Enterprise $500k+, Mid-Market $100k-$500k, SMB below $100k) in
    every file that carries it; the implementation fee follows the segment.
  * Every history row carries the customer's age of first MRR and its New Business or Customer Success line
    (customer_buckets.py, agreed Oct 9 2026). The movement types above stay as they are for bookings and
    commissions; the bucket lines are what the ARR waterfall and retention use. first_mrr_date on the customer
    master is the latest restart of that age.
"""

from __future__ import annotations

import datetime as dt
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_v5_dataset import (ZERO, Dataset, allocate, last_day, num, padd, pidx, prange, q,  # noqa: E402
                              ramp_curve, write)
from customer_history_actuals import measure, simulate  # noqa: E402
from customer_history_plans import (BOOKED, CANCELLED, CANCELLED_SHARE, EXPECTED_FIELDS,  # noqa: E402
                                    HISTORY_FIELDS, PAUSED, FORECAST_RENEWAL_PROBABILITY, WF_COLUMNS, return_note,
                                    History, actual_renewals, forecast_deals, pick, prospect_segments,
                                    renewal_commissions, renewal_rows, segment_for, signing_arr, simulate_budget,
                                    simulate_forecast, tie, tie_budget_deals, u, waterfall)
from add_implementation_revenue import FEE_BY_SEGMENT, TERMS_DAYS as IMPLEMENTATION_TERMS_DAYS  # noqa: E402
from collections_model import NO_START, NO_START_TERMS_DAYS, NO_STARTS, NON_PAYMENT, NONPAY_CHURN, no_start_exit  # noqa: E402
from customer_buckets import RESTART_AFTER_MONTHS, classify  # noqa: E402
from pipeline_waterfalls import FIELDS as PIPELINE_FIELDS, rebuild as rebuild_pipelines  # noqa: E402
from pipeline_waterfalls import summaries as pipeline_summaries  # noqa: E402
from revenue_from_arr import rebase, recurring_ratio  # noqa: E402
from sales_team import VERSIONS, active, assign_csms, quota_type, team_employees  # noqa: E402

FIRST = "2024-01"
LAST_PRE_2026 = "2025-12"
SIMULATED_FROM = padd(LAST_PRE_2026, 1)
CLOSE = "2026-06"
PRE_FROM = "2023-07"
PAUSE_FROM = "2024-04"
PAUSE_SHARE = Decimal("0.5")
RENEWAL_PLAN = "PLAN-RENEWAL"
HISTORY_FILE = "Actual_customer_arr_history.csv"
ACCOUNT_CHANNEL = "Customer Success"


def weight_source(v: str) -> str:
    what = "expected ARR" if v == "Forecast" else "ARR"
    return f"{v}_customer_arr_history.csv ({what} after the month's movements)"


def renewal_rate(employees: list[dict], renewals: list[dict], months: list[str]) -> Decimal:
    """The rate that pays the CSMs their commission targets (for the months each was employed) on the renewals."""
    target = sum((num(e["commission_target"]) * sum(1 for p in months if active(e, p)) / 12
                  for e in employees if quota_type(e["role"]) == "Expansion ARR"), ZERO)
    booked = sum((num(r["renewal_arr"]) for r in renewals if r["renewal_period"][:7] in months), ZERO)
    if target <= 0 or booked <= 0:
        raise ValueError(f"renewal plan rate needs CSM commission targets ({target}) and renewal ARR ({booked})")
    return (target / booked).quantize(Decimal("0.0001"))


def restate(rows: list[dict], wf: dict[str, dict[str, Decimal]], begin: Decimal, org: str) -> Decimal:
    """A plan's ARR waterfall from ``begin`` with its movements unchanged: each month ends at beginning + movements
    to the cent and the next begins there. Returns the last ending."""
    for r in sorted(rows, key=lambda r: r["period"]):
        w = wf[r["period"][:7]]
        net = w["new_business_arr"] + w["expansion_arr"] + w["reactivation_arr"] - w["contraction_arr"] - w["churn_arr"]
        w["beginning_arr"], w["ending_arr"] = begin, begin + net
        r.update({"organization_id": org, "beginning_arr": f"{begin:.2f}", "ending_arr": f"{begin + net:.2f}",
                  "net_new_arr": f"{net:.2f}",
                  "renewal_arr": f"{begin - w['contraction_arr'] - w['churn_arr']:.2f}", "waterfall_check": "0"})
        begin += net
    return begin


def customer_number(cid: str) -> int:
    return int(cid.split("-")[1])


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
    opp_fields, crm_opps = ds.get("Actual_opportunities.csv")
    region_of = {}
    for v in ("Actual", "Budget", "Forecast"):
        for r in ds.rows(f"{v}_opportunities.csv"):
            region_of[r["customer_state"]] = r["region"]
    team = team_employees({v: ds.rows(f"{v}_Employees.csv") for v in VERSIONS}, Counter(o["region"] for o in crm_opps))
    notes.append("team: " + "; ".join(
        f"{v} " + ", ".join(f"{t} {n}" for t, n in sorted(Counter(e["region"] for e in team[v]
                                                                    if e["department"] in ("Sales", "Customer Success")).items()))
        for v in VERSIONS) + " (Sales and Customer Success by territory)")

    b_fields, b_opps = ds.get("Budget_opportunities.csv")
    bwf_fields, bwf_rows = ds.get("Budget_MRR_Waterfall.csv")
    WB = waterfall(bwf_rows)
    end = restate(bwf_rows, WB, W[LAST_PRE_2026]["ending_arr"], org)
    notes.append(f"Budget ARR waterfall starts from the Actual {LAST_PRE_2026} close; ends {end:,.2f}")
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

    def anniv(c: str) -> str:
        return start[c][5:7]

    # ---- former customers (not in the master): new records
    prefixes = sorted({re.sub(r"\s+\d+$", "", r["customer_name"]) for r in master})
    industries = sorted({r["industry"] for r in master})
    states = sorted({r["billing_state"] for r in master})
    terms = [r["billing_terms"] for r in master]
    cadences = [r["billing_cadence"] for r in master]
    next_no = max(customer_number(c) for c in mrow) + 1
    new_rows: list[dict] = []

    def new_customer(tag: str, departs: str, starts: str = "") -> str:
        """A former customer whose anniversary is the month it leaves (or that starts in ``starts``). Segment is set
        from the history once it is built."""
        nonlocal next_no
        cid = f"CUST-{next_no:04d}"
        next_no += 1
        k = f"former|{cid}"
        latest = min(pidx(departs) - 7, pidx("2023-06"))
        s = padd("2019-01", int(u(k + "|start") * (latest - pidx("2019-01") + 1)))
        s = f"{s[:4]}-{departs[5:7]}"
        if pidx(s) > latest:
            s = padd(s, -12)
        s = starts or s
        row = {"organization_id": org, "customer_id": cid,
               "customer_name": f"{prefixes[int(u(k + '|name') * len(prefixes))]} {next_no - 1}",
               "segment": "", "industry": industries[int(u(k + "|ind") * len(industries))], "status": "",
               "customer_start_date": f"{s}-01", "contract_start_date": f"{s}-01",
               "billing_cadence": cadences[int(u(k + "|cad") * len(cadences))],
               "billing_terms": terms[int(u(k + "|terms") * len(terms))],
               "billing_state": states[int(u(k + "|state") * len(states))], "source_crm": "Salesforce",
               "netsuite_customer_id": f"NS-{cid}", "stripe_customer_id": f"cus_demo_{cid.split('-')[1]}",
               "starting_mrr_jan_2026": "0", "starting_arr_jan_2026": "0", "currency": "USD", "_tag": tag}
        new_rows.append(row)
        mrow[cid] = row
        start[cid] = s
        h.info[cid] = {"customer_name": row["customer_name"], "segment": ""}
        return cid

    # ---- returns: every 2024-2025 month's reactivation ARR, split 1-2 ways
    returns: list[dict] = []
    for p in prange(FIRST, LAST_PRE_2026):
        total = W[p]["reactivation_arr"]
        n = 1 if total < 40000 else 2
        amts = allocate(total, [(f"{p}#{i}", Decimal(1) + u(f"rsplit|{p}|{i}")) for i in range(n)])
        for key, a in sorted(amts.items()):
            returns.append({"period": p, "amount": a, "key": key})
    wb = tot = ZERO
    for r in returns:
        tot += r["amount"]
        r["kind"] = CANCELLED if wb + r["amount"] <= CANCELLED_SHARE * tot + Decimal("15000") and wb < CANCELLED_SHARE * tot else PAUSED
        if r["kind"] == CANCELLED:
            wb += r["amount"]
        p, key = r["period"], r["key"]
        lo = max(1 if r["kind"] == CANCELLED else 2, pidx(p) - pidx(LAST_PRE_2026))
        hi = RESTART_AFTER_MONTHS if r["kind"] == CANCELLED else 14
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
    notes.append(f"returns 2024-2025: {len(returns)} (${tot:,.2f}); after cancelling "
                 f"{sum(1 for r in returns if r['kind'] == CANCELLED)} (${wb:,.2f}, {wb / tot:.1%} of reactivation ARR); "
                 f"after a pause {sum(1 for r in returns if r['kind'] == PAUSED)}")

    used: set[str] = set()
    opening_masters = sorted(c for c in mrow if start[c] < FIRST)
    early_masters = [c for c in opening_masters if start[c] < PRE_FROM]

    # Opportunity owners are assigned by region, so each deal goes to a customer in its own region where one fits.
    def region(c: str) -> str:
        return region_of.get(mrow[c]["billing_state"], "")

    def in_region(cands: list[str], o: dict) -> list[str]:
        return [c for c in cands if region(c) == o["region"]] or cands

    def at_renewal(cands: list[str], o: dict) -> list[str]:
        return [c for c in cands if anniv(c) == o["period"][5:7]] or cands

    # Budget churn customers hold their Dec 2025 ARR (= the Budget churn deal) flat in the Actual history.
    opening: dict[str, Decimal] = {}
    budget_pins: dict[str, str] = {}
    for o in sorted((o for o in b_opps if o["opportunity_type"] == "Churn"), key=lambda o: (o["period"], o["opportunity_id"])):
        cands = [c for c in opening_masters if c not in used]
        c = pick(at_renewal(in_region(cands, o), o), 1, f"bchurn|{o['opportunity_id']}", lambda c: jan26[c])[0]
        budget_pins[o["opportunity_id"]] = c
        opening[c] = num(o["amount_arr"])
        used.add(c)
    budget_churners = list(budget_pins.values())

    # ---- returners: master customers
    departures: dict[str, list[tuple[str, str, Decimal, str]]] = defaultdict(list)
    returning: dict[str, list[tuple[str, Decimal, str]]] = defaultdict(list)
    pre_departures: list[tuple[str, str, Decimal, str]] = []
    pool = [c for c in early_masters if c not in used]
    for r in returns:
        cands = [x for x in pool if x not in used]
        cands = [x for x in cands if anniv(x) == r["departed"][5:7]] or cands
        c = pick(cands, 1, f"ret|{r['key']}", lambda c: Decimal(1))[0]
        used.add(c)
        r["customer"] = c
        kind = "Churn" if r["kind"] == CANCELLED else "Pause"
        if r["departed"] >= FIRST:
            opening[c] = r["baseline"]
            departures[r["departed"]].append((c, kind, r["baseline"], ""))
        else:
            pre_departures.append((r["departed"], c, r["baseline"], kind))
        returning[r["period"]].append((c, r["amount"], return_note(r["kind"], r["months_away"])))

    # ---- no-starts: booked, onboarded and billed but never paid; service suspended and the contract ended inside
    # its first year. Their ARR is carved out of the booking month's new business and the exit month's churn.
    ns_plan = []
    ns_out: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for ns in NO_STARTS:
        _, _, suspended, left = no_start_exit(ns)
        if pidx(left) - pidx(ns.booked) >= 12 or not FIRST <= ns.booked < left <= LAST_PRE_2026:
            raise ValueError(f"no-start booked {ns.booked} leaves {left}: must leave inside its first year, by {LAST_PRE_2026}")
        a = q(W[ns.booked]["new_business_arr"] * ns.nb_share)
        ns_plan.append((ns, suspended, left, a))
        ns_out[left] += a

    # ---- formers: the rest of each month's churn; about half of those leaving from PAUSE_FROM pause
    for p in prange(FIRST, LAST_PRE_2026):
        rem = W[p]["churn_arr"] - sum((x[2] for x in departures[p]), ZERO) - ns_out[p]
        if rem <= 0:
            raise ValueError(f"{p}: returners' departures {W[p]['churn_arr'] - rem} exceed churn {W[p]['churn_arr']}")
        n = max(1, int((rem / Decimal(85000)).to_integral_value()))
        split = sorted(allocate(rem, [(f"{p}#{i}", Decimal("0.5") + u(f"csplit|{p}|{i}")) for i in range(n)]).items())
        pauses = [p >= PAUSE_FROM and u(f"pause|{key}") < PAUSE_SHARE for key, _ in split]
        if p in dict(NONPAY_CHURN) and all(pauses):
            pauses[-1] = False  # the month's non-payment churn is a full churn
        for (key, a), pause in zip(split, pauses):
            c = new_customer("former", p)
            opening[c] = a
            departures[p].append((c, "Pause" if pause else "Churn", a, ""))
    no_starts: dict[str, list[tuple[str, Decimal, str]]] = defaultdict(list)
    for ns, suspended, left, a in ns_plan:
        c = new_customer("no-start", left, starts=ns.booked)
        mrow[c].update({"billing_cadence": "Monthly", "billing_terms": f"Net {NO_START_TERMS_DAYS}"})
        no_starts[ns.booked].append((c, a, f"no-start: {ns.reason}"))
        departures[left].append((c, "Churn", a, f"no-start: never paid; service suspended {suspended:%Y-%m-%d}"))

    # ---- opening balances
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

    flat = set(budget_churners) | {c for x in no_starts.values() for c, *_ in x}
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
        for c, a, note in returning[p]:
            h.move(p, c, "Reactivation", a, note=note)
        starters = sorted(c for c in mrow if start[c] == p and c in jan26)
        if not starters:
            raise ValueError(f"{p}: new business {W[p]['new_business_arr']} but no customer starts")
        nb = W[p]["new_business_arr"] - sum((a for _, a, _ in no_starts[p]), ZERO)
        for c, a in allocate(nb, [(c, jan26[c] * (Decimal("0.6") + Decimal("0.4") * u(f"nb|{c}"))) for c in starters]).items():
            h.move(p, c, "New Business", a)
        for c, a, note in no_starts[p]:
            h.move(p, c, "New Business", a, note=note)
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

    # ---- churn type: no-starts, and one non-payment churn in each NONPAY_CHURN month (a full churn of a customer
    # past its first year that never comes back)
    ns_ids = {c for x in no_starts.values() for c, *_ in x}
    for r in h.rows:
        if r["customer_id"] in ns_ids and r["movement_type"] == "Churn":
            r["churn_type"] = NO_START
    nonpay: list[str] = []

    def choose_nonpay(m: str, cands: list[str]) -> str:
        """The month's non-payment churn among full churns past their first year, monthly-billed where one is."""
        cands = sorted(c for c in cands if c not in ns_ids and pidx(m) - pidx(start[c]) >= 12)
        cands = [c for c in cands if mrow.get(c, {}).get("billing_cadence") == "Monthly"] or cands
        if not cands:
            raise ValueError(f"{m}: no full churn past its first year to mark as non-payment")
        return pick(cands, 1, f"nonpay|{m}", lambda c: Decimal(1))[0]

    def mark_nonpay(m: str, reason: str, c: str) -> None:
        rows = [r for r in h.rows if r["customer_id"] == c and r["period"] == m and r["movement_type"] == "Churn"]
        if len(rows) != 1 or any(r["customer_id"] == c and r["period"] > m and r["movement_type"] in
                                 ("Reactivation", "New Business") for r in h.rows):
            raise ValueError(f"{m} {c}: a non-payment churn must leave in the month and never come back")
        rows[0]["churn_type"] = NON_PAYMENT
        rows[0]["note"] = "; ".join(x for x in (rows[0]["note"], f"non-payment: {reason}") if x)
        nonpay.append(f"{c} {m}")

    collections_churn = set(ns_ids)
    nonpay_reason = dict(NONPAY_CHURN)
    for m, reason in NONPAY_CHURN:
        if m <= LAST_PRE_2026:
            back: dict[str, str] = {}
            for r in h.rows:
                if r["movement_type"] in ("Reactivation", "New Business"):
                    back[r["customer_id"]] = max(back.get(r["customer_id"], ""), r["period"])
            c = choose_nonpay(m, [r["customer_id"] for r in h.rows if r["period"] == m and r["movement_type"] == "Churn"
                                  and r["ending_arr"] == 0 and back.get(r["customer_id"], "") <= m])
            mark_nonpay(m, reason, c)
            collections_churn.add(c)

    dec = h.eop[LAST_PRE_2026]
    masters = [r["customer_id"] for r in master]
    if any(dec.get(c, ZERO) <= 0 for c in masters) or sum((dec[c] for c in masters), ZERO) != sum(jan26.values(), ZERO):
        raise ValueError("master customers at Dec 2025 don't keep their count and total ARR")
    notes.append(f"master: {len(masters)} customers active at Dec 2025, ARR {sum((dec[c] for c in masters), ZERO):,.2f} "
                 f"(unchanged total); {len(new_rows)} former customers added "
                 f"({sum(1 for x in departures.values() for _, k, *_ in x if k == 'Pause')} paused)")

    # ---- Jan-Jun 2026: customer by customer at the 2025 rates
    curve = ramp_curve(ds)
    window = prange(padd(SIMULATED_FROM, -12), LAST_PRE_2026)
    rates = measure(h, start, window, team["Actual"], curve, collections_churn)
    notes.append(rates.describe())
    taken = {customer_number(c) for c in mrow}
    for v in VERSIONS:
        for name in (f"{v}_opportunities.csv", f"{v}_opportunity_movements.csv", f"{v}_customers.csv"):
            taken |= {customer_number(r["customer_id"]) for r in ds.rows(name)}
    next_logo = max(taken) + 1
    states_in = {t: [s for s in states if region_of.get(s) == t] for t in sorted(set(region_of.values()))}
    logo_info: dict[str, dict[str, str]] = {}

    def new_logo(p: str, territory: str, arr: Decimal, key: str) -> str:
        nonlocal next_logo
        if not states_in.get(territory):
            raise ValueError(f"no customer state in territory {territory}")
        cid = f"CUST-{next_logo:05d}"
        name = f"{prefixes[int(u(key + '|name') * len(prefixes))]} {next_logo}"
        next_logo += 1
        logo_info[cid] = {"customer_name": name, "industry": industries[int(u(key + "|ind") * len(industries))],
                          "billing_state": states_in[territory][int(u(key + "|state") * len(states_in[territory]))],
                          "billing_cadence": cadences[int(u(key + "|cad") * len(cadences))],
                          "billing_terms": terms[int(u(key + "|terms") * len(terms))]}
        start[cid] = p
        h.info[cid] = {"customer_name": name, "segment": segment_for(arr)}
        return cid

    opp_no = max(int(r["opportunity_id"].rsplit("-", 1)[1])
                 for name in ("Actual_opportunities.csv", "Actual_opportunity_movements.csv") for r in ds.rows(name))

    def next_id() -> str:
        nonlocal opp_no
        opp_no += 1
        return f"ACT-OPP-{opp_no}"

    sim_months = prange(SIMULATED_FROM, CLOSE)
    nonpay_2026: dict[str, str] = {}

    def nonpay_in(m: str, cancelled: list[str]) -> str:
        nonpay_2026[m] = choose_nonpay(m, cancelled)
        return nonpay_2026[m]

    deals = simulate(h, rates, sim_months, start, team["Actual"], curve, collections_churn,
                     {m for m in nonpay_reason if m >= SIMULATED_FROM}, nonpay_in, new_logo, next_id)
    for m, c in sorted(nonpay_2026.items()):
        mark_nonpay(m, nonpay_reason[m], c)
    notes.append(f"churn type: {len(ns_ids)} no-starts ({', '.join(sorted(ns_ids))}), non-payment churn {', '.join(nonpay)}")
    by_kind = Counter((d["period"], d["kind"]) for d in deals)
    notes.append("Jan-Jun 2026 movements: " + "; ".join(
        f"{p} " + ", ".join(f"{k} {by_kind[(p, k)]}" for k in ("New Business", "Expansion", "Reactivation",
                                                               "Contraction", "Churn", "Pause") if by_kind[(p, k)])
        for p in sim_months))
    for t in sorted({d["team"] for d in deals if d["team"]}):
        mine = [d for d in deals if d["team"] == t]
        notes.append(f"{t} new business: {len(mine)} deals, ARR {sum((d['amount'] for d in mine), ZERO):,.2f}")

    # ---- Actual ARR waterfall 2026 = the history
    by_col: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for r in h.rows:
        if r["period"] >= SIMULATED_FROM and r["waterfall_column"]:
            by_col[r["period"]][r["waterfall_column"]] += abs(r["movement_arr"])
    for p in sim_months:
        W[p] = {**{k: by_col[p][k] for k in WF_COLUMNS}, "beginning_arr": sum(h.eop[padd(p, -1)].values(), ZERO),
                "ending_arr": sum(h.eop[p].values(), ZERO)}
    wf_fields, wf_rows = ds.get("Actual_MRR_Waterfall.csv")
    for r in wf_rows:
        p = r["period"][:7]
        if p in sim_months:
            w = W[p]
            net = w["new_business_arr"] + w["expansion_arr"] + w["reactivation_arr"] - w["contraction_arr"] - w["churn_arr"]
            r.update({k: f"{w[k]:.2f}" for k in (*WF_COLUMNS, "beginning_arr", "ending_arr")})
            r.update({"net_new_arr": f"{net:.2f}", "renewal_arr": f"{w['beginning_arr'] - w['contraction_arr'] - w['churn_arr']:.2f}",
                      "waterfall_check": "0"})
    opening_sum = sum((r["ending_arr"] for r in h.rows if r["movement_type"] == "Opening balance"), ZERO)
    notes.append(tie(h, W, months, opening_sum))
    notes.append(f"Actual ending ARR {CLOSE}: {W[CLOSE]['ending_arr']:,.2f}")

    # ---- Forecast ARR waterfall: from the new June close, its movements unchanged
    fwf_fields, fwf_rows = ds.get("Forecast_MRR_Waterfall.csv")
    end = restate(fwf_rows, WF, W[CLOSE]["ending_arr"], org)
    notes.append(f"Forecast ARR waterfall starts from the Actual {CLOSE} close; ends {end:,.2f}")

    # ---- pipeline waterfalls: every version closes its own ARR movements at the measured Actual rates
    pipelines, pw_notes = rebuild_pipelines(
        ds.rows("Actual_pipeline_waterfall.csv"), {"Actual": W, "Forecast": WF, "Budget": WB}, SIMULATED_FROM, CLOSE,
        sorted({r["period"][:7] for r in ds.rows("Forecast_pipeline_waterfall.csv") if r["period"][:7] <= CLOSE}))
    notes += pw_notes
    crm_created = {r["period"][:7]: num(r["new_pipeline_created"]) for r in pipelines["Actual"]
                   if r["opportunity_type"] == "New Business"}

    # ---- Actual opportunities: one per 2026 movement
    lags: dict[str, list[int]] = defaultdict(list)
    for o in crm_opps:
        closed = o["actual_close_date"] or o["expected_close_date"]
        if o["created_date"] and closed:
            lags[o["opportunity_type"]].append((dt.date.fromisoformat(closed[:10])
                                                - dt.date.fromisoformat(o["created_date"][:10])).days)
    spend: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for r in ds.rows("Actual_marketing_pipeline.csv"):
        spend[r["period"][:7]][r["marketing_channel"]] += num(r["marketing_spend"])
    for p in sim_months:
        if not sum(spend[p].values(), ZERO):
            raise ValueError(f"{p}: no Actual marketing spend to draw New Business channels from")
    crm_won: dict[str, Decimal] = defaultdict(Decimal)
    crm_reach: dict[str, Decimal] = defaultdict(Decimal)
    for o in crm_opps:
        if o["opportunity_type"] == "New Business" and o["close_status"] == "Closed Won":
            crm_won[o["marketing_channel"]] += num(o["amount_arr"])
    for p in sorted({o["period"][:7] for o in crm_opps}):
        total = sum(spend[p].values(), ZERO)
        for c, s in spend[p].items():
            crm_reach[c] += crm_created[p] * s / total
    win = {c: crm_won[c] / crm_reach[c] if crm_reach[c] else ZERO for c in crm_reach}
    behind: dict[str, Decimal] = defaultdict(Decimal)

    def expect(p: str) -> None:
        weight = {c: spend[p][c] * win.get(c, ZERO) for c in spend[p]}
        total = sum(weight.values(), ZERO)
        for c, x in weight.items():
            behind[c] += W[p]["new_business_arr"] * x / total

    def channel(d: dict) -> str:
        fits = sorted(c for c in spend[d["period"]] if win.get(c, ZERO) > 0)
        if not fits:
            raise ValueError(f"{d['opportunity_id']}: no channel with CRM wins and spend in {d['period']}")
        c = max(fits, key=lambda c: behind[c])
        behind[c] -= d["amount"]
        return c

    def describe(d: dict) -> str:
        if d["kind"] == "New Business":
            return f"{d['team']} new business at the team's measured attainment of ramped quota"
        return {"Pause": "paused at renewal", "Churn": "cancelled at renewal", "Contraction": "contraction",
                "Expansion": "expansion"}.get(d["kind"], d["note"])

    def attrs(c: str) -> dict[str, str]:
        return mrow[c] if c in mrow else logo_info[c]

    nb_channel: dict[str, str] = {}
    for p in sim_months:
        expect(p)
        for d in sorted((d for d in deals if d["kind"] == "New Business" and d["period"] == p),
                        key=lambda d: (-d["amount"], d["opportunity_id"])):
            nb_channel[d["opportunity_id"]] = channel(d)
    opps: list[dict] = []
    for d in deals:
        c, p, oid = d["customer_id"], d["period"], d["opportunity_id"]
        t = "Churn" if d["kind"] == "Pause" else d["kind"]
        if not lags[t]:
            raise ValueError(f"no CRM {t} deals with created and close dates to draw a created date from")
        m, status, close = attrs(c), BOOKED[t], last_day(p)
        lag = sorted(lags[t])[int(u(f"lag|{oid}") * len(lags[t]))]
        opps.append({
            "organization_id": org, "version": "Actual", "period": p, "opportunity_id": oid,
            "opportunity_name": f"{m['customer_name']} - {t} - {p}", "customer_id": c, "customer_name": m["customer_name"],
            "opportunity_type": t, "stage": status, "close_status": status,
            "created_date": (close - dt.timedelta(days=lag)).isoformat(), "expected_close_date": close.isoformat(),
            "actual_close_date": close.isoformat() if status == "Closed Won" else "", "contract_start_date": f"{p}-01",
            "contract_end_date": f"{padd(p, 12)}-01", "contract_term_months": "12",
            "billing_cadence": m["billing_cadence"], "billing_terms": m["billing_terms"],
            "customer_state": m["billing_state"], "region": region_of[m["billing_state"]], "segment": "",
            "industry": m["industry"], "marketing_channel": nb_channel.get(oid, ACCOUNT_CHANNEL), "owner": "",
            "amount_arr": f"{d['amount']:.2f}", "weighted_arr": f"{d['amount']:.2f}", "probability": "1.0",
            "waterfall_type": status, "pipeline_movement_type": status,
            "source_note": f"Customer ARR history: {describe(d)}"})
    logos = {o["customer_id"]: o for o in opps if o["opportunity_type"] == "New Business"}
    crm_booked = {o["opportunity_id"] for o in crm_opps}
    mv_a = ds.rows("Actual_opportunity_movements.csv")
    mv_a[:] = [r for r in mv_a if r["opportunity_id"] not in crm_booked] + [dict(o) for o in opps]
    imp_a = ds.rows("Actual_implementation_schedule.csv")
    kept = [r for r in imp_a if r["source"] != "Actual_opportunities.csv"]
    seq = max(int(r["invoice_id"].rsplit("-", 1)[1]) for r in kept)
    added = []
    for o in sorted(logos.values(), key=lambda o: (o["actual_close_date"], o["opportunity_id"])):
        seq += 1
        signed = dt.date.fromisoformat(o["actual_close_date"])
        due = signed + dt.timedelta(days=IMPLEMENTATION_TERMS_DAYS)
        added.append({"organization_id": org, "version": "Actual", "period": signed.strftime("%Y-%m"),
                      "customer_id": o["customer_id"], "customer_name": o["customer_name"], "segment": "",
                      "source": "Actual_opportunities.csv", "source_record_id": o["opportunity_id"],
                      "win_probability": "1", "implementation_fee": "", "invoice_id": f"IMP-A-{seq:05d}",
                      "invoice_date": signed.isoformat(), "due_date": due.isoformat(),
                      "collection_period": due.strftime("%Y-%m")})
    imp_a[:] = kept + added
    notes.append(f"Actual opportunities: {len(opps)} from the 2026 history replace the {len(crm_opps)} CRM deals; "
                 f"{len(logos)} new logos; New Business channels (each tracking pipeline created x the channel's "
                 f"win rate on the CRM deals) "
                 + ", ".join(f"{c} {n} (win {win.get(c, ZERO):.1%})"
                             for c, n in sorted(Counter(nb_channel.values()).items())))

    # ---- Budget and Forecast
    taken = {customer_number(c) for c in list(mrow) + list(logos)}
    for v_opps in (b_opps, f_all):
        taken |= {customer_number(o["customer_id"]) for o in v_opps}
    next_logo = max(taken) + 1
    renamed: dict[str, tuple[str, str]] = {}
    seen: set[str] = set()
    for o in sorted(f_opps, key=lambda o: (o["period"], o["opportunity_id"])):
        cid = o["customer_id"]
        if o["opportunity_type"] != "New Business":
            continue
        if cid in mrow or cid in logos or h.eop[CLOSE].get(cid, ZERO) > 0 or cid in seen:
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
    notes.append(f"Forecast new business on a customer already in the Actual history or already won earlier in the "
                 f"Forecast is a new logo: {', '.join(f'{a} -> {b[0]} {b[1]}' for a, b in renamed.items()) or 'none'}")

    def plan_region(c: str) -> str:
        return region(c) if c in mrow else region_of.get((plan_logos["Budget"].get(c) or plan_logos["Forecast"].get(c)
                                                          or logos[c])["customer_state"], "")

    hb, b_assign = simulate_budget(org, h.info, dec, LAST_PRE_2026, h.rows, b_opps, WB, budget_pins, plan_region, anniv,
                                   start, notes)
    hf, f_assign, f_due = simulate_forecast(org, h.info, h.eop[CLOSE], CLOSE, h.rows, f_opps, WF, plan_region, anniv,
                                            start, notes, {d["customer_id"] for d in deals if d["kind"] == "Expansion"})

    # ---- renewal pipelines and renewal commissions
    churn_by_month: dict[str, set[str]] = defaultdict(set)
    for o in opps:
        if o["opportunity_type"] == "Churn":
            churn_by_month[o["period"]].add(o["customer_id"])
    a_due = actual_renewals(h, sim_months, anniv, start, churn_by_month)
    ren_fields, old_ren = ds.get("Actual_renewal_pipeline.csv")
    old_by_customer = {r["customer_id"]: r for r in sorted(old_ren, key=lambda r: r["renewal_period"])}
    a_ren = renewal_rows(org, "Actual", a_due, old_ren, old_by_customer, h.info)
    by_customer = {r["customer_id"]: r for r in a_ren}
    by_customer.update({c: r for c, r in old_by_customer.items() if c not in by_customer})
    f_ren = renewal_rows(org, "Forecast", f_due, old_ren, by_customer, h.info,
                         {"renewal_probability": f"{FORECAST_RENEWAL_PROBABILITY}", "renewal_stage": "Commit"})
    a_exp = [{"customer_id": o["customer_id"], "period": o["period"], "expansion_arr": num(o["amount_arr"])}
             for o in opps if o["opportunity_type"] == "Expansion"]
    csm_of = assign_csms([{"customer_id": r["customer_id"], "period": r["renewal_period"][:7]} for r in a_ren] + a_exp,
                         team["Actual"], plan_region, {})
    assign_csms([{"customer_id": r["customer_id"], "period": r["renewal_period"][:7]} for r in f_ren],
                team["Forecast"], plan_region, csm_of)
    name_of = {e["employee_id"]: e["employee_name"] for v in VERSIONS for e in team[v]}
    for r in a_ren + f_ren:
        r["customer_success_manager"] = name_of[csm_of[r["customer_id"]]]
    com_fields = ds.fields("Actual_renewal_commissions.csv")
    rep_of = {name_of[i]: i for i in set(csm_of.values())}
    ren_rate = renewal_rate(team["Actual"], a_ren, sim_months)
    a_com = renewal_commissions(org, a_ren, rep_of, ren_rate, last_day)
    notes.append(f"CSMs: {len(set(csm_of.values()))} employee CSMs for {len(csm_of)} customers renewing or expanding "
                 + "(" + ", ".join(f"{name_of[i]} {n}" for i, n in sorted(Counter(csm_of.values()).items())) + ")")
    notes.append(f"renewal pipeline: Actual {len(a_ren)} renewals Jan-Jun 2026 (renewal ARR "
                 f"{sum((num(r['renewal_arr']) for r in a_ren), ZERO):,.2f}), Forecast {len(f_ren)} Jul-Dec 2026; "
                 f"renewal commissions {len(a_com)} at {ren_rate} (the rate that pays the CSMs' commission targets) "
                 f"({sum((num(r['commission_amount']) for r in a_com), ZERO):,.2f})")

    # ---- segment: ARR at signing; plan-only logos from their deal, prospects once opportunities are re-pointed
    actual_seg = {c: segment_for(a) for c, a in signing_arr(h.rows).items()}
    seg_of: dict[str, dict[str, str]] = {"Actual": dict(actual_seg)}
    for v in ("Budget", "Forecast"):
        seg_of[v] = dict(actual_seg)
        for cid, o in sorted(plan_logos[v].items()):
            seg_of[v].setdefault(cid, segment_for(num(o["amount_arr"])))
    for r in master + new_rows:
        r["segment"] = actual_seg[r["customer_id"]]
    for v, hist in (("Actual", h), ("Budget", hb), ("Forecast", hf)):
        for r in hist.rows:
            r["segment"] = seg_of[v][r["customer_id"]]
    notes.append("segment = ARR at signing (earliest ARR on record for customers signed before the history): "
                 + ", ".join(f"{k} {n}" for k, n in sorted(Counter(actual_seg[r["customer_id"]] for r in master + new_rows).items()))
                 + " in the customer master; 2026 new logos "
                 + ", ".join(f"{k} {n}" for k, n in sorted(Counter(actual_seg[c] for c in logos).items())))

    # ---- customer buckets: age of first MRR; New Business (first 12 months) vs Customer Success
    classify(h.rows, start)
    classify(hb.rows, start, prior=[r for r in h.rows if r["period"] <= LAST_PRE_2026])
    classify(hf.rows, start, prior=[r for r in h.rows if r["period"] <= CLOSE])
    for r in h.rows:
        expected = {NO_START: "no_start", NON_PAYMENT: "churn"}.get(r.get("churn_type", ""))
        if expected and r["waterfall_line"] != expected:
            raise ValueError(f"{r['period']} {r['customer_id']}: {r['churn_type']} churn at age "
                             f"{r['customer_age_months']} is {r['waterfall_line']}")
    for v, hist in (("Actual", h), ("Budget", hb), ("Forecast", hf)):
        counts = Counter(r["waterfall_line"] for r in hist.rows if r["waterfall_line"])
        notes.append(f"{v} bucket lines: " + ", ".join(f"{k} {n}" for k, n in sorted(counts.items())))
    first_mrr = {r["customer_id"]: r["first_mrr_period"] for r in sorted(h.rows, key=lambda r: r["period"])}
    if "first_mrr_date" not in master_fields:
        master_fields.insert(master_fields.index("customer_start_date") + 1, "first_mrr_date")

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
        nr["first_mrr_date"] = f"{first_mrr[c]}-01"
        a = dec.get(c, ZERO)
        nr["starting_arr_jan_2026"] = f"{a:.2f}"
        nr["starting_mrr_jan_2026"] = f"{q(a / 12):.2f}"
        out_master.append(nr)
    notes.append("status at " + CLOSE + ": " + ", ".join(f"{k} {n}" for k, n in sorted(Counter(r["status"] for r in out_master).items()))
                 + f" (plus {len(logos)} 2026 new logos added by the v5 build)")

    def logo_row(v: str, o: dict) -> dict:
        cid = o["customer_id"]
        return {"organization_id": org, "customer_id": cid, "customer_name": o["customer_name"], "segment": seg_of[v][cid],
                "industry": o["industry"], "status": "Active", "customer_start_date": o["contract_start_date"],
                "first_mrr_date": f"{o['period'][:7]}-01", "contract_start_date": o["contract_start_date"], "billing_cadence": o["billing_cadence"],
                "billing_terms": o["billing_terms"], "billing_state": o["customer_state"], "source_crm": "Salesforce",
                "netsuite_customer_id": f"NS-{cid}", "stripe_customer_id": f"cus_demo_{cid.split('-')[1]}",
                "starting_mrr_jan_2026": "0", "starting_arr_jan_2026": "0", "currency": "USD"}

    shutil.copytree(src, dst)
    for v in VERSIONS:
        write(os.path.join(dst, f"{v}_Employees.csv"), ds.fields(f"{v}_Employees.csv"), team[v])
    write(os.path.join(dst, "Actual_customers.csv"), master_fields, out_master)
    for v in ("Budget", "Forecast"):
        extra = [logo_row(v, o) for cid, o in sorted(plan_logos[v].items()) if cid not in logos]
        write(os.path.join(dst, f"{v}_customers.csv"), master_fields, out_master + extra)
        notes.append(f"{v}_customers.csv: the Actual customer master plus {len(extra)} {v}-only new logos (Active)")
    for name, fields, hist in ((HISTORY_FILE, HISTORY_FIELDS, h), ("Budget_customer_arr_history.csv", HISTORY_FIELDS, hb),
                               ("Forecast_customer_arr_history.csv", EXPECTED_FIELDS, hf)):
        hist.rows.sort(key=lambda r: (r["period"], r["customer_id"], r["movement_type"]))
        write(os.path.join(dst, name), fields, hist.rows)
    write(os.path.join(dst, "Actual_MRR_Waterfall.csv"), wf_fields, wf_rows)
    write(os.path.join(dst, "Forecast_MRR_Waterfall.csv"), fwf_fields, fwf_rows)
    write(os.path.join(dst, "Budget_MRR_Waterfall.csv"), bwf_fields, bwf_rows)
    for v, rows in pipelines.items():
        write(os.path.join(dst, f"{v}_pipeline_waterfall.csv"), PIPELINE_FIELDS, rows)
    write(os.path.join(dst, "Actual_renewal_pipeline.csv"), ren_fields, a_ren)
    write(os.path.join(dst, "Forecast_renewal_pipeline.csv"), ren_fields, f_ren)
    booking = pipeline_summaries(pipelines, {"Actual": W, "Forecast": WF, "Budget": WB}, {"Actual": a_ren, "Forecast": f_ren},
                                 CLOSE, {v: sorted(r["period"][:7] for r in ds.rows(f"{v}_bookings_summary.csv"))
                                         for v in ("Budget", "Forecast")})
    for v, rows in booking.items():
        write(os.path.join(dst, f"{v}_bookings_summary.csv"), ds.fields(f"{v}_bookings_summary.csv"), rows)
    notes.append("bookings summaries: " + "; ".join(
        f"{v} {len(rows)} months, weighted pipeline {rows[-1]['weighted_pipeline_arr']:,.2f} at {rows[-1]['period']}"
        for v, rows in booking.items()))
    write(os.path.join(dst, "Actual_renewal_commissions.csv"), com_fields, a_com)
    for v in VERSIONS:
        plan_fields, plans = ds.get(f"{v}_commission_plans.csv")
        if any(r["plan_id"] == RENEWAL_PLAN for r in plans):
            raise ValueError(f"{v}_commission_plans.csv already has {RENEWAL_PLAN}")
        plans.append({"organization_id": org, "plan_id": RENEWAL_PLAN, "role": "CSM",
                      "eligible_opportunity_type": "Renewal", "base_commission_rate": f"{ren_rate}",
                      "accelerator_multiplier": "1.0", "accelerator_threshold": "1.0", "accelerated_rate": f"{ren_rate}",
                      "clawback_window_months": "0"})
        write(os.path.join(dst, f"{v}_commission_plans.csv"), plan_fields, plans)

    info = {c: mrow[c] for c in mrow}
    for cid, o in logos.items():
        info[cid] = {"customer_name": o["customer_name"], "segment": actual_seg[cid], "industry": o["industry"],
                     "billing_state": o["customer_state"], "billing_terms": o["billing_terms"]}

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

    impl: dict[str, dict[str, Decimal]] = {v: defaultdict(Decimal) for v in VERSIONS}
    for v, fields, v_opps, to, keep in (("Actual", opp_fields, opps, {}, None),
                                        ("Budget", b_fields, b_opps, b_assign, None),
                                        ("Forecast", f_fields, f_opps, f_assign, {o["opportunity_id"] for o in f_opps})):
        before = {o["opportunity_id"]: o["region"] for o in v_opps}
        n_opp = repoint(v_opps, to)
        moved_region = sum(1 for o in v_opps if o["region"] != before[o["opportunity_id"]])
        mv_fields, mv = ds.get(f"{v}_opportunity_movements.csv")
        if keep is not None:
            dropped = {o["opportunity_id"] for o in f_all} - keep
            mv = [r for r in mv if r["opportunity_id"] not in dropped]
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
        seg_of[v].update(prospect_segments(v_opps + mv, seg_of[v]))
        for r in v_opps + mv:
            r["segment"] = seg_of[v][r["customer_id"]]
        write(os.path.join(dst, f"{v}_opportunities.csv"), fields, v_opps)
        write(os.path.join(dst, f"{v}_opportunity_movements.csv"), mv_fields, mv)
        if v != "Actual":
            notes.append(f"{v} opportunities: {n_opp} pointed at customers in the {v} history; {n_mv} matching "
                         f"movement rows; {moved_region} changed region (no in-region customer fit)")

        # implementation fee by segment; deal rows follow their opportunity's customer
        imp_fields, imp = ds.get(f"{v}_implementation_schedule.csv")
        before_fee = sum((num(r["implementation_fee"]) for r in imp if r["implementation_fee"]), ZERO)
        for r in imp:
            if r["source"] == f"{v}_opportunities.csv":
                o = by_id[r["source_record_id"]]
                r["customer_id"], r["customer_name"] = o["customer_id"], o["customer_name"]
            r["segment"] = seg_of[v][r["customer_id"]]
            r["implementation_fee"] = f"{q(FEE_BY_SEGMENT[r['segment']] * num(r['win_probability'])):.2f}"
            impl[v][r["period"][:7]] += num(r["implementation_fee"])
        write(os.path.join(dst, f"{v}_implementation_schedule.csv"), imp_fields, imp)
        notes.append(f"{v} implementation fees by segment: {len(imp)} rows, "
                     f"{before_fee:,.2f} -> {sum((num(r['implementation_fee']) for r in imp), ZERO):,.2f}")

    sched_fields = ds.fields("Actual_recurring_services_schedule.csv")
    for v, hist in (("Actual", h), ("Budget", hb), ("Forecast", hf)):
        periods = months if v == "Actual" else sorted({r["period"] for r in ds.rows(f"{v}_recurring_services_schedule.csv")})
        rows = []
        for p in periods:
            snap = hist.eop[p]
            for c in sorted(snap):
                rows.append({"organization_id": org, "version": v, "period": p, "customer_id": c,
                             "customer_name": h.info[c]["customer_name"], "segment": seg_of[v][c],
                             "weight_source": weight_source(v), "customer_arr": snap[c]})
        write(os.path.join(dst, f"{v}_recurring_services_schedule.csv"), sched_fields, rows)
    notes.append("revenue weights: each version's customer ARR history, month by month (Forecast: expected ARR)")

    # ---- revenue follows ARR in the simulated Actual months and the plans
    a_fields, a_rows = ds.get("Actual_income_statement.csv")
    ratio = recurring_ratio(a_rows, impl["Actual"], h.eop, window)
    notes.append(f"recurring revenue = {ratio:.4f} x customer ARR at the month end / 12 ({window[0]}..{window[-1]})")
    for v, hist, v_months in (("Actual", h, sim_months), ("Budget", hb, sorted(WB)), ("Forecast", hf, sorted(WF))):
        fields, rows = (a_fields, a_rows) if v == "Actual" else ds.get(f"{v}_income_statement.csv")
        sbc = {r["period"][:7]: r for r in ds.rows(f"{v}_SBC_Schedule.csv")}
        old, new = rebase(rows, sbc, impl[v], hist.eop, v_months, ratio)
        write(os.path.join(dst, f"{v}_income_statement.csv"), fields, rows)
        notes.append(f"{v} revenue {v_months[0]}..{v_months[-1]}: {old:,.2f} -> {new:,.2f} (cost lines keep their ratio "
                     f"to revenue on the cash part; stock comp unchanged)")

    rets = [r for r in h.rows if r["movement_type"] == "Reactivation" and r["period"] <= LAST_PRE_2026]
    above = sum(1 for r in returns if r["amount"] > r["baseline"])
    below = sum(1 for r in returns if r["amount"] < r["baseline"])
    notes.append(f"2024-2025 returns vs ARR left with: {above} above, {below} below, {len(rets) - above - below} equal")
    with open(os.path.join(dst, "customer_history_notes.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(notes) + "\n")
    return notes


if __name__ == "__main__":
    for line in build(sys.argv[1], sys.argv[2]):
        print(line)
