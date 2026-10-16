"""Jan-Jun 2026 Actual customer movements, customer by customer, at the rates the 2025 customer history shows.

Used by build_customer_history.py (writes files only; never touches the database).

Rules:
  * Rates are measured on the twelve months before the first simulated month, from the Actual customer history
    built from the ARR waterfall:
      - leaving at renewal: ARR that left / ARR due for renewal (anniversary month, 12+ months since the customer
        last started), and the share of those departures that paused rather than cancelled;
      - contraction and expansion: movement ARR / ARR active at the prior month end, with the movement sizes seen
        (share of the customer's ARR), both counting only customers that last started before the twelve months; a
        customer moves with probability rate / mean share, by a share drawn from the ones seen;
      - returns: ARR left with by the customers that returned / ARR-months paused, and the same within
        RESTART_AFTER_MONTHS of cancelling (collections cases never return); a return is the ARR left with x a
        return / left-with ratio seen;
      - new business: each closing team's new business / its ramped quota (Hiring_Ramp_Assumptions.csv). A deal
        belongs to the team its size goes to (sales_team.enterprise_floor, measured on the same twelve months);
        deal sizes are the ARR at signing of every customer on record, by the team that size goes to.
  * Each month: customers due for renewal leave at the departure rate (pausing at the pause share; a non-payment
    churn month has at least one cancellation), paused and recently cancelled customers return, each team books
    new business, then active customers contract and expand. A team's expected new business is its ramped quota
    that month x its attainment, carried month to month; the next deal (drawn from its sizes) books once the
    expected total passes what is booked by half the deal. The deal's territory is drawn in proportion to the
    team's ramped quota there. A customer that starts a contract in the window (new or returning) does not move
    again in it. A customer expands at most once, and only when it has a renewal due in the window's year that it
    stays for: the expansion is credited to the CSM on that renewal.
  * Draws are stable hashes of the customer and month (no random seed).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from build_v5_dataset import ZERO, padd, pidx, q, ramped_quota
from customer_buckets import RESTART_AFTER_MONTHS
from customer_history_plans import (CANCELLED, PAUSED, History, departures_at, last_starts, return_note,
                                    signing_arr, u)
from sales_team import BOOKINGS_ROLES, CLOSING_TEAMS, TERRITORIES, closing_team, enterprise_floor

DEPARTURES = ("Churn", "Pause")
MOVES = ("Contraction", "Expansion")
UP_MOVEMENTS = ("New Business", "Expansion", "Reactivation")


def _draw(pool: list[Decimal], key: str) -> Decimal:
    return pool[int(u(key) * len(pool))]


def _pct(x: Decimal) -> str:
    return f"{x:.2%}"


def closers(team: list[dict[str, str]]) -> list[dict[str, str]]:
    out = [e for e in team if e["role"] in BOOKINGS_ROLES]
    bad = sorted({e["sub_department"] for e in out} - set(CLOSING_TEAMS))
    if bad:
        raise ValueError(f"closers outside the closing teams: {bad}")
    return out


def is_due(c: str, p: str, start: dict[str, str], last: dict[str, str]) -> bool:
    return start[c][5:7] == p[5:7] and pidx(last[c]) <= pidx(p) - 12


@dataclass
class Rates:
    window: tuple[str, str]
    depart: Decimal
    pause_share: Decimal
    move: dict[str, Decimal]
    shares: dict[str, list[Decimal]]
    back: dict[str, Decimal]
    return_ratios: list[Decimal]
    floor: Decimal
    attainment: dict[str, Decimal]
    deal_sizes: dict[str, list[Decimal]]

    def describe(self) -> str:
        return (f"rates {self.window[0]}..{self.window[1]}: leave at renewal {_pct(self.depart)} of ARR due "
                f"({_pct(self.pause_share)} pause); contraction {_pct(self.move['Contraction'])} and expansion "
                f"{_pct(self.move['Expansion'])} of customers a month; back after a pause {_pct(self.back[PAUSED])} "
                f"and after cancelling {_pct(self.back[CANCELLED])} of the ARR away a month; {CLOSING_TEAMS[0]} "
                f"closes new business from {self.floor:,.2f}; attainment "
                + ", ".join(f"{t} {_pct(a)} ({len(self.deal_sizes[t])} deal sizes)"
                            for t, a in sorted(self.attainment.items())))


def measure(h: History, start: dict[str, str], window: list[str], team: list[dict[str, str]], curve,
            excluded: set[str]) -> Rates:
    """Rates over ``window`` (months already in ``h``). ``excluded``: customers whose churn is a collections case."""
    inside = set(window)
    by_period: dict[str, list[dict]] = defaultdict(list)
    for r in h.rows:
        by_period[r["period"]].append(r)
    away: dict[str, tuple[str, str, Decimal]] = {}
    last = dict(start)
    due_arr = left_arr = active_arr = ZERO
    n_left = n_paused = 0
    moved = {k: ZERO for k in MOVES}
    shares: dict[str, list[Decimal]] = {k: [] for k in MOVES}
    exposure = {PAUSED: ZERO, CANCELLED: ZERO}
    backs = {PAUSED: ZERO, CANCELLED: ZERO}
    ratios: list[Decimal] = []
    for p in sorted(set(by_period) | inside):
        due: set[str] = set()
        if p in inside:
            prev = h.eop[padd(p, -1)]
            due = {c for c in prev if is_due(c, p, start, last)}
            due_arr += sum((prev[c] for c in due), ZERO)
            active_arr += sum((a for c, a in prev.items() if last[c] < window[0]), ZERO)
            for c, (kind, when, left) in away.items():
                if c in excluded:
                    continue
                if kind == "Pause":
                    exposure[PAUSED] += left
                elif 1 <= pidx(p) - pidx(when) <= RESTART_AFTER_MONTHS:
                    exposure[CANCELLED] += left
        for r in by_period[p]:
            c, kind = r["customer_id"], r["movement_type"]
            b, m = r["beginning_arr"], abs(r["movement_arr"])
            if kind in DEPARTURES:
                if c in due:
                    left_arr += b
                    n_left += 1
                    n_paused += kind == "Pause"
                away[c] = (kind, p, b)
            elif kind == "Reactivation":
                how, _, left = away.pop(c, ("", "", ZERO))
                if p in inside and left:
                    backs[PAUSED if how == "Pause" else CANCELLED] += left
                    ratios.append(m / left)
                last[c] = p
            elif kind == "New Business":
                away.pop(c, None)
                last[c] = p
            elif kind in MOVES and p in inside and last[c] < window[0]:
                moved[kind] += m
                shares[kind].append(m / b)
    empty = [k for k in MOVES if not shares[k]] + [k for k in (PAUSED, CANCELLED) if not exposure[k]]
    if not due_arr or not n_left or empty:
        raise ValueError(f"{window[0]}..{window[-1]}: nothing to measure for {empty or ['departures at renewal']}")

    cap: dict[str, Decimal] = defaultdict(Decimal)
    for e in closers(team):
        for p in window:
            cap[e["sub_department"]] += ramped_quota(e, p, curve)
    deals = [r["movement_arr"] for p in window for r in by_period[p] if r["movement_type"] == "New Business"]
    floor = enterprise_floor(deals, cap)
    won: dict[str, Decimal] = defaultdict(Decimal)
    for a in deals:
        won[closing_team(a, floor)] += a
    sizes: dict[str, list[Decimal]] = defaultdict(list)
    for a in signing_arr(h.rows).values():
        if a > 0:
            sizes[closing_team(a, floor)].append(a)
    return Rates(
        window=(window[0], window[-1]), depart=left_arr / due_arr, pause_share=Decimal(n_paused) / n_left,
        move={k: moved[k] / active_arr / (sum(shares[k], ZERO) / len(shares[k])) for k in MOVES},
        shares={k: sorted(v) for k, v in shares.items()},
        back={k: backs[k] / exposure[k] for k in (PAUSED, CANCELLED)}, return_ratios=sorted(ratios), floor=floor,
        attainment={t: won[t] / cap[t] for t in CLOSING_TEAMS}, deal_sizes={t: sorted(sizes[t]) for t in CLOSING_TEAMS})


def fit_month_to_target(h: History, deals: list[dict], period: str, target: Decimal) -> None:
    """Scale the month's new, expansion and reactivation ARR so net new lands on ``target``.

    Churn, pauses and contraction stay the customers that actually left. Later months renew the
    scaled balances, and the deal list is the same amounts the history rows carry.
    """
    rows = [r for r in h.rows if r["period"] == period and r["movement_type"] in UP_MOVEMENTS]
    gross = sum((r["movement_arr"] for r in rows), ZERO)
    deductions = sum((-r["movement_arr"] for r in h.rows
                      if r["period"] == period and r["movement_type"] not in UP_MOVEMENTS
                      and r["waterfall_column"]), ZERO)
    need = target + deductions
    if gross <= 0 or need <= 0:
        raise ValueError(f"{period}: cannot fit net new {target} onto booked ARR {gross}")
    factor = need / gross
    by_opp = {d["opportunity_id"]: d for d in deals if d["period"] == period}
    for row in rows:
        updated = q(row["movement_arr"] * factor)
        if updated <= 0:
            updated = Decimal("0.01")
        row["movement_arr"] = updated
        row["ending_arr"] = row["beginning_arr"] + updated
        h.arr[row["customer_id"]] = row["ending_arr"]
        deal = by_opp.get(row["opportunity_id"])
        if deal is not None:
            deal["amount"] = updated
    drift = need - sum((r["movement_arr"] for r in rows), ZERO)
    top = max(rows, key=lambda r: (r["movement_arr"], r["opportunity_id"]))
    top["movement_arr"] += drift
    top["ending_arr"] += drift
    h.arr[top["customer_id"]] = top["ending_arr"]
    deal = by_opp.get(top["opportunity_id"])
    if deal is not None:
        deal["amount"] = top["movement_arr"]


def simulate(h: History, rates: Rates, months: list[str], start: dict[str, str], team: list[dict[str, str]], curve,
             excluded: set[str], nonpay_months: set[str], choose_nonpay, new_logo, next_id,
             targets: dict[str, Decimal] | None = None) -> list[dict]:
    """Moves the customers in ``h`` through ``months``. ``choose_nonpay(period, cancelled)`` picks the non-payment
    churn among the month's cancellations (it never returns); ``new_logo(period, territory, arr, key)`` adds a
    customer and returns its ID; ``next_id()`` returns the next opportunity ID. Returns the deals (one per
    movement)."""
    away = departures_at(h.rows, padd(months[0], -1))
    last = last_starts(h.rows, start)
    expanded: set[str] = set()
    expected = {t: ZERO for t in CLOSING_TEAMS}
    booked = {t: ZERO for t in CLOSING_TEAMS}
    count = {t: 0 for t in CLOSING_TEAMS}
    deals: list[dict] = []

    def stays_on_book(c: str) -> bool:
        renewal = f"{months[0][:4]}-{start[c][5:7]}"
        if not is_due(c, renewal, start, last):
            return False
        return renewal not in months or u(f"depart|{renewal}|{c}") >= rates.depart

    def book(p: str, c: str, kind: str, amount: Decimal, note: str = "", team_name: str = "") -> None:
        oid = next_id()
        h.move(p, c, kind, amount, oid, note)
        deals.append({"period": p, "customer_id": c, "kind": kind, "amount": amount, "opportunity_id": oid,
                      "note": note, "team": team_name})

    for p in months:
        prev = dict(h.eop[padd(p, -1)])
        leaving = [c for c in sorted(prev) if is_due(c, p, start, last) and u(f"depart|{p}|{c}") < rates.depart]
        paused = {c: u(f"pause|{p}|{c}") < rates.pause_share for c in leaving}
        if p in nonpay_months:
            if not leaving:
                raise ValueError(f"{p}: a non-payment churn month with no customer leaving at renewal")
            if all(paused.values()):
                paused[leaving[-1]] = False
            excluded = excluded | {choose_nonpay(p, [c for c in leaving if not paused[c]])}
        for c in leaving:
            kind = "Pause" if paused[c] else "Churn"
            book(p, c, kind, prev[c], "paused at renewal" if paused[c] else "cancelled at renewal")
            away[c] = (kind, p, prev[c])

        for c in sorted(away):
            kind, when, left = away[c]
            gone = pidx(p) - pidx(when)
            if c in excluded or gone < 1:
                continue
            how = PAUSED if kind == "Pause" else CANCELLED
            if how == CANCELLED and gone > RESTART_AFTER_MONTHS:
                continue
            if u(f"back|{p}|{c}") < rates.back[how]:
                book(p, c, "Reactivation", q(left * _draw(rates.return_ratios, f"backsize|{p}|{c}")),
                     return_note(how, gone))
                del away[c]
                last[c] = p

        for t in sorted(CLOSING_TEAMS):
            quota = {r: ZERO for r in TERRITORIES}
            for e in closers(team):
                if e["sub_department"] == t:
                    quota[e["region"]] += ramped_quota(e, p, curve)
            total = sum(quota.values(), ZERO)
            expected[t] += total * rates.attainment[t]
            while total and rates.deal_sizes[t]:
                key = f"nb|{t}|{count[t]}"
                size = _draw(rates.deal_sizes[t], key)
                if booked[t] + size / 2 > expected[t]:
                    break
                x, region = u(f"{key}|territory"), TERRITORIES[-1]
                for r in TERRITORIES:
                    x -= quota[r] / total
                    if x < 0:
                        region = r
                        break
                c = new_logo(p, region, size, key)
                book(p, c, "New Business", size, team_name=t)
                last[c] = p
                booked[t] += size
                count[t] += 1

        for kind in MOVES:
            for c in sorted(prev):
                if c in h.moved[p] or last[c] >= months[0] or (kind == "Expansion" and c in expanded):
                    continue
                if kind == "Expansion" and not stays_on_book(c):
                    continue
                if u(f"{kind}|{p}|{c}") < rates.move[kind]:
                    a = q(prev[c] * _draw(rates.shares[kind], f"{kind}size|{p}|{c}"))
                    if a > 0:
                        book(p, c, kind, a)
                        if kind == "Expansion":
                            expanded.add(c)
        if targets and p in targets:
            fit_month_to_target(h, deals, p, targets[p])
        h.close_month(p)
    return deals
