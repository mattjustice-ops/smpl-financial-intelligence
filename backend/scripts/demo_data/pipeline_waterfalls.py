"""Pipeline waterfalls for every version, from the ARR movements they close into.

Rules:
  * Closed-won each month is the version's own ARR movement of the opportunity type in its ARR waterfall (New
    Business, Expansion, Reactivation, Contraction, Churn; a pause is churn).
  * Each version runs at the Actual pipeline's rates over the 12 months before it starts, type by type: pipeline
    created per dollar closed-won, and closed lost and slipped as shares of the open pipeline (beginning + created).
    created = closed-won x that rate; lost and slipped = open pipeline x their rates; ending = open - won - lost -
    slipped, and the next month begins there.
  * Actual: the months after the source history begin from its last ending. Forecast: the months after the close
    begin from the Actual close; its months through the close are the Actual rows. Budget: begins from the Actual
    ending the month before its first month, one row per type like the other versions.
  * Coverage is the ending pipeline over the next month's closed-won of the type (the Actual close looks into the
    Forecast); blank when there is no next month or it closes nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from build_v5_dataset import ZERO, num, padd, q

TYPES = ("New Business", "Expansion", "Reactivation", "Contraction", "Churn")
MOVEMENT = {"New Business": "new_business_arr", "Expansion": "expansion_arr", "Reactivation": "reactivation_arr",
            "Contraction": "contraction_arr", "Churn": "churn_arr"}
FIELDS = ["organization_id", "version", "period", "opportunity_type", "beginning_pipeline_arr", "new_pipeline_created",
          "closed_won_arr", "closed_lost_arr", "slipped_arr", "ending_pipeline_arr", "pipeline_coverage"]
WINDOW = 12


@dataclass(frozen=True)
class Rates:
    created: Decimal
    lost: Decimal
    slipped: Decimal


def window(start: str) -> list[str]:
    return [padd(start, -k) for k in range(WINDOW, 0, -1)]


def measure(rows: list[dict], months: list[str]) -> dict[str, Rates]:
    """Each type's created per dollar won, and lost and slipped per dollar of open pipeline, over the months."""
    by = {(r["period"][:7], r["opportunity_type"]): r for r in rows}
    gaps = [f"{p} {t}" for p in months for t in TYPES if (p, t) not in by]
    if gaps:
        raise ValueError(f"no Actual pipeline waterfall row to measure rates from: {gaps}")
    out = {}
    for t in TYPES:
        rs = [by[(p, t)] for p in months]
        won = sum((num(r["closed_won_arr"]) for r in rs), ZERO)
        made = sum((num(r["new_pipeline_created"]) for r in rs), ZERO)
        open_ = sum((num(r["beginning_pipeline_arr"]) + num(r["new_pipeline_created"]) for r in rs), ZERO)
        if won <= 0 or open_ <= 0:
            raise ValueError(f"{t}: no closed-won ({won}) or open pipeline ({open_}) in {months[0]}..{months[-1]}")
        out[t] = Rates(made / won, sum((num(r["closed_lost_arr"]) for r in rs), ZERO) / open_,
                       sum((num(r["slipped_arr"]) for r in rs), ZERO) / open_)
    return out


def roll(org: str, version: str, begin: dict[str, Decimal], arr: dict[str, dict[str, Decimal]],
         months: list[str], rates: dict[str, Rates]) -> list[dict]:
    rows = []
    b = dict(begin)
    for p in months:
        for t in TYPES:
            won = arr[p][MOVEMENT[t]]
            if won < 0:
                raise ValueError(f"{version} {p} {t}: ARR movement {won} is negative")
            made = q(won * rates[t].created)
            open_ = b[t] + made
            lost, slipped = q(open_ * rates[t].lost), q(open_ * rates[t].slipped)
            end = open_ - won - lost - slipped
            if end < 0:
                raise ValueError(f"{version} {p} {t}: ending pipeline {end} (open {open_}, won {won})")
            rows.append({"organization_id": org, "version": version, "period": p, "opportunity_type": t,
                         "beginning_pipeline_arr": b[t], "new_pipeline_created": made, "closed_won_arr": won,
                         "closed_lost_arr": lost, "slipped_arr": slipped, "ending_pipeline_arr": end})
            b[t] = end
    return rows


