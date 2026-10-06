"""Align the demo deal files with the MRR waterfall before implementation revenue is added.

Writes a full copy of the source folder with these files changed (never touches the database):
  Actual_opportunities.csv              + June 2026 deals for every deal type
  Actual_opportunity_movements.csv      + the same June deals
  Forecast_opportunities.csv            Jul-Dec open deals: close_status "Open", stage from probability
  Forecast_opportunity_movements.csv    the same deals take the same labels
  pipeline_deals_log.csv

Rules (agreed with Matt, Oct 5 2026):
  * Forecast is the open CRM pipeline. Deals keep their amount and probability, so weighted
    ARR still equals the waterfall. Deals that have not closed are "Open", and the stage
    follows the probability: 35% Evaluation, 50% Proposal, 65% Negotiation, 80% Commit.
    Expected new logos for a month = sum of New Business probabilities.
  * Actual June 2026 had waterfall ARR but no deals. June deals for each type (New Business,
    Expansion, Reactivation, Contraction, Churn) are built from May's deals of that type
    (same segment, channel, owner, stage and terms), new customer and deal IDs, amounts
    scaled to June's ARR for that type.
  * The script stops if any June type or any month's forecast weighted New Business ARR does
    not tie to the waterfall.

Usage:
  python prepare_pipeline_deals.py <source_folder> <output_folder>
"""

from __future__ import annotations

import csv
import os
import shutil
import sys
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
NEW_BUSINESS = "New Business"
JUNE, TEMPLATE_MONTH = "2026-06", "2026-05"
FORECAST_START = "2026-07"
OPEN_STAGES = {"Discovery", "Evaluation", "Proposal", "Negotiation", "Commit"}
STAGE_BY_PROBABILITY = {Decimal("0.35"): "Evaluation", Decimal("0.5"): "Proposal",
                        Decimal("0.65"): "Negotiation", Decimal("0.8"): "Commit"}
DEAL_TYPES = (NEW_BUSINESS, "Expansion", "Reactivation", "Contraction", "Churn")
WATERFALL_COLUMN = {NEW_BUSINESS: "new_business_arr", "Expansion": "expansion_arr", "Reactivation": "reactivation_arr",
                    "Contraction": "contraction_arr", "Churn": "churn_arr"}
TOLERANCE = Decimal("1.00")


