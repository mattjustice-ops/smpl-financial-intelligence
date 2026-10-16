"""Rebuild the opportunity movements behind every pipeline waterfall cell, deal by deal.

  python rebuild_opportunity_movements.py <dataset_folder> <out_folder>

Copies <dataset_folder> to <out_folder> and rewrites <version>_opportunity_movements.csv for every version and the
pipeline validation files; pipeline_deals_log.csv keeps its entries for other files and gets this run's. Run it
after rebuild_marketing_funnel.py.

Each row is one event on one deal: Pipeline Created, Closed Won, Closed Lost or Slipped Pipeline (the booking types
New Business, Expansion and Reactivation), or the Contraction / Churn deal itself. For every version, month and
booking type the rows of a label add up to the pipeline waterfall cell (<version>_pipeline_waterfall.csv) to the
cent, so the dashboard drill-down ties to the cell it opens from.

Rules:
  * Months: Actual from its first CRM month (Actual_opportunities.csv) to the close; Budget its plan year; Forecast
    the months after the close. A closed month stays on Actual. Earlier Actual months have no deal detail
    in the CRM export.
  * Closed Won: the version's deals of the type closed that month (<version>_opportunities.csv) with their owner,
    customer and channel; Actual and Budget at their ARR, Forecast at expected ARR (weighted), as its waterfall.
    Contraction and Churn rows are the version's deals of those types.
  * New Business pipeline created runs channel by channel from the marketing pipeline
    (<version>_marketing_pipeline.csv); closed lost and slipped are the waterfall's, taken from the open deals of
    any channel, and in the CRM months the Actual marketing pipeline's lost, slipped, beginning and ending by channel
    are restated to those deals. Expansion and Reactivation that are not a named deal are one waterfall
    cell, so the unattributed remainder is carried as Customer Success. A named deal keeps its own
    marketing channel on every movement row. A new-business customer can expand intra-contract; that
    stays type Expansion, on that customer, and is not recategorized as New Business.
  * Pipeline Created: the deals created that month. A deal that closes in the months shown is created in its
    created month (a created month before them puts it in the beginning pipeline); the rest of the month's
    pipeline is new pipeline-only deals. New Business creates exactly the month's opportunities_created deals in
    the channel; Expansion and Reactivation one per average Actual deal of the type (at least one). Pipeline-only
    amounts vary deal to deal around the month's average and add up to it to the cent.
  * The pipeline open at the start: the Actual pipeline waterfall's beginning (New Business: by channel from the
    marketing pipeline), less the deals that close later, as deals at the average Actual deal size, created in the
    months before as the Actual marketing pipeline created them (latest first). Budget begins from the same deals;
    Forecast from the deals still open at the close.
  * Closed Lost and Slipped Pipeline take the open pipeline-only deals whose ARR comes closest to the month's
    amount (oldest on a tie), leaving at least one deal open while pipeline remains; the amounts then move pro
    rata to add up to it and the deals left open in each channel to its remaining balance (ARR changes while a
    deal is worked). A deal is split in two when the month needs more deals than are open.
    Lost deals close at probability 0; created and slipped deals carry the version's win rate of the type
    (won / (won + lost) over its months).
  * Pipeline-only deals: New Business on new prospects (CUST IDs above every customer and deal ID; names from the
    customer file's words; territory, industry, state and billing from the channel's Actual deals); Expansion on
    active customers, Reactivation on churned or paused ones (the version's customer file). Owners are AEs on the
    version's staff that month, round-robin in the deal's territory (any territory when it has none).
    Segment is the band of the deal's first ARR in the version.
"""

from __future__ import annotations

import calendar
import datetime as dt
import os
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from decimal import ROUND_HALF_UP, Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_v5_dataset import allocate, padd, prange, stable_unit  # noqa: E402
from customer_history_plans import segment_for  # noqa: E402
from sales_team import BOOKINGS_ROLES, active  # noqa: E402
from sync_v5_statements import ZERO, num, q, read, write  # noqa: E402

CLOSE = "2026-06"
VERSIONS = ("Actual", "Budget", "Forecast")
BOOKING = ("New Business", "Expansion", "Reactivation")
NB = "New Business"
CS_CHANNEL = "Customer Success"
PREFIX = {"Actual": "ACT", "Budget": "BUD", "Forecast": "FOR"}
CREATED, WON, LOST, SLIPPED = "Pipeline Created", "Closed Won", "Closed Lost", "Slipped Pipeline"
WF = {CREATED: "new_pipeline_created", WON: "closed_won_arr", LOST: "closed_lost_arr", SLIPPED: "slipped_arr"}
DEPARTED = ("Churned", "Paused")
COPY = ("customer_id", "customer_name", "customer_state", "region", "segment", "industry", "billing_cadence",
        "billing_terms", "contract_term_months", "marketing_channel", "owner")


@dataclass
class Deal:
    id: str
    type: str
    channel: str
    created: dt.date
    amount: Decimal
    attrs: dict[str, str]
    known: dict[str, str] | None = None
    exit: tuple[str, str, Decimal] | None = None
    owner_by: dict[str, str] = field(default_factory=dict)
    current: Decimal | None = None

    def __post_init__(self) -> None:
        if self.current is None:
            self.current = self.amount


def month(d: str) -> str:
    return d[:7]


