"""Period column coercion for demo CSV uploads."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.schemas.demo_csv import MrrWaterfallRow


def test_mrr_waterfall_period_accepts_us_short_dates() -> None:
    row = MrrWaterfallRow.model_validate(
        {
            "period": "1/1/2026",
            "customer_id": "CUST-001",
            "beginning_mrr": "1000",
            "ending_mrr": "1100",
            "movement_type": "unchanged",
        }
    )
    assert row.period == date(2026, 1, 1)


def test_mrr_waterfall_period_accepts_yyyy_mm() -> None:
    row = MrrWaterfallRow.model_validate(
        {
            "period": "2026-05",
            "customer_id": "CUST-001",
            "movement_type": "new",
        }
    )
    assert row.period == date(2026, 5, 1)


def test_mrr_waterfall_period_normalizes_mid_month_to_first() -> None:
    row = MrrWaterfallRow.model_validate(
        {
            "period": "03/15/2026",
            "customer_id": "CUST-001",
            "movement_type": "unchanged",
        }
    )
    assert row.period == date(2026, 3, 1)
