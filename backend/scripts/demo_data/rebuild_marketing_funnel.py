"""Rebuild the marketing funnel: Actual lead volume follows program spend; plan funnels run back from plan bookings.

  python rebuild_marketing_funnel.py <dataset_folder> <out_folder>

Copies <dataset_folder> to <out_folder> and rewrites the marketing files there. Run it after
sync_v5_statements.py, so each month's marketing spend already equals the GL program accounts.

Rules:
  * A channel's deal size is the average of its CRM New Business deals (Actual_opportunities.csv). Every month,
    version and channel: opportunities = the version's New Business deals created that month in the channel, plus
    the rest of the pipeline created / that deal size (whole opportunities; at least one when any is left).
  * Actual: SQLs = opportunities / the month's SQL-to-opportunity rate, MQLs = SQLs / its MQL-to-SQL rate, SALs =
    SQLs x its SQL-to-SAL rate (Actual_funnel_conversion_rates.csv; whole leads). Cost per MQL = spend / MQLs.
  * Actual pipeline is the channel split of the company New Business pipeline waterfall
    (Actual_pipeline_waterfall.csv), so the channels add up to it every month:
      - pipeline created: the month's company pipeline created x the channel's share of that month's spend; a
        channel creates at least the CRM deals created in it that month (the rest is split over the other channels
        by spend);
      - closed-won: the CRM's New Business deals closed that month by channel (Actual_opportunities.csv);
        a month with no deals in the CRM splits the company closed-won by pipeline created x the
        channel's win rate over the CRM months, no channel closing more than its open pipeline (beginning +
        created; what it cannot hold goes to the other channels by the same weights);
      - closed lost and slipped: the company amounts split by each channel's open pipeline
        (beginning + created - closed-won); ending = what remains, and the next month begins there.
        The first month's beginning pipeline is split by that month's spend. In the CRM months
        rebuild_opportunity_movements.py restates lost and slipped by channel from the deals.
  * A plan version that omits an Actual channel plans it every month at the channel's Actual share of spend over
    the (up to) 12 Actual months before the version's first plan month; the other channels' spend scales so each
    month's total (GL marketing programs) is unchanged.
  * Forecast after the close and Budget are the version's New Business pipeline waterfall split by channel
    (<version>_pipeline_waterfall.csv), so the channels add up to it to the cent every month, and the funnel runs
    back from it at the channel's Actual totals. Closed-won is the version's New Business deals that month by
    channel (<version>_opportunities.csv; Budget at their ARR, Forecast at expected ARR); they and the version's
    New Business ARR (<version>_customer_arr_history.csv) must both equal the waterfall's closed-won. Pipeline
    created splits the waterfall's by the month's spend, each channel creating at least the deals created in it
    that month (as in the Actual months). Opportunities as above; SQLs = opportunities / the Actual opportunities per SQL;
    MQLs = SQLs / the Actual SQLs per MQL; SALs = SQLs x the Actual SALs per SQL.
    Cost per MQL is the plan's spend / those MQLs, so it moves when planned spend and planned bookings
    diverge.
  * Forecast months through the close are the Actual rows.
  * Ratio columns are recomputed from the rebuilt counts; Forecast_marketing_pipeline_summary.csv is
    the monthly total of Forecast_marketing_pipeline.csv.
"""

from __future__ import annotations

import os
import shutil
import sys
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sync_v5_statements import ZERO, num, q, read, write  # noqa: E402

CLOSE = "2026-06"
PLAN_VERSIONS = ("Forecast", "Budget")
COUNT_KEYS = ("mqls", "sqls", "sals", "opportunities_created")
MONEY_KEYS = ("pipeline_arr_created", "closed_won_arr", "expected_closed_won_arr")
NB_COLUMN = "new_business_arr"
NB_TYPE = "New Business"
WATERFALL_COLUMNS = {
    "beginning_pipeline_arr": "beginning_pipeline_arr",
    "pipeline_arr_created": "new_pipeline_created",
    "closed_won_arr": "closed_won_arr",
    "closed_lost_arr": "closed_lost_arr",
    "slipped_pipeline_arr": "slipped_arr",
    "ending_pipeline_arr": "ending_pipeline_arr",
}
ACTUAL_NOTE = "Channel split of the New Business pipeline waterfall; closed-won from CRM deals"