def day_in(p: str, key: str, not_before: dt.date | None = None) -> dt.date:
    y, m = int(p[:4]), int(p[5:7])
    last = calendar.monthrange(y, m)[1]
    first = not_before.day if not_before and not_before.year == y and not_before.month == m else 1
    return dt.date(y, m, first + int(stable_unit(key) * (last - first + 1)))


def last_day(p: str) -> dt.date:
    y, m = int(p[:4]), int(p[5:7])
    return dt.date(y, m, calendar.monthrange(y, m)[1])


def add_months(d: dt.date, n: int) -> dt.date:
    i = d.year * 12 + d.month - 1 + n
    y, m = divmod(i, 12)
    return dt.date(y, m + 1, min(d.day, calendar.monthrange(y, m + 1)[1]))


def ratio(a: Decimal, b: Decimal, places: str = "0.01") -> str:
    return f"{(a / b).quantize(Decimal(places), ROUND_HALF_UP)}" if b else ""


def spread(total: Decimal, n: int, key: str) -> list[Decimal]:
    """``n`` amounts around total / n that add up to it to the cent."""
    if n <= 0:
        return []
    got = allocate(total, [(str(i), Decimal("0.6") + stable_unit(f"{key}|{i}") * Decimal("0.8")) for i in range(n)])
    return [got[str(i)] for i in range(n)]


class Ids:
    def __init__(self, path) -> None:
        self.next_opp = {}
        for v in VERSIONS:
            ids = [r["opportunity_id"] for r in read(path(f"{v}_opportunities.csv"))[1]]
            self.next_opp[v] = max(int(i.rsplit("-", 1)[1]) for i in ids) + 1
        seen = [r["customer_id"] for v in VERSIONS for name in (f"{v}_customers.csv", f"{v}_opportunities.csv")
                for r in read(path(name))[1]]
        self.next_cust = max(int(c.split("-")[1]) for c in seen) + 1
        names = [r["customer_name"].rsplit(" ", 1)[0].split(" ") for r in read(path("Actual_customers.csv"))[1]]
        self.first = sorted({n[0] for n in names if len(n) == 2})
        self.second = sorted({n[1] for n in names if len(n) == 2})
        if not self.first or not self.second:
            raise SystemExit("Actual_customers.csv: no two-word customer names to name prospects from")

    def opp(self, v: str) -> str:
        n = self.next_opp[v]
        self.next_opp[v] += 1
        return f"{PREFIX[v]}-OPP-{n}"

    def prospect(self) -> tuple[str, str]:
        n = self.next_cust
        self.next_cust += 1
        cid = f"CUST-{n:05d}"
        a = self.first[int(stable_unit(f"{cid}|a") * len(self.first))]
        b = self.second[int(stable_unit(f"{cid}|b") * len(self.second))]
        return cid, f"{a} {b} {n}"


class Owners:
    """AEs on each version's staff, round-robin by month and territory."""

    def __init__(self, path) -> None:
        self.staff = {v: sorted((e for e in read(path(f"{v}_Employees.csv"))[1] if e["role"] in BOOKINGS_ROLES),
                                key=lambda e: e["employee_id"]) for v in VERSIONS}
        self.turn: Counter = Counter()

    def valid(self, v: str, name: str, p: str) -> bool:
        return any(e["employee_name"] == name and active(e, p) for e in self.staff[v])

    def pick(self, v: str, p: str, region: str) -> str:
        on = [e for e in self.staff[v] if active(e, p)]
        if not on:
            raise SystemExit(f"{v} {p}: no AE on staff")
        local = [e for e in on if e["region"] == region] or on
        k = (v, p, region)
        self.turn[k] += 1
        return local[(self.turn[k] - 1) % len(local)]["employee_name"]


