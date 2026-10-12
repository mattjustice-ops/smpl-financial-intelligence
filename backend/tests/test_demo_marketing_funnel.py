"""Demo-data marketing funnel rebuild (scripts/demo_data/rebuild_marketing_funnel.py)."""

from __future__ import annotations

import csv
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "demo_data"))

import rebuild_marketing_funnel as mf  # noqa: E402

ACTUAL_FIELDS = ["organization_id", "version", "period", "marketing_channel", "mqls", "sqls", "sals",
                 "opportunities_created", "pipeline_arr_created", "closed_won_arr", "marketing_spend", "cost_per_mql",
                 "cost_per_sql", "pipeline_per_dollar_spend", "pipeline_coverage_ratio"]
FORECAST_FIELDS = ["organization_id", "version", "period", "marketing_channel", "mqls", "sqls", "sals",
                   "opportunities_created", "pipeline_arr_created", "expected_closed_won_arr", "closed_won_arr",
                   "marketing_spend", "cost_per_mql", "cost_per_sql", "pipeline_per_dollar_spend",
                   "pipeline_coverage_ratio"]
BUDGET_FIELDS = ["organization_id", "version", "period", "marketing_channel", "mqls", "sqls", "opportunities_created",
                 "pipeline_arr_created", "closed_won_arr", "marketing_spend", "cost_per_sql",
                 "pipeline_coverage_ratio", "pipeline_per_dollar_spend"]
HISTORY_FIELDS = ["period", "customer_id", "movement_arr", "waterfall_column"]


