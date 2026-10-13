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
                 "opportunities_created", "pipeline_arr_created", "closed_won_arr", "closed_lost_arr",
                 "slipped_pipeline_arr", "beginning_pipeline_arr", "ending_pipeline_arr", "marketing_spend",
                 "cost_per_mql", "cost_per_sql", "pipeline_per_dollar_spend", "win_rate_on_pipeline_created",
                 "marketing_cac_proxy", "notes", "pipeline_coverage_ratio"]
FORECAST_FIELDS = ["organization_id", "version", "period", "marketing_channel", "mqls", "sqls", "sals",
                   "opportunities_created", "pipeline_arr_created", "expected_closed_won_arr", "closed_won_arr",
                   "marketing_spend", "cost_per_mql", "cost_per_sql", "pipeline_per_dollar_spend",
                   "pipeline_coverage_ratio"]
BUDGET_FIELDS = ["organization_id", "version", "period", "marketing_channel", "mqls", "sqls", "opportunities_created",
                 "pipeline_arr_created", "closed_won_arr", "marketing_spend", "cost_per_sql",
                 "pipeline_coverage_ratio", "pipeline_per_dollar_spend"]
HISTORY_FIELDS = ["period", "customer_id", "movement_arr", "waterfall_column"]
CONV_FIELDS = ["period", "marketing_channel", "mql_to_sql_rate", "sql_to_sal_rate", "sql_to_opportunity_rate",
               "pipeline_to_closed_won_rate", "closed_won_arr", "pipeline_arr_created"]
WATERFALL_FIELDS = ["period", "opportunity_type", "beginning_pipeline_arr", "new_pipeline_created", "closed_won_arr",
                    "closed_lost_arr", "slipped_arr", "ending_pipeline_arr"]