class World:
    def __init__(self, path) -> None:
        self.path = path
        self.ids = Ids(path)
        self.owners = Owners(path)
        self.opps = {v: read(path(f"{v}_opportunities.csv"))[1] for v in VERSIONS}
        self.fields = read(path("Actual_opportunity_movements.csv"))[0]
        self.wf = {v: {(month(r["period"]), r["opportunity_type"]): r
                       for r in read(path(f"{v}_pipeline_waterfall.csv"))[1]} for v in VERSIONS}
        self.mk = {v: {(month(r["period"]), r["marketing_channel"]): r
                       for r in read(path(f"{v}_marketing_pipeline.csv"))[1]} for v in VERSIONS}
        self.org = self.opps["Actual"][0]["organization_id"]
        actual = self.opps["Actual"]
        self.start = min(month(o["period"]) for o in actual)
        if max(month(o["period"]) for o in actual) != CLOSE:
            raise SystemExit(f"Actual opportunities do not reach the {CLOSE} close")
        self.nb_size, self.size, self.templates = {}, {}, defaultdict(list)
        by: dict[str, list[Decimal]] = defaultdict(list)
        for o in actual:
            if o["opportunity_type"] == NB:
                by[o["marketing_channel"]].append(num(o["amount_arr"]))
                self.templates[o["marketing_channel"]].append(o)
            elif o["opportunity_type"] in BOOKING:
                by[o["opportunity_type"]].append(num(o["amount_arr"]))
        for k, xs in by.items():
            avg = q(sum(xs, ZERO) / len(xs))
            (self.size if k in BOOKING else self.nb_size)[k] = avg
        missing = [t for t in BOOKING[1:] if t not in self.size]
        if missing:
            raise SystemExit(f"no Actual deals to size {missing} from")
        region = defaultdict(Counter)
        for v in VERSIONS:
            for o in self.opps[v]:
                region[o["customer_state"]][o["region"]] += 1
        self.region_of_state = {s: c.most_common(1)[0][0] for s, c in region.items()}
        self.customers = {v: read(path(f"{v}_customers.csv"))[1] for v in VERSIONS}

    def size_of(self, t: str, channel: str) -> Decimal:
        if t != NB:
            return self.size[t]
        if channel not in self.nb_size:
            raise SystemExit(f"channel {channel}: no Actual New Business deals to size its pipeline from")
        return self.nb_size[channel]

    def prospect_attrs(self, v: str, t: str, channel: str, deal_id: str) -> dict[str, str]:
        if t == NB:
            tpl = self.templates[channel]
            o = tpl[int(stable_unit(f"{deal_id}|tpl") * len(tpl))]
            cid, name = self.ids.prospect()
            return {"customer_id": cid, "customer_name": name, "customer_state": o["customer_state"],
                    "region": o["region"], "industry": o["industry"], "billing_cadence": o["billing_cadence"],
                    "billing_terms": o["billing_terms"], "contract_term_months": o["contract_term_months"],
                    "marketing_channel": channel}
        pool = [c for c in self.customers[v]
                if (c["status"] == "Active" and num(c["starting_arr_jan_2026"]) > 0) == (t == "Expansion")
                and (t == "Expansion" or c["status"] in DEPARTED)]
        if not pool:
            raise SystemExit(f"{v}: no customers for {t} pipeline")
        c = pool[int(stable_unit(f"{deal_id}|cust") * len(pool))]
        if c["billing_state"] not in self.region_of_state:
            raise SystemExit(f"{c['customer_id']}: no deal in state {c['billing_state']} to place it in a territory")
        return {"customer_id": c["customer_id"], "customer_name": c["customer_name"],
                "customer_state": c["billing_state"], "region": self.region_of_state[c["billing_state"]],
                "industry": c["industry"], "billing_cadence": c["billing_cadence"], "billing_terms": c["billing_terms"],
                "contract_term_months": "12", "marketing_channel": CS_CHANNEL, "segment": c["segment"]}


def key_of(o: dict[str, str]) -> tuple[str, str]:
    """Pipeline bucket for a named deal.

    New Business is its marketing channel. Expansion and Reactivation are one waterfall cell, so the
    unattributed remainder of that cell is carried as Customer Success. The movement row still writes
    the deal's own marketing_channel. An expansion on a customer who was new business stays Expansion.
    """
    t = o["opportunity_type"]
    return t, (o["marketing_channel"] if t == NB else CS_CHANNEL)


def known_amount(v: str, o: dict[str, str]) -> Decimal:
    return num(o["weighted_arr"] if v == "Forecast" else o["amount_arr"])


def win_rates(w: World, v: str, months: list[str]) -> dict[str, Decimal]:
    out = {}
    for t in BOOKING:
        won = sum((num(w.wf[v][(p, t)]["closed_won_arr"]) for p in months), ZERO)
        lost = sum((num(w.wf[v][(p, t)]["closed_lost_arr"]) for p in months), ZERO)
        out[t] = (won / (won + lost)).quantize(Decimal("0.01"), ROUND_HALF_UP) if won + lost else ZERO
    return out


def opening_pool(w: World, log: list[dict]) -> dict[str, list[Deal]]:
    """The pipeline open at the start of the Actual CRM months, as deals, by type (oldest first)."""
    s = w.start
    begin: dict[tuple[str, str], Decimal] = {}
    for (p, c), r in w.mk["Actual"].items():
        if p == s:
            begin[(NB, c)] = num(r["beginning_pipeline_arr"])
    nb_total = num(w.wf["Actual"][(s, NB)]["beginning_pipeline_arr"])
    if sum((a for (t, _), a in begin.items() if t == NB), ZERO) != nb_total:
        raise SystemExit(f"Actual {s}: marketing beginning pipeline != the New Business waterfall's {nb_total}")
    for t in BOOKING[1:]:
        begin[(t, CS_CHANNEL)] = num(w.wf["Actual"][(s, t)]["beginning_pipeline_arr"])
    for o in w.opps["Actual"]:
        if o["opportunity_type"] in BOOKING and month(o["created_date"]) < s:
            begin[key_of(o)] = begin.get(key_of(o), ZERO) - num(o["amount_arr"])
    pool: dict[str, list[Deal]] = {t: [] for t in BOOKING}
    for k, amount in sorted(begin.items()):
        t, c = k
        if amount < 0:
            raise SystemExit(f"Actual {s} {t} {c}: deals created before {s} exceed the beginning pipeline")
        if amount == 0:
            continue
        n = max(1, int((amount / w.size_of(t, c)).quantize(Decimal("1"), ROUND_HALF_UP)))
        ids = [w.ids.opp("Actual") for _ in range(n)]
        amounts = spread(amount, n, f"open|{t}|{c}")
        made = {padd(s, -i): num(w.mk["Actual"].get((padd(s, -i), c), {}).get("pipeline_arr_created", "0"))
                for i in range(1, 13)} if t == NB else {}
        deals, p, room = [], padd(s, -1), None
        for i, a in zip(ids, amounts):
            if t == NB:
                room = made.get(p, ZERO) if room is None else room
                while room < a and p > padd(s, -12):
                    p = padd(p, -1)
                    room = made.get(p, ZERO)
                room -= a
            d = Deal(i, t, c, day_in(p, f"{i}|created"), a, w.prospect_attrs("Actual", t, c, i))
            deals.append(d)
        pool[t] = sorted(pool[t] + deals, key=lambda d: (d.created, d.id))
        log.append({"version": "Actual", "period": s, "file": "Actual_opportunity_movements.csv", "action": "opened",
                    "detail": f"{t} {c}: {n} open deals in the beginning pipeline", "amount": amount})
    return pool


