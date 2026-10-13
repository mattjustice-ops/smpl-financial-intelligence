"""Reshape the backfilled Actual ARR history so its movements run into the first operating month.

  python reshape_history_waterfall.py <dataset_folder> <out_folder>

Copies <dataset_folder> to <out_folder> and rewrites the history months (the Actual months before the first
month with CRM opportunities) of Actual_MRR_Waterfall.csv and Actual_pipeline_waterfall.csv. Run it first,
before reclass_support_labor.py.

Rules:
  * Each movement's rate (movement / beginning ARR) ramps on a straight line from the history's own level in
    the first history month to the first operating month's rate: month i of n is scaled by
    1 + (R - 1) x i / n, where R = the first operating month's rate / the history's average rate. Month-to-month
    swings in the history stay.
  * The history's year-end ARR (each December) and its first beginning ARR stay. New business in each year is
    scaled by one factor so the year ends on its ARR; it is the movement the CRM pipeline converts.
  * Pipeline waterfall: closed-won of each opportunity type moves to the reshaped movement, and pipeline
    created moves by the same amount, so beginning, lost, slipped and ending pipeline stay.
  * net_new_arr, ending_arr and the check columns are recomputed; renewal ARR and retention rates are set the
    way build_v5_dataset.py defines them (it recomputes them from the customer buckets later).
"""

from __future__ import annotations

import os
import shutil
import sys
from collections import defaultdict
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sync_v5_statements import ZERO, num, q, read, write  # noqa: E402

INFLOWS = ("new_business_arr", "expansion_arr", "reactivation_arr")
OUTFLOWS = ("contraction_arr", "churn_arr")
MOVEMENTS = INFLOWS + OUTFLOWS
BALANCING = "new_business_arr"
PIPELINE_TYPES = {"New Business": "new_business_arr", "Expansion": "expansion_arr", "Reactivation": "reactivation_arr",
                  "Contraction": "contraction_arr", "Churn": "churn_arr"}


def net(row: dict) -> Decimal:
    return sum((row[k] for k in INFLOWS), ZERO) - sum((row[k] for k in OUTFLOWS), ZERO)


def reshape(history: list[dict], first_operating: dict) -> tuple[list[dict], list[str]]:
    """history: months in order with beginning_arr, ending_arr and MOVEMENTS as Decimals."""
    n = len(history)
    begin_total = sum((r["beginning_arr"] for r in history), ZERO)
    ramp: dict[str, Decimal] = {}
    for k in MOVEMENTS:
        avg = sum((r[k] for r in history), ZERO) / begin_total
        target = first_operating[k] / first_operating["beginning_arr"]
        if avg <= 0:
            raise SystemExit(f"history has no {k} to ramp")
        ramp[k] = target / avg
    out = [{"period": r["period"], **{k: r[k] * (1 + (ramp[k] - 1) * Decimal(i) / n) for k in MOVEMENTS}}
           for i, r in enumerate(history)]

    notes = ["ramp to the first operating month's rate: " + ", ".join(f"{k} x{ramp[k]:.3f}" for k in MOVEMENTS)]
    years = defaultdict(list)
    for i, r in enumerate(history):
        years[r["period"][:4]].append(i)
    begin = history[0]["beginning_arr"]
    for y in sorted(years):
        idx = years[y]
        target_end = history[idx[-1]]["ending_arr"]
        others = sum((net(out[i]) - out[i][BALANCING] for i in idx), ZERO)
        nb = sum((out[i][BALANCING] for i in idx), ZERO)
        need = target_end - begin - others
        if nb <= 0 or need < 0:
            raise SystemExit(f"{y}: the other movements leave {need:,.2f} of new business to reach {target_end:,.2f}")
        g = need / nb
        for i in idx:
            out[i][BALANCING] *= g
        for k in MOVEMENTS:
            for i in idx:
                out[i][k] = q(out[i][k])
        drift = target_end - begin - sum((net(out[i]) for i in idx), ZERO)
        big = max(idx, key=lambda i: out[i][BALANCING])
        out[big][BALANCING] += drift
        for i in idx:
            out[i]["beginning_arr"] = begin
            begin = begin + net(out[i])
            out[i]["ending_arr"] = begin
        if begin != target_end:
            raise SystemExit(f"{y}: reshaped history ends at {begin:,.2f}, not {target_end:,.2f}")
        notes.append(f"{y}: new business x{g:.4f} to end the year at {target_end:,.2f}")
    if out[-1]["ending_arr"] != first_operating["beginning_arr"]:
        raise SystemExit("reshaped history does not end at the first operating month's beginning ARR")
    for r in out:
        bad = [k for k in MOVEMENTS if r[k] < 0]
        if bad:
            raise SystemExit(f"{r['period']}: negative {bad}")
    return out, notes