OPP_FIELDS = ["period", "opportunity_type", "close_status", "marketing_channel", "amount_arr"]


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
    # Search: $40k spend, 20 MQLs -> $2,000 per MQL. Events: $10k, 5 MQLs -> $2,000.
    # The loaded pipeline columns are placeholders the rebuild replaces.
    actual = [
        {"version": "Actual", "period": "2026-05", "marketing_channel": "Search", "mqls": "15", "sqls": "6", "sals": "3",
         "opportunities_created": "1.8", "pipeline_arr_created": "1", "closed_won_arr": "1", "marketing_spend": "10000"},
        {"version": "Actual", "period": "2026-05", "marketing_channel": "Events", "mqls": "1", "sqls": "1", "sals": "1",
         "opportunities_created": "0.3", "pipeline_arr_created": "1", "closed_won_arr": "1", "marketing_spend": "2000"},
        {"version": "Actual", "period": "2026-06", "marketing_channel": "Search", "mqls": "5", "sqls": "2", "sals": "1",
         "opportunities_created": "0.6", "pipeline_arr_created": "1", "closed_won_arr": "1", "marketing_spend": "30000"},
        {"version": "Actual", "period": "2026-06", "marketing_channel": "Events", "mqls": "4", "sqls": "2", "sals": "1",
         "opportunities_created": "0.5", "pipeline_arr_created": "1", "closed_won_arr": "1", "marketing_spend": "8000"},
    ]
    write(d / "Actual_marketing_pipeline.csv", ACTUAL_FIELDS, actual)
    write(d / "Actual_marketing_spend_by_channel.csv", ["period", "marketing_channel", "marketing_spend", "cost_per_sql"],
          [{k: r[k] for k in ("period", "marketing_channel", "marketing_spend")} for r in actual])
    write(d / "Actual_funnel_conversion_rates.csv", CONV_FIELDS,
          [{"period": r["period"], "marketing_channel": r["marketing_channel"], "mql_to_sql_rate": "0.4",
            "sql_to_sal_rate": "0.5", "sql_to_opportunity_rate": "0.3", "pipeline_to_closed_won_rate": "0.3",
            "closed_won_arr": "1", "pipeline_arr_created": "1"} for r in actual])
    # Company New Business pipeline: May has no CRM deals, June's deals tie to its closed-won.
    write(d / "Actual_pipeline_waterfall.csv", WATERFALL_FIELDS, [
        {"period": "2026-05", "opportunity_type": "New Business", "beginning_pipeline_arr": "240000",
         "new_pipeline_created": "120000", "closed_won_arr": "80000", "closed_lost_arr": "28000", "slipped_arr": "14000",
         "ending_pipeline_arr": "238000"},
        {"period": "2026-06", "opportunity_type": "New Business", "beginning_pipeline_arr": "238000",
         "new_pipeline_created": "190000", "closed_won_arr": "120000", "closed_lost_arr": "30800", "slipped_arr": "0",
         "ending_pipeline_arr": "277200"},
        {"period": "2026-06", "opportunity_type": "Renewal", "beginning_pipeline_arr": "5", "new_pipeline_created": "5",
         "closed_won_arr": "5", "closed_lost_arr": "0", "slipped_arr": "0", "ending_pipeline_arr": "5"},
    ])
    write(d / "Actual_opportunities.csv", OPP_FIELDS, [
        {"period": "2026-06", "opportunity_type": "New Business", "close_status": "Closed Won",
         "marketing_channel": "Search", "amount_arr": "60000"},
        {"period": "2026-06", "opportunity_type": "New Business", "close_status": "Closed Won",
         "marketing_channel": "Search", "amount_arr": "40000"},
        {"period": "2026-06", "opportunity_type": "New Business", "close_status": "Closed Won",
         "marketing_channel": "Events", "amount_arr": "20000"},
        {"period": "2026-06", "opportunity_type": "New Business", "close_status": "Closed Lost",
         "marketing_channel": "Events", "amount_arr": "99999"},
        {"period": "2026-06", "opportunity_type": "Expansion", "close_status": "Closed Won",
         "marketing_channel": "Search", "amount_arr": "99999"},
    ])
    write(d / "Forecast_marketing_pipeline.csv", FORECAST_FIELDS, [
        {"version": "Forecast", "period": "2026-06", "marketing_channel": "Search", "mqls": "1", "marketing_spend": "30000"},
        {"version": "Forecast", "period": "2026-07", "marketing_channel": "Search", "mqls": "1", "marketing_spend": "40000"},
        {"version": "Forecast", "period": "2026-07", "marketing_channel": "Events", "mqls": "1", "marketing_spend": "8000"},
    ])
    write(d / "Budget_marketing_pipeline.csv", BUDGET_FIELDS, [
        {"version": "Budget", "period": "2026-07", "marketing_channel": "Events", "mqls": "1", "marketing_spend": "6000"},
        {"version": "Budget", "period": "2026-07", "marketing_channel": "Search", "mqls": "1", "marketing_spend": "4000"},
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


def actual_rows(out: Path) -> dict[tuple[str, str], dict[str, str]]:
    return {(r["period"], r["marketing_channel"]): r for r in read(out / "Actual_marketing_pipeline.csv")}


def test_mqls_follow_spend_at_one_cost_per_mql(src: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    mf.main(str(src), str(out))
    a = actual_rows(out)
    assert a[("2026-05", "Search")]["mqls"] == "5"
    assert a[("2026-05", "Events")]["mqls"] == "1"
    assert a[("2026-06", "Search")]["mqls"] == "15"
    assert a[("2026-06", "Events")]["mqls"] == "4"
    assert a[("2026-06", "Search")]["sqls"] == "6"
    assert a[("2026-06", "Search")]["sals"] == "3"
    assert Decimal(a[("2026-06", "Search")]["opportunities_created"]) == Decimal("1.80")
    assert Decimal(a[("2026-06", "Search")]["cost_per_mql"]) == Decimal("2000.00")
    spend = {(r["period"], r["marketing_channel"]): r for r in read(out / "Actual_marketing_spend_by_channel.csv")}
    assert Decimal(spend[("2026-06", "Search")]["cost_per_sql"]) == Decimal("5000.00")


def test_actual_pipeline_is_the_new_business_waterfall_split_by_channel(src: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    mf.main(str(src), str(out))
    a = actual_rows(out)
    money = lambda p, c, k: Decimal(a[(p, c)][k])  # noqa: E731
    # Created follows spend: May 10k/2k of 12k spend, June 30k/8k of 38k.
    assert money("2026-05", "Search", "pipeline_arr_created") == Decimal("100000.00")
    assert money("2026-05", "Events", "pipeline_arr_created") == Decimal("20000.00")
    assert money("2026-06", "Search", "pipeline_arr_created") == Decimal("150000.00")
    assert money("2026-06", "Events", "pipeline_arr_created") == Decimal("40000.00")
    # June closed-won is the CRM's New Business deals; Search wins 100k of 150k, Events 20k of 40k.
    assert money("2026-06", "Search", "closed_won_arr") == Decimal("100000.00")
    assert money("2026-06", "Events", "closed_won_arr") == Decimal("20000.00")
    assert a[("2026-06", "Search")]["win_rate_on_pipeline_created"] == "0.6667"
    # May has no deals: 80k split by created x CRM win rate (100k x 2/3 vs 20k x 1/2).
    assert money("2026-05", "Search", "closed_won_arr") == Decimal("69565.22")
    assert money("2026-05", "Events", "closed_won_arr") == Decimal("10434.78")
    assert money("2026-05", "Search", "beginning_pipeline_arr") == Decimal("200000.00")
    for p, w in (("2026-05", {"closed_lost_arr": "28000", "slipped_pipeline_arr": "14000", "ending_pipeline_arr": "238000"}),
                 ("2026-06", {"beginning_pipeline_arr": "238000", "closed_lost_arr": "30800",
                              "ending_pipeline_arr": "277200"})):
        for k, total in w.items():
            assert money(p, "Search", k) + money(p, "Events", k) == Decimal(total)
    for c in ("Search", "Events"):
        for p in ("2026-05", "2026-06"):
            r = {k: money(p, c, k) for k in ("beginning_pipeline_arr", "pipeline_arr_created", "closed_won_arr",
                                              "closed_lost_arr", "slipped_pipeline_arr", "ending_pipeline_arr")}
            assert r["beginning_pipeline_arr"] + r["pipeline_arr_created"] - r["closed_won_arr"] - r["closed_lost_arr"] \
                - r["slipped_pipeline_arr"] == r["ending_pipeline_arr"]
        assert money("2026-06", c, "beginning_pipeline_arr") == money("2026-05", c, "ending_pipeline_arr")
    assert a[("2026-06", "Search")]["marketing_cac_proxy"] == "0.3000"
    assert a[("2026-06", "Search")]["pipeline_coverage_ratio"] == "1.50"
    assert a[("2026-06", "Search")]["notes"] == mf.ACTUAL_NOTE
    conv = {(r["period"], r["marketing_channel"]): r for r in read(out / "Actual_funnel_conversion_rates.csv")}
    assert Decimal(conv[("2026-05", "Search")]["closed_won_arr"]) == Decimal("69565.22")
    assert conv[("2026-06", "Events")]["pipeline_to_closed_won_rate"] == "0.5000"


def test_plan_bookings_follow_the_versions_new_business(src: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    mf.main(str(src), str(out))
    f = {(r["period"], r["marketing_channel"]): r for r in read(out / "Forecast_marketing_pipeline.csv")}
    # Closed month copies Actual.
    jun = f[("2026-06", "Search")]
    assert jun["mqls"] == "15" and Decimal(jun["closed_won_arr"]) == Decimal("100000.00")
    jul = f[("2026-07", "Search")]
    assert jul["mqls"] == "20"
    # Search: 169,565.22 of 200k Actual New Business on 250k created.
    assert Decimal(jul["closed_won_arr"]) == Decimal("84782.61")
    assert Decimal(jul["expected_closed_won_arr"]) == Decimal("84782.61")
    assert Decimal(jul["pipeline_arr_created"]) == Decimal("125000.00")
    assert jul["pipeline_coverage_ratio"] == "1.47"
    b = {r["marketing_channel"]: r for r in read(out / "Budget_marketing_pipeline.csv")}
    assert b["Events"]["mqls"] == "3" and b["Search"]["mqls"] == "2"
    # Events: 30,434.78 of 200k on 60k created; the channels' shares add to the version's New Business.
    assert Decimal(b["Events"]["closed_won_arr"]) == Decimal("15217.39")
    assert Decimal(b["Events"]["pipeline_arr_created"]) == Decimal("30000.00")
    assert Decimal(b["Events"]["closed_won_arr"]) + Decimal(b["Search"]["closed_won_arr"]) == Decimal("100000.00")
    s = {r["period"]: r for r in read(out / "Forecast_marketing_pipeline_summary.csv")}
    assert s["2026-07"]["mqls"] == "24"
    assert Decimal(s["2026-07"]["forecast_marketing_sourced_closed_won_arr"]) == Decimal("100000.00")


def test_a_version_without_a_channel_shares_its_new_business_over_the_planned_ones(src: Path, tmp_path: Path) -> None:
    rows = read(src / "Budget_marketing_pipeline.csv")
    write(src / "Budget_marketing_pipeline.csv", BUDGET_FIELDS, [r for r in rows if r["marketing_channel"] == "Events"])
    notes = mf.main(str(src), str(tmp_path / "out"))
    b = read(tmp_path / "out" / "Budget_marketing_pipeline.csv")
    assert len(b) == 1 and Decimal(b[0]["closed_won_arr"]) == Decimal("100000.00")
    assert any("Budget plans no rows for ['Search']" in n for n in notes)


def test_refuses_crm_deals_that_do_not_tie_to_the_waterfall(src: Path, tmp_path: Path) -> None:
    rows = read(src / "Actual_opportunities.csv")
    rows[0]["amount_arr"] = "60001"
    write(src / "Actual_opportunities.csv", OPP_FIELDS, rows)
    with pytest.raises(SystemExit, match="CRM New Business deals"):
        mf.main(str(src), str(tmp_path / "out"))


def test_refuses_closed_won_beyond_open_pipeline(src: Path, tmp_path: Path) -> None:
    # Events books 115k on 40k created in June, so May's split hands it more than its 60k open pipeline.
    rows = read(src / "Actual_opportunities.csv")
    rows[0]["amount_arr"], rows[1]["amount_arr"], rows[2]["amount_arr"] = "0", "5000", "115000"
    write(src / "Actual_opportunities.csv", OPP_FIELDS, rows)
    with pytest.raises(SystemExit, match="exceeds open pipeline"):
        mf.main(str(src), str(tmp_path / "out"))


def test_refuses_a_month_missing_a_channel(src: Path, tmp_path: Path) -> None:
    rows = read(src / "Actual_marketing_pipeline.csv")
    write(src / "Actual_marketing_pipeline.csv", ACTUAL_FIELDS, [r for r in rows if r["marketing_channel"] != "Events"
                                                                  or r["period"] != "2026-05"])
    with pytest.raises(SystemExit, match="no row for"):
        mf.main(str(src), str(tmp_path / "out"))


def test_refuses_unpriced_plan_channels(src: Path, tmp_path: Path) -> None:
    rows = read(src / "Budget_marketing_pipeline.csv")
    rows[0]["marketing_channel"] = "Podcasts"
    write(src / "Budget_marketing_pipeline.csv", BUDGET_FIELDS, rows)
    with pytest.raises(SystemExit, match="no Actual history"):
        mf.main(str(src), str(tmp_path / "out"))


def test_refuses_relative_folders(src: Path) -> None:
    with pytest.raises(SystemExit, match="absolute"):
        mf.main("relative", "out")
