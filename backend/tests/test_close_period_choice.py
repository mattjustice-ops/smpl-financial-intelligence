"""The reporting close a person opens is a view, not a new stored close."""

from __future__ import annotations

import pytest

from app.services.reporting.org_reporting_settings import chosen_close_period, close_periods_for_review


def test_loaded_actuals_through_the_close_are_the_choices():
    periods = close_periods_for_review(
        ["2026-03", "2026-01", "2026-07", "2026-06"],
        "2026-06",
        "2026-01",
    )
    assert periods == ["2026-01", "2026-03", "2026-06"]


def test_an_empty_ledger_offers_the_fiscal_year_through_the_close():
    periods = close_periods_for_review([], "2026-06", "2026-01")
    assert periods == ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]


def test_a_blank_request_keeps_the_stored_close():
    assert chosen_close_period(None, ["2026-05", "2026-06"], "2026-06") == "2026-06"


def test_a_loaded_month_can_be_opened():
    assert chosen_close_period("2026-05", ["2026-05", "2026-06"], "2026-06") == "2026-05"


def test_a_month_past_the_close_is_refused():
    with pytest.raises(ValueError, match="not loaded"):
        chosen_close_period("2026-07", ["2026-05", "2026-06"], "2026-06")