def take(open_: list[Deal], target: Decimal) -> list[Deal]:
    """Deals from ``open_`` that come closest to ``target`` (at least one): each step adds the deal that brings the
    total nearest, the oldest on a tie, until no deal brings it nearer."""
    picked, total, left = [], ZERO, list(open_)
    while left:
        d = min(left, key=lambda d: (abs(total + d.current - target), d.created, d.id))
        if picked and abs(total + d.current - target) >= abs(total - target):
            break
        picked.append(d)
        left.remove(d)
        total += d.current
    return picked


def exits(w: World, v: str, p: str, t: str, pool: list[Deal], first: str, log: list[dict],
          created_at: dict[str, int], events: list[list]) -> list[tuple[str, Deal, Decimal]]:
    """The month's closed lost and slipped of the type, each from the open pipeline-only deals whose ARR comes
    closest to it, moved pro rata to the waterfall amount; the deals left open in each channel then move pro rata to
    the channel's remaining balance, so the open deals always add up to the waterfall. With fewer open deals than
    that needs, the largest
    deal open since before ``first`` is split in two (it has no Pipeline Created row here); Expansion and
    Reactivation, whose deal counts are not planned, may split any open deal, its Pipeline Created row split with
    it."""
    targets = [(label, num(w.wf[v][(p, t)][WF[label]])) for label in (LOST, SLIPPED)]
    targets = [(label, a) for label, a in targets if a]
    open_ = [d for d in pool if d.exit is None]
    rest = sum((d.current for d in open_), ZERO) - sum((a for _, a in targets), ZERO)
    if rest < 0:
        raise SystemExit(f"{v} {p} {t}: closed lost and slipped {targets} exceed the open pipeline-only deals")
    need = len(targets) + (1 if rest > 0 else 0)
    while len(open_) < need:
        older = [d for d in open_ if month(d.created.isoformat()) < first or (t != NB and d.id in created_at)]
        if not older:
            raise SystemExit(f"{v} {p} {t}: {len(targets)} exits ({targets}) and {len(open_)} open deals")
        d = max(older, key=lambda d: (d.current, d.id))
        a, b = spread(d.amount, 2, f"split|{d.id}")
        ca, cb = spread(d.current, 2, f"split|{d.id}")
        twin_id = w.ids.opp("Actual" if d.id not in created_at else v)
        twin = replace(d, id=twin_id, amount=b, current=cb, owner_by={},
                       attrs=w.prospect_attrs(v, d.type, d.channel, twin_id))
        d.amount, d.current = a, ca
        if d.id in created_at:
            ev = events[created_at[d.id]]
            ev[3] = a
            created_at[twin_id] = len(events)
            events.append([CREATED, ev[1], twin, b])
        pool.insert(pool.index(d) + 1, twin)
        open_.insert(open_.index(d) + 1, twin)
        log.append({"version": v, "period": p, "file": f"{v}_opportunity_movements.csv", "action": "split",
                    "detail": f"{t}: open deal {d.id} split into {d.id} and {twin.id} to cover {len(targets)} exits "
                              f"and the pipeline left open", "amount": ca + cb})
    before = defaultdict(Decimal)
    for d in open_:
        before[d.channel] += d.current
    gone = defaultdict(Decimal)
    out = []
    for i, (label, target) in enumerate(targets):
        keep = len(targets) - i - 1 + (1 if rest > 0 else 0)
        allowed = open_[:len(open_) - keep]
        balance = {c: before[c] - gone[c] for c in before}
        picked, amounts = pick(allowed, open_, target, balance) if keep else (open_, None)
        if amounts is None:
            amounts = exit_amounts(picked, target, open_, balance)
        if amounts is None:
            raise SystemExit(f"{v} {p} {t} {label} {target}: no open deals can close it out")
        moved = sum((d.current for d in picked), ZERO)
        for d in list(picked):
            d.exit = (label, p, amounts[d.id])
            d.current = amounts[d.id]
            gone[d.channel] += amounts[d.id]
            out.append((label, d, amounts[d.id]))
            open_.remove(d)
        if moved != target:
            log.append({"version": v, "period": p, "file": f"{v}_opportunity_movements.csv", "action": "resized",
                        "detail": f"{t} {label}: {len(amounts)} deals from {moved:.2f} to the waterfall's "
                                  f"{target:.2f} (x{target / moved:.4f})", "amount": target - moved})
    for c in sorted({d.channel for d in open_}):
        mine = [d for d in open_ if d.channel == c]
        now = allocate(before[c] - gone[c], [(d.id, d.current) for d in mine])
        for d in mine:
            d.current = now[d.id]
    return out


