"""Actual marketing programs: January-June 2026 is the rate and the channel mix.

January-May 2026 is copied from the source ledger. June program dollars are the close.
2024 and 2025 are that month's revenue times the January-June 2026 program rate.
June, before the close replaces it, is that month's sales and marketing after the subledgers.
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
    "2026-06": (("6300", "-600.60", "Paid Search"), ("6310", "-60.00", "Events")),
}


def source_gl(drop: str | None = None) -> list[dict[str, str]]:
    rows = []
    for period, items in SOURCE.items():
        if period == drop:
            continue
        rows.extend(gl_row(period, account, amount, notes) for account, amount, notes in items)
    rows.append(gl_row("2024-01", "6000", "1799887.64", "Sales & Marketing"))
    rows.append({
        "period": "2026-06", "account_number": "4000", "department": "Sales", "cost_center": "SAL",
        "notes": "Revenue", "amount": "10000.00", "statement": "Income Statement",
        "statement_category": "Revenue", "source_record_id": "rev-2026-06", "source_system": "GL",
    })
    return rows


def inputs(overrides: dict[str, tuple[str, str, str]] | None = None):
    """summary S&M, already-booked S&M, and revenue for every month that has no program rows."""
    summary, booked = [], {}
    for period in rg.SOURCE_PROGRAM_MONTHS:
        summary.append({"period": period, "sales_and_marketing": "0.00", "revenue": "10000.00"})
    for period in sorted(rg.GENERATED_PROGRAM_MONTHS):
        default_rev = "10000.00" if period in rg.PROGRAM_RATE_MONTHS else "1000.00"
        sm, held, rev = (overrides or {}).get(period, ("1000.00", "600.00", default_rev))
        summary.append({"period": period, "sales_and_marketing": sm, "revenue": rev})
        booked[(period, "sales_and_marketing")] = Decimal(held)
    return summary, booked


def program_rate() -> Decimal:
    """Source program total 2,321.92 over 6 x 10,000 of revenue (January-June)."""
    return Decimal("2321.92") / Decimal("60000")


def at_rate(revenue: str) -> Decimal:
    return (Decimal(revenue) * program_rate()).quantize(Decimal("0.01"))


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


def test_history_months_use_the_2026_program_rate_on_that_months_revenue():
    summary, booked = inputs({
        "2024-01": ("500.00", "300.00", "6000.00"),
        "2024-03": ("580.00", "400.00", "3000.00"),
        "2025-01": ("700.00", "450.00", "8000.00"),
    })
    rows, _ = rg.actual_marketing_program_rows(source_gl(), summary, booked)
    got = by_period(rows)
    assert total(got["2024-01"]) == at_rate("6000.00")
    assert total(got["2024-01"]) != Decimal("200.00")
    assert total(got["2026-01"]) == Decimal("110.10")
    search = next(r for r in got["2024-01"] if r["notes"].startswith("Paid Search"))
    assert rg.HISTORY_PROGRAM_NOTE in search["notes"]
    assert rg.GENERATED_PROGRAM_NOTE not in search["notes"]
    assert total(got["2024-03"]) == at_rate("3000.00")
    accrual = next(r for r in got["2024-03"] if "Events Agency" in r["notes"])
    assert accrual["amount"] != "9.82"
    assert total(got["2025-01"]) == at_rate("8000.00")


def test_june_close_placeholder_uses_that_months_sales_and_marketing():
    summary, booked = inputs({
        "2024-06": ("650.00", "300.00", "4000.00"),
        "2024-07": ("800.00", "300.00", "5000.00"),
        "2026-06": ("700.00", "300.00", "9000.00"),
    })
    rows, log = rg.actual_marketing_program_rows(source_gl(), summary, booked)
    got = by_period(rows)
    # June revenue on the statement is 9,000, so the rate is the program total over 59,000.
    june_rate = Decimal("2321.92") / Decimal("59000")
    assert total(got["2024-06"]) == (Decimal("4000.00") * june_rate).quantize(Decimal("0.01"))
    assert total(got["2024-07"]) == (Decimal("5000.00") * june_rate).quantize(Decimal("0.01"))
    assert total(got["2026-06"]) == Decimal("400.00")
    june = got["2026-06"]
    assert all(rg.GENERATED_PROGRAM_NOTE in r["notes"] for r in june)
    assert not any("Events Agency" in r["notes"] for r in june)
    assert any("Events Agency" in r["notes"] for r in got["2024-07"])
    assert "700.00" in next(x["detail"] for x in log if x["period"] == "2026-06")
    generated = {x["period"] for x in log if x["action"] == "generated"}
    assert generated == rg.GENERATED_PROGRAM_MONTHS


def test_missing_source_month_refuses():
    summary, booked = inputs()
    with pytest.raises(ValueError, match="2026-04"):
        rg.actual_marketing_program_rows(source_gl(drop="2026-04"), summary, booked)


def test_june_subledgers_above_sales_and_marketing_refuse():
    summary, booked = inputs({"2026-06": ("100.00", "150.00", "1000.00")})
    with pytest.raises(ValueError, match="2026-06"):
        rg.actual_marketing_program_rows(source_gl(), summary, booked)


class _Line:
    def __init__(self, account: str, description: str):
        self.account = account
        self.description = description


def test_generated_vendor_bills_carry_the_note():
    usage = _Line("6300", "Usage")
    assert rg.HISTORY_PROGRAM_NOTE in rg._program_bill_note("Actual", "2024-06", usage, "Usage; bill 1")
    assert rg.GENERATED_PROGRAM_NOTE in rg._program_bill_note("Actual", "2026-06", usage, "Usage; accrued")
    assert rg.GENERATED_PROGRAM_NOTE not in rg._program_bill_note("Actual", "2026-01", usage, "Usage; bill 1")
    assert rg.GENERATED_PROGRAM_NOTE not in rg._program_bill_note("Budget", "2024-06", usage, "Usage")
    assert rg.GENERATED_PROGRAM_NOTE not in rg._program_bill_note(
        "Actual", "2024-06", _Line("6200", "Usage"), "Usage")


def _close_row(account: str, amount: str, department: str = "Sales") -> dict:
    return {"period": "2026-06", "account_number": account, "amount": amount, "department": department,
            "statement": "Income Statement", "notes": "June close"}


def test_june_close_rows_use_the_source_sign_and_refuse_the_gap_fill():
    # Source June is stored like the other 2026 detail: expenses negative. The close comes back debit-positive.
    rows = [_close_row("6100", "-10.00"), _close_row("6300", "-2.50", "Marketing")]
    got = rg.actual_close_rows(rows)
    assert [r["amount"] for r in got] == ["10.00", "2.50"]
    gap = [_close_row(a, "1.00", "All") for a in ("4000", "5000", "6000", "6500", "7000", "7500", "8000", "8500")]
    with pytest.raises(ValueError, match="gap fill"):
        rg.actual_close_rows(gap)
