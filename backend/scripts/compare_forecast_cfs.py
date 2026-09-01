"""Compare Forecast CFS: CSV vs warehouse vs platform build_ts_data vs API."""
import csv
import json
import uuid
from pathlib import Path

import urllib.request

from app.db.session import SessionLocal
from app.services.reporting.three_statement_payload import (
    build_ts_data,
    build_outlook_api_payload,
    _read_statement_table,
)

ORG = uuid.UUID("8571e520-0687-4516-bdee-379f37c58c1f")
CSV = Path.home() / "OneDrive/Documents/simple CSVS"
PERIODS = [f"2026-{m:02d}" for m in range(7, 13)]
FIELDS = [
    "beginning_cash",
    "ending_cash",
    "net_change",
    "cfo",
    "cfi",
    "capex",
    "net_income",
    "da",
    "sbc",
    "chg_ar",
    "chg_ap",
    "chg_dr",
    "chg_prepaids",
    "cash_tie_variance",
]

CSV_MAP = {
    "beginning_cash": "beginning_cash",
    "ending_cash": "ending_cash",
    "net_change": "net_change_in_cash",
    "cfo": "net_cash_from_operating_activities",
    "cfi": "net_cash_from_investing_activities",
    "capex": "capital_expenditures",
    "net_income": "net_income",
    "da": "depreciation_and_amortization",
    "sbc": "stock_based_compensation",
    "chg_ar": "change_in_accounts_receivable",
    "chg_ap": "change_in_accounts_payable",
    "chg_dr": "change_in_deferred_revenue",
    "chg_prepaids": "change_in_prepaids",
}


def load_csv():
    rows = list(csv.DictReader(open(CSV / "Forecast_cash_flow_statement.csv", encoding="utf-8-sig")))
    return {r["period"]: r for r in rows}


def f(v):
    if v is None or v == "":
        return None
    return float(v)


def main():
    csv_by = load_csv()
    db = SessionLocal()
    ts = build_ts_data(db, ORG, as_of="2026-06", start_period="2026-01", end_period="2026-12")
    plat = ts["Forecast"]["cfs"]
    wh_rows = _read_statement_table(db, ORG, "forecast_cash_flow_statement")
    if isinstance(wh_rows, list):
        wh_by = {r["period"]: r for r in wh_rows}
    else:
        wh_by = wh_rows
    payload = build_outlook_api_payload(db, ORG)
    api_cfs = payload["TS_DATA"]["Forecast"]["cfs"]
    db.close()

    print("FORECAST CFS ALIGNMENT CHECK")
    print("=" * 72)
    mismatches = []
    for p in PERIODS:
        print(f"\n--- {p} ---")
        for field in FIELDS:
            if field == "cash_tie_variance":
                pv = plat.get(p, {}).get(field)
                if pv is not None and abs(pv) > 1:
                    print(f"  platform variance: {pv:,.0f}")
                continue
            csv_key = CSV_MAP.get(field, field)
            cv = f(csv_by.get(p, {}).get(csv_key))
            wv = f(wh_by.get(p, {}).get(csv_key)) if isinstance(wh_by.get(p), dict) else None
            pv = f(plat.get(p, {}).get(field))
            av = f(api_cfs.get(p, {}).get(field))
            if cv is None:
                continue
            ok_plat = pv is not None and abs((pv or 0) - cv) < 1
            ok_wh = wv is not None and abs(wv - cv) < 1
            if not ok_plat:
                mismatches.append((p, field, cv, pv, "platform"))
                print(
                    f"  {field:16} CSV={cv:>14,.0f}  platform={pv if pv is not None else 'MISSING':>14}  "
                    f"{'OK' if ok_plat else 'MISMATCH'}"
                )
            elif field in ("beginning_cash", "ending_cash", "net_change", "cfo", "cfi"):
                print(f"  {field:16} CSV={cv:>14,.0f}  platform={pv:>14,.0f}  OK")

    print("\n" + "=" * 72)
    print(f"Total field mismatches (CSV vs platform): {len(mismatches)}")
    if mismatches:
        by_field = {}
        for _, field, _, _, _ in mismatches:
            by_field[field] = by_field.get(field, 0) + 1
        print("Mismatch counts by field:", dict(sorted(by_field.items())))


if __name__ == "__main__":
    main()
