"""Production FE ↔ Board single-source guard: TS_DATA.Actual vs SRC.actuals.

Both Board Platform and Forecast Engine hydrate from build_unified_outlook_payload
(same warehouse tables). This regression fails if those two shapes diverge for the
same period on the production path. Demo HTML seeds are out of scope.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.reporting.three_statement_payload import (
    OUTLOOK_TS_SRC_MONEY_TOLERANCE,
    assert_outlook_ts_src_actuals_aligned,
    diff_outlook_ts_src_actuals,
)


def _aligned_payload() -> dict:
    period = "2026-06"
    is_row = {
        "revenue": 7_412_000.0,
        "cogs": 1_537_000.0,
        "gross_profit": 5_875_000.0,
        "sm": 3_150_000.0,
        "rd": 1_220_000.0,
        "ga": 810_000.0,
        "ebitda": -1_297_000.0,
        "da": 122_000.0,
        "net_income": -1_454_000.0,
    }
    bs_row = {
        "cash": 70_610_000.0,
        "ar": 1_040_000.0,
        "ap": 520_000.0,
        "deferred_rev": 1_120_000.0,
        "dr": 1_120_000.0,
    }
    cfs_row = {
        "beginning_cash": 66_030_000.0,
        "ending_cash": 70_610_000.0,
        "cfo": 4_800_000.0,
        "net_change": 4_580_000.0,
    }
    src_row = {**is_row, **bs_row, **cfs_row}
    return {
        "meta": {"close_month": period},
        "TS_DATA": {
            "Actual": {
                "periods": [period],
                "is": {period: is_row},
                "bs": {period: bs_row},
                "cfs": {period: cfs_row},
            }
        },
        "SRC": {"actuals": {period: src_row}},
    }


def test_diff_empty_when_ts_and_src_aligned() -> None:
    payload = _aligned_payload()
    assert diff_outlook_ts_src_actuals(payload["TS_DATA"], payload["SRC"], as_of="2026-06") == []
    assert_outlook_ts_src_actuals_aligned(payload)


def test_diff_catches_deferred_rev_divergence() -> None:
    payload = _aligned_payload()
    # Simulate the known demo-style Board bug without touching demo seeds.
    payload["TS_DATA"]["Actual"]["bs"]["2026-06"]["deferred_rev"] = 50_917_501.0
    diffs = diff_outlook_ts_src_actuals(payload["TS_DATA"], payload["SRC"], as_of="2026-06")
    assert diffs
    assert any(d["field"] == "deferred_rev" and d["reason"] == "significant_miss" for d in diffs)
    with pytest.raises(ValueError, match="deferred_rev"):
        assert_outlook_ts_src_actuals_aligned(payload)


def test_diff_within_one_dollar_passes() -> None:
    payload = _aligned_payload()
    payload["SRC"]["actuals"]["2026-06"]["revenue"] = 7_412_000.50
    assert diff_outlook_ts_src_actuals(payload["TS_DATA"], payload["SRC"], as_of="2026-06") == []


def test_diff_just_over_one_dollar_fails() -> None:
    payload = _aligned_payload()
    payload["SRC"]["actuals"]["2026-06"]["revenue"] = 7_412_001.01
    diffs = diff_outlook_ts_src_actuals(payload["TS_DATA"], payload["SRC"], as_of="2026-06")
    assert any(d["field"] == "revenue" for d in diffs)


def test_cannot_loosen_money_tolerance() -> None:
    payload = _aligned_payload()
    with pytest.raises(ValueError, match="money_tolerance"):
        diff_outlook_ts_src_actuals(
            payload["TS_DATA"],
            payload["SRC"],
            money_tolerance=OUTLOOK_TS_SRC_MONEY_TOLERANCE + Decimal("0.01"),
        )


def test_one_side_missing_is_divergence() -> None:
    payload = _aligned_payload()
    del payload["SRC"]["actuals"]["2026-06"]["cash"]
    diffs = diff_outlook_ts_src_actuals(payload["TS_DATA"], payload["SRC"], as_of="2026-06")
    assert any(d["field"] == "cash" and d["reason"] == "one_side_missing" for d in diffs)
