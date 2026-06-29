"""Tests for MDA Excel numeric value helpers."""

from __future__ import annotations

from decimal import Decimal

from app.services.reporting.export.mda_excel_values import (
    numeric_block_from_formatted,
    numeric_horizon_block,
    parse_deck_money_to_m,
    parse_deck_pct_to_ratio,
)


def test_parse_deck_money_to_m() -> None:
    assert parse_deck_money_to_m("$85.31M") == 85.31
    assert parse_deck_money_to_m("$+413.1K") == 0.4131
    assert parse_deck_money_to_m("-$1.05M") == -1.05


def test_parse_deck_pct_to_ratio() -> None:
    assert parse_deck_pct_to_ratio("-4.8%") == -0.048
    assert parse_deck_pct_to_ratio("79.2%") == 0.792


def test_numeric_horizon_block_money() -> None:
    blk = numeric_horizon_block(Decimal("21050000"), Decimal("22100000"))
    assert blk["actual"] == 21.05
    assert blk["budget"] == 22.1
    assert round(blk["variance"], 2) == -1.05


def test_numeric_block_from_formatted_pl_detail() -> None:
    blk = numeric_block_from_formatted(
        {"actual": "$21.05M", "budget": "$22.10M", "variance": "-$1.05M", "var_pct": "-4.8%"}
    )
    assert blk["actual"] == 21.05
    assert blk["budget"] == 22.1
