"""Demo-data New Business and Customer Success buckets (scripts/demo_data/customer_buckets.py)."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "demo_data"))

import customer_buckets as cb  # noqa: E402


def row(c: str, p: str, kind: str, begin: str, end: str) -> dict:
    return {"customer_id": c, "period": p, "movement_type": kind, "beginning_arr": begin,
            "movement_arr": str(Decimal(end) - Decimal(begin)), "ending_arr": end}


def lines(rows: list[dict]) -> list[tuple[str, str, int]]:
    return [(r["period"], r["waterfall_line"], r["customer_age_months"]) for r in rows]


def test_first_year_movements_are_new_business_and_handoff_at_twelve_months():
    rows = [row("A", "2024-01", "New Business", "0", "100"),
            row("A", "2024-06", "Expansion", "100", "150"),
            row("A", "2024-12", "Contraction", "150", "120"),
            row("A", "2025-01", "Expansion", "120", "130"),
            row("A", "2025-02", "Contraction", "130", "110")]
    cb.classify(rows, {})
    assert lines(rows) == [("2024-01", "new_logo", 0), ("2024-06", "first_year_expansion", 5),
                           ("2024-12", "first_year_contraction", 11), ("2025-01", "expansion", 12),
                           ("2025-02", "contraction", 13)]
    assert [r["customer_bucket"] for r in rows] == ["New Business"] * 3 + ["Customer Success"] * 2
    assert all(r["movement_subcategory"] == "" for r in rows)


def test_departure_before_twelve_months_is_no_start_and_return_is_winback():
    rows = [row("B", "2024-01", "New Business", "0", "100"),
            row("B", "2024-08", "Churn", "100", "0"),
            row("B", "2024-10", "Reactivation", "0", "80")]
    cb.classify(rows, {})
    assert lines(rows) == [("2024-01", "new_logo", 0), ("2024-08", "no_start", 7), ("2024-10", "winback", 9)]
    assert rows[2]["first_mrr_period"] == "2024-01"


def test_return_within_six_months_after_twelve_is_reactivation():
    rows = [row("C", "2022-01", "Opening balance", "100", "100"),
            row("C", "2024-03", "Pause", "100", "0"),
            row("C", "2024-09", "Reactivation", "0", "100")]
    cb.classify(rows, {"C": "2020-05-01"})
    assert lines(rows) == [("2022-01", "", 20), ("2024-03", "churn", 46), ("2024-09", "reactivation", 52)]
    assert rows[2]["customer_bucket"] == "Customer Success"


def test_return_after_more_than_six_months_restarts_age_as_winback():
    rows = [row("D", "2021-01", "New Business", "0", "100"),
            row("D", "2024-03", "Pause", "100", "0"),
            row("D", "2024-10", "Reactivation", "0", "90"),
            row("D", "2025-01", "Expansion", "90", "120"),
            row("D", "2025-10", "Expansion", "120", "150")]
    cb.classify(rows, {})
    assert lines(rows) == [("2021-01", "new_logo", 0), ("2024-03", "churn", 38), ("2024-10", "winback", 0),
                           ("2025-01", "first_year_expansion", 3), ("2025-10", "expansion", 12)]
    assert rows[2]["first_mrr_period"] == "2024-10"


def test_plan_rows_continue_from_prior_actual_rows_including_the_opening_month():
    actual = [row("E", "2024-01", "New Business", "0", "100"),
              row("E", "2025-03", "Churn", "100", "0"),
              row("E", "2025-12", "Reactivation", "0", "100")]
    plan = [row("E", "2025-12", "Opening balance", "100", "100"),
            row("E", "2026-04", "Expansion", "100", "130")]
    cb.classify(actual, {})
    cb.classify(plan, {}, prior=actual)
    assert lines(actual)[2] == ("2025-12", "winback", 0)
    assert lines(plan) == [("2025-12", "", 0), ("2026-04", "first_year_expansion", 4)]


def test_reactivation_without_a_departure_is_an_error():
    with pytest.raises(ValueError, match="without a departure"):
        cb.classify([row("F", "2024-01", "Reactivation", "0", "10")], {})


def test_bucket_waterfall_sums_lines_and_measures_customer_success_beginning():
    rows = [row("G", "2023-01", "New Business", "0", "200"),
            row("H", "2023-06", "New Business", "0", "100"),
            row("G", "2024-01", "Contraction", "200", "150"),
            row("H", "2024-01", "Churn", "100", "0"),
            row("J", "2024-01", "New Business", "0", "50")]
    cb.classify(rows, {})
    w = cb.bucket_waterfall(rows, ["2024-01"])["2024-01"]
    assert w["customer_success_beginning_arr"] == Decimal("200")
    assert w["customer_success_contraction_arr"] == Decimal("50")
    assert w["no_start_arr"] == Decimal("100")
    assert w["new_logo_arr"] == Decimal("50")
    assert w["new_business_bucket_arr"] == Decimal("-50")
