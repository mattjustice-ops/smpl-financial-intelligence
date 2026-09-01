"""
Track A: Re-anchor Budget/Forecast cash from Actual endpoints and roll CFS formulaically.
Updates BS cash (+ equity plug) to match CFS ending each month.

Budget Jan 2026 beginning = Actual Dec 2025 cash
Forecast Jul 2026 beginning = Actual Jun 2026 cash
"""
from __future__ import annotations

import csv
import shutil
from datetime import datetime
from pathlib import Path

CSV_DIR = Path.home() / "OneDrive/Documents/simple CSVS"
BACKUP = CSV_DIR.parent / f"simple CSVS_backup_pre_trackA_{datetime.now():%Y%m%d_%H%M}"

BUDGET_START = 25_742_097.73  # Actual Dec 2025 cash
FORECAST_START = 30_000_000.0  # Actual Jun 2026 cash


def read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({h: r.get(h, "") for h in headers})


def fnum(v) -> float:
    return float(v or 0)


def roll_cfs(headers: list[str], rows: list[dict], start_cash: float) -> list[dict]:
    rows = sorted(rows, key=lambda r: r["period"])
    prior = start_cash
    out = []
    for r in rows:
        row = dict(r)
        op = fnum(row["net_cash_from_operating_activities"])
        inv = fnum(row["net_cash_from_investing_activities"])
        fin = fnum(row["net_cash_from_financing_activities"])
        nc = op + inv + fin
        beg = prior
        end = beg + nc
        row["beginning_cash"] = f"{beg:.2f}"
        row["net_change_in_cash"] = f"{nc:.2f}"
        row["ending_cash"] = f"{end:.2f}"
        prior = end
        out.append(row)
    return out


def sync_bs_cash(bs_headers: list[str], bs_rows: list[dict], cfs_by_period: dict[str, dict]) -> list[dict]:
    out = []
    for r in bs_rows:
        row = dict(r)
        p = row["period"]
        if p not in cfs_by_period:
            out.append(row)
            continue
        new_cash = fnum(cfs_by_period[p]["ending_cash"])
        old_cash = fnum(row["cash"])
        delta = new_cash - old_cash
        row["cash"] = f"{new_cash:.2f}"
        row["equity"] = f"{fnum(row['equity']) + delta:.2f}"
        row["total_assets"] = f"{fnum(row['total_assets']) + delta:.2f}"
        row["total_liabilities_and_equity"] = row["total_assets"]
        # balance_check should remain 0
        out.append(row)
    return out


def verify_cfs(rows: list[dict]) -> list[str]:
    issues = []
    for r in rows:
        p = r["period"]
        beg, end, nc = fnum(r["beginning_cash"]), fnum(r["ending_cash"]), fnum(r["net_change_in_cash"])
        op = fnum(r["net_cash_from_operating_activities"])
        inv = fnum(r["net_cash_from_investing_activities"])
        fin = fnum(r["net_cash_from_financing_activities"])
        if abs(beg + nc - end) > 0.02:
            issues.append(f"{p}: beg+nc!=end")
        if abs(op + inv + fin - nc) > 0.02:
            issues.append(f"{p}: op+inv+fin!=nc")
    for i in range(1, len(rows)):
        if abs(fnum(rows[i - 1]["ending_cash"]) - fnum(rows[i]["beginning_cash"])) > 0.02:
            issues.append(f"continuity {rows[i-1]['period']}->{rows[i]['period']}")
    return issues


def verify_bs(bs_rows: list[dict], cfs_by_period: dict[str, dict]) -> list[str]:
    issues = []
    for r in bs_rows:
        p = r["period"]
        if p not in cfs_by_period:
            continue
        if abs(fnum(r["cash"]) - fnum(cfs_by_period[p]["ending_cash"])) > 0.02:
            issues.append(f"{p}: BS cash != CFS ending")
        if abs(fnum(r["balance_check"])) > 0.02:
            issues.append(f"{p}: balance_check != 0")
    return issues


def process_scenario(prefix: str, start_cash: float) -> dict:
    cfs_path = CSV_DIR / f"{prefix}_cash_flow_statement.csv"
    bs_path = CSV_DIR / f"{prefix}_balance_sheet.csv"
    cfs_h, cfs_rows = read_csv(cfs_path)
    bs_h, bs_rows = read_csv(bs_path)

    rolled = roll_cfs(cfs_h, cfs_rows, start_cash)
    cfs_by = {r["period"]: r for r in rolled}
    synced_bs = sync_bs_cash(bs_h, bs_rows, cfs_by)

    write_csv(cfs_path, cfs_h, rolled)
    write_csv(bs_path, bs_h, synced_bs)

    cfs_issues = verify_cfs(rolled)
    bs_issues = verify_bs(synced_bs, cfs_by)
    return {
        "prefix": prefix,
        "start": start_cash,
        "dec_ending": fnum(rolled[-1]["ending_cash"]),
        "cfs_issues": cfs_issues,
        "bs_issues": bs_issues,
    }


def main() -> None:
    if not BACKUP.exists():
        shutil.copytree(CSV_DIR, BACKUP)
        print(f"Backup: {BACKUP}")

    budget = process_scenario("Budget", BUDGET_START)
    forecast = process_scenario("Forecast", FORECAST_START)

    print("\n=== Track A complete ===")
    for r in (budget, forecast):
        print(f"\n{r['prefix']}:")
        print(f"  Start cash: ${r['start']:,.2f}")
        print(f"  Dec ending: ${r['dec_ending']:,.2f}")
        if r["cfs_issues"]:
            print(f"  CFS issues: {r['cfs_issues']}")
        else:
            print("  CFS: all identity checks pass")
        if r["bs_issues"]:
            print(f"  BS issues: {r['bs_issues']}")
        else:
            print("  BS: cash ties CFS, balance_check OK")


if __name__ == "__main__":
    main()
