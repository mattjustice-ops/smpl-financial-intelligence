"""Demo-data history reshape (scripts/demo_data/reshape_history_waterfall.py)."""

from __future__ import annotations

import csv
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "demo_data"))

import reshape_history_waterfall as rh  # noqa: E402

WF_FIELDS = ["period", "beginning_arr", "new_business_arr", "expansion_arr", "renewal_arr", "contraction_arr",
             "churn_arr", "reactivation_arr", "net_new_arr", "ending_arr", "gross_retention_rate",
             "net_dollar_retention_rate", "waterfall_check"]
PIPE_FIELDS = ["period", "opportunity_type", "beginning_pipeline_arr", "new_pipeline_created", "closed_won_arr",
               "closed_lost_arr", "slipped_arr", "ending_pipeline_arr"]
# period, beginning, new business, expansion, reactivation, contraction, churn; the last month is operating.
MONTHS = [("2024-11", 1000, 20, 10, 2, 1, 5), ("2024-12", 1026, 30, 10, 2, 2, 6), ("2025-01", 1060, 20, 12, 2, 1, 5),
          ("2025-02", 1088, 25, 12, 3, 2, 6), ("2025-03", 1120, 40, 14, 3, 6, 9)]
TYPES = {"New Business": 2, "Expansion": 3, "Reactivation": 4, "Contraction": 5, "Churn": 6}


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
    wf = []
    for p, bop, nb, ex, re_, co, ch in MONTHS:
        wf.append({"period": p, "beginning_arr": bop, "new_business_arr": nb, "expansion_arr": ex,
                   "reactivation_arr": re_, "contraction_arr": co, "churn_arr": ch, "renewal_arr": 1,
                   "net_new_arr": nb + ex + re_ - co - ch, "ending_arr": bop + nb + ex + re_ - co - ch,
                   "gross_retention_rate": 1, "net_dollar_retention_rate": 1, "waterfall_check": 0})
    write(d / "Actual_MRR_Waterfall.csv", WF_FIELDS, wf)
    write(d / "Actual_pipeline_waterfall.csv", PIPE_FIELDS, [
        {"period": m[0], "opportunity_type": t, "beginning_pipeline_arr": 100, "new_pipeline_created": 3 * m[i],
         "closed_won_arr": m[i], "closed_lost_arr": m[i], "slipped_arr": m[i],
         "ending_pipeline_arr": 100 + 3 * m[i] - 3 * m[i]} for m in MONTHS for t, i in TYPES.items()])
    write(d / "Actual_opportunities.csv", ["period", "opportunity_type"], [{"period": "2025-03", "opportunity_type": "New Business"}])
    return d


def run(src: Path, tmp_path: Path) -> tuple[dict[str, dict[str, Decimal]], list[str]]:
    out = tmp_path / "out"
    notes = rh.main(str(src), str(out))
    wf = {r["period"]: {k: Decimal(v) for k, v in r.items() if k != "period"} for r in read(out / "Actual_MRR_Waterfall.csv")}
    return wf, notes


def test_history_ramps_into_the_first_operating_month_and_keeps_year_end_arr(src: Path, tmp_path: Path) -> None:
    wf, notes = run(src, tmp_path)
    assert wf["2024-12"]["ending_arr"] == Decimal("1060.00")
    assert wf["2025-02"]["ending_arr"] == Decimal("1120.00")
    assert wf["2024-11"]["beginning_arr"] == Decimal("1000.00")
    # The operating month is untouched.
    assert wf["2025-03"]["new_business_arr"] == Decimal("40") and wf["2025-03"]["churn_arr"] == Decimal("9")
    periods = [m[0] for m in MONTHS[:-1]]
    for a, b in zip(periods, periods[1:]):
        assert wf[a]["ending_arr"] == wf[b]["beginning_arr"]
    for p in periods:
        r = wf[p]
        net = r["new_business_arr"] + r["expansion_arr"] + r["reactivation_arr"] - r["contraction_arr"] - r["churn_arr"]
        assert r["beginning_arr"] + net == r["ending_arr"] == r["beginning_arr"] + r["net_new_arr"]
        kept = r["beginning_arr"] - r["contraction_arr"] - r["churn_arr"]
        assert r["renewal_arr"] == kept
        assert r["gross_retention_rate"] == (kept / r["beginning_arr"]).quantize(Decimal("0.0001"), ROUND_HALF_UP)
    # Contraction: history averages 6 / 4174 of beginning ARR, the operating month 6 / 1120; month i of 4 ramps.
    ramp = (Decimal(6) / 1120) / (Decimal(6) / 4174)
    assert wf["2024-11"]["contraction_arr"] == Decimal("1.00")
    assert wf["2025-02"]["contraction_arr"] == (2 * (1 + (ramp - 1) * Decimal(3) / 4)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    assert any(n.startswith("2024: new business x") for n in notes)


def test_pipeline_closed_won_follows_the_movement_and_balances_stay(src: Path, tmp_path: Path) -> None:
    wf, _ = run(src, tmp_path)
    before = {(r["period"], r["opportunity_type"]): r for r in read(src / "Actual_pipeline_waterfall.csv")}
    after = {(r["period"], r["opportunity_type"]): r for r in read(tmp_path / "out" / "Actual_pipeline_waterfall.csv")}
    col = {"New Business": "new_business_arr", "Expansion": "expansion_arr", "Reactivation": "reactivation_arr",
           "Contraction": "contraction_arr", "Churn": "churn_arr"}
    for (p, t), r in after.items():
        b = before[(p, t)]
        if p == "2025-03":
            assert r == b
            continue
        assert Decimal(r["closed_won_arr"]) == wf[p][col[t]]
        d = Decimal(r["closed_won_arr"]) - Decimal(b["closed_won_arr"])
        assert Decimal(r["new_pipeline_created"]) == Decimal(b["new_pipeline_created"]) + d
        for k in ("beginning_pipeline_arr", "closed_lost_arr", "slipped_arr", "ending_pipeline_arr"):
            assert r[k] == b[k]


def test_refuses_without_an_operating_month_waterfall(src: Path, tmp_path: Path) -> None:
    write(src / "Actual_opportunities.csv", ["period", "opportunity_type"], [{"period": "2025-04", "opportunity_type": "New Business"}])
    with pytest.raises(SystemExit, match="first operating month"):
        rh.main(str(src), str(tmp_path / "out"))


def test_refuses_pipeline_created_below_zero(src: Path, tmp_path: Path) -> None:
    # 2024 new business is scaled down to end the year on its ARR, so November's closed-won falls by about $1.
    rows = read(src / "Actual_pipeline_waterfall.csv")
    for r in rows:
        if r["period"] == "2024-11" and r["opportunity_type"] == "New Business":
            r["new_pipeline_created"], r["ending_pipeline_arr"] = "0.5", "40.5"
    write(src / "Actual_pipeline_waterfall.csv", PIPE_FIELDS, rows)
    with pytest.raises(SystemExit, match="cannot follow"):
        rh.main(str(src), str(tmp_path / "out"))


def test_refuses_a_waterfall_that_does_not_roll(src: Path, tmp_path: Path) -> None:
    rows = read(src / "Actual_MRR_Waterfall.csv")
    rows[2]["beginning_arr"] = "1061"
    write(src / "Actual_MRR_Waterfall.csv", WF_FIELDS, rows)
    with pytest.raises(SystemExit, match="does not roll"):
        rh.main(str(src), str(tmp_path / "out"))


def test_refuses_relative_folders(src: Path) -> None:
    with pytest.raises(SystemExit, match="absolute"):
        rh.main("relative", "out")
