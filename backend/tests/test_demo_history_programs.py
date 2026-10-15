"""Actual marketing programs: January-May 2026 is the source ledger; other months are generated from it."""

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
    rows.append(gl_row("2024-01", "6000", "-1799887.64", "Sales & Marketing"))
    return rows


def by_period(rows):
    out: dict[str, list] = {}
    for row in rows:
        out.setdefault(row["period"], []).append(row)
    return out


def total(rows) -> Decimal:
    return sum((Decimal(r["amount"]) for r in rows), Decimal("0"))


def test_source_months_are_booked_and_not_flagged():
    rows, log = rg.actual_marketing_program_rows(source_gl())
    got = by_period(rows)
    assert total(got["2026-01"]) == Decimal("110.10")
    assert total(got["2026-03"]) == Decimal("340.12")
    assert any(r["notes"] == "Vendor payment / accrual for Events Agency" and r["amount"] == "9.82"
               for r in got["2026-03"])
    for period in rg.SOURCE_PROGRAM_MONTHS:
        assert all(rg.GENERATED_PROGRAM_NOTE not in r["notes"] for r in got[period])
    booked = [x for x in log if x["action"] == "booked"]
    assert [x["period"] for x in booked] == rg.SOURCE_PROGRAM_MONTHS
    assert "not scaled" in booked[0]["detail"]


def test_same_calendar_month_copies_the_source_and_is_flagged():
    rows, _ = rg.actual_marketing_program_rows(source_gl())
    got = by_period(rows)
    assert total(got["2024-01"]) == total(got["2026-01"])
    assert total(got["2025-03"]) == total(got["2026-03"])
    accrual = [r for r in got["2024-03"] if "Events Agency" in r["notes"]]
    assert len(accrual) == 1 and accrual[0]["amount"] == "9.82"
    assert rg.GENERATED_PROGRAM_NOTE in accrual[0]["notes"]
    assert all(rg.GENERATED_PROGRAM_NOTE in r["notes"] for r in got["2024-01"])


def test_other_months_are_the_january_may_average():
    rows, log = rg.actual_marketing_program_rows(source_gl())
    got = by_period(rows)
    # 1,661.32 of source spend / 5 = 332.264 -> 332.26. The March-only 9.82 is one fifth, 1.96.
    assert total(got["2026-06"]) == Decimal("332.26")
    assert total(got["2024-06"]) == Decimal("332.26")
    assert total(got["2025-12"]) == Decimal("332.26")
    accrual = [r for r in got["2026-06"] if "Events Agency" in r["notes"]]
    assert len(accrual) == 1 and accrual[0]["amount"] == "1.96"
    assert rg.GENERATED_PROGRAM_NOTE in accrual[0]["notes"]
    generated = {x["period"] for x in log if x["action"] == "generated"}
    assert generated == rg.GENERATED_PROGRAM_MONTHS


def test_missing_source_month_refuses():
    with pytest.raises(ValueError, match="2026-04"):
        rg.actual_marketing_program_rows(source_gl(drop="2026-04"))


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
