"""Variance, direction, and compact formatting for board visuals."""

from __future__ import annotations

from decimal import Decimal

from app.services.board_package.package import fmt_money, fmt_pct


def direction_from_delta(delta: Decimal | None) -> str | None:
    if delta is None or delta == 0:
        return "flat"
    return "up" if delta > 0 else "down"


def direction_glyph(direction: str | None) -> str:
    return {"up": "▲", "down": "▼", "flat": "●"}.get(direction or "flat", "●")


def variance_subtext(
    actual: Decimal,
    compare: Decimal,
    *,
    currency: str = "USD",
    label: str = "vs Budget",
) -> str:
    if compare == 0 and actual == 0:
        return f"{label}: n/a"
    delta = actual - compare
    if compare == 0:
        return f"{label}: {fmt_money(delta, currency)}"
    pct = delta / compare
    sign = "+" if delta >= 0 else ""
    return f"{label}: {sign}{fmt_money(delta, currency)} ({sign}{float(pct):.1%})"


def tone_from_variance(actual: Decimal, compare: Decimal, *, higher_is_better: bool = True) -> str:
    if actual == compare:
        return "neutral"
    favorable = actual > compare if higher_is_better else actual < compare
    return "favorable" if favorable else "unfavorable"


def truncate_table_rows(rows: list[list[str]], max_rows: int) -> list[list[str]]:
    if len(rows) <= max_rows:
        return rows
    return rows[: max_rows - 1] + [["…", f"+{len(rows) - max_rows + 1} more rows in workbook"]]