def exit_amounts(picked: list[Deal], target: Decimal, open_: list[Deal],
                 balance: dict[str, Decimal]) -> dict[str, Decimal] | None:
    """Exit ARR for ``picked`` adding up to ``target``: a channel left with no open deal closes out its whole open
    balance (pro rata over its deals); the other picked deals move pro rata to the rest, each of their channels
    keeping a positive open balance. None when that cannot be done."""
    ids = {d.id for d in picked}
    left = {d.channel for d in open_ if d.id not in ids}
    fixed = [d for d in picked if d.channel not in left]
    flex = [d for d in picked if d.channel in left]
    out: dict[str, Decimal] = {}
    for c in {d.channel for d in fixed}:
        out.update(allocate(balance[c], [(d.id, d.current) for d in fixed if d.channel == c]))
    room = target - sum(out.values(), ZERO)
    if not flex:
        return out if room == 0 else None
    if room <= 0:
        return None
    out.update(allocate(room, [(d.id, d.current) for d in flex]))
    for c in {d.channel for d in flex}:
        if balance[c] - sum((out[d.id] for d in flex if d.channel == c), ZERO) <= 0:
            return None
    return out


def pick(allowed: list[Deal], open_: list[Deal], target: Decimal,
         balance: dict[str, Decimal]) -> tuple[list[Deal], dict[str, Decimal] | None]:
    """The best-fit deals for ``target`` from ``allowed``; when their channels cannot close out at it, the best fit
    plus one more deal, then the single deal nearest the target."""
    first = take(allowed, target)
    near = sum((x.current for x in first), ZERO)
    tries = [first]
    tries += [first + [d] for d in sorted((d for d in allowed if d not in first),
                                          key=lambda d: (abs(near + d.current - target), d.created, d.id))]
    tries += [[d] for d in sorted(allowed, key=lambda d: (abs(d.current - target), d.created, d.id))]
    for picked in tries:
        amounts = exit_amounts(picked, target, open_, balance)
        if amounts is not None:
            return picked, amounts
    return first, None


def run_version(w: World, v: str, months: list[str], pool: dict[str, list[Deal]],
                log: list[dict]) -> tuple[list[tuple[str, str, Deal, Decimal]], dict[str, list[Deal]]]:
    """Events (label, month, deal, amount) for the version's own months; returns them and the deals still open."""
    pool = {t: [replace(d, owner_by=dict(d.owner_by)) for d in pool.get(t, [])] for t in BOOKING}
    events: list[tuple[str, str, Deal, Decimal]] = []
    known = [o for o in w.opps[v] if o["opportunity_type"] in BOOKING and month(o["period"]) in months]
    by_created: dict[tuple[str, tuple[str, str]], list[Deal]] = defaultdict(list)
    for o in sorted(known, key=lambda o: (o["created_date"], o["opportunity_id"])):
        d = Deal(o["opportunity_id"], o["opportunity_type"], o["marketing_channel"],
                 dt.date.fromisoformat(o["created_date"]),
                 known_amount(v, o), {k: o[k] for k in COPY}, known=o)
        d.exit = (WON, month(o["period"]), d.amount)
        if month(o["created_date"]) > month(o["period"]):
            raise SystemExit(f"{v} {o['opportunity_id']}: created after it closes")
        if month(o["created_date"]) >= months[0]:
            by_created[(month(o["created_date"]), key_of(o))].append(d)
        events.append([WON, month(o["period"]), d, d.amount])
    created_at: dict[str, int] = {}
    keys = sorted({(NB, c) for (p, c) in w.mk[v] if p in months} | {(t, CS_CHANNEL) for t in BOOKING[1:]})
    for p in months:
        for k in keys:
            t, c = k
            if t == NB:
                r = w.mk[v].get((p, c))
                made = num(r["pipeline_arr_created"]) if r else ZERO
                count = int(r["opportunities_created"]) if r else 0
            else:
                made, count = num(w.wf[v][(p, t)]["new_pipeline_created"]), None
            mine = by_created.get((p, k), [])
            rest = made - sum((d.amount for d in mine), ZERO)
            if rest < 0:
                raise SystemExit(f"{v} {p} {t} {c}: deals created {made - rest} exceed pipeline created {made}")
            if count is None:
                n = max(1, int((rest / w.size_of(t, c)).quantize(Decimal("1"), ROUND_HALF_UP))) if rest > 0 else 0
            else:
                n = count - len(mine)
                if n < 0 or (rest > 0 and n == 0) or (rest == 0 and n > 0):
                    raise SystemExit(f"{v} {p} {c}: {count} opportunities created for {len(mine)} closing deals "
                                     f"and {rest} of other pipeline")
            for d in mine:
                events.append([CREATED, p, d, d.amount])
            for a in spread(rest, n, f"{v}|{p}|{t}|{c}"):
                i = w.ids.opp(v)
                d = Deal(i, t, c, day_in(p, f"{i}|created"), a, w.prospect_attrs(v, t, c, i))
                pool[t].append(d)
                created_at[i] = len(events)
                events.append([CREATED, p, d, a])
        for t in BOOKING:
            pool[t].sort(key=lambda d: (d.created, d.id))
            for label, d, a in exits(w, v, p, t, pool[t], months[0], log, created_at, events):
                events.append([label, p, d, a])
            pool[t] = [d for d in pool[t] if d.exit is None]
            reserved = sum((d.amount for (cp, k), ds in by_created.items() if k[0] == t and cp <= p
                            for d in ds if d.exit[1] > p), ZERO)
            if sum((d.current for d in pool[t]), ZERO) + reserved != num(w.wf[v][(p, t)]["ending_pipeline_arr"]):
                raise SystemExit(f"{v} {p} {t}: open deals {sum((d.current for d in pool[t]), ZERO) + reserved} != "
                                 f"waterfall ending {w.wf[v][(p, t)]['ending_pipeline_arr']}")
    return events, pool


