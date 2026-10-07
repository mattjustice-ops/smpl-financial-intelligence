"""Customer ARR history engine, plus the Budget and Forecast customer histories and renewal pipelines.

Used by build_customer_history.py (writes files only; never touches the database).

Rules (agreed with Matt, Oct 7 2026):
  * Budget starts from Actual customer ARR at Dec 2025 and Forecast from Actual at Jun 2026. Each plan
    month's deals land on customers, one customer each, and customer movements add up to that plan's ARR
    waterfall to the cent.
  * Budget is a plan: deals are booked at their full amount. Expansion, reactivation, contraction and churn
    deal amounts are scaled per month to the Budget waterfall (new business already ties). Budget churn
    customers hold their ARR flat in the Actual history until Dec 2025 so the plan churns exactly what they
    had.
  * Forecast is expected value: each deal moves its customer by its weighted ARR (probability x amount), and
    each renewal due moves its customer by renewal ARR x (1 - renewal probability). Forecast rows carry the
    probability and the full opportunity ARR. A Forecast churn deal is the customer's whole ARR; the month's
    last churn deal takes the cents so churn deals plus expected renewal lapses equal waterfall churn.
  * Returns follow the Actual rules: a restart after a pause (no time limit) or a winback within 6 months of
    churning; about 20% of each plan's reactivation ARR is winbacks. A restart goes to a paused customer
    whose ARR left with is closest to the deal.
  * Renewal pipeline: a customer is due in its anniversary month (customer start month) once it has been a
    customer for 12 months since it last started; renewal ARR is its ARR at the end of the prior month.
    Customers with a churn deal that month are not in the renewal pipeline (they are leaving instead).
  * Segment is the customer's ARR at signing: Enterprise $500k+, Mid-Market $100k-$500k, SMB below $100k.
    Customers that signed before the history starts use the earliest ARR on record; a prospect uses its
    first New Business deal.
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_v5_dataset import ZERO, allocate, num, padd, pidx, prange, q, stable_unit  # noqa: E402

HISTORY_FIELDS = ["organization_id", "version", "period", "customer_id", "customer_name", "segment", "movement_type",
                  "beginning_arr", "movement_arr", "ending_arr", "waterfall_column", "opportunity_id", "note"]
EXPECTED_FIELDS = HISTORY_FIELDS + ["probability", "opportunity_arr"]
COLUMN = {"New Business": "new_business_arr", "Expansion": "expansion_arr", "Reactivation": "reactivation_arr",
          "Contraction": "contraction_arr", "Churn": "churn_arr", "Pause": "churn_arr", "Opening balance": ""}
WF_COLUMNS = ("new_business_arr", "expansion_arr", "reactivation_arr", "contraction_arr", "churn_arr")
DEAL_TYPES = ("New Business", "Expansion", "Reactivation", "Contraction", "Churn")
BOOKED = {"New Business": "Closed Won", "Expansion": "Closed Won", "Reactivation": "Closed Won",
          "Contraction": "Contraction", "Churn": "Churn"}
WINBACK_WINDOW = 6
WINBACK_SHARE = Decimal("0.20")
CONTRACTION_CAP = Decimal("0.6")
FORECAST_RENEWAL_PROBABILITY = Decimal("0.95")
SEGMENT_FLOORS = (("Enterprise", Decimal(500000)), ("Mid-Market", Decimal(100000)), ("SMB", ZERO))


def segment_for(arr: Decimal) -> str:
    return next(name for name, floor in SEGMENT_FLOORS if arr >= floor)


def signing_arr(rows: list[dict]) -> dict[str, Decimal]:
    """Each customer's ARR at signing: after its first New Business or opening balance, or what it left with
    when its first row is a departure from before the history."""
    first: dict[str, Decimal] = {}
    for r in sorted(rows, key=lambda r: r["period"]):
        c = r["customer_id"]
        if c not in first:
            first[c] = num(r["beginning_arr"]) if r["movement_type"] in ("Churn", "Pause") else num(r["ending_arr"])
    return first


def prospect_segments(opps: list[dict], known: dict[str, str]) -> dict[str, str]:
    """Customers not in the history: segment of their first New Business deal (full amount)."""
    out: dict[str, str] = {}
    for o in sorted(opps, key=lambda o: (o["period"], o["opportunity_id"])):
        c = o["customer_id"]
        if c in known or c in out:
            continue
        if o["opportunity_type"] != "New Business":
            raise ValueError(f"{o['opportunity_id']}: {o['opportunity_type']} on {c}, which has no ARR history")
        out[c] = segment_for(num(o["amount_arr"]))
    return out


def u(key: str) -> Decimal:
    return stable_unit(key)


def pick(cands: list[str], n: int, key: str, weight) -> list[str]:
    """Deterministic weighted sample without replacement (Efraimidis-Spirakis)."""
    def score(c: str) -> float:
        w = float(weight(c)) or 1e-9
        return (float(u(f"{key}|{c}")) + 1e-6) ** (1.0 / w)
    return sorted(cands, key=lambda c: (-score(c), c))[:n]


class History:
    """One version's customer ARR, month by month. ``expected`` (Forecast): churn need not leave zero, and rows
    carry the deal probability and full opportunity ARR."""

    def __init__(self, org: str, version: str = "Actual", expected: bool = False):
        self.org, self.version, self.expected = org, version, expected
        self.arr: dict[str, Decimal] = defaultdict(lambda: ZERO)
        self.rows: list[dict] = []
        self.info: dict[str, dict[str, str]] = {}
        self.eop: dict[str, dict[str, Decimal]] = {}
        self.moved: dict[str, set[str]] = defaultdict(set)

    def move(self, p: str, cid: str, kind: str, amount: Decimal, opp: str = "", note: str = "",
             probability: Decimal | None = None, full: Decimal | None = None) -> None:
        begin = self.arr[cid]
        delta = -amount if kind in ("Contraction", "Churn", "Pause") else amount
        end = begin + delta
        if amount <= 0 or end < 0:
            raise ValueError(f"{self.version} {p} {cid} {kind} {amount}: ARR {begin} would become {end}")
        if kind in ("Churn", "Pause") and end != 0 and not self.expected:
            raise ValueError(f"{self.version} {p} {cid} {kind} leaves {end}")
        if kind in ("New Business", "Reactivation") and begin != 0:
            raise ValueError(f"{self.version} {p} {cid} {kind} while active ({begin})")
        if cid in self.moved[p]:
            raise ValueError(f"{self.version} {p} {cid}: second movement in the month")
        self.moved[p].add(cid)
        self.arr[cid] = end
        i = self.info[cid]
        row = {"organization_id": self.org, "version": self.version, "period": p, "customer_id": cid,
               "customer_name": i["customer_name"], "segment": i["segment"], "movement_type": kind,
               "beginning_arr": begin, "movement_arr": delta, "ending_arr": end,
               "waterfall_column": COLUMN[kind], "opportunity_id": opp, "note": note}
        if self.expected:
            row["probability"] = "" if probability is None else f"{probability.normalize():f}"
            row["opportunity_arr"] = full if full is not None else amount
        self.rows.append(row)

    def open(self, cid: str, amount: Decimal, period: str, note: str) -> None:
        self.arr[cid] = amount
        i = self.info[cid]
        row = {"organization_id": self.org, "version": self.version, "period": period, "customer_id": cid,
               "customer_name": i["customer_name"], "segment": i["segment"],
               "movement_type": "Opening balance", "beginning_arr": amount, "movement_arr": ZERO,
               "ending_arr": amount, "waterfall_column": "", "opportunity_id": "", "note": note}
        if self.expected:
            row["probability"], row["opportunity_arr"] = "", ""
        self.rows.append(row)

    def close_month(self, p: str) -> None:
        self.eop[p] = {c: a for c, a in self.arr.items() if a > 0}


def waterfall(rows: list[dict]) -> dict[str, dict[str, Decimal]]:
    return {r["period"][:7]: {k: num(r[k]) for k in (*WF_COLUMNS, "beginning_arr", "ending_arr")} for r in rows}


def tie(h: History, W: dict[str, dict[str, Decimal]], months: list[str], opening: Decimal) -> str:
    """Every month, every movement column to the cent; ending ARR within the waterfall's own rounding (5 cents, or
    under a dollar where the waterfall states ending ARR in whole dollars)."""
    by = defaultdict(lambda: defaultdict(lambda: ZERO))
    for r in h.rows:
        if r["waterfall_column"]:
            by[r["period"]][r["waterfall_column"]] += abs(r["movement_arr"])
    bad, wf_rounding, worst = [], ZERO, ZERO
    for p in months:
        for col in WF_COLUMNS:
            if by[p][col] != W[p][col]:
                bad.append(f"{p} {col} {by[p][col]} vs {W[p][col]}")
        w = W[p]
        own = w["ending_arr"] - (w["beginning_arr"] + w["new_business_arr"] + w["expansion_arr"] + w["reactivation_arr"]
                                 - w["contraction_arr"] - w["churn_arr"])
        wf_rounding = max(wf_rounding, abs(own))
        diff = abs(sum(h.eop[p].values(), ZERO) - w["ending_arr"])
        worst = max(worst, diff)
        tol = Decimal("0.99") if w["ending_arr"] == w["ending_arr"].to_integral_value() else Decimal("0.05")
        if abs(own) > tol or diff > tol:
            bad.append(f"{p} ending {sum(h.eop[p].values(), ZERO)} vs {w['ending_arr']} (waterfall's own rounding {own})")
    if opening != W[months[0]]["beginning_arr"]:
        bad.append(f"opening {opening} vs {W[months[0]]['beginning_arr']}")
    if bad:
        raise ValueError(f"{h.version} history does not tie to the waterfall: " + "; ".join(bad[:10]))
    return (f"{h.version} ties: {len(months)} months x 5 movement columns and opening ARR to the cent; ending ARR within "
            f"{worst} (the waterfall's own ending ARR differs from beginning + movements by up to {wf_rounding})")


def departures_at(rows: list[dict], through: str) -> dict[str, tuple[str, str, Decimal]]:
    """Customers out at ``through``: customer -> (Churn or Pause, month left, ARR left with)."""
    out: dict[str, tuple[str, str, Decimal]] = {}
    for r in sorted(rows, key=lambda r: r["period"]):
        if r["period"] > through:
            break
        c, kind = r["customer_id"], r["movement_type"]
        if kind in ("Churn", "Pause") and num(r["ending_arr"]) == 0:
            out[c] = (kind, r["period"], num(r["beginning_arr"]))
        elif kind in ("Reactivation", "New Business"):
            out.pop(c, None)
    return out


def last_starts(rows: list[dict], start: dict[str, str]) -> dict[str, str]:
    """Month each customer last started (customer start, or its latest new business / reactivation)."""
    out = dict(start)
    for r in rows:
        if r["movement_type"] in ("Reactivation", "New Business"):
            out[r["customer_id"]] = max(out.get(r["customer_id"], ""), r["period"])
    return out


# ----------------------------------------------------------------------------- plan deals


def tie_budget_deals(opps: list[dict], W: dict[str, dict[str, Decimal]], notes: list[str]) -> None:
    """Budget deal amounts per month and type = the Budget waterfall (new business already ties)."""
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for o in opps:
        if BOOKED.get(o["opportunity_type"]) == o["close_status"]:
            groups[(o["period"][:7], o["opportunity_type"])].append(o)
    factors = []
    for (p, t), rows in sorted(groups.items()):
        target = W[p][COLUMN[t]]
        before = sum((num(o["amount_arr"]) for o in rows), ZERO)
        if t == "New Business" and abs(before - target) > Decimal("0.05"):
            raise ValueError(f"Budget {p} new business deals {before} vs waterfall {target}")
        new = allocate(target, [(o["opportunity_id"], num(o["amount_arr"])) for o in rows])
        for o in rows:
            a = new[o["opportunity_id"]]
            o["amount_arr"] = f"{a:.2f}"
            o["weighted_arr"] = f"{q(a * num(o['probability'])):.2f}"
        if t != "New Business":
            factors.append(target / before)
    missing = [f"{p} {t}" for p in sorted(W) for t in DEAL_TYPES if W[p][COLUMN[t]] and (p, t) not in groups]
    if missing:
        raise ValueError(f"Budget waterfall movements without deals: {missing}")
    notes.append(f"Budget deals: amounts scaled per month to the Budget waterfall ({len(factors)} month-type groups, "
                 f"x{min(factors):.3f}..x{max(factors):.3f}); weighted = amount x probability; new business unchanged")


def forecast_deals(opps: list[dict], W: dict[str, dict[str, Decimal]], first: str, notes: list[str]) -> list[dict]:
    """Forecast deals from ``first``; weighted ARR per month and type (churn aside) = the waterfall to the cent."""
    dropped = [o for o in opps if o["period"][:7] < first]
    keep = [o for o in opps if o["period"][:7] >= first]
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for o in keep:
        groups[(o["period"][:7], o["opportunity_type"])].append(o)
    cents = []
    for (p, t), rows in sorted(groups.items()):
        if t == "Churn":
            continue
        diff = W[p][COLUMN[t]] - sum((num(o["weighted_arr"]) for o in rows), ZERO)
        if abs(diff) > Decimal("0.05"):
            raise ValueError(f"Forecast {p} {t}: weighted deals differ from the waterfall by {diff}")
        if diff:
            top = max(rows, key=lambda o: (num(o["weighted_arr"]), o["opportunity_id"]))
            top["weighted_arr"] = f"{num(top['weighted_arr']) + diff:.2f}"
            cents.append(f"{top['opportunity_id']} {diff:+}")
    notes.append(f"Forecast deals: {len(dropped)} rows before {first} removed (that month is Actual); weighted cents moved "
                 f"to the waterfall: {', '.join(cents) or 'none'}")
    return keep


# ----------------------------------------------------------------------------- plan histories


class Plan:
    """Shared state for simulating one plan version."""

    def __init__(self, h: History, deals: list[dict], region, anniv, start_of, departed, logo_ids: set[str]):
        self.h, self.deals = h, deals
        self.region, self.anniv = region, anniv
        self.start_of = dict(start_of)
        self.departed = dict(departed)
        self.logos = logo_ids
        self.assign: dict[str, str] = {}
        self.no_more: set[str] = set()
        self.returned: list[dict] = []

    def in_region(self, cands: list[str], o: dict) -> list[str]:
        return [c for c in cands if self.region(c) == o["region"]] or cands

    def active(self, p: str, extra=lambda c: True) -> list[str]:
        h = self.h
        return [c for c in sorted(h.arr) if h.arr[c] > 0 and c not in h.moved[p] and c not in self.logos
                and c not in self.no_more and extra(c)]

    def reactivation_kinds(self) -> dict[str, str]:
        out, wb, tot = {}, ZERO, ZERO
        for o in sorted((o for o in self.deals if o["opportunity_type"] == "Reactivation"),
                        key=lambda o: (o["period"], o["opportunity_id"])):
            a = num(o["amount_arr"])
            tot += a
            kind = "winback" if wb + a <= WINBACK_SHARE * tot + Decimal("15000") and wb < WINBACK_SHARE * tot else "restart"
            if kind == "winback":
                wb += a
            out[o["opportunity_id"]] = kind
        return out

    def returner(self, p: str, o: dict, kind: str) -> tuple[str, str]:
        a = num(o["amount_arr"])

        def cands(k: str) -> list[str]:
            if k == "winback":
                return [c for c, (dk, dp, _) in self.departed.items()
                        if dk == "Churn" and 1 <= pidx(p) - pidx(dp) <= WINBACK_WINDOW]
            return [c for c, (dk, _, _) in self.departed.items() if dk == "Pause"]

        pool = cands(kind)
        if not pool:
            kind = "restart" if kind == "winback" else "winback"
            pool = cands(kind)
        if not pool:
            raise ValueError(f"{self.h.version} {p} {o['opportunity_id']}: no paused or recently churned customer to return")
        pool = self.in_region(sorted(pool), o)
        c = min(pool, key=lambda c: (abs(self.departed[c][2] - a), c))
        return c, kind


def _months_of(deals: list[dict]) -> list[str]:
    return sorted({o["period"][:7] for o in deals})


def _by_month(deals: list[dict], p: str, t: str) -> list[dict]:
    return sorted((o for o in deals if o["period"][:7] == p and o["opportunity_type"] == t), key=lambda o: o["opportunity_id"])


def _day(date: str) -> int:
    """Day of month from 2026-04-28 or 6/28/2026."""
    return int(date.split("/")[1]) if "/" in date else int(date.split("-")[2])


def simulate_budget(org: str, info: dict, opening: dict[str, Decimal], open_period: str, actual_rows: list[dict],
                    deals: list[dict], W: dict, churn_pins: dict[str, str], region, anniv, start_of,
                    notes: list[str]) -> tuple[History, dict[str, str]]:
    h = History(org, "Budget")
    h.info = info
    for c in sorted(opening):
        h.open(c, opening[c], open_period, f"Actual ARR at {open_period} (the Budget starts from the Actual close)")
    logos = {o["customer_id"] for o in deals if o["opportunity_type"] == "New Business"}
    s = Plan(h, deals, region, anniv, last_starts([r for r in actual_rows if r["period"] <= open_period], start_of),
             departures_at(actual_rows, open_period), logos)
    pinned = set(churn_pins.values())
    kinds = s.reactivation_kinds()
    counts = defaultdict(int)
    for p in _months_of(deals):
        for o in _by_month(deals, p, "Churn"):
            c, a = churn_pins[o["opportunity_id"]], num(o["amount_arr"])
            if h.arr[c] != a:
                raise ValueError(f"Budget {p} {o['opportunity_id']}: {c} has {h.arr[c]}, churn deal {a}")
            h.move(p, c, "Churn", a, o["opportunity_id"])
            s.assign[o["opportunity_id"]] = c
            s.departed[c] = ("Churn", p, a)
            pinned.discard(c)
        for o in sorted(_by_month(deals, p, "Contraction"), key=lambda o: (-num(o["amount_arr"]), o["opportunity_id"])):
            a = num(o["amount_arr"])
            cands = s.active(p, lambda c: c not in pinned and h.arr[c] * CONTRACTION_CAP >= a)
            if not cands:
                raise ValueError(f"Budget {p} {o['opportunity_id']}: no customer large enough to contract {a}")
            c = pick(s.in_region(cands, o), 1, f"bcon|{o['opportunity_id']}", lambda c: h.arr[c])[0]
            h.move(p, c, "Contraction", a, o["opportunity_id"])
            s.assign[o["opportunity_id"]] = c
        for o in _by_month(deals, p, "Reactivation"):
            c, kind = s.returner(p, o, kinds[o["opportunity_id"]])
            dp = s.departed.pop(c)[1]
            h.move(p, c, "Reactivation", num(o["amount_arr"]), o["opportunity_id"],
                   f"{kind} after {pidx(p) - pidx(dp)} months away")
            s.assign[o["opportunity_id"]] = c
            s.no_more.add(c)
            counts[kind] += 1
        for o in _by_month(deals, p, "New Business"):
            h.move(p, o["customer_id"], "New Business", num(o["amount_arr"]), o["opportunity_id"])
        for o in sorted(_by_month(deals, p, "Expansion"), key=lambda o: (-num(o["amount_arr"]), o["opportunity_id"])):
            a = num(o["amount_arr"])
            cands = s.active(p, lambda c: c not in pinned and h.arr[c] >= a)
            if not cands:
                raise ValueError(f"Budget {p} {o['opportunity_id']}: no customer large enough to expand {a}")
            c = pick(s.in_region(cands, o), 1, f"bexp|{o['opportunity_id']}", lambda c: h.arr[c])[0]
            h.move(p, c, "Expansion", a, o["opportunity_id"])
            s.assign[o["opportunity_id"]] = c
        h.close_month(p)
    notes.append(tie(h, W, _months_of(deals), sum(opening.values(), ZERO)))
    notes.append(f"Budget returns: {counts['winback']} winbacks, {counts['restart']} restarts")
    return h, s.assign


def renewal_due(p: str, snap: dict[str, Decimal], anniv, last_start: dict[str, str], skip: set[str]) -> list[str]:
    return [c for c in sorted(snap) if snap[c] > 0 and anniv(c) == p[5:7] and c not in skip
            and pidx(last_start.get(c, p)) <= pidx(p) - 12]


def simulate_forecast(org: str, info: dict, opening: dict[str, Decimal], open_period: str, actual_rows: list[dict],
                      deals: list[dict], W: dict, region, anniv, start_of,
                      notes: list[str]) -> tuple[History, dict[str, str], list[dict]]:
    """Returns the history, deal -> customer, and the renewal pipeline (customer, month, renewal ARR, renewal id)."""
    h = History(org, "Forecast", expected=True)
    h.info = info
    for c in sorted(opening):
        h.open(c, opening[c], open_period, f"Actual ARR at {open_period} (the Forecast starts from the Actual close)")
    logos = {o["customer_id"] for o in deals if o["opportunity_type"] == "New Business"}
    s = Plan(h, deals, region, anniv, last_starts([r for r in actual_rows if r["period"] <= open_period], start_of),
             departures_at(actual_rows, open_period), logos)
    kinds = s.reactivation_kinds()
    counts = defaultdict(int)
    touched: set[str] = set()
    renewals: list[dict] = []
    off = []
    for p in _months_of(deals):
        prev = dict(h.arr)
        churn = _by_month(deals, p, "Churn")
        lapse_est = sum((prev[c] for c in renewal_due(p, prev, anniv, s.start_of, s.no_more)), ZERO) \
            * (1 - FORECAST_RENEWAL_PROBABILITY)
        target_est = W[p]["churn_arr"] - lapse_est
        orig_w = sum((num(o["weighted_arr"]) for o in churn), ZERO)
        chosen: list[tuple[dict, str]] = []

        def churn_cands(o: dict, extra=lambda c: True) -> list[str]:
            cands = [c for c in s.active(p, lambda c: c not in touched and extra(c)) if c not in {x for _, x in chosen}]
            return s.in_region(cands, o)

        for o in churn[:-1]:
            want = num(o["amount_arr"]) * target_est / orig_w
            cands = churn_cands(o)
            cands = [c for c in cands if anniv(c) == p[5:7]] or cands
            chosen.append((o, min(cands, key=lambda c: (abs(h.arr[c] - want), c))))
        skip = s.no_more | {c for _, c in chosen}
        due = renewal_due(p, prev, anniv, s.start_of, skip)
        lapse = ZERO
        for i, c in enumerate(due, 1):
            ren_arr = prev[c]
            amt = q(ren_arr * (1 - FORECAST_RENEWAL_PROBABILITY))
            rid = f"FREN-{p[5:7]}-{i:03d}"
            renewals.append({"customer_id": c, "period": p, "renewal_arr": ren_arr, "renewal_id": rid})
            h.move(p, c, "Churn", amt, rid,
                   f"renewal {rid} expected to lapse (renewal probability {FORECAST_RENEWAL_PROBABILITY})",
                   1 - FORECAST_RENEWAL_PROBABILITY, ren_arr)
            touched.add(c)
            lapse += amt
        rem = W[p]["churn_arr"] - lapse
        for o, c in chosen:
            w = q(num(o["probability"]) * h.arr[c])
            rem -= w
            o["amount_arr"], o["weighted_arr"] = f"{h.arr[c]:.2f}", f"{w:.2f}"
        last = churn[-1]
        pr = num(last["probability"])
        cands = [c for c in churn_cands(last) if h.arr[c] >= rem]
        if rem <= 0 or not cands:
            raise ValueError(f"Forecast {p}: churn deals must carry {rem} after renewal lapses {lapse}")
        c = min(cands, key=lambda c: (abs(pr * h.arr[c] - rem), c))
        chosen.append((last, c))
        last["amount_arr"], last["weighted_arr"] = f"{h.arr[c]:.2f}", f"{rem:.2f}"
        off.append(rem / h.arr[c] - pr)
        for o, c in chosen:
            full, w = num(o["amount_arr"]), num(o["weighted_arr"])
            h.move(p, c, "Churn", w, o["opportunity_id"], "", num(o["probability"]), full)
            s.assign[o["opportunity_id"]] = c
            s.no_more.add(c)
        for o in sorted(_by_month(deals, p, "Contraction"), key=lambda o: (-num(o["amount_arr"]), o["opportunity_id"])):
            a, w = num(o["amount_arr"]), num(o["weighted_arr"])
            cands = s.active(p, lambda c: h.arr[c] * CONTRACTION_CAP >= a)
            if not cands:
                raise ValueError(f"Forecast {p} {o['opportunity_id']}: no customer large enough to contract {a}")
            c = pick(s.in_region(cands, o), 1, f"fcon|{o['opportunity_id']}", lambda c: h.arr[c])[0]
            h.move(p, c, "Contraction", w, o["opportunity_id"], "", num(o["probability"]), a)
            s.assign[o["opportunity_id"]] = c
            touched.add(c)
        for o in _by_month(deals, p, "Reactivation"):
            c, kind = s.returner(p, o, kinds[o["opportunity_id"]])
            dp = s.departed.pop(c)[1]
            h.move(p, c, "Reactivation", num(o["weighted_arr"]), o["opportunity_id"],
                   f"{kind} after {pidx(p) - pidx(dp)} months away", num(o["probability"]), num(o["amount_arr"]))
            s.assign[o["opportunity_id"]] = c
            s.no_more.add(c)
            counts[kind] += 1
        for o in _by_month(deals, p, "New Business"):
            h.move(p, o["customer_id"], "New Business", num(o["weighted_arr"]), o["opportunity_id"], "",
                   num(o["probability"]), num(o["amount_arr"]))
        for o in sorted(_by_month(deals, p, "Expansion"), key=lambda o: (-num(o["amount_arr"]), o["opportunity_id"])):
            a, w = num(o["amount_arr"]), num(o["weighted_arr"])
            cands = s.active(p, lambda c: h.arr[c] >= a)
            if not cands:
                raise ValueError(f"Forecast {p} {o['opportunity_id']}: no customer large enough to expand {a}")
            c = pick(s.in_region(cands, o), 1, f"fexp|{o['opportunity_id']}", lambda c: h.arr[c])[0]
            h.move(p, c, "Expansion", w, o["opportunity_id"], "", num(o["probability"]), a)
            s.assign[o["opportunity_id"]] = c
            touched.add(c)
        h.close_month(p)
    notes.append(tie(h, W, _months_of(deals), sum(opening.values(), ZERO)))
    notes.append(f"Forecast returns: {counts['winback']} winbacks, {counts['restart']} restarts; renewals due "
                 f"{len(renewals)} (renewal ARR {sum((r['renewal_arr'] for r in renewals), ZERO):,.2f}); each month's "
                 f"last churn deal weighted at {min(off):+.3f}..{max(off):+.3f} of its probability x ARR")
    return h, s.assign, renewals


# ----------------------------------------------------------------------------- renewal pipeline


def renewal_rows(org: str, version: str, due: list[dict], donors: list[dict], by_customer: dict[str, dict],
                 info: dict, fixed: dict[str, str] | None = None) -> list[dict]:
    """Renewal pipeline rows. Scores, CSM and auto-renew come from the customer's earlier renewal row when there is
    one, otherwise from an existing row picked by hash; ``fixed`` overrides fields (Forecast probability and stage)."""
    out = []
    for r in due:
        c, p = r["customer_id"], r["period"]
        d = by_customer.get(c) or donors[int(u(f"rendonor|{version}|{c}|{p}") * len(donors))]
        day = _day(d["renewal_due_date"])
        row = {"organization_id": org, "renewal_id": r["renewal_id"], "customer_id": c,
               "customer_name": info[c]["customer_name"], "renewal_period": p,
               "renewal_due_date": f"{p}-{min(day, 28):02d}", "renewal_arr": f"{r['renewal_arr']:.2f}",
               "renewal_probability": d["renewal_probability"], "renewal_risk_score": d["renewal_risk_score"],
               "customer_health_score": d["customer_health_score"], "expected_uplift_pct": "0",
               "expected_post_renewal_arr": f"{r['renewal_arr']:.2f}", "auto_renew_flag": d["auto_renew_flag"],
               "customer_success_manager": d["customer_success_manager"], "renewal_stage": d["renewal_stage"],
               "version": version}
        row.update(fixed or {})
        out.append(row)
    return out


def actual_renewals(h: History, months: list[str], anniv, start_of: dict[str, str], churn_by_month: dict[str, set[str]]) -> list[dict]:
    """Actual renewals due: anniversary month, at least 12 months since the customer last started, not churning."""
    starts = dict(start_of)
    out = []
    for p in months:
        for r in h.rows:
            if r["period"] < p and r["movement_type"] in ("Reactivation", "New Business"):
                starts[r["customer_id"]] = max(starts.get(r["customer_id"], ""), r["period"])
        snap = h.eop[padd(p, -1)]
        for c in renewal_due(p, snap, anniv, starts, churn_by_month.get(p, set())):
            out.append({"customer_id": c, "period": p, "renewal_arr": snap[c], "renewal_id": ""})
    for n, r in enumerate(out, 1):
        r["renewal_id"] = f"REN-{n:06d}"
    return out


def renewal_commissions(org: str, rows: list[dict], rep_of: dict[str, str], rate: Decimal, last_day) -> list[dict]:
    out = []
    for n, r in enumerate(rows, 1):
        booked = num(r["renewal_arr"])
        p = r["renewal_period"]
        out.append({"organization_id": org, "version": "Actual", "commission_id": f"COMM-REN-{n:06d}", "period": p,
                    "rep_id": rep_of[r["customer_success_manager"]], "rep_name": r["customer_success_manager"],
                    "opportunity_id": f"OPP-{r['renewal_id']}", "customer_id": r["customer_id"],
                    "booked_arr": f"{booked:.2f}", "commission_rate": f"{rate}", "commission_amount": f"{q(booked * rate):.2f}",
                    "payout_date": last_day(p).isoformat(), "clawback_flag": "No", "plan_id": "PLAN-RENEWAL"})
    return out