def whole(x: Decimal) -> Decimal:
    return x.quantize(Decimal("1"), ROUND_HALF_UP)


def count(x: Decimal) -> str:
    return str(int(x))


def ratio(a: Decimal, b: Decimal, places: str = "0.0001") -> str:
    return f"{(a / b).quantize(Decimal(places), ROUND_HALF_UP)}" if b else ""


def crm_deal_size(path) -> dict[str, Decimal]:
    """Each channel's average CRM New Business deal."""
    _, rows = read(path("Actual_opportunities.csv"))
    amount: dict[str, Decimal] = defaultdict(Decimal)
    deals: dict[str, int] = defaultdict(int)
    for r in rows:
        if r["opportunity_type"] == NB_TYPE and r["close_status"] == "Closed Won":
            c = r["marketing_channel"]
            if num(r["amount_arr"]) <= 0:
                raise SystemExit(f"CRM New Business deal with no ARR: {r['period'][:7]} {c} {r['amount_arr']}")
            amount[c] += num(r["amount_arr"])
            deals[c] += 1
    return {c: amount[c] / deals[c] for c in deals}


def deals_created(path, v: str) -> tuple[dict[tuple[str, str], Decimal], dict[tuple[str, str], int]]:
    """A version's New Business deals by the month they were created and channel: their pipeline (Actual and Budget
    at ARR, Forecast at expected ARR) and how many."""
    _, rows = read(path(f"{v}_opportunities.csv"))
    amount: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    n: dict[tuple[str, str], int] = defaultdict(int)
    for o in rows:
        if o["opportunity_type"] == NB_TYPE and (v != "Actual" or o["close_status"] == "Closed Won"):
            k = (o["created_date"][:7], o["marketing_channel"])
            amount[k] += num(o["weighted_arr" if v == "Forecast" else "amount_arr"])
            n[k] += 1
    return amount, n


def opportunities(pipeline: Decimal, deal_size: Decimal, made: int = 0, made_arr: Decimal = ZERO) -> Decimal:
    """The deals created that month plus the rest of the pipeline in deals of the channel's size (at least one)."""
    rest = pipeline - made_arr
    if rest < 0:
        raise SystemExit(f"pipeline created {pipeline} is below the deals created that month {made_arr}")
    return Decimal(made) + (max(whole(rest / deal_size), Decimal(1)) if rest > 0 else ZERO)


def plan_deals(path, v: str) -> dict[tuple[str, str], Decimal]:
    """A plan's New Business deals by month and channel: Budget at their ARR, Forecast at expected (weighted) ARR."""
    _, rows = read(path(f"{v}_opportunities.csv"))
    out: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for o in rows:
        if o["opportunity_type"] == NB_TYPE:
            out[(o["period"][:7], o["marketing_channel"])] += num(o["weighted_arr" if v == "Forecast" else "amount_arr"])
    return out


def new_business_by_month(path: str) -> dict[str, Decimal]:
    _, rows = read(path)
    out: dict[str, Decimal] = defaultdict(Decimal)
    for r in rows:
        if r["waterfall_column"] == NB_COLUMN:
            out[r["period"][:7]] += num(r["movement_arr"])
    return out


def set_ratios(r: dict, fields: list[str]) -> None:
    spend = num(r["marketing_spend"])
    mqls, sqls = num(r["mqls"]), num(r["sqls"])
    if "cost_per_mql" in fields:
        r["cost_per_mql"] = q(spend / mqls) if mqls else ""
    if "cost_per_sql" in fields:
        r["cost_per_sql"] = q(spend / sqls) if sqls else ""
    if "pipeline_per_dollar_spend" in fields:
        r["pipeline_per_dollar_spend"] = ratio(num(r["pipeline_arr_created"]), spend)
    if "pipeline_coverage_ratio" in fields:
        r["pipeline_coverage_ratio"] = ratio(num(r["pipeline_arr_created"]), num(r["closed_won_arr"]), "0.01")
    if "win_rate_on_pipeline_created" in fields:
        r["win_rate_on_pipeline_created"] = ratio(num(r["closed_won_arr"]), num(r["pipeline_arr_created"]))
    if "marketing_cac_proxy" in fields:
        r["marketing_cac_proxy"] = ratio(spend, num(r["closed_won_arr"]))