def write(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


@pytest.fixture()
def src(tmp_path: Path) -> Path:
    d = tmp_path / "src"
    d.mkdir()
    # Search: $10k and $30k spend, 20 MQLs in total -> $2,000 per MQL. Events: $8k, 4 MQLs -> $2,000.
    actual = [
        {"version": "Actual", "period": "2026-05", "marketing_channel": "Search", "mqls": "15", "sqls": "6", "sals": "3",
         "opportunities_created": "1.8", "pipeline_arr_created": "100000", "closed_won_arr": "30000", "marketing_spend": "10000"},
        {"version": "Actual", "period": "2026-06", "marketing_channel": "Search", "mqls": "5", "sqls": "2", "sals": "1",
         "opportunities_created": "0.6", "pipeline_arr_created": "200000", "closed_won_arr": "60000", "marketing_spend": "30000"},
        {"version": "Actual", "period": "2026-06", "marketing_channel": "Events", "mqls": "4", "sqls": "2", "sals": "1",
         "opportunities_created": "0.5", "pipeline_arr_created": "50000", "closed_won_arr": "10000", "marketing_spend": "8000"},
    ]
    write(d / "Actual_marketing_pipeline.csv", ACTUAL_FIELDS, actual)
    write(d / "Actual_marketing_spend_by_channel.csv", ["period", "marketing_channel", "marketing_spend", "cost_per_sql"],
          [{k: r[k] for k in ("period", "marketing_channel", "marketing_spend")} for r in actual])
    write(d / "Actual_funnel_conversion_rates.csv",
          ["period", "marketing_channel", "mql_to_sql_rate", "sql_to_sal_rate", "sql_to_opportunity_rate"],
          [{"period": r["period"], "marketing_channel": r["marketing_channel"], "mql_to_sql_rate": "0.4",
            "sql_to_sal_rate": "0.5", "sql_to_opportunity_rate": "0.3"} for r in actual])
    write(d / "Forecast_marketing_pipeline.csv", FORECAST_FIELDS, [
        {"version": "Forecast", "period": "2026-06", "marketing_channel": "Search", "mqls": "1", "marketing_spend": "30000"},
        {"version": "Forecast", "period": "2026-07", "marketing_channel": "Search", "mqls": "1", "marketing_spend": "40000"},
    ])
    write(d / "Budget_marketing_pipeline.csv", BUDGET_FIELDS, [
        {"version": "Budget", "period": "2026-07", "marketing_channel": "Events", "mqls": "1", "marketing_spend": "6000"},
    ])
    write(d / "Forecast_marketing_pipeline_summary.csv",
          ["period", "forecast_marketing_pipeline_arr", "forecast_marketing_spend", "forecast_marketing_sourced_closed_won_arr",
           "pipeline_coverage_ratio", "spend_as_percent_of_pipeline", "marketing_spend_as_percent_of_closed_won_arr",
           "mqls", "sqls", "opportunities_created"],
          [{"period": "2026-06"}, {"period": "2026-07"}])
    # Actual New Business 200k over the two months; plans book 100k in July.
    for v, rows in (("Actual", [("2026-05", "80000"), ("2026-06", "120000")]), ("Forecast", [("2026-07", "100000")]),
                    ("Budget", [("2026-07", "100000")])):
        write(d / f"{v}_customer_arr_history.csv", HISTORY_FIELDS,
              [{"period": p, "customer_id": f"C{i}", "movement_arr": a, "waterfall_column": "new_business_arr"}
               for i, (p, a) in enumerate(rows)] + [{"period": rows[0][0], "customer_id": "X", "movement_arr": "999999",
                                                     "waterfall_column": "expansion_arr"}])
    return d


def test_mqls_follow_spend_at_one_cost_per_mql(src: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    mf.main(str(src), str(out))
    a = {(r["period"], r["marketing_channel"]): r for r in read(out / "Actual_marketing_pipeline.csv")}
    assert a[("2026-05", "Search")]["mqls"] == "5"
    assert a[("2026-06", "Search")]["mqls"] == "15"
    assert a[("2026-06", "Events")]["mqls"] == "4"
    assert a[("2026-06", "Search")]["sqls"] == "6"
    assert a[("2026-06", "Search")]["sals"] == "3"
    assert Decimal(a[("2026-06", "Search")]["opportunities_created"]) == Decimal("1.80")
    assert Decimal(a[("2026-06", "Search")]["cost_per_mql"]) == Decimal("2000.00")
    assert a[("2026-06", "Search")]["closed_won_arr"] == "60000"
    assert Decimal(read(out / "Actual_marketing_spend_by_channel.csv")[1]["cost_per_sql"]) == Decimal("5000.00")


def test_plan_bookings_follow_the_versions_new_business(src: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    mf.main(str(src), str(out))
    f = {r["period"]: r for r in read(out / "Forecast_marketing_pipeline.csv")}
    # Closed month copies Actual.
    assert f["2026-06"]["mqls"] == "15" and Decimal(f["2026-06"]["closed_won_arr"]) == Decimal("60000")
    jul = f["2026-07"]
    assert jul["mqls"] == "20"
    # Search: 90k of 200k Actual New Business, win rate 90k / 300k.
    assert Decimal(jul["closed_won_arr"]) == Decimal("45000.00")
    assert Decimal(jul["expected_closed_won_arr"]) == Decimal("45000.00")
    assert Decimal(jul["pipeline_arr_created"]) == Decimal("150000.00")
    assert jul["pipeline_coverage_ratio"] == "3.33"
    b = read(out / "Budget_marketing_pipeline.csv")[0]
    assert b["mqls"] == "3"
    assert Decimal(b["closed_won_arr"]) == Decimal("5000.00")
    assert Decimal(b["pipeline_arr_created"]) == Decimal("25000.00")
    s = {r["period"]: r for r in read(out / "Forecast_marketing_pipeline_summary.csv")}
    assert s["2026-07"]["mqls"] == "20"
    assert Decimal(s["2026-07"]["forecast_marketing_sourced_closed_won_arr"]) == Decimal("45000.00")


def test_refuses_unpriced_plan_channels(src: Path, tmp_path: Path) -> None:
    rows = read(src / "Budget_marketing_pipeline.csv")
    rows[0]["marketing_channel"] = "Podcasts"
    write(src / "Budget_marketing_pipeline.csv", BUDGET_FIELDS, rows)
    with pytest.raises(SystemExit, match="no Actual history"):
        mf.main(str(src), str(tmp_path / "out"))


def test_refuses_relative_folders(src: Path) -> None:
    with pytest.raises(SystemExit, match="absolute"):
        mf.main("relative", "out")
