"""Opportunity mix is the deal ledger totaled by type."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "demo_data"))

import refresh_reference_files as ref  # noqa: E402


def test_mix_totals_the_deals_and_drops_a_stale_snapshot():
    deals = [
        {"opportunity_type": "New Business", "amount_arr": "100.10"},
        {"opportunity_type": "New Business", "amount_arr": "50.00"},
        {"opportunity_type": "Churn", "amount_arr": "20.005"},
        {"opportunity_type": "Expansion", "amount_arr": "3"},
    ]
    rows = ref.opportunity_mix_rows(deals)
    assert [r["opportunity_type"] for r in rows] == ["Churn", "Expansion", "New Business"]
    assert rows[-1] == {"opportunity_type": "New Business", "count": "2", "sum": "150.10"}
    assert rows[0]["sum"] == "20.01"