def split(total: Decimal, weights: dict[str, Decimal], what: str) -> dict[str, Decimal]:
    """Cents in proportion to the weights that add back to the total; the largest weight takes the rounding."""
    tw = sum(weights.values(), ZERO)
    if tw <= 0:
        if total:
            raise SystemExit(f"{what}: {total} to split but no weight")
        return {c: ZERO for c in weights}
    out = {c: q(total * w / tw) for c, w in weights.items()}
    big = max(weights, key=lambda c: weights[c])
    out[big] += total - sum(out.values(), ZERO)
    return out


def floored_split(total: Decimal, weights: dict[str, Decimal], floors: dict[str, Decimal], what: str) -> dict[str, Decimal]:
    """split() with no share below its floor: a share under its floor is held at the floor and the rest is split
    again over the others by their weights."""
    if total < sum(floors.values(), ZERO):
        raise SystemExit(f"{what}: {total} is below the floors {sum(floors.values(), ZERO)}")
    held: dict[str, Decimal] = {}
    while True:
        free = {c: w for c, w in weights.items() if c not in held}
        out = split(total - sum(held.values(), ZERO), free, what)
        under = [c for c in free if out[c] < floors[c]]
        if not under:
            return {**held, **out}
        held.update({c: floors[c] for c in under})


def capped_split(total: Decimal, weights: dict[str, Decimal], caps: dict[str, Decimal], what: str) -> dict[str, Decimal]:
    """split() with no share above its cap: a capped share is held at the cap and the rest is split again over the
    others by their weights (by their caps when none of them has weight)."""
    if total > sum(caps.values(), ZERO):
        raise SystemExit(f"{what}: {total} exceeds the caps {sum(caps.values(), ZERO)}")
    held: dict[str, Decimal] = {}
    while True:
        free = {c: w for c, w in weights.items() if c not in held}
        if sum(free.values(), ZERO) <= 0:
            free = {c: caps[c] for c in free}
        out = split(total - sum(held.values(), ZERO), free, what)
        over = [c for c in free if out[c] > caps[c]]
        if not over:
            return {**held, **out}
        held.update({c: caps[c] for c in over})


def plan_every_channel(v: str, fields: list[str], rows: list[dict], actual: list[dict]) -> tuple[list[dict], list[str]]:
    """Rows for the Actual channels the version omits, at their Actual share of spend (see module doc)."""
    channels = sorted({r["marketing_channel"] for r in actual})
    missing = sorted(set(channels) - {r["marketing_channel"] for r in rows})
    if not missing:
        return rows, []
    plan = sorted({r["period"][:7] for r in rows if not (v == "Forecast" and r["period"][:7] <= CLOSE)})
    window = sorted({r["period"][:7] for r in actual if r["period"][:7] < plan[0]})[-12:]
    if not window:
        raise SystemExit(f"{v}: no Actual months before {plan[0]} to plan {missing} from")
    spend: dict[str, Decimal] = defaultdict(Decimal)
    for r in actual:
        if r["period"][:7] in window:
            spend[r["marketing_channel"]] += num(r["marketing_spend"])
    total = sum(spend.values(), ZERO)
    if not total:
        raise SystemExit(f"{v}: no Actual spend in {window[0]}..{window[-1]} to plan {missing} from")
    share = {c: spend[c] / total for c in missing}
    by_month: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_month[r["period"][:7]].append(r)
    out = []
    for p in sorted(by_month):
        month = by_month[p]
        spent = sum((num(r["marketing_spend"]) for r in month), ZERO)
        added = {c: q(spent * share[c]) for c in missing}
        rest = split(spent - sum(added.values(), ZERO), {r["marketing_channel"]: num(r["marketing_spend"]) for r in month},
                     f"{v} {p} spend")
        for r in month:
            r["marketing_spend"] = rest[r["marketing_channel"]]
        out += month + [{**{k: "" for k in fields}, **{k: month[0][k] for k in ("organization_id", "version", "period")
                                                       if k in fields},
                         "marketing_channel": c, "marketing_spend": added[c]} for c in missing]
    return out, [f"{v} plans {missing} at their Actual share of spend over {window[0]}..{window[-1]} "
                 f"({', '.join(f'{c} {share[c]:.4f}' for c in missing)}); the other channels' spend scales to the month's total"]