def main(src: str, dst: str) -> list[str]:
    if not (os.path.isabs(src) and os.path.isabs(dst)):
        raise SystemExit("folders must be absolute paths")
    if os.path.exists(dst):
        raise SystemExit(f"{dst} exists; pick a new folder")
    shutil.copytree(src, dst)
    path = lambda name: os.path.join(dst, name)  # noqa: E731

    _, opps = read(path("Actual_opportunities.csv"))
    if not opps:
        raise SystemExit("no Actual opportunities; the first operating month is unknown")
    first_op = min(r["period"][:7] for r in opps)
    wf_fields, wf_rows = read(path("Actual_MRR_Waterfall.csv"))
    rows = sorted(wf_rows, key=lambda r: r["period"])
    keyed = [{"period": r["period"][:7], "beginning_arr": num(r["beginning_arr"]), "ending_arr": num(r["ending_arr"]),
              **{k: num(r[k]) for k in MOVEMENTS}} for r in rows]
    for a, b in zip(keyed, keyed[1:]):
        if a["ending_arr"] != b["beginning_arr"]:
            raise SystemExit(f"Actual ARR waterfall does not roll from {a['period']} to {b['period']}")
    for r in keyed:
        if r["period"] >= first_op and r["beginning_arr"] + net(r) != r["ending_arr"]:
            raise SystemExit(f"{r['period']}: Actual ARR waterfall movements do not foot")
    history = [r for r in keyed if r["period"] < first_op]
    operating = [r for r in keyed if r["period"] == first_op]
    if not history or not operating:
        raise SystemExit(f"need history before and an ARR waterfall row for the first operating month {first_op}")
    new, notes = reshape(history, operating[0])
    notes.insert(0, f"history {history[0]['period']}..{history[-1]['period']} ramps into {first_op} "
                    f"(first month with CRM opportunities)")

    by_period = {r["period"]: r for r in new}
    delta: dict[tuple[str, str], Decimal] = {}
    for r in rows:
        x = by_period.get(r["period"][:7])
        if x is None:
            continue
        for k in MOVEMENTS:
            delta[(r["period"][:7], k)] = x[k] - num(r[k])
            r[k] = f"{x[k]:.2f}"
        bop, co, ch = x["beginning_arr"], x["contraction_arr"], x["churn_arr"]
        kept = bop - co - ch
        r["beginning_arr"], r["ending_arr"] = f"{bop:.2f}", f"{x['ending_arr']:.2f}"
        r["net_new_arr"] = f"{net(x):.2f}"
        if "renewal_arr" in wf_fields:
            r["renewal_arr"] = f"{kept:.2f}"
        if "gross_retention_rate" in wf_fields:
            r["gross_retention_rate"] = f"{kept / bop:.4f}"
        if "net_dollar_retention_rate" in wf_fields:
            r["net_dollar_retention_rate"] = f"{(kept + x['expansion_arr'] + x['reactivation_arr']) / bop:.4f}"
        if "waterfall_check" in wf_fields:
            r["waterfall_check"] = "0"
    write(path("Actual_MRR_Waterfall.csv"), wf_fields, wf_rows)

    pf, prow = read(path("Actual_pipeline_waterfall.csv"))
    moved = 0
    for r in prow:
        p, col = r["period"][:7], PIPELINE_TYPES.get(r["opportunity_type"])
        if p not in by_period:
            continue
        if col is None:
            raise SystemExit(f"{p}: pipeline type {r['opportunity_type']} has no ARR movement to follow")
        d = delta[(p, col)]
        won, made = num(r["closed_won_arr"]) + d, num(r["new_pipeline_created"]) + d
        if won != by_period[p][col] or made < 0:
            raise SystemExit(f"{p} {r['opportunity_type']}: pipeline closed-won {won} / created {made} cannot follow "
                             f"the reshaped movement {by_period[p][col]}")
        r["closed_won_arr"], r["new_pipeline_created"] = f"{won:.2f}", f"{made:.2f}"
        moved += 1
    if moved != len(new) * len(PIPELINE_TYPES):
        raise SystemExit(f"pipeline waterfall has {moved} history rows, expected {len(new) * len(PIPELINE_TYPES)}")
    write(path("Actual_pipeline_waterfall.csv"), pf, prow)

    last, op = new[-1], operating[0]
    notes.append(f"{last['period']} -> {first_op}: " + ", ".join(
        f"{k} {last[k]:,.0f} -> {op[k]:,.0f}" for k in MOVEMENTS))
    return notes


if __name__ == "__main__":
    for n in main(sys.argv[1], sys.argv[2]):
        print(n)