def _read(path: str) -> tuple[list[str], list[dict[str, str]]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def _write(path: str, fields: list[str], rows: list[dict[str, str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def _num(value) -> Decimal:
    text = str(value or "0").replace(",", "").strip()
    return Decimal(text or "0")


def _waterfall_new_arr(src: str, version: str) -> dict[str, Decimal]:
    _, rows = _read(os.path.join(src, f"{version}_MRR_Waterfall.csv"))
    return {r["period"][:7]: _num(r["new_business_arr"]) for r in rows}


def _june_closed_arr(src: str, deal_type: str) -> Decimal:
    _, rows = _read(os.path.join(src, "Actual_pipeline_waterfall.csv"))
    match = [r for r in rows if r["period"][:7] == JUNE and r["opportunity_type"] == deal_type]
    if len(match) != 1:
        raise ValueError(f"expected one {JUNE} {deal_type} row in Actual_pipeline_waterfall.csv, found {len(match)}")
    return _num(match[0]["closed_won_arr"])


def _june_waterfall_arr(src: str, deal_type: str) -> Decimal:
    _, rows = _read(os.path.join(src, "Actual_MRR_Waterfall.csv"))
    match = [r for r in rows if r["period"][:7] == JUNE]
    return abs(_num(match[0][WATERFALL_COLUMN[deal_type]])) if match else Decimal("0")


def _all_ids(src: str) -> tuple[int, int]:
    """Highest Actual deal number and customer number used in any deal file."""
    deal_max = cust_max = 0
    for version in ("Actual", "Budget", "Forecast"):
        for name in (f"{version}_opportunities.csv", f"{version}_opportunity_movements.csv"):
            path = os.path.join(src, name)
            if not os.path.exists(path):
                continue
            for r in _read(path)[1]:
                if r["opportunity_id"].startswith("ACT-OPP-"):
                    deal_max = max(deal_max, int(r["opportunity_id"].rsplit("-", 1)[1]))
                cust_max = max(cust_max, int(r["customer_id"].rsplit("-", 1)[1]))
    return deal_max, cust_max


def build_june_deals(src: str, log: list[dict[str, str]]) -> list[dict[str, str]]:
    """June deals for every type, New Business first so its IDs stay the same as before."""
    _, opps = _read(os.path.join(src, "Actual_opportunities.csv"))
    if any(r["period"][:7] == JUNE for r in opps):
        raise ValueError(f"Actual_opportunities.csv already has {JUNE} deals")
    deal_no, cust_no = _all_ids(src)
    deals: list[dict[str, str]] = []
    for deal_type in DEAL_TYPES:
        template = sorted((r for r in opps if r["period"][:7] == TEMPLATE_MONTH and r["opportunity_type"] == deal_type),
                          key=lambda r: r["opportunity_id"])
        if not template:
            raise ValueError(f"no {TEMPLATE_MONTH} {deal_type} deals to use as a template")
        target = _june_closed_arr(src, deal_type)
        waterfall = _june_waterfall_arr(src, deal_type)
        if abs(target - waterfall) > TOLERANCE:
            raise ValueError(f"{JUNE} {deal_type} closed ARR {target} does not match waterfall {waterfall}")
        base = sum((_num(r["amount_arr"]) for r in template), Decimal("0"))
        factor = target / base
        left = target
        built: list[dict[str, str]] = []
        for i, t in enumerate(template):
            last = i == len(template) - 1
            amount = left if last else (_num(t["amount_arr"]) * factor).quantize(CENT, rounding=ROUND_HALF_UP)
            left -= amount
            deal_no += 1
            cust_no += 1
            name = f"{t['customer_name'].rsplit(' ', 1)[0]} {cust_no}"
            built.append({
                **t,
                "period": JUNE, "opportunity_id": f"ACT-OPP-{deal_no}",
                "opportunity_name": f"{name} - {deal_type} - {JUNE}",
                "customer_id": f"CUST-{cust_no:05d}", "customer_name": name,
                "created_date": f"{JUNE}-{t['created_date'][8:10]}", "expected_close_date": f"{JUNE}-30",
                "actual_close_date": f"{JUNE}-30" if t["actual_close_date"] else "",
                "contract_start_date": f"{JUNE}-01", "contract_end_date": "2027-06-01",
                "amount_arr": f"{amount:.2f}", "weighted_arr": f"{amount:.2f}",
                "source_note": f"June 2026 deal built from {t['opportunity_id']} ({TEMPLATE_MONTH}); "
                               f"amount scaled to June {deal_type} ARR in the waterfall",
            })
        total = sum((_num(d["amount_arr"]) for d in built), Decimal("0"))
        if total != target:
            raise ValueError(f"June {deal_type} deals total {total} != {target}")
        log.append({"version": "Actual", "period": JUNE, "file": "Actual_opportunities.csv", "action": "added",
                    "detail": f"{len(built)} {deal_type} deals from {TEMPLATE_MONTH} template, "
                              f"scaled x{factor:.4f} to the waterfall", "amount": f"{total:.2f}"})
        deals += built
    return deals


def append_rows(path: str, rows: list[dict[str, str]], log: list[dict[str, str]]) -> None:
    fields, existing = _read(path)
    _write(path, fields, existing + [{k: r.get(k, "") for k in fields} for r in rows])
    log.append({"version": "Actual", "period": JUNE, "file": os.path.basename(path), "action": "added",
                "detail": f"{len(rows)} rows", "amount": ""})


def relabel_open(path: str, log: list[dict[str, str]]) -> list[dict[str, str]]:
    """Open forecast deals: 'Closed Won' -> 'Open', and stage set from probability."""
    fields, rows = _read(path)
    opened: dict[str, int] = defaultdict(int)
    restaged = 0
    for r in rows:
        if r["period"][:7] < FORECAST_START or r["stage"] not in OPEN_STAGES or r["actual_close_date"]:
            continue
        if r["close_status"] == "Closed Won":
            r["close_status"] = "Open"
            opened[r["period"][:7]] += 1
        stage = STAGE_BY_PROBABILITY.get(_num(r["probability"]).normalize())
        if stage is None:
            raise ValueError(f"{r['opportunity_id']}: no stage for probability {r['probability']}")
        if r["stage"] != stage:
            r["stage"] = stage
            restaged += 1
    _write(path, fields, rows)
    log.append({"version": "Forecast", "period": "", "file": os.path.basename(path), "action": "relabeled",
                "detail": f"{sum(opened.values())} open-stage deals 'Closed Won' -> 'Open' "
                          f"({', '.join(f'{p}: {n}' for p, n in sorted(opened.items()))}); "
                          f"{restaged} stages set from probability", "amount": ""})
    return rows


def copy_labels(path: str, deals: list[dict[str, str]], log: list[dict[str, str]]) -> None:
    """Movements for the same deal and month take the deal's stage and status."""
    labels = {(d["opportunity_id"], d["period"][:7]): (d["stage"], d["close_status"]) for d in deals}
    fields, rows = _read(path)
    changed = 0
    for r in rows:
        label = labels.get((r["opportunity_id"], r["period"][:7]))
        if label and (r["stage"], r["close_status"]) != label:
            r["stage"], r["close_status"] = label
            changed += 1
    _write(path, fields, rows)
    log.append({"version": "Forecast", "period": "", "file": os.path.basename(path), "action": "relabeled",
                "detail": f"{changed} movement rows take the deal's stage and status", "amount": ""})


def check_forecast_pipeline(src: str, rows: list[dict[str, str]], log: list[dict[str, str]]) -> None:
    waterfall = _waterfall_new_arr(src, "Forecast")
    by_month: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        if r["opportunity_type"] == NEW_BUSINESS and r["close_status"] == "Open":
            by_month[r["period"][:7]].append(r)
    for period in sorted(p for p in waterfall if p >= FORECAST_START):
        deals = by_month.get(period, [])
        weighted = sum((_num(d["amount_arr"]) * _num(d["probability"]) for d in deals), Decimal("0"))
        if abs(weighted - waterfall[period]) > TOLERANCE:
            raise ValueError(f"Forecast {period}: weighted New Business ARR {weighted:.2f} != waterfall {waterfall[period]:.2f}")
        logos = sum((_num(d["probability"]) for d in deals), Decimal("0"))
        log.append({"version": "Forecast", "period": period, "file": "Forecast_opportunities.csv", "action": "checked",
                    "detail": f"{len(deals)} open New Business deals; expected new logos {logos}; "
                              f"weighted ARR ties to waterfall {waterfall[period]:,.2f}",
                    "amount": f"{weighted:.2f}"})


def main(src: str, dst: str) -> None:
    if os.path.abspath(src) == os.path.abspath(dst):
        raise ValueError("output folder must differ from the source folder")
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(src):
        if name.lower().endswith(".csv") and os.path.isfile(os.path.join(src, name)):
            shutil.copy2(os.path.join(src, name), os.path.join(dst, name))

    log: list[dict[str, str]] = []
    june = build_june_deals(src, log)
    append_rows(os.path.join(dst, "Actual_opportunities.csv"), june, log)
    append_rows(os.path.join(dst, "Actual_opportunity_movements.csv"), june, log)

    forecast = relabel_open(os.path.join(dst, "Forecast_opportunities.csv"), log)
    copy_labels(os.path.join(dst, "Forecast_opportunity_movements.csv"), forecast, log)
    check_forecast_pipeline(src, forecast, log)

    _write(os.path.join(dst, "pipeline_deals_log.csv"), ["version", "period", "file", "action", "detail", "amount"], log)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
