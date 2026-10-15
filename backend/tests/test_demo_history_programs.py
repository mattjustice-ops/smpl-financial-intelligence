"""Actual marketing programs: January-May 2026 is the source ledger.

Months with no program rows are booked at that month's own sales and marketing after the subledgers,
split with the 2026 channel mix.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "demo_data"))

import rebuild_gl_to_summary as rg  # noqa: E402


def gl_row(period: str, account: str, amount: str, notes: str) -> dict[str, str]:
    return {
        "period": period, "account_number": account, "department": "Marketing", "cost_center": "MKT-DG",
        "notes": notes, "amount": amount, "statement": "Income Statement",
        "source_record_id": f"{notes}-{period}", "source_system": "GL",
    }


# Credit-positive, matching the source GL. March has one extra accrual.
SOURCE = {
    "2026-01": (("6300", "-100.10", "Paid Search"), ("6310", "-10.00", "Events")),
    "2026-02": (("6300", "-200.20", "Paid Search"), ("6310", "-20.00", "Events")),
    "2026-03": (("6300", "-300.30", "Paid Search"), ("6310", "-30.00", "Events"),
                ("6300", "-9.82", "Vendor payment / accrual for Events Agency")),
    "2026-04": (("6300", "-400.40", "Paid Search"), ("6310", "-40.00", "Events")),
    "2026-05": (("6300", "-500.50", "Paid Search"), ("6310", "-50.00", "Events")),
}


def source_gl(drop: str | None = None) -> list[dict[str, str]]:
    rows = []
    for period, items in SOURCE.items():
        if period == drop:
            continue
        rows.extend(gl_row(period, account, amount, notes) for account, amount, notes in items)
    rows.append(gl_row("2024-01", "6000", "1799887.64", "Sales & Marketing"))
    return rows


def inputs(overrides: dict[str, tuple[str, str]] | None = None):
    """summary S&M and already-booked S&M for every month that has no program rows."""
    summary, booked = [], {}
    for period in sorted(rg.GENERATED_PROGRAM_MONTHS):
        sm, held = (overrides or {}).get(period, ("1000.00", "600.00"))
        summary.append({"period": period, "sales_and_marketing": sm})
        booked[(period, "sales_and_marketing")] = Decimal(held)
    return summary, booked


def by_period(rows):
    out: dict[str, list] = {}
    for row in rows:
        out.setdefault(row["period"], []).append(row)
    return out


def total(rows) -> Decimal:
    return sum((Decimal(r["amount"]) for r in rows), Decimal("0"))


def test_source_months_are_booked_and_not_flagged():
    summary, booked = inputs()
    rows, log = rg.actual_marketing_program_rows(source_gl(), summary, booked)
    got = by_period(rows)
    assert total(got["2026-01"]) == Decimal("110.10")
    assert total(got["2026-03"]) == Decimal("340.12")
    assert any(r["notes"] == "Vendor payment / accrual for Events Agency" and r["amount"] == "9.82"
               for r in got["2026-03"])
    for period in rg.SOURCE_PROGRAM_MONTHS:
        assert all(rg.GENERATED_PROGRAM_NOTE not in r["notes"] for r in got[period])
    booked_log = [x for x in log if x["action"] == "booked"]
    assert [x["period"] for x in booked_log] == rg.SOURCE_PROGRAM_MONTHS
    assert "not scaled" in booked_log[0]["detail"]


def test_a_month_without_program_rows_uses_its_own_sales_and_marketing():
    summary, booked = inputs({
        "2024-01": ("500.00", "300.00"),
        "2024-03": ("580.00", "400.00"),
        "2025-01": ("700.00", "450.00"),
    })
    rows, _ = rg.actual_marketing_program_rows(source_gl(), summary, booked)
    got = by_period(rows)
    # 2024-01 remainder is 200, not January 2026's 110.10. Mix is 100.10 and 10.00.
    assert total(got["2024-01"]) == Decimal("200.00")
    assert total(got["2026-01"]) == Decimal("110.10")
    search = next(r for r in got["2024-01"] if r["notes"].startswith("Paid Search"))
    events = next(r for r in got["2024-01"] if r["notes"].startswith("Events"))
    assert search["amount"] == "181.83"
    assert events["amount"] == "18.17"
    assert rg.GENERATED_PROGRAM_NOTE in search["notes"]
    # March keeps the March-only accrual as its share of March's own remainder (180), not the 9.82 source amount.
    assert total(got["2024-03"]) == Decimal("180.00")
    accrual = next(r for r in got["2024-03"] if "Events Agency" in r["notes"])
    assert accrual["amount"] != "9.82"
    assert Decimal(accrual["amount"]) < Decimal("9.82")
    assert total(got["2025-01"]) == Decimal("250.00")


def test_june_through_december_use_that_months_remainder():
    summary, booked = inputs({
        "2024-06": ("650.00", "300.00"),
        "2024-07": ("800.00", "300.00"),
        "2026-06": ("700.00", "300.00"),
    })
    rows, log = rg.actual_marketing_program_rows(source_gl(), summary, booked)
    got = by_period(rows)
    assert total(got["2024-06"]) == Decimal("350.00")
    assert total(got["2024-07"]) == Decimal("500.00")
    assert total(got["2026-06"]) == Decimal("400.00")
    assert total(got["2026-06"]) != Decimal("332.26")
    accrual = next(r for r in got["2026-06"] if "Events Agency" in r["notes"])
    assert rg.GENERATED_PROGRAM_NOTE in accrual["notes"]
    assert "700.00" in next(x["detail"] for x in log if x["period"] == "2026-06")
    generated = {x["period"] for x in log if x["action"] == "generated"}
    assert generated == rg.GENERATED_PROGRAM_MONTHS


def test_missing_source_month_refuses():
    summary, booked = inputs()
    with pytest.raises(ValueError, match="2026-04"):
        rg.actual_marketing_program_rows(source_gl(drop="2026-04"), summary, booked)


def test_subledgers_above_the_months_sales_and_marketing_refuse():
    summary, booked = inputs({"2024-06": ("100.00", "150.00")})
    with pytest.raises(ValueError, match="2024-06"):
        rg.actual_marketing_program_rows(source_gl(), summary, booked)


class _Line:
    def __init__(self, account: str, description: str):
        self.account = account
        self.description = description


def test_generated_vendor_bills_carry_the_note():
    usage = _Line("6300", "Usage")
    assert rg.GENERATED_PROGRAM_NOTE in rg._program_bill_note("Actual", "2024-06", usage, "Usage; bill 1")
    assert rg.GENERATED_PROGRAM_NOTE in rg._program_bill_note("Actual", "2026-06", usage, "Usage; accrued")
    assert rg.GENERATED_PROGRAM_NOTE not in rg._program_bill_note("Actual", "2026-01", usage, "Usage; bill 1")
    assert rg.GENERATED_PROGRAM_NOTE not in rg._program_bill_note("Budget", "2024-06", usage, "Usage")
    assert rg.GENERATED_PROGRAM_NOTE not in rg._program_bill_note(
        "Actual", "2024-06", _Line("6200", "Usage"), "Usage")