def rebuild_actual_pipeline(path, actual: list[dict]) -> list[str]:
    """Actual channel pipeline = the company New Business pipeline waterfall split by channel (see module doc)."""
    _, wf_rows = read(path("Actual_pipeline_waterfall.csv"))
    wf = {r["period"][:7]: r for r in wf_rows if r["opportunity_type"] == NB_TYPE}
    _, opp_rows = read(path("Actual_opportunities.csv"))
    crm: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for r in opp_rows:
        if r["opportunity_type"] == NB_TYPE and r["close_status"] == "Closed Won":
            crm[r["period"][:7]][r["marketing_channel"]] += num(r["amount_arr"])

    by_month: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in actual:
        by_month[r["period"][:7]][r["marketing_channel"]] = r
    months = sorted(by_month)
    channels = sorted({r["marketing_channel"] for r in actual})
    gaps = [f"{p} {c}" for p in months for c in channels if c not in by_month[p]]
    if gaps:
        raise SystemExit(f"Actual marketing pipeline has no row for {gaps}")
    missing = [p for p in months if p not in wf]
    if missing:
        raise SystemExit(f"no New Business pipeline waterfall for {missing}")
    unknown = sorted({c for p in crm for c in crm[p]} - set(channels))
    if unknown:
        raise SystemExit(f"CRM New Business deals in channels with no marketing rows: {unknown}")
    crm_months = [p for p in months if p in crm]
    if not crm_months:
        raise SystemExit("no CRM New Business deals in the Actual months")
    for p in crm_months:
        booked = sum(crm[p].values(), ZERO)
        if abs(booked - num(wf[p]["closed_won_arr"])) > Decimal("0.01"):
            raise SystemExit(f"{p}: CRM New Business deals {booked} != pipeline waterfall closed-won {wf[p]['closed_won_arr']}")

    made, _ = deals_created(path, "Actual")
    unknown = sorted({f"{p} {c}" for p, c in made if p not in by_month or c not in channels})
    if unknown:
        raise SystemExit(f"CRM New Business deals created in months or channels with no marketing rows: {unknown}")
    spend = {p: {c: num(by_month[p][c]["marketing_spend"]) for c in channels} for p in months}
    created = {p: floored_split(num(wf[p]["new_pipeline_created"]), spend[p],
                                {c: made.get((p, c), ZERO) for c in channels},
                                f"{p} pipeline created") for p in months}
    won_crm = {c: sum((crm[p].get(c, ZERO) for p in crm_months), ZERO) for c in channels}
    created_crm = {c: sum((created[p][c] for p in crm_months), ZERO) for c in channels}
    win = {c: won_crm[c] / created_crm[c] if created_crm[c] else ZERO for c in channels}

    prev: dict[str, Decimal] | None = None
    for p in months:
        w = {k: num(wf[p][col]) for k, col in WATERFALL_COLUMNS.items()}
        if prev is None:
            begin = split(w["beginning_pipeline_arr"], spend[p], f"{p} beginning pipeline")
        else:
            if abs(sum(prev.values(), ZERO) - w["beginning_pipeline_arr"]) > Decimal("0.01"):
                raise SystemExit(f"{p}: pipeline waterfall beginning {w['beginning_pipeline_arr']} != prior ending")
            begin = prev
        if p in crm:
            won = {c: crm[p].get(c, ZERO) for c in channels}
        else:
            won = capped_split(w["closed_won_arr"], {c: created[p][c] * win[c] for c in channels},
                               {c: begin[c] + created[p][c] for c in channels}, f"{p} closed-won")
        open_ = {c: begin[c] + created[p][c] - won[c] for c in channels}
        short = [f"{c} {open_[c]}" for c in channels if open_[c] < 0]
        if short:
            raise SystemExit(f"{p}: closed-won exceeds open pipeline for {short}")
        lost = split(w["closed_lost_arr"], open_, f"{p} closed lost")
        slipped = split(w["slipped_pipeline_arr"], open_, f"{p} slipped")
        end = {c: open_[c] - lost[c] - slipped[c] for c in channels}
        if any(v < 0 for v in end.values()) or abs(sum(end.values(), ZERO) - w["ending_pipeline_arr"]) > Decimal("0.01"):
            raise SystemExit(f"{p}: channel ending pipeline does not foot to the waterfall")
        for c in channels:
            r = by_month[p][c]
            r["beginning_pipeline_arr"], r["pipeline_arr_created"], r["closed_won_arr"] = begin[c], created[p][c], won[c]
            r["closed_lost_arr"], r["slipped_pipeline_arr"], r["ending_pipeline_arr"] = lost[c], slipped[c], end[c]
            if "notes" in r:
                r["notes"] = ACTUAL_NOTE
        prev = end

    notes = [f"Actual pipeline: {len(months)} months split from the New Business pipeline waterfall; closed-won from "
             f"CRM deals in {crm_months[0]}..{crm_months[-1]}"]
    notes += [f"  {c}: CRM win rate {win[c]:.4f} (won {won_crm[c]:,.2f} of {created_crm[c]:,.2f} created)" for c in channels]
    return notes


