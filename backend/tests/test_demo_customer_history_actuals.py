"""Demo-data 2026 Actual customer movements and revenue from ARR (scripts/demo_data)."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "demo_data"))

import customer_history_actuals as cha  # noqa: E402
import revenue_from_arr as rfa  # noqa: E402
from build_v5_dataset import padd  # noqa: E402
from customer_history_plans import CANCELLED, PAUSED, History  # noqa: E402

D = Decimal
WINDOW = [f"2025-{m:02d}" for m in range(1, 13)]
START = {"A": "2023-03", "B": "2023-03", "D": "2023-06", "E": "2023-01", "F": "2025-04", "G": "2025-08"}
TEAM = [
    {"employee_id": "EMP-1", "role": "Account Executive", "sub_department": "Mid-Market Sales", "region": "South",
     "annual_quota_arr": "1200000", "productivity_ramp_months": "0", "hire_date": "2020-01-01", "termination_date": ""},
    {"employee_id": "EMP-2", "role": "Senior Account Executive", "sub_department": "Enterprise Sales", "region": "West",
     "annual_quota_arr": "1200000", "productivity_ramp_months": "0", "hire_date": "2020-01-01", "termination_date": ""},
    {"employee_id": "EMP-3", "role": "Customer Success Manager", "sub_department": "Customer Success", "region": "South",
     "annual_quota_arr": "500000", "productivity_ramp_months": "0", "hire_date": "2020-01-01", "termination_date": ""},
]


def history() -> History:
    """A pauses at its March renewal and returns in September above what it left with; D cancels at its June
    renewal; E expands, B contracts; F (SMB) and G (Enterprise) sign."""
    h = History("org")
    h.info = {c: {"customer_name": c, "segment": ""} for c in START}
    for c, a in (("A", "100000"), ("B", "300000"), ("D", "50000"), ("E", "200000")):
        h.open(c, D(a), "2023-12", "opening")
    moves = {"2025-03": [("A", "Pause", "100000")], "2025-04": [("F", "New Business", "60000")],
             "2025-05": [("E", "Expansion", "20000")], "2025-06": [("D", "Churn", "50000")],
             "2025-07": [("B", "Contraction", "30000")], "2025-08": [("G", "New Business", "600000")],
             "2025-09": [("A", "Reactivation", "110000")]}
    p = "2024-01"
    while p <= "2025-12":
        for c, kind, a in moves.get(p, []):
            h.move(p, c, kind, D(a))
        h.close_month(p)
        p = padd(p, 1)
    return h


def test_rates_are_measured_on_the_year_before():
    r = cha.measure(history(), START, WINDOW, TEAM, {}, set())
    # Due: E in January (200k), A and B in March (400k), D in June (50k); A and D left (150k), one of them paused.
    assert r.depart == D(150000) / D(650000)
    assert r.pause_share == D("0.5")
    # A was away six months at 100k and came back; D was away six months at 50k within the restart window.
    assert r.back[PAUSED] == D(100000) / D(600000)
    assert r.back[CANCELLED] == 0
    assert r.return_ratios == [D("1.1")]
    # ARR at the prior month end over the year for customers that started before it (A after its return is out).
    active = D(650000) * 3 + D(550000) * 2 + D(570000) + D(520000) + D(490000) * 5
    assert r.move["Expansion"] == D(20000) / active / D("0.1")
    assert r.move["Contraction"] == D(30000) / active / D("0.1")
    # Equal quota: Enterprise takes the largest deals up to half of the year's 660k, which G alone passes.
    assert r.floor == D(600000)
    assert r.attainment == {"Mid-Market Sales": D(60000) / D(1200000), "Enterprise Sales": D(600000) / D(1200000)}
    assert r.deal_sizes["Enterprise Sales"] == [D(600000)]
    assert r.deal_sizes["Mid-Market Sales"] == [D(50000), D(60000), D(100000), D(200000), D(300000)]


def test_a_collections_case_never_counts_as_away():
    # D's cancellation is the only one; as a collections case it leaves nothing to measure returns on.
    with pytest.raises(ValueError, match="nothing to measure"):
        cha.measure(history(), START, WINDOW, TEAM, {}, {"D"})


def test_simulated_months_book_one_deal_per_movement():
    h = history()
    r = cha.measure(h, START, WINDOW, TEAM, {}, set())
    logos: list[str] = []
    ids = iter(range(1, 1000))

    def new_logo(p, region, arr, key):
        c = f"N{len(logos) + 1}"
        logos.append(c)
        h.info[c] = {"customer_name": c, "segment": ""}
        START[c] = p
        return c

    months = [f"2026-{m:02d}" for m in range(1, 13)]
    try:
        deals = cha.simulate(h, r, months, START, TEAM, {}, set(), set(), lambda p, cands: cands[0], new_logo,
                             lambda: f"OPP-{next(ids)}")
    finally:
        for c in logos:
            START.pop(c, None)
    rows = {x["opportunity_id"]: x for x in h.rows if x["opportunity_id"]}
    assert len(rows) == len(deals)
    for d in deals:
        x = rows[d["opportunity_id"]]
        assert (x["period"], x["customer_id"], x["movement_type"], abs(x["movement_arr"])) == \
            (d["period"], d["customer_id"], d["kind"], d["amount"])
    assert logos and {d["customer_id"] for d in deals if d["kind"] == "New Business"} == set(logos)
    expanded = [d["customer_id"] for d in deals if d["kind"] == "Expansion"]
    assert len(expanded) == len(set(expanded))
    # New logos do not move again in the window; A came back in September 2025, so its next renewal is after
    # 2026 (no CSM credit) and it cannot expand.
    assert not {d["customer_id"] for d in deals if d["kind"] in ("Expansion", "Contraction")} & set(logos)
    assert "A" not in expanded
    # Expected new business: ramped quota x attainment each month; a deal books once the expected total passes
    # what is booked by half the deal, so a team never runs ahead by more than half its largest deal.
    for team, top in (("Mid-Market Sales", D(300000)), ("Enterprise Sales", D(600000))):
        booked = sum((d["amount"] for d in deals if d["team"] == team), D(0))
        assert booked <= D(100000) * 12 * r.attainment[team] + top / 2


def test_a_non_payment_month_needs_someone_leaving_at_renewal():
    h = history()
    r = cha.measure(h, START, WINDOW, TEAM, {}, set())
    with pytest.raises(ValueError, match="no customer leaving at renewal"):
        cha.simulate(h, r, ["2026-01", "2026-02"], START, TEAM, {}, set(), {"2026-02"}, lambda p, cands: cands[0],
                     lambda *a: "X", lambda: "OPP-1")


def test_customers_are_due_on_their_anniversary_a_year_after_they_last_started():
    last = {"A": "2025-09", "B": "2023-03"}
    assert cha.is_due("B", "2026-03", START, last)
    assert not cha.is_due("A", "2026-03", START, last)
    assert not cha.is_due("B", "2026-04", START, last)


def test_revenue_runs_at_the_measured_ratio_to_arr_and_costs_keep_their_ratio_on_the_cash_part():
    eop = {"2025-12": {"A": D(1200000)}, "2026-01": {"A": D(1440000)}}
    rows = [{"period": "2025-12", "revenue": "95000"}]
    ratio = rfa.recurring_ratio(rows, {"2025-12": D(5000)}, eop, ["2025-12"])
    assert ratio == D("0.9")
    row = {"period": "2026-01", "revenue": "100000.00", "cost_of_revenue": "30000.00", "sales_and_marketing": "40000.00",
           "research_and_development": "20000.00", "general_and_administrative": "10000.00",
           "depreciation_and_amortization": "1000.00", "interest_expense": "500.00", "tax_expense": "0.00"}
    sbc = {"2026-01": {col: "2000.00" for col in rfa.SBC_COLUMNS.values()}}
    before, after = rfa.rebase([row], sbc, {"2026-01": D(2000)}, eop, ["2026-01"], ratio)
    # 0.9 x 1.44M / 12 + 2k implementation = 110k: each line's cash part scales by 1.1, stock comp stays.
    assert (before, after) == (D(100000), D(110000))
    assert row["revenue"] == "110000.00"
    assert row["cost_of_revenue"] == "32800.00"
    assert row["depreciation_and_amortization"] == "1100.00"
    assert row["gross_profit"] == "77200.00"
    assert row["ebitda"] == f"{D('77200') - D('43800') - D('21800') - D('10800'):.2f}"
    assert row["net_income"] == f"{D(row['ebitda']) - D('1100') - D('500'):.2f}"
    with pytest.raises(ValueError, match="no income statement rows"):
        rfa.rebase([], sbc, {}, eop, ["2026-01"], ratio)
