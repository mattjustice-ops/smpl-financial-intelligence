"""Align the demo deal files with the MRR waterfall before implementation revenue is added.

Writes a full copy of the source folder with these files changed (never touches the database):
  Actual_opportunities.csv              + June 2026 closed-won New Business deals
  Actual_opportunity_movements.csv      + the same June deals as "Closed Won" movements
  Forecast_opportunities.csv            Jul-Dec deals in an open stage: close_status "Open"
  Forecast_opportunity_movements.csv    same relabel
  pipeline_deals_log.csv

Rules (agreed with Matt, Oct 5 2026):
  * Forecast is the open CRM pipeline. Deals keep their stage, amount and probability; only
    the "Closed Won" label on deals that have not closed changes to "Open". Expected new
    logos for a month = sum of New Business probabilities; weighted ARR = waterfall new ARR.
  * Actual June 2026 had new-business ARR in the waterfall but no deals. The June deals are
    built from May's closed-won New Business deals (same segment, channel, owner and terms),
    new customer and deal IDs, amounts scaled to June's closed-won ARR.
  * The script stops if June's total or any month's forecast weighted ARR does not tie to
    the waterfall.

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


def _june_closed_won_arr(src: str) -> Decimal:
    _, rows = _read(os.path.join(src, "Actual_pipeline_waterfall.csv"))
    match = [r for r in rows if r["period"][:7] == JUNE and r["opportunity_type"] == NEW_BUSINESS]
    if len(match) != 1:
        raise ValueError(f"expected one {JUNE} New Business row in Actual_pipeline_waterfall.csv, found {len(match)}")
    return _num(match[0]["closed_won_arr"])


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
    _, opps = _read(os.path.join(src, "Actual_opportunities.csv"))
    if any(r["period"][:7] == JUNE and r["opportunity_type"] == NEW_BUSINESS for r in opps):
        raise ValueError(f"Actual_opportunities.csv already has {JUNE} New Business deals")
    template = sorted((r for r in opps if r["period"][:7] == TEMPLATE_MONTH and r["opportunity_type"] == NEW_BUSINESS
                       and r["close_status"] == "Closed Won"), key=lambda r: r["opportunity_id"])
    if not template:
        raise ValueError(f"no {TEMPLATE_MONTH} closed-won New Business deals to use as a template")
    target = _june_closed_won_arr(src)
    waterfall = _waterfall_new_arr(src, "Actual").get(JUNE, Decimal("0"))
    if abs(target - waterfall) > TOLERANCE:
        raise ValueError(f"{JUNE} closed-won ARR {target} does not match waterfall new ARR {waterfall}")
    base = sum((_num(r["amount_arr"]) for r in template), Decimal("0"))
    factor = target / base
    deal_max, cust_max = _all_ids(src)
    deals: list[dict[str, str]] = []
    left = target
    for i, t in enumerate(template):
        last = i == len(template) - 1
        amount = left if last else (_num(t["amount_arr"]) * factor).quantize(CENT, rounding=ROUND_HALF_UP)
        left -= amount
        cust_no = cust_max + 1 + i
        stem = t["customer_name"].rsplit(" ", 1)[0]
        name = f"{stem} {cust_no}"
        created = f"{JUNE}-{t['created_date'][8:10]}"
        deals.append({
            **t,
            "period": JUNE, "opportunity_id": f"ACT-OPP-{deal_max + 1 + i}",
            "opportunity_name": f"{name} - {NEW_BUSINESS} - {JUNE}",
            "customer_id": f"CUST-{cust_no:05d}", "customer_name": name,
            "created_date": created, "expected_close_date": f"{JUNE}-30", "actual_close_date": f"{JUNE}-30",
            "contract_start_date": f"{JUNE}-01", "contract_end_date": "2027-06-01",
            "amount_arr": f"{amount:.2f}", "weighted_arr": f"{amount:.2f}", "probability": "1.0",
            "source_note": f"June 2026 deal built from {t['opportunity_id']} ({TEMPLATE_MONTH}); "
                           f"amount scaled to June closed-won ARR in the waterfall",
        })
    total = sum((_num(d["amount_arr"]) for d in deals), Decimal("0"))
    if total != target:
        raise ValueError(f"June deals total {total} != {target}")
    log.append({"version": "Actual", "period": JUNE, "file": "Actual_opportunities.csv", "action": "added",
                "detail": f"{len(deals)} closed-won New Business deals from {TEMPLATE_MONTH} template, "
                          f"scaled x{factor:.4f} to the waterfall", "amount": f"{total:.2f}"})
    return deals


def append_rows(path: str, rows: list[dict[str, str]], log: list[dict[str, str]]) -> None:
    fields, existing = _read(path)
    _write(path, fields, existing + [{k: r.get(k, "") for k in fields} for r in rows])
    log.append({"version": "Actual", "period": JUNE, "file": os.path.basename(path), "action": "added",
                "detail": f"{len(rows)} rows", "amount": ""})


def relabel_open(path: str, log: list[dict[str, str]]) -> list[dict[str, str]]:
    fields, rows = _read(path)
    changed: dict[str, int] = defaultdict(int)
    for r in rows:
        if (r["period"][:7] >= FORECAST_START and r["close_status"] == "Closed Won"
                and r["stage"] in OPEN_STAGES and not r["actual_close_date"]):
            r["close_status"] = "Open"
            changed[r["period"][:7]] += 1
    _write(path, fields, rows)
    log.append({"version": "Forecast", "period": "", "file": os.path.basename(path), "action": "relabeled",
                "detail": f"{sum(changed.values())} open-stage deals 'Closed Won' -> 'Open' "
                          f"({', '.join(f'{p}: {n}' for p, n in sorted(changed.items()))})", "amount": ""})
    return rows


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
    relabel_open(os.path.join(dst, "Forecast_opportunity_movements.csv"), log)
    check_forecast_pipeline(src, forecast, log)

    _write(os.path.join(dst, "pipeline_deals_log.csv"), ["version", "period", "file", "action", "detail", "amount"], log)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
