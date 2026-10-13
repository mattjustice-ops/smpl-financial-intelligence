"""Demo GL rebuild: 2024-2025 marketing programs at the Jan-Jun 2026 Actual programs-to-revenue ratio."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "demo_data"))

import rebuild_gl_to_summary as rg  # noqa: E402

LINE = "sales_and_marketing"


def summary(history_sm: str = "999.00") -> list[dict[str, str]]:
    rows = [{"period": p, "revenue": "1000.00", LINE: history_sm} for p in rg.HISTORY_MONTHS]
    rows += [{"period": p, "revenue": "2000.00", LINE: "700.00"} for p in rg.PROGRAM_RATIO_MONTHS]
    return rows


def booked(history: Decimal = Decimal("300"), actual: Decimal = Decimal("500")) -> dict:
    out = {(p, LINE): history for p in rg.HISTORY_MONTHS}
    out.update({(p, LINE): actual for p in rg.PROGRAM_RATIO_MONTHS})
    return out


def test_history_sm_is_booked_plus_programs_at_the_2026_ratio():
    rows, log = rg.history_programs_at_actual_ratio(summary(), booked())
    by = {r["period"]: r for r in rows}
    # 2026: programs 200 on revenue 2000 -> 10%; history: 300 booked + 10% x 1000.
    for p in rg.HISTORY_MONTHS:
        assert Decimal(by[p][LINE]) == Decimal("400.00")
    for p in rg.PROGRAM_RATIO_MONTHS:
        assert by[p][LINE] == "700.00"
    assert len(log) == len(rg.HISTORY_MONTHS)
    assert "999.00" in log[0]["detail"]


def test_history_programs_follow_revenue():
    rows = summary()
    rows[0]["revenue"] = "3000.00"
    out, _ = rg.history_programs_at_actual_ratio(rows, booked())
    assert Decimal(out[0][LINE]) - Decimal("300") == Decimal("300.00")


def test_no_2026_programs_refuses_instead_of_sizing_history_at_zero():
    with pytest.raises(ValueError, match="no ratio"):
        rg.history_programs_at_actual_ratio(summary(), booked(actual=Decimal("700")))


def test_missing_month_refuses():
    rows = [r for r in summary() if r["period"] != "2026-03"]
    with pytest.raises(ValueError, match="2026-03"):
        rg.history_programs_at_actual_ratio(rows, booked())
