"""Unit tests for the pure MRR classification engine."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.services.mrr.engine import (
    CustomerMrrMovement,
    MovementType,
    classify_customer,
    compute_waterfall,
    quantize_money,
    summarize_company,
)

PERIOD = date(2026, 2, 1)


def _d(v: str | int | float) -> Decimal:
    return Decimal(str(v))


# ---------------------------------------------------------------------------
# classify_customer — covers every movement bucket and edge cases
# ---------------------------------------------------------------------------


def test_new_customer_no_history() -> None:
    row = classify_customer("C1", PERIOD, _d(0), _d(100), had_historical_mrr=False)
    assert row is not None
    assert row.movement_type is MovementType.NEW
    assert row.new_mrr == _d("100.00")
    assert row.reactivation_mrr == _d("0.00")
    assert row.beginning_mrr == _d("0.00")
    assert row.ending_mrr == _d("100.00")


def test_reactivation_when_history_exists() -> None:
    row = classify_customer("C1", PERIOD, _d(0), _d(50), had_historical_mrr=True)
    assert row is not None
    assert row.movement_type is MovementType.REACTIVATION
    assert row.reactivation_mrr == _d("50.00")
    assert row.new_mrr == _d("0.00")


def test_expansion_strict_increase() -> None:
    row = classify_customer("C1", PERIOD, _d(100), _d(150), had_historical_mrr=True)
    assert row is not None
    assert row.movement_type is MovementType.EXPANSION
    assert row.expansion_mrr == _d("50.00")


def test_contraction_strict_decrease_above_zero() -> None:
    row = classify_customer("C1", PERIOD, _d(100), _d(80), had_historical_mrr=True)
    assert row is not None
    assert row.movement_type is MovementType.CONTRACTION
    assert row.contraction_mrr == _d("20.00")


def test_churn_drop_to_zero() -> None:
    row = classify_customer("C1", PERIOD, _d(100), _d(0), had_historical_mrr=True)
    assert row is not None
    assert row.movement_type is MovementType.CHURN
    assert row.churn_mrr == _d("100.00")
    assert row.ending_mrr == _d("0.00")


def test_unchanged_keeps_same_mrr() -> None:
    row = classify_customer("C1", PERIOD, _d(100), _d(100), had_historical_mrr=True)
    assert row is not None
    assert row.movement_type is MovementType.UNCHANGED
    assert row.new_mrr == _d("0.00")
    assert row.expansion_mrr == _d("0.00")
    assert row.contraction_mrr == _d("0.00")
    assert row.churn_mrr == _d("0.00")
    assert row.reactivation_mrr == _d("0.00")


def test_zero_to_zero_is_skipped() -> None:
    """Customer inactive in both months should not produce a waterfall row."""
    assert classify_customer("C1", PERIOD, _d(0), _d(0), had_historical_mrr=False) is None
    assert classify_customer("C1", PERIOD, _d(0), _d(0), had_historical_mrr=True) is None


def test_negative_mrr_is_treated_as_zero() -> None:
    """Defensive: negative inputs are clamped, not raised."""
    row = classify_customer("C1", PERIOD, _d(-10), _d(100), had_historical_mrr=False)
    assert row is not None
    assert row.movement_type is MovementType.NEW
    assert row.new_mrr == _d("100.00")


def test_fractional_cents_round_half_up() -> None:
    row = classify_customer("C1", PERIOD, _d("100.005"), _d("100.015"), had_historical_mrr=True)
    assert row is not None
    assert row.movement_type is MovementType.EXPANSION
    assert row.expansion_mrr == _d("0.01")


def test_only_one_movement_bucket_is_nonzero() -> None:
    """For any given row exactly one of new/expansion/contraction/churn/reactivation is > 0."""
    cases = [
        (_d(0), _d(10), False),
        (_d(0), _d(10), True),
        (_d(10), _d(0), True),
        (_d(10), _d(20), True),
        (_d(20), _d(10), True),
    ]
    for prior, current, history in cases:
        row = classify_customer("C1", PERIOD, prior, current, had_historical_mrr=history)
        assert row is not None
        nonzero = sum(
            1
            for b in (
                row.new_mrr,
                row.expansion_mrr,
                row.contraction_mrr,
                row.churn_mrr,
                row.reactivation_mrr,
            )
            if b > 0
        )
        assert nonzero == 1, row


# ---------------------------------------------------------------------------
# compute_waterfall — multi-customer composition
# ---------------------------------------------------------------------------


def test_compute_waterfall_handles_all_buckets_together() -> None:
    rows = compute_waterfall(
        period=PERIOD,
        prior_mrr_by_customer={
            "EXIST": _d(100),
            "EXPAND": _d(100),
            "CONTRACT": _d(100),
            "CHURN": _d(100),
            # NEW and REACTIVATE both had 0 last month
            "REACTIVATE": _d(0),
        },
        current_mrr_by_customer={
            "EXIST": _d(100),
            "EXPAND": _d(150),
            "CONTRACT": _d(80),
            "CHURN": _d(0),
            "NEW": _d(200),
            "REACTIVATE": _d(75),
        },
        historical_active_customers={"REACTIVATE"},
    )
    by_id = {r.customer_id: r for r in rows}

    assert by_id["EXIST"].movement_type is MovementType.UNCHANGED
    assert by_id["EXPAND"].movement_type is MovementType.EXPANSION
    assert by_id["EXPAND"].expansion_mrr == _d("50.00")
    assert by_id["CONTRACT"].movement_type is MovementType.CONTRACTION
    assert by_id["CONTRACT"].contraction_mrr == _d("20.00")
    assert by_id["CHURN"].movement_type is MovementType.CHURN
    assert by_id["CHURN"].churn_mrr == _d("100.00")
    assert by_id["NEW"].movement_type is MovementType.NEW
    assert by_id["NEW"].new_mrr == _d("200.00")
    assert by_id["REACTIVATE"].movement_type is MovementType.REACTIVATION
    assert by_id["REACTIVATE"].reactivation_mrr == _d("75.00")


def test_compute_waterfall_excludes_inactive_in_both_months() -> None:
    rows = compute_waterfall(
        period=PERIOD,
        prior_mrr_by_customer={"GONE": _d(0)},
        current_mrr_by_customer={"GONE": _d(0)},
        historical_active_customers={"GONE"},
    )
    assert rows == []


# ---------------------------------------------------------------------------
# summarize_company — totals must satisfy the waterfall identity
# ---------------------------------------------------------------------------


def test_waterfall_identity_balances() -> None:
    rows = compute_waterfall(
        period=PERIOD,
        prior_mrr_by_customer={
            "A": _d(100),
            "B": _d(200),
            "C": _d(50),
            "D": _d(40),
        },
        current_mrr_by_customer={
            "A": _d(120),  # expansion +20
            "B": _d(150),  # contraction -50
            "C": _d(0),    # churn 50
            "E": _d(75),   # new 75
            "F": _d(40),   # reactivation 40
        },
        historical_active_customers={"F"},
    )
    summary = summarize_company(PERIOD, rows)
    identity = (
        summary.beginning_mrr
        + summary.new_mrr
        + summary.expansion_mrr
        + summary.reactivation_mrr
        - summary.contraction_mrr
        - summary.churn_mrr
    )
    assert identity == summary.ending_mrr


def test_summary_counts_by_movement_type() -> None:
    # A: 100 -> 0   (churn)
    # B: 50  -> 0   (churn)
    # C: 0   -> 75  (new, no history)
    # D: 0   -> 60  (reactivation, in history)
    rows = compute_waterfall(
        period=PERIOD,
        prior_mrr_by_customer={"A": _d(100), "B": _d(50)},
        current_mrr_by_customer={"A": _d(0), "C": _d(75), "D": _d(60)},
        historical_active_customers={"D"},
    )
    summary = summarize_company(PERIOD, rows)
    assert summary.new_customers == 1
    assert summary.churned_customers == 2
    assert summary.reactivated_customers == 1


def test_quantize_money_rounds_to_cents() -> None:
    assert quantize_money(Decimal("1.234")) == Decimal("1.23")
    assert quantize_money(Decimal("1.235")) == Decimal("1.24")
    assert quantize_money(Decimal("1.245")) == Decimal("1.25")


# ---------------------------------------------------------------------------
# Property: rows from compute_waterfall must individually satisfy the
# customer-level identity beginning + (new + expansion + reactivation)
# - contraction - churn == ending.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prior, current, history",
    [
        (0, 0, False),
        (0, 100, False),
        (0, 100, True),
        (100, 0, True),
        (100, 100, True),
        (100, 150, True),
        (100, 50, True),
        (75, 75, False),
    ],
)
def test_row_level_identity(prior: int, current: int, history: bool) -> None:
    row: CustomerMrrMovement | None = classify_customer(
        "X", PERIOD, _d(prior), _d(current), had_historical_mrr=history
    )
    if row is None:
        assert prior == 0 and current == 0
        return
    identity = (
        row.beginning_mrr
        + row.new_mrr
        + row.expansion_mrr
        + row.reactivation_mrr
        - row.contraction_mrr
        - row.churn_mrr
    )
    assert identity == row.ending_mrr
