"""Rebuild the marketing funnel so lead volume follows program spend and plan bookings follow the CRM.

  python rebuild_marketing_funnel.py <dataset_folder> <out_folder>

Copies <dataset_folder> to <out_folder> and rewrites the marketing files there. Run it after
sync_v5_statements.py, so each month's marketing spend already equals the GL program accounts.

Rules:
  * Cost per MQL is one rate per channel: the channel's Actual spend / its Actual MQLs over every
    Actual month. Every month in every version: MQLs = channel spend / that rate (whole leads).
  * Actual: SQLs, SALs and opportunities come from the MQLs at the month's own conversion rates
    (Actual_funnel_conversion_rates.csv). Pipeline and closed-won ARR stay as loaded.
  * Forecast after the close and Budget: conversion rates are the channel's Actual totals (SQL / MQL,
    SAL / SQL, opportunities / SQL, closed-won / pipeline). Closed-won ARR is the channel's Actual
    share of new business (closed-won / the Actual history's New Business ARR) times the version's
    own New Business ARR that month (<version>_customer_arr_history.csv). Pipeline created =
    closed-won / the channel's Actual win rate.
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
    if "pipeline_coverage_ratio" in fields and r.get("version") != "Actual":
        r["pipeline_coverage_ratio"] = ratio(num(r["pipeline_arr_created"]), num(r["closed_won_arr"]), "0.01")


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
        set_ratios(r, af)
    write(path("Actual_marketing_pipeline.csv"), af, actual)
    by_key = {(r["period"][:7], r["marketing_channel"]): r for r in actual}

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
            won = q(x["share"] * nb[v].get(p, ZERO))
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