def ending(rows: list[dict], p: str) -> dict[str, Decimal]:
    out = {r["opportunity_type"]: num(r["ending_pipeline_arr"]) for r in rows if r["period"][:7] == p}
    if set(out) != set(TYPES):
        raise ValueError(f"no pipeline ending for {sorted(set(TYPES) - set(out))} in {p}")
    return out


def set_coverage(rows: list[dict], following: list[dict]) -> None:
    won = {(r["period"][:7], r["opportunity_type"]): num(r["closed_won_arr"]) for r in rows + following}
    for r in rows:
        nxt = won.get((padd(r["period"][:7], 1), r["opportunity_type"]), ZERO)
        r["pipeline_coverage"] = (f"{(num(r['ending_pipeline_arr']) / nxt).quantize(Decimal('0.01'), ROUND_HALF_UP)}"
                                  if nxt else "")


def rebuild(actual: list[dict], arr: dict[str, dict[str, dict[str, Decimal]]], rebuilt_from: str, close: str,
            forecast_through_close: list[str]) -> tuple[dict[str, list[dict]], list[str]]:
    """``actual`` is the Actual pipeline waterfall (source history through the month before ``rebuilt_from``);
    ``arr`` is each version's ARR waterfall by month. Returns each version's rows and notes."""
    org = actual[0]["organization_id"]
    kept = [dict(r, version="Actual") for r in actual if r["period"][:7] < rebuilt_from]
    a_months = [p for p in sorted(arr["Actual"]) if p >= rebuilt_from]
    if not a_months or a_months[-1] != close:
        raise ValueError(f"Actual ARR waterfall months {a_months[:1]}..{a_months[-1:]} do not reach the {close} close")
    notes = []

    def log(version: str, start: str, rates: dict[str, Rates]) -> None:
        w = window(start)
        notes.append(f"{version} pipeline rates ({w[0]}..{w[-1]} Actual): " + "; ".join(
            f"{t} created {r.created:.4f}x won, lost {r.lost:.4f} and slipped {r.slipped:.4f} of open"
            for t, r in rates.items()))

    a_rates = measure(kept, window(rebuilt_from))
    log("Actual", rebuilt_from, a_rates)
    a_rows = kept + roll(org, "Actual", ending(kept, padd(rebuilt_from, -1)), arr["Actual"], a_months, a_rates)

    f_months = sorted(arr["Forecast"])
    if f_months[0] != padd(close, 1):
        raise ValueError(f"Forecast ARR waterfall starts {f_months[0]}, not the month after the {close} close")
    f_rates = measure(a_rows, window(f_months[0]))
    log("Forecast", f_months[0], f_rates)
    f_rows = [dict(r, version="Forecast") for r in a_rows if r["period"][:7] in forecast_through_close]
    f_rows += roll(org, "Forecast", ending(a_rows, close), arr["Forecast"], f_months, f_rates)

    b_months = sorted(arr["Budget"])
    b_rates = measure(a_rows, window(b_months[0]))
    log("Budget", b_months[0], b_rates)
    b_rows = roll(org, "Budget", ending(a_rows, padd(b_months[0], -1)), arr["Budget"], b_months, b_rates)

    set_coverage(a_rows, f_rows)
    set_coverage(f_rows, [])
    set_coverage(b_rows, [])
    for v, rows in (("Actual", a_rows), ("Forecast", f_rows), ("Budget", b_rows)):
        last = max(r["period"][:7] for r in rows)
        notes.append(f"{v} pipeline waterfall: {len(rows)} rows; {last} ending " + ", ".join(
            f"{t} {e:,.2f}" for t, e in ending(rows, last).items()))
    return {"Actual": a_rows, "Forecast": f_rows, "Budget": b_rows}, notes
