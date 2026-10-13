"""Rebuild the marketing funnel so lead volume follows program spend and plan bookings follow the CRM.

  python rebuild_marketing_funnel.py <dataset_folder> <out_folder>

Copies <dataset_folder> to <out_folder> and rewrites the marketing files there. Run it after
sync_v5_statements.py, so each month's marketing spend already equals the GL program accounts.

Rules:
  * Cost per MQL is one rate per channel: the channel's Actual spend / its Actual MQLs over every
    Actual month. Every month in every version: MQLs = channel spend / that rate (whole leads).
  * Actual: SQLs, SALs and opportunities come from the MQLs at the month's own conversion rates
    (Actual_funnel_conversion_rates.csv).
  * Actual pipeline is the channel split of the company New Business pipeline waterfall
    (Actual_pipeline_waterfall.csv), so the channels add up to it every month:
      - pipeline created: the month's company pipeline created x the channel's share of that month's spend;
      - closed-won: the CRM's New Business deals closed that month by channel (Actual_opportunities.csv);
        a month with no deals in the CRM splits the company closed-won by pipeline created x the
        channel's win rate over the CRM months;
      - closed lost and slipped: the company amounts split by each channel's open pipeline
        (beginning + created - closed-won); ending = what remains, and the next month begins there.
        The first month's beginning pipeline is split by that month's spend.
  * Forecast after the close and Budget: conversion rates are the channel's Actual totals (SQL / MQL,
    SAL / SQL, opportunities / SQL, closed-won / pipeline). Closed-won ARR is the channel's Actual
    share of new business (closed-won / the Actual history's New Business ARR, rescaled over the
    channels the version plans) times the version's own New Business ARR that month
    (<version>_customer_arr_history.csv). Pipeline created = closed-won / the channel's Actual win rate.
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


def hundredths(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), ROUND_HALF_UP)


def ratio(a: Decimal, b: Decimal, places: str = "0.0001") -> str:
    return f"{(a / b).quantize(Decimal(places), ROUND_HALF_UP)}" if b else ""


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

    spend = {p: {c: num(by_month[p][c]["marketing_spend"]) for c in channels} for p in months}
    created = {p: split(num(wf[p]["new_pipeline_created"]), spend[p], f"{p} pipeline created") for p in months}
    won_crm = {c: sum((crm[p].get(c, ZERO) for p in crm_months), ZERO) for c in channels}
    created_crm = {c: sum((created[p][c] for p in crm_months), ZERO) for c in channels}
    win = {c: won_crm[c] / created_crm[c] if created_crm[c] else ZERO for c in channels}

    prev: dict[str, Decimal] | None = None
    for p in months:
        w = {k: num(wf[p][col]) for k, col in WATERFALL_COLUMNS.items()}
        if p in crm:
            won = {c: crm[p].get(c, ZERO) for c in channels}
        else:
            won = split(w["closed_won_arr"], {c: created[p][c] * win[c] for c in channels}, f"{p} closed-won")
        if prev is None:
            begin = split(w["beginning_pipeline_arr"], spend[p], f"{p} beginning pipeline")
        else:
            if abs(sum(prev.values(), ZERO) - w["beginning_pipeline_arr"]) > Decimal("0.01"):
                raise SystemExit(f"{p}: pipeline waterfall beginning {w['beginning_pipeline_arr']} != prior ending")
            begin = prev
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

    spend: dict[str, Decimal] = defaultdict(Decimal)
    mqls: dict[str, Decimal] = defaultdict(Decimal)
    for r in actual:
        spend[r["marketing_channel"]] += num(r["marketing_spend"])
        mqls[r["marketing_channel"]] += num(r["mqls"])
    cpl = {c: spend[c] / mqls[c] for c in spend if mqls[c]}
    missing = sorted(c for c in spend if c not in cpl)
    if missing:
        raise SystemExit(f"no Actual MQLs to price channels {missing}")

    for r in actual:
        key = (r["period"][:7], r["marketing_channel"])
        rates = conv.get(key)
        if rates is None:
            raise SystemExit(f"no Actual conversion rates for {key}")
        m = whole(num(r["marketing_spend"]) / cpl[r["marketing_channel"]])
        s = whole(m * num(rates["mql_to_sql_rate"]))
        r["mqls"], r["sqls"] = count(m), count(s)
        r["sals"] = count(whole(s * num(rates["sql_to_sal_rate"])))
        r["opportunities_created"] = hundredths(s * num(rates["sql_to_opportunity_rate"]))
    notes += rebuild_actual_pipeline(path, actual)
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
        for k in COUNT_KEYS + ("pipeline_arr_created", "closed_won_arr"):
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
            "share": t["closed_won_arr"] / actual_nb,
        }
    notes.append(f"Actual {months[0]}..{months[-1]}: New Business ARR {actual_nb:,.2f}; marketing closed-won "
                 f"{sum((t['closed_won_arr'] for t in tot.values()), ZERO):,.2f}")
    for c in sorted(rate):
        x = rate[c]
        notes.append(f"{c}: cost per MQL {cpl[c]:,.2f}; MQL->SQL {x['sql']:.4f}, SQL->SAL {x['sal']:.4f}, "
                     f"SQL->opportunity {x['opp']:.4f}, win rate {x['win']:.4f}, share of New Business {x['share']:.4f}")

    for v in PLAN_VERSIONS:
        vf, vrows = read(path(f"{v}_marketing_pipeline.csv"))
        unknown = sorted({r["marketing_channel"] for r in vrows} - set(cpl))
        if unknown:
            raise SystemExit(f"{v} channels with no Actual history: {unknown}")
        planned = sorted({r["marketing_channel"] for r in vrows})
        planned_share = sum((rate[c]["share"] for c in planned), ZERO)
        if not planned_share:
            raise SystemExit(f"{v} channels have no Actual closed-won to share New Business by")
        unplanned = sorted(set(rate) - set(planned))
        if unplanned:
            notes.append(f"{v} plans no rows for {unplanned}; its New Business is shared over the {len(planned)} "
                         f"planned channels ({planned_share:.4f} of the Actual share)")
        for r in vrows:
            p, c = r["period"][:7], r["marketing_channel"]
            if v == "Forecast" and p <= CLOSE:
                a = by_key.get((p, c))
                if a is None:
                    raise SystemExit(f"Forecast {p} {c}: no Actual row for a closed month")
                for k in COUNT_KEYS + MONEY_KEYS:
                    if k in vf:
                        r[k] = a["closed_won_arr"] if k == "expected_closed_won_arr" else a[k]
                r["marketing_spend"] = a["marketing_spend"]
                set_ratios(r, vf)
                continue
            x = rate[c]
            m = whole(num(r["marketing_spend"]) / cpl[c])
            s = whole(m * x["sql"])
            r["mqls"], r["sqls"] = count(m), count(s)
            if "sals" in vf:
                r["sals"] = count(whole(s * x["sal"]))
            r["opportunities_created"] = hundredths(s * x["opp"])
            won = q(x["share"] / planned_share * nb[v].get(p, ZERO))
            r["closed_won_arr"] = won
            if "expected_closed_won_arr" in vf:
                r["expected_closed_won_arr"] = won
            r["pipeline_arr_created"] = q(won / x["win"]) if x["win"] else ZERO
            set_ratios(r, vf)
        write(path(f"{v}_marketing_pipeline.csv"), vf, vrows)
        notes.append(f"{v}: {len(vrows)} rows rebuilt; New Business ARR {sum(nb[v].values(), ZERO):,.2f}")

    summ = path("Forecast_marketing_pipeline_summary.csv")
    if os.path.exists(summ):
        _, frows = read(path("Forecast_marketing_pipeline.csv"))
        agg: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
        for r in frows:
            for k in ("mqls", "sqls", "opportunities_created", "pipeline_arr_created", "closed_won_arr", "marketing_spend"):
                agg[r["period"][:7]][k] += num(r[k])
        f_, rows = read(summ)
        for r in rows:
            a = agg.get(r["period"][:7])
            if a is None:
                raise SystemExit(f"Forecast summary month {r['period'][:7]} has no pipeline rows")
            r["forecast_marketing_pipeline_arr"] = q(a["pipeline_arr_created"])
            r["forecast_marketing_sourced_closed_won_arr"] = q(a["closed_won_arr"])
            r["forecast_marketing_spend"] = q(a["marketing_spend"])
            r["mqls"], r["sqls"] = count(a["mqls"]), count(a["sqls"])
            r["opportunities_created"] = hundredths(a["opportunities_created"])
            r["pipeline_coverage_ratio"] = ratio(a["pipeline_arr_created"], a["closed_won_arr"], "0.01")
            r["spend_as_percent_of_pipeline"] = ratio(a["marketing_spend"], a["pipeline_arr_created"])
            r["marketing_spend_as_percent_of_closed_won_arr"] = ratio(a["marketing_spend"], a["closed_won_arr"])
        write(summ, f_, rows)
    return notes


if __name__ == "__main__":
    for n in main(sys.argv[1], sys.argv[2]):
        print(n)