def rows_for(w: World, v: str, events: list[tuple[str, str, Deal, Decimal]], rates: dict[str, Decimal],
             months: list[str]) -> list[dict]:
    out = []
    first_amount: dict[str, Decimal] = {}
    order = {CREATED: 0, WON: 1, LOST: 1, SLIPPED: 1}
    events = sorted(events, key=lambda e: (e[1], order[e[0]], e[2].id))
    for label, p, d, a in events:
        first_amount.setdefault(d.attrs["customer_id"], a)
    for label, p, d, a in events:
        o = d.known
        attrs = dict(d.attrs)
        if o is None and "segment" not in attrs:
            attrs["segment"] = segment_for(first_amount[attrs["customer_id"]])
        owner = d.owner_by.get(v)
        if owner is None:
            if o is not None:
                owner = o["owner"]
            else:
                start = max(month(d.created.isoformat()), months[0])
                inherited = next(iter(d.owner_by.values()), None)
                owner = inherited if inherited and w.owners.valid(v, inherited, start) else \
                    w.owners.pick(v, start, attrs["region"])
            d.owner_by[v] = owner
        attrs["owner"] = owner
        if d.exit is not None:
            close = d.exit[1]
        else:
            close = padd(months[-1], 1)
        expected = dt.date.fromisoformat(o["expected_close_date"]) if o else last_day(close)
        term = int(attrs["contract_term_months"] or 12)
        start_c = dt.date.fromisoformat(o["contract_start_date"]) if o and o["contract_start_date"] else \
            dt.date(expected.year, expected.month, 1) if expected.day == 1 else add_months(dt.date(expected.year, expected.month, 1), 1)
        end_c = dt.date.fromisoformat(o["contract_end_date"]) if o and o["contract_end_date"] else add_months(start_c, term)
        prob = num(o["probability"]) if o and v == "Forecast" else rates[d.type]
        if label == WON:
            stage, status, prob_row, closed = "Closed Won", "Closed Won", Decimal("1") if v != "Forecast" else prob, \
                (o["actual_close_date"] or o["expected_close_date"])
        elif label == LOST:
            stage, status, prob_row = "Closed Lost", "Closed Lost", ZERO
            closed = day_in(p, f"{d.id}|lost", d.created).isoformat()
        elif label == SLIPPED:
            stage, status, prob_row, closed = "Negotiation", "Open", prob, ""
        else:
            stage, status, prob_row, closed = "Discovery", "Open", prob, ""
        if v == "Forecast" and o is not None:
            weighted = a
            note = "Forecast deal at expected ARR (ARR x probability), as the Forecast pipeline waterfall"
        else:
            weighted = q(a * prob_row)
            note = ("CRM deal" if o is not None else "Pipeline-only deal") + {
                CREATED: ": pipeline created", WON: ": closed won", LOST: ": closed lost at its ARR that month",
                SLIPPED: ": slipped out of the month at its ARR then"}[label]
        if label == LOST and d.exit and d.amount != a:
            note += f" (created at {d.amount:.2f})"
        out.append({
            "organization_id": w.org, "version": v, "period": f"{p}-01", "opportunity_id": d.id,
            "opportunity_name": o["opportunity_name"] if o else
            f"{attrs['customer_name']} - {d.type} - {month(d.created.isoformat())}",
            **{k: attrs[k] for k in COPY}, "opportunity_type": d.type, "stage": stage, "close_status": status,
            "created_date": d.created.isoformat(),
            "expected_close_date": (last_day(p) if label == SLIPPED else expected).isoformat(),
            "actual_close_date": closed if label in (WON, LOST) else "",
            "contract_start_date": start_c.isoformat(), "contract_end_date": end_c.isoformat(),
            "amount_arr": a, "weighted_arr": weighted, "probability": f"{prob_row}",
            "waterfall_type": label, "pipeline_movement_type": label, "source_note": note})
    return out


def restate_actual_channels(w: World, events: list[tuple[str, str, Deal, Decimal]], months: list[str]) -> str:
    """Actual marketing pipeline in the CRM months: closed lost and slipped by channel = the New Business deals lost
    and slipped in the channel; beginning and ending roll from the first CRM month's beginning."""
    fields, rows = read(w.path("Actual_marketing_pipeline.csv"))
    out: dict[tuple[str, str, str], Decimal] = defaultdict(Decimal)
    for label, p, d, a in events:
        if d.type == NB and label in (LOST, SLIPPED):
            out[(p, d.channel, label)] += a
    by = {(month(r["period"]), r["marketing_channel"]): r for r in rows}
    stray = sorted({f"{p} {c}" for p, c, _ in out if (p, c) not in by})
    if stray:
        raise SystemExit(f"New Business deals lost or slipped in channels with no Actual marketing row: {stray}")
    begin = {c: num(r["beginning_pipeline_arr"]) for (p, c), r in by.items() if p == months[0]}
    for p in months:
        for c in sorted(begin):
            r = by[(p, c)]
            lost, slipped = out[(p, c, LOST)], out[(p, c, SLIPPED)]
            end = begin[c] + num(r["pipeline_arr_created"]) - num(r["closed_won_arr"]) - lost - slipped
            if end < 0:
                raise SystemExit(f"Actual {p} {c}: deals lost and slipped leave the channel's pipeline at {end}")
            r["beginning_pipeline_arr"], r["closed_lost_arr"], r["slipped_pipeline_arr"] = begin[c], lost, slipped
            r["ending_pipeline_arr"] = end
            begin[c] = end
    write(w.path("Actual_marketing_pipeline.csv"), fields, rows)
    w.mk["Actual"] = {(month(r["period"]), r["marketing_channel"]): r for r in rows}
    return (f"Actual marketing pipeline {months[0]}..{months[-1]}: closed lost and slipped by channel restated from "
            f"the deals; {months[-1]} ending by channel " + ", ".join(f"{c} {e:,.2f}" for c, e in sorted(begin.items())))


