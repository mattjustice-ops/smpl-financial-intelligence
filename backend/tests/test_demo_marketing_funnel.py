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
    # The loaded lead and pipeline columns are placeholders the rebuild replaces.
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
    # Plans book 100k of New Business in July on 155k of pipeline created.
    for v in ("Forecast", "Budget"):
        write(d / f"{v}_pipeline_waterfall.csv", WATERFALL_FIELDS, [
            {"period": "2026-07", "opportunity_type": "New Business", "beginning_pipeline_arr": "277200",
             "new_pipeline_created": "155000", "closed_won_arr": "100000", "closed_lost_arr": "30000",
             "slipped_arr": "0", "ending_pipeline_arr": "302200"},
            {"period": "2026-07", "opportunity_type": "Expansion", "beginning_pipeline_arr": "9",
             "new_pipeline_created": "9", "closed_won_arr": "9", "closed_lost_arr": "0", "slipped_arr": "0",
             "ending_pipeline_arr": "9"},
        ])
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


def test_actual_opportunities_follow_pipeline_at_the_crm_deal_size(src: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    mf.main(str(src), str(out))
    a = actual_rows(out)
    # Deal size: Search (60k + 40k) / 2 = 50k, Events 20k. Pipeline created: May 100k / 20k, June 150k / 40k.
    opps = {k: r["opportunities_created"] for k, r in a.items()}
    assert opps == {("2026-05", "Search"): "2", ("2026-05", "Events"): "1",
                    ("2026-06", "Search"): "3", ("2026-06", "Events"): "2"}
    # Leads run back at 0.3 SQL->opportunity, 0.4 MQL->SQL, 0.5 SQL->SAL (whole, half up).
    assert (a[("2026-05", "Search")]["sqls"], a[("2026-05", "Search")]["mqls"]) == ("7", "18")
    assert (a[("2026-06", "Search")]["sqls"], a[("2026-06", "Search")]["mqls"], a[("2026-06", "Search")]["sals"]) \
        == ("10", "25", "5")
    assert (a[("2026-06", "Events")]["sqls"], a[("2026-06", "Events")]["mqls"]) == ("7", "18")
    assert Decimal(a[("2026-06", "Search")]["cost_per_mql"]) == Decimal("1200.00")
    spend = {(r["period"], r["marketing_channel"]): r for r in read(out / "Actual_marketing_spend_by_channel.csv")}
    assert Decimal(spend[("2026-06", "Search")]["cost_per_sql"]) == Decimal("3000.00")


def test_opportunities_are_whole_and_at_least_one_with_pipeline_and_the_deals_closed() -> None:
    d = Decimal
    assert mf.opportunities(d("125000"), d("50000")) == 3
    assert mf.opportunities(d("10"), d("50000")) == 1
    assert mf.opportunities(d("0"), d("50000")) == 0
    assert mf.opportunities(d("100000"), d("50000"), 3) == 3


def test_refuses_crm_deals_with_no_arr(src: Path, tmp_path: Path) -> None:
    rows = read(src / "Actual_opportunities.csv")
    rows.append({"period": "2026-06", "opportunity_type": "New Business", "close_status": "Closed Won",
                 "marketing_channel": "Search", "amount_arr": "0"})
    write(src / "Actual_opportunities.csv", OPP_FIELDS, rows)
    with pytest.raises(SystemExit, match="deal with no ARR"):
        mf.main(str(src), str(tmp_path / "out"))


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


def test_plan_funnel_runs_back_from_the_versions_pipeline(src: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    mf.main(str(src), str(out))
    f = {(r["period"], r["marketing_channel"]): r for r in read(out / "Forecast_marketing_pipeline.csv")}
    # Closed month copies Actual.
    jun = f[("2026-06", "Search")]
    assert jun["mqls"] == "25" and Decimal(jun["closed_won_arr"]) == Decimal("100000.00")
    jul = f[("2026-07", "Search")]
    # Search: 169,565.22 of 200k Actual New Business on 250k created.
    assert Decimal(jul["closed_won_arr"]) == Decimal("84782.61")
    assert Decimal(jul["expected_closed_won_arr"]) == Decimal("84782.61")
    assert Decimal(jul["pipeline_arr_created"]) == Decimal("125000.00")
    assert jul["pipeline_coverage_ratio"] == "1.47"
    # 125k / the 50k deal size = 2.5 -> 3 opportunities; Search Actual: 5 opportunities, 17 SQLs, 43 MQLs.
    assert jul["opportunities_created"] == "3"
    assert jul["sqls"] == "10" and jul["mqls"] == "25"
    assert Decimal(jul["cost_per_mql"]) == Decimal("1600.00")
    b = {r["marketing_channel"]: r for r in read(out / "Budget_marketing_pipeline.csv")}
    # Events: 30k / 20k = 1.5 -> 2 opportunities; Actual 3 opportunities, 10 SQLs, 26 MQLs.
    assert b["Events"]["opportunities_created"] == "2"
    assert b["Events"]["sqls"] == "7" and b["Events"]["mqls"] == "18" and b["Search"]["mqls"] == "25"
    # Events: 30,434.78 of 200k on 60k created; the channels' shares add to the version's New Business.
    assert Decimal(b["Events"]["closed_won_arr"]) == Decimal("15217.39")
    assert Decimal(b["Events"]["pipeline_arr_created"]) == Decimal("30000.00")
    assert Decimal(b["Events"]["closed_won_arr"]) + Decimal(b["Search"]["closed_won_arr"]) == Decimal("100000.00")
    s = {r["period"]: r for r in read(out / "Forecast_marketing_pipeline_summary.csv")}
    assert s["2026-07"]["mqls"] == "43" and s["2026-07"]["opportunities_created"] == "5"
    assert Decimal(s["2026-07"]["forecast_marketing_sourced_closed_won_arr"]) == Decimal("100000.00")


def test_plan_channels_add_up_to_the_versions_pipeline_waterfall(src: Path, tmp_path: Path) -> None:
    # Pipeline created 186k (1.2x): split by closed-won / win rate, Search 125k x 1.2, Events 30k x 1.2.
    rows = read(src / "Budget_pipeline_waterfall.csv")
    rows[0]["new_pipeline_created"] = "186000"
    write(src / "Budget_pipeline_waterfall.csv", WATERFALL_FIELDS, rows)
    out = tmp_path / "out"
    mf.main(str(src), str(out))
    b = {r["marketing_channel"]: r for r in read(out / "Budget_marketing_pipeline.csv")}
    assert Decimal(b["Search"]["pipeline_arr_created"]) == Decimal("150000.00")
    assert Decimal(b["Events"]["pipeline_arr_created"]) == Decimal("36000.00")
    assert Decimal(b["Events"]["closed_won_arr"]) == Decimal("15217.39")
    assert b["Search"]["opportunities_created"] == "3" and b["Events"]["opportunities_created"] == "2"


def test_refuses_a_plan_waterfall_that_does_not_close_the_versions_new_business(src: Path, tmp_path: Path) -> None:
    rows = read(src / "Forecast_pipeline_waterfall.csv")
    rows[0]["closed_won_arr"] = "100000.01"
    write(src / "Forecast_pipeline_waterfall.csv", WATERFALL_FIELDS, rows)
    with pytest.raises(SystemExit, match="Forecast 2026-07: pipeline waterfall closed-won"):
        mf.main(str(src), str(tmp_path / "out"))


def test_refuses_a_plan_month_with_no_pipeline_waterfall(src: Path, tmp_path: Path) -> None:
    rows = read(src / "Budget_pipeline_waterfall.csv")
    write(src / "Budget_pipeline_waterfall.csv", WATERFALL_FIELDS, [r for r in rows if r["opportunity_type"] != "New Business"])
    with pytest.raises(SystemExit, match="Budget 2026-07: no New Business pipeline waterfall"):
        mf.main(str(src), str(tmp_path / "out"))


def test_a_version_without_a_channel_plans_it_at_its_actual_share_of_spend(src: Path, tmp_path: Path) -> None:
    rows = read(src / "Budget_marketing_pipeline.csv")
    write(src / "Budget_marketing_pipeline.csv", BUDGET_FIELDS, [r for r in rows if r["marketing_channel"] == "Events"])
    notes = mf.main(str(src), str(tmp_path / "out"))
    b = {r["marketing_channel"]: r for r in read(tmp_path / "out" / "Budget_marketing_pipeline.csv")}
    # Actual May-June spend: Search 40k of 50k. July's 6k total: Search 4.8k, Events 1.2k.
    assert Decimal(b["Search"]["marketing_spend"]) == Decimal("4800.00")
    assert Decimal(b["Events"]["marketing_spend"]) == Decimal("1200.00")
    assert b["Search"]["period"] == "2026-07" and b["Search"]["version"] == "Budget"
    # Bookings are shared over every Actual channel, as when the plan has both.
    assert Decimal(b["Events"]["closed_won_arr"]) == Decimal("15217.39")
    assert Decimal(b["Search"]["closed_won_arr"]) == Decimal("84782.61")
    assert b["Search"]["mqls"] == "25"
    assert any("Budget plans ['Search'] at their Actual share of spend over 2026-05..2026-06 (Search 0.8000)" in n
               for n in notes)


def test_refuses_crm_deals_that_do_not_tie_to_the_waterfall(src: Path, tmp_path: Path) -> None:
    rows = read(src / "Actual_opportunities.csv")
    rows[0]["amount_arr"] = "60001"
    write(src / "Actual_opportunities.csv", OPP_FIELDS, rows)
    with pytest.raises(SystemExit, match="CRM New Business deals"):
        mf.main(str(src), str(tmp_path / "out"))


def test_no_channel_closes_more_than_its_pipeline(src: Path, tmp_path: Path) -> None:
    # Events books 119,998 of June's 120k, above its 40k spend share of the 190k created: it creates 119,998,
    # Search 70,002. Its CRM win rate is then 1 and Search's near 0, so May's 80k would nearly all go to Events,
    # but it has only 60k open (40k beginning + 20k created); the other 20k goes to Search.
    rows = read(src / "Actual_opportunities.csv")
    rows[0]["amount_arr"], rows[1]["amount_arr"], rows[2]["amount_arr"] = "1", "1", "119998"
    write(src / "Actual_opportunities.csv", OPP_FIELDS, rows)
    out = tmp_path / "out"
    mf.main(str(src), str(out))
    a = actual_rows(out)
    money = lambda p, c, k: Decimal(a[(p, c)][k])  # noqa: E731
    assert money("2026-06", "Events", "pipeline_arr_created") == Decimal("119998.00")
    assert money("2026-06", "Search", "pipeline_arr_created") == Decimal("70002.00")
    assert money("2026-05", "Events", "closed_won_arr") == Decimal("60000.00")
    assert money("2026-05", "Search", "closed_won_arr") == Decimal("20000.00")
    assert money("2026-05", "Events", "ending_pipeline_arr") == Decimal("0.00")


def test_refuses_crm_deals_beyond_the_months_pipeline_created(src: Path, tmp_path: Path) -> None:
    rows = read(src / "Actual_pipeline_waterfall.csv")
    rows[1]["new_pipeline_created"] = "110000"
    write(src / "Actual_pipeline_waterfall.csv", WATERFALL_FIELDS, rows)
    with pytest.raises(SystemExit, match="below the floors"):
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
