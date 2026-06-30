"""Tests for SMPL Ops period parsing and cost estimates."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.services.ops.ops_period import parse_calendar_month, recent_calendar_months
from app.services.ops.usage_tracking import estimate_llm_cost_usd


def test_estimate_llm_cost_sonnet() -> None:
    cost = estimate_llm_cost_usd(
        "claude-sonnet-4-6",
        input_tokens=1_000_000,
        output_tokens=100_000,
    )
    assert cost == Decimal("4.500000")


def test_estimate_llm_cost_unknown_model_uses_default() -> None:
    cost = estimate_llm_cost_usd("unknown-model", input_tokens=0, output_tokens=0)
    assert cost == Decimal("0")


def test_parse_calendar_month_bounds() -> None:
    start, end = parse_calendar_month("2026-06")
    assert start == datetime(2026, 6, 1, tzinfo=timezone.utc)
    assert end == datetime(2026, 7, 1, tzinfo=timezone.utc)


def test_parse_calendar_month_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        parse_calendar_month("2026-13")


def test_recent_calendar_months_includes_current() -> None:
    months = recent_calendar_months(count=3)
    assert len(months) == 3
    assert months[0].startswith("202")