def booked_rows(w: World, v: str, months: list[str]) -> list[dict]:
    """Contraction and Churn: the version's deals of those types."""
    out = []
    for o in w.opps[v]:
        if o["opportunity_type"] in BOOKING or month(o["period"]) not in months:
            continue
        out.append({**o, "waterfall_type": o["opportunity_type"], "pipeline_movement_type": o["opportunity_type"]})
    return out


def check(w: World, v: str, rows: list[dict], months: list[str]) -> None:
    got: dict[tuple[str, str, str], Decimal] = defaultdict(Decimal)
    for r in rows:
        if r["opportunity_type"] in BOOKING:
            got[(month(r["period"]), r["opportunity_type"], r["pipeline_movement_type"])] += num(r["amount_arr"])
    bad = [f"{p} {t} {label}: {got[(p, t, label)]} vs {w.wf[v][(p, t)][col]}"
           for p in months for t in BOOKING for label, col in WF.items()
           if got[(p, t, label)] != num(w.wf[v][(p, t)][col])]
    if bad:
        raise SystemExit(f"{v} movements do not add up to the pipeline waterfall: {bad[:6]}")


def waterfall_summary(w: World) -> list[dict]:
    out, ends = [], {}
    for v in ("Actual", "Forecast", "Budget"):
        by = defaultdict(lambda: defaultdict(Decimal))
        for (p, t), r in w.wf[v].items():
            if t in BOOKING:
                for k in ("beginning_pipeline_arr", "new_pipeline_created", "closed_won_arr", "closed_lost_arr",
                          "slipped_arr", "ending_pipeline_arr"):
                    by[p][k] += num(r[k])
        ps = sorted(by)
        var = max(abs(by[p]["beginning_pipeline_arr"] + by[p]["new_pipeline_created"] - by[p]["closed_won_arr"]
                      - by[p]["closed_lost_arr"] - by[p]["slipped_arr"] - by[p]["ending_pipeline_arr"]) for p in ps)
        chained = all(by[a]["ending_pipeline_arr"] == by[b]["beginning_pipeline_arr"] for a, b in zip(ps, ps[1:]))
        cover = [by[a]["ending_pipeline_arr"] / by[b]["closed_won_arr"] for a, b in zip(ps, ps[1:])
                 if by[b]["closed_won_arr"]]
        ends[v] = by
        out.append({"version": v, "beginning_pipeline": by[ps[0]]["beginning_pipeline_arr"],
                    "ending_pipeline": by[ps[-1]]["ending_pipeline_arr"],
                    "total_pipeline_created": sum((by[p]["new_pipeline_created"] for p in ps), ZERO),
                    "total_closed_won": sum((by[p]["closed_won_arr"] for p in ps), ZERO),
                    "avg_pipeline_coverage": ratio(sum(cover, ZERO), Decimal(len(cover))) if cover else "",
                    "max_waterfall_variance": var, "continuity_check": "PASS" if chained and var == 0 else "FAIL"})
    a_end = ends["Actual"][CLOSE]["ending_pipeline_arr"]
    f_begin = ends["Forecast"][padd(CLOSE, 1)]["beginning_pipeline_arr"]
    out.append({"version": "Actual_to_Forecast_Continuity", "beginning_pipeline": a_end, "ending_pipeline": f_begin,
                "total_pipeline_created": ZERO, "total_closed_won": ZERO, "avg_pipeline_coverage": "",
                "max_waterfall_variance": abs(a_end - f_begin), "continuity_check": "PASS" if a_end == f_begin else "FAIL"})
    return out


def drilldown_validation(w: World, rows_by: dict[str, list[dict]], months_by: dict[str, list[str]]) -> list[dict]:
    out = []
    for v in ("Actual", "Forecast", "Budget"):
        mrr = {month(r["period"]): r for r in read(w.path(f"{v}_MRR_Waterfall.csv"))[1]}
        if v == "Forecast":
            mrr.update({month(r["period"]): r for r in read(w.path("Actual_MRR_Waterfall.csv"))[1]
                        if month(r["period"]) <= CLOSE})
        for p in months_by[v]:
            got = defaultdict(Decimal)
            for r in rows_by[v]:
                if month(r["period"]) == p and r["opportunity_type"] in BOOKING:
                    got[r["pipeline_movement_type"]] += num(r["amount_arr"])
            cell = {label: sum((num(w.wf[v][(p, t)][col]) for t in BOOKING), ZERO) for label, col in WF.items()}
            booked = sum((num(mrr[p][c]) for c in ("new_business_arr", "expansion_arr", "reactivation_arr")), ZERO)
            var = {label: got[label] - cell[label] for label in WF}
            row = {"version": v, "period": p,
                   "pipeline_created_waterfall": cell[CREATED], "pipeline_created_opportunities": got[CREATED],
                   "closed_won_waterfall": cell[WON], "closed_won_opportunities": got[WON],
                   "mrr_new_business_arr": booked, "closed_lost_waterfall": cell[LOST],
                   "closed_lost_opportunities": got[LOST], "slipped_waterfall": cell[SLIPPED],
                   "slipped_opportunities": got[SLIPPED], "pipeline_created_variance": var[CREATED],
                   "closed_won_to_mrr_variance": got[WON] - booked, "closed_lost_variance": var[LOST],
                   "slipped_variance": var[SLIPPED]}
            row["status"] = "PASS" if not any(var.values()) and row["closed_won_to_mrr_variance"] == 0 else "FAIL"
            out.append(row)
    return out