def main(src: str, dst: str) -> list[str]:
    if not (os.path.isabs(src) and os.path.isabs(dst)):
        raise SystemExit("folders must be absolute paths")
    if os.path.exists(dst):
        raise SystemExit(f"{dst} exists; pick a new folder")
    shutil.copytree(src, dst)
    notes: list[str] = []
    path = lambda name: os.path.join(dst, name)  # noqa: E731

    af, actual = read(path("Actual_marketing_pipeline.csv"))
    _, conv_rows = read(path("Actual_funnel_conversion_rates.csv"))
    conv = {(r["period"][:7], r["marketing_channel"]): r for r in conv_rows}
    if any(r["period"][:7] > CLOSE for r in actual):
        raise SystemExit(f"Actual marketing pipeline runs past the {CLOSE} close")

    notes += rebuild_actual_pipeline(path, actual)
    deal = crm_deal_size(path)
    made_arr, made_n = deals_created(path, "Actual")
    unsized = sorted({r["marketing_channel"] for r in actual} - set(deal))
    if unsized:
        raise SystemExit(f"no CRM New Business deals to size opportunities in channels {unsized}")
    for r in actual:
        key = (r["period"][:7], r["marketing_channel"])
        rates = conv.get(key)
        if rates is None:
            raise SystemExit(f"no Actual conversion rates for {key}")
        to_opp, to_sql = num(rates["sql_to_opportunity_rate"]), num(rates["mql_to_sql_rate"])
        if not (to_opp > 0 and to_sql > 0):
            raise SystemExit(f"{key}: conversion rates must be positive to run opportunities back to leads")
        o = opportunities(num(r["pipeline_arr_created"]), deal[key[1]], made_n.get(key, 0), made_arr.get(key, ZERO))
        s = whole(o / to_opp)
        r["opportunities_created"], r["sqls"] = count(o), count(s)
        r["mqls"] = count(whole(s / to_sql))
        r["sals"] = count(whole(s * num(rates["sql_to_sal_rate"])))
    for r in actual:
        set_ratios(r, af)
    write(path("Actual_marketing_pipeline.csv"), af, actual)
    by_key = {(r["period"][:7], r["marketing_channel"]): r for r in actual}

    cf, conv_rows = read(path("Actual_funnel_conversion_rates.csv"))
    for r in conv_rows:
        a = by_key[(r["period"][:7], r["marketing_channel"])]
        for k in ("closed_won_arr", "pipeline_arr_created"):
            if k in cf:
                r[k] = a[k]
        if "pipeline_to_closed_won_rate" in cf:
            r["pipeline_to_closed_won_rate"] = ratio(num(a["closed_won_arr"]), num(a["pipeline_arr_created"]))
    write(path("Actual_funnel_conversion_rates.csv"), cf, conv_rows)

    sf, srows = read(path("Actual_marketing_spend_by_channel.csv"))
    for r in srows:
        a = by_key[(r["period"][:7], r["marketing_channel"])]
        r["cost_per_sql"] = a["cost_per_sql"]
    write(path("Actual_marketing_spend_by_channel.csv"), sf, srows)

    tot: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for r in actual:
        t = tot[r["marketing_channel"]]
        for k in COUNT_KEYS + ("pipeline_arr_created", "closed_won_arr", "marketing_spend"):
            t[k] += num(r[k])
    nb = {v: new_business_by_month(path(f"{v}_customer_arr_history.csv")) for v in ("Actual",) + PLAN_VERSIONS}
    months = sorted({r["period"][:7] for r in actual})
    actual_nb = sum((nb["Actual"].get(p, ZERO) for p in months), ZERO)
    if not actual_nb:
        raise SystemExit("no Actual New Business ARR in the history")
    rate = {}
    for c, t in tot.items():
        rate[c] = {
            "sql": t["sqls"] / t["mqls"] if t["mqls"] else ZERO,
            "sal": t["sals"] / t["sqls"] if t["sqls"] else ZERO,
            "opp": t["opportunities_created"] / t["sqls"] if t["sqls"] else ZERO,
            "win": t["closed_won_arr"] / t["pipeline_arr_created"] if t["pipeline_arr_created"] else ZERO,
        }
    notes.append(f"Actual {months[0]}..{months[-1]}: New Business ARR {actual_nb:,.2f}; marketing closed-won "
                 f"{sum((t['closed_won_arr'] for t in tot.values()), ZERO):,.2f}")
    for c in sorted(rate):
        x, t = rate[c], tot[c]
        notes.append(f"{c}: deal size {deal[c]:,.2f}, {t['opportunities_created']:.0f} opportunities, cost per MQL "
                     f"{t['marketing_spend'] / t['mqls']:,.2f}; MQL->SQL {x['sql']:.4f}, SQL->SAL {x['sal']:.4f}, "
                     f"SQL->opportunity {x['opp']:.4f}, win rate {x['win']:.4f}")
    no_funnel = [c for c in sorted(rate) if not all(rate[c][k] for k in ("sql", "opp"))]
    if no_funnel:
        raise SystemExit(f"channels with no Actual funnel to run plan bookings back through: {no_funnel}")

    for v in PLAN_VERSIONS:
        vf, vrows = read(path(f"{v}_marketing_pipeline.csv"))
        unknown = sorted({r["marketing_channel"] for r in vrows} - set(rate))
        if unknown:
            raise SystemExit(f"{v} channels with no Actual history: {unknown}")
        vrows, added = plan_every_channel(v, vf, vrows, actual)
        if v == "Forecast":
            vrows = [r for r in vrows if r["period"][:7] > CLOSE]
        notes += added
        _, wf_rows = read(path(f"{v}_pipeline_waterfall.csv"))
        wf = {r["period"][:7]: r for r in wf_rows if r["opportunity_type"] == NB_TYPE}
        booked = plan_deals(path, v)
        made_arr, made_n = deals_created(path, v)
        by_month: dict[str, list[dict]] = defaultdict(list)
        for r in vrows:
            by_month[r["period"][:7]].append(r)
        stray = sorted({f"{p} {c}" for p, c in list(booked) + list(made_arr) if (v != "Forecast" or p > CLOSE)
                        and c not in {r["marketing_channel"] for r in by_month.get(p, [])}})
        if stray:
            raise SystemExit(f"{v} New Business deals in channels or months with no marketing row: {stray}")
        won: dict[tuple[str, str], Decimal] = {}
        pipe: dict[tuple[str, str], Decimal] = {}
        for p, month in sorted(by_month.items()):
            w = wf.get(p)
            if w is None:
                raise SystemExit(f"{v} {p}: no New Business pipeline waterfall")
            if num(w["closed_won_arr"]) != nb[v].get(p, ZERO):
                raise SystemExit(f"{v} {p}: pipeline waterfall closed-won {w['closed_won_arr']} != New Business ARR "
                                 f"{nb[v].get(p, ZERO)}")
            channels = [r["marketing_channel"] for r in month]
            won.update({(p, c): booked.get((p, c), ZERO) for c in channels})
            if sum((won[(p, c)] for c in channels), ZERO) != num(w["closed_won_arr"]):
                raise SystemExit(f"{v} {p}: New Business deals {sum((won[(p, c)] for c in channels), ZERO)} != "
                                 f"pipeline waterfall closed-won {w['closed_won_arr']}")
            pipe.update({(p, c): a for c, a in floored_split(
                num(w["new_pipeline_created"]), {r["marketing_channel"]: num(r["marketing_spend"]) for r in month},
                {c: made_arr.get((p, c), ZERO) for c in channels}, f"{v} {p} pipeline created").items()})
        for r in vrows:
            p, c = r["period"][:7], r["marketing_channel"]
            x = rate[c]
            opps = opportunities(pipe[(p, c)], deal[c], made_n.get((p, c), 0), made_arr.get((p, c), ZERO))
            s = whole(opps / x["opp"])
            r["mqls"], r["sqls"] = count(whole(s / x["sql"])), count(s)
            if "sals" in vf:
                r["sals"] = count(whole(s * x["sal"]))
            r["opportunities_created"] = count(opps)
            r["closed_won_arr"] = won[(p, c)]
            if "expected_closed_won_arr" in vf:
                r["expected_closed_won_arr"] = won[(p, c)]
            r["pipeline_arr_created"] = pipe[(p, c)]
            set_ratios(r, vf)
        write(path(f"{v}_marketing_pipeline.csv"), vf, vrows)
        notes.append(f"{v}: {len(vrows)} rows rebuilt; New Business ARR {sum(nb[v].values(), ZERO):,.2f}")

    summ = path("Forecast_marketing_pipeline_summary.csv")
    if os.path.exists(summ):
        _, frows = read(path("Forecast_marketing_pipeline.csv"))
        agg: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
        for r in frows:
            if r["period"][:7] <= CLOSE:
                raise SystemExit(f"Forecast marketing pipeline still has the closed month {r['period'][:7]}")
            for k in ("mqls", "sqls", "opportunities_created", "pipeline_arr_created", "closed_won_arr", "marketing_spend"):
                agg[r["period"][:7]][k] += num(r[k])
        f_, existing = read(summ)
        org = next((r.get("organization_id") for r in existing if r.get("organization_id")), "")
        rows = []
        for p in sorted(agg):
            a = agg[p]
            r = {"organization_id": org, "version": "Forecast", "period": p}
            r["forecast_marketing_pipeline_arr"] = q(a["pipeline_arr_created"])
            r["forecast_marketing_sourced_closed_won_arr"] = q(a["closed_won_arr"])
            r["forecast_marketing_spend"] = q(a["marketing_spend"])
            r["mqls"], r["sqls"] = count(a["mqls"]), count(a["sqls"])
            r["opportunities_created"] = count(a["opportunities_created"])
            r["pipeline_coverage_ratio"] = ratio(a["pipeline_arr_created"], a["closed_won_arr"], "0.01")
            r["spend_as_percent_of_pipeline"] = ratio(a["marketing_spend"], a["pipeline_arr_created"])
            r["marketing_spend_as_percent_of_closed_won_arr"] = ratio(a["marketing_spend"], a["closed_won_arr"])
            rows.append(r)
        write(summ, f_, rows)
    return notes


if __name__ == "__main__":
    for n in main(sys.argv[1], sys.argv[2]):
        print(n)
