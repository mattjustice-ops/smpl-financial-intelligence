"""Tests for SMPL Ops usage tracking and metrics."""

from __future__ import annotations

import uuid
from decimal import Decimal

from app.services.ops.usage_tracking import estimate_llm_cost_usd


def test_estimate_llm_cost_sonnet() -> None:
    cost = estimate_llm_cost_usd(
        "claude-sonnet-4-6",
        input_tokens=1_000_000,
        output_tokens=100_000,
    )
    # $3/M in + $15/M out for 1M/100k tokens
    assert cost == Decimal("4.500000")


def test_estimate_llm_cost_unknown_model_uses_default() -> None:
    cost = estimate_llm_cost_usd("unknown-model", input_tokens=0, output_tokens=0)
    assert cost == Decimal("0")
