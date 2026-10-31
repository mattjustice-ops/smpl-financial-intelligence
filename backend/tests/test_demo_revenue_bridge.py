"""Budget and forecast subscription come from the ARR bridge, including months through the close."""

from __future__ import annotations

import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "demo_data"))

import build_v5_dataset as v5  # noqa: E402


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def rows(self, name):
        return self._rows


def test_bridge_recognizes_from_opening_deferred_and_keeps_earlier_months():
    book = v5.Revenue.__new__(v5.Revenue)
    book.version = "Budget"
    book.months = ["2025-12", "2026-01", "2026-02"]
    book.meta = {
        ("c1", "2026-01"): {"customer_arr": Decimal("1200")},
        ("c1", "2026-02"): {"customer_arr": Decimal("1320")},
    }
    book.by_cust = defaultdict(dict)
    book.sub = {"2025-12": Decimal("1.00")}
    book.rsvc = {"2025-12": Decimal("0.10")}
    book.billed = {}
    waterfall = [
        {"period": "2026-01", "beginning_arr": "1200", "ending_arr": "1320", "new_business_arr": "120"},
        {"period": "2026-02", "beginning_arr": "1320", "ending_arr": "1320", "new_business_arr": "0"},
    ]
    book.apply_arr_bridge(_Rows(waterfall), Decimal("100"), Decimal("1200"), "2026-01")

    assert book.sub["2025-12"] == Decimal("1.00")
    assert book.sub["2026-01"] == Decimal("100.00")
    assert book.rsvc["2026-01"] == Decimal("10.00")
    assert book.billed[("c1", "2026-01")] == Decimal("120.00")
    assert book.sub["2026-02"] == Decimal("110.00")
    assert book.rsvc["2026-02"] == Decimal("11.00")
