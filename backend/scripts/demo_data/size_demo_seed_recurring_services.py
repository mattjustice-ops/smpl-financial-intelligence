"""Size the Board demo seed's recurring services revenue at 10% of subscription revenue.

Same rule as the dataset (add_recurring_services_revenue.py): recurring services is 10% of
the month's subscription revenue, billed monthly at month end and collected the following
month. Only the change from the seed's current recurring services is applied, so every
other relationship in the seed stays as it was:
  income statement  rec_svc_rev, svc_rev, revenue, gross_profit, gm_pct, ebitda, net_income
  cash flow         net_income, chg_ar, cfo, net_change, beginning_cash, ending_cash
  balance sheet     cash, ar, total_assets, equity, total_le
Forecast continues from Actual (its first month follows Actual June); Actual and Budget
start in January with no recurring services receivable carried in. Running it again
changes nothing.

Writes TS_DATA in frontend/public/board/index.html and the canonical mirror. Then run
``node frontend/scripts/extract-demo-seed.mjs`` to refresh shared/smpl-demo-seed.js.

Usage:
  python size_demo_seed_recurring_services.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from split_demo_seed_services import BOARD_FILES, _object_span  # noqa: E402

RATE = 0.10
CHAIN_FROM = {"Forecast": "Actual"}


def _r(x: float) -> float:
    return round(x + 0.0, 2)


def size_ts_data(ts: dict) -> list[str]:
    log: list[str] = []
    carried: dict[str, tuple[float, float]] = {}
    for version in ("Actual", "Forecast", "Budget"):
        data = ts[version]
        prior_delta, prior_cash = carried.get(CHAIN_FROM.get(version, ""), (0.0, 0.0))
        cum_income = prior_cash + prior_delta
        cum_cash = prior_cash
        for p in data["periods"]:
            row, cfs, bs = data["is"][p], data["cfs"][p], data["bs"][p]
            target = _r(RATE * float(row["sub_rev"]))
            delta = _r(target - float(row["rec_svc_rev"]))
            collected = prior_delta
            begin_cash = cum_cash
            cum_cash = _r(cum_cash + collected)
            cum_income = _r(cum_income + delta)

            row["rec_svc_rev"] = target
            for k in ("svc_rev", "revenue", "gross_profit", "ebitda", "net_income"):
                row[k] = _r(float(row[k]) + delta)
            if row["revenue"]:
                row["gm_pct"] = round(row["gross_profit"] / row["revenue"], 3)

            cfs["net_income"] = _r(float(cfs["net_income"]) + delta)
            cfs["chg_ar"] = _r(float(cfs["chg_ar"]) - (delta - prior_delta))
            cfs["cfo"] = _r(float(cfs["cfo"]) + collected)
            cfs["net_change"] = _r(float(cfs["net_change"]) + collected)
            cfs["beginning_cash"] = _r(float(cfs["beginning_cash"]) + begin_cash)
            cfs["ending_cash"] = _r(float(cfs["ending_cash"]) + cum_cash)

            bs["cash"] = _r(float(bs["cash"]) + cum_cash)
            bs["ar"] = _r(float(bs["ar"]) + delta)
            bs["total_assets"] = _r(float(bs["total_assets"]) + cum_cash + delta)
            bs["equity"] = _r(float(bs["equity"]) + cum_income)
            bs["total_le"] = _r(float(bs["total_le"]) + cum_income)

            log.append(f"{version} {p}: recurring services {target:,.2f} (change {delta:,.2f}); "
                       f"subscription {float(row['sub_rev']):,.2f}")
            prior_delta = delta
        carried[version] = (prior_delta, cum_cash)
    return log


def main() -> None:
    for path in BOARD_FILES:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        a, b = _object_span(text, "TS_DATA")
        ts = json.loads(text[a:b])
        log = size_ts_data(ts)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text[:a] + json.dumps(ts, separators=(",", ":")) + text[b:])
        print(path)
        print("\n".join(log))


if __name__ == "__main__":
    main()