def marketing_summary(w: World) -> list[dict]:
    out = []
    for v in ("Actual", "Forecast", "Budget"):
        by = defaultdict(lambda: defaultdict(Decimal))
        for (p, _), r in w.mk[v].items():
            if v != "Actual" or p >= w.start:
                for k in ("closed_won_arr", "pipeline_arr_created", "marketing_spend"):
                    by[p][k] += num(r[k])
        for p in sorted(by):
            out.append({"file": f"{v}_marketing_pipeline.csv", "period": p, **by[p],
                        "pipeline_per_spend": ratio(by[p]["pipeline_arr_created"], by[p]["marketing_spend"])})
    return out


def main(src: str, dst: str) -> list[str]:
    if not (os.path.isabs(src) and os.path.isabs(dst)):
        raise SystemExit("folders must be absolute paths")
    if os.path.exists(dst):
        raise SystemExit(f"{dst} exists; pick a new folder")
    shutil.copytree(src, dst)
    path = lambda name: os.path.join(dst, name)  # noqa: E731
    w = World(path)
    log: list[dict] = []
    notes: list[str] = []
    a_months = prange(w.start, CLOSE)
    b_months = sorted({p for p, _ in w.wf["Budget"]})
    f_all = sorted({p for p, _ in w.wf["Forecast"]})
    f_through, f_months = [p for p in f_all if p <= CLOSE], [p for p in f_all if p > CLOSE]
    if f_through:
        raise SystemExit(f"Forecast pipeline waterfall still has closed months {f_through}")

    opening = opening_pool(w, log)
    for d in (d for ds in opening.values() for d in ds):
        d.owner_by["Actual"] = w.owners.pick("Actual", w.start, d.attrs["region"])
    rows_by, months_by = {}, {"Actual": a_months, "Budget": b_months, "Forecast": f_months}
    still_open = opening
    for v, months, start_pool in (("Actual", a_months, opening), ("Budget", b_months, opening),
                                  ("Forecast", f_months, None)):
        events, left = run_version(w, v, months, still_open if start_pool is None else start_pool, log)
        rows = rows_for(w, v, events, win_rates(w, v, months), months) + booked_rows(w, v, months)
        if v == "Actual":
            still_open = left
            notes.append(restate_actual_channels(w, events, months))
        rows.sort(key=lambda r: (r["period"], r["opportunity_type"], r["pipeline_movement_type"], r["opportunity_id"]))
        check(w, v, rows, months_by[v])
        rows_by[v] = rows
        write(path(f"{v}_opportunity_movements.csv"), w.fields, rows)
        c = Counter(r["pipeline_movement_type"] for r in rows)
        notes.append(f"{v} movements {months_by[v][0]}..{months_by[v][-1]}: {len(rows)} rows ("
                     + ", ".join(f"{k} {n}" for k, n in sorted(c.items())) + f"); "
                     f"{len({r['opportunity_id'] for r in rows})} deals")
    notes.append(f"Actual months before {w.start}: no deal detail in the CRM export")
    resized = [x for x in log if x["action"] == "resized"]
    if resized:
        worst = max(resized, key=lambda x: abs(Decimal(x["detail"].rsplit("(x", 1)[1][:-1]) - 1))
        notes.append(f"{len(resized)} closed lost / slipped amounts moved pro rata from the deals' created ARR; "
                     f"largest move {worst['version']} {worst['period']} {worst['detail']}")
    write(path("opportunity_pipeline_drilldown_validation.csv"),
          read(path("opportunity_pipeline_drilldown_validation.csv"))[0], drilldown_validation(w, rows_by, months_by))
    write(path("pipeline_waterfall_validation_summary.csv"),
          read(path("pipeline_waterfall_validation_summary.csv"))[0], waterfall_summary(w))
    write(path("pipeline_refresh_validation_summary.csv"),
          ["file", "period", "closed_won_arr", "pipeline_arr_created", "marketing_spend", "pipeline_per_spend"],
          marketing_summary(w))
    log_fields = ["version", "period", "file", "action", "detail", "amount"]
    kept = [r for r in read(path("pipeline_deals_log.csv"))[1] if not r["file"].endswith("_opportunity_movements.csv")] \
        if os.path.exists(path("pipeline_deals_log.csv")) else []
    write(path("pipeline_deals_log.csv"), log_fields, kept + log)
    return notes


if __name__ == "__main__":
    for n in main(sys.argv[1], sys.argv[2]):
        print(n)
