"""Demo-data pipeline waterfalls from each version's ARR movements (scripts/demo_data/pipeline_waterfalls.py)."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "demo_data"))

import pipeline_waterfalls as pw  # noqa: E402

D = Decimal
HISTORY = [f"2025-{m:02d}" for m in range(1, 13)]


def history_row(p: str, t: str) -> dict:
    return {"organization_id": "org", "version": "Actual", "period": p, "opportunity_type": t,
            "beginning_pipeline_arr": "700.00", "new_pipeline_created": "300.00", "closed_won_arr": "100.00",
            "closed_lost_arr": "200.00", "slipped_arr": "50.00", "ending_pipeline_arr": "650.00",
            "pipeline_coverage": "3"}


def arr(months: list[str], amount: str = "100") -> dict[str, dict[str, Decimal]]:
    return {p: {col: D(amount) for col in pw.MOVEMENT.values()} for p in months}


def build(close: str = "2026-03"):
    actual = [history_row(p, t) for p in HISTORY for t in pw.TYPES]
    waterfalls = {"Actual": arr(HISTORY + ["2026-01", "2026-02", "2026-03"]),
                  "Forecast": arr(["2026-04", "2026-05"], "200"), "Budget": arr(["2026-01", "2026-02", "2026-03"], "150")}
    return pw.rebuild(actual, waterfalls, "2026-01", close, [close])


def rows_for(rows: list[dict], t: str = "New Business") -> dict[str, dict]:
    return {r["period"]: r for r in rows if r["opportunity_type"] == t}


def test_rates_are_created_per_dollar_won_and_shares_of_open_pipeline():
    rates = pw.measure([history_row(p, t) for p in HISTORY for t in pw.TYPES], HISTORY)
    assert rates["Churn"] == pw.Rates(D(3), D("0.2"), D("0.05"))


def test_actual_rolls_from_the_last_source_ending_at_the_measured_rates():
    out, _ = build()
    jan, feb = rows_for(out["Actual"])["2026-01"], rows_for(out["Actual"])["2026-02"]
    assert (jan["beginning_pipeline_arr"], jan["new_pipeline_created"], jan["closed_won_arr"]) == (D(650), D(300), D(100))
    assert (jan["closed_lost_arr"], jan["slipped_arr"], jan["ending_pipeline_arr"]) == (D(190), D("47.50"), D("612.50"))
    assert feb["beginning_pipeline_arr"] == jan["ending_pipeline_arr"]
    assert rows_for(out["Actual"])["2025-12"]["pipeline_coverage"] == "6.50"
    assert jan["pipeline_coverage"] == "6.13"


def test_forecast_opens_at_the_close_and_carries_the_close_rows():
    out, _ = build()
    a, f = rows_for(out["Actual"]), rows_for(out["Forecast"])
    assert sorted(f) == ["2026-03", "2026-04", "2026-05"]
    assert f["2026-03"]["ending_pipeline_arr"] == a["2026-03"]["ending_pipeline_arr"]
    assert f["2026-04"]["beginning_pipeline_arr"] == a["2026-03"]["ending_pipeline_arr"]
    assert f["2026-04"]["closed_won_arr"] == D(200)
    assert a["2026-03"]["pipeline_coverage"] == f["2026-03"]["pipeline_coverage"] != ""
    assert f["2026-05"]["pipeline_coverage"] == ""


def test_budget_opens_at_the_actual_ending_before_it_one_row_per_type():
    out, _ = build()
    b = out["Budget"]
    assert len(b) == 3 * len(pw.TYPES)
    jan = rows_for(b)["2026-01"]
    assert jan["beginning_pipeline_arr"] == D(650) and jan["closed_won_arr"] == D(150)
    assert jan["new_pipeline_created"] == D(450)


def test_no_next_month_closing_anything_leaves_coverage_blank():
    rows = [{"period": "2026-01", "opportunity_type": "Churn", "ending_pipeline_arr": D(10), "closed_won_arr": D(1)},
            {"period": "2026-02", "opportunity_type": "Churn", "ending_pipeline_arr": D(10), "closed_won_arr": D(0)}]
    pw.set_coverage(rows, [])
    assert [r["pipeline_coverage"] for r in rows] == ["", ""]


def test_missing_history_months_and_negative_endings_raise():
    with pytest.raises(ValueError, match="no Actual pipeline waterfall row"):
        pw.measure([history_row(p, t) for p in HISTORY[1:] for t in pw.TYPES], HISTORY)
    rates = {t: pw.Rates(D(1), D("0.5"), D("0.4")) for t in pw.TYPES}
    with pytest.raises(ValueError, match="ending pipeline"):
        pw.roll("org", "Budget", {t: D(0) for t in pw.TYPES}, arr(["2026-01"]), ["2026-01"], rates)
