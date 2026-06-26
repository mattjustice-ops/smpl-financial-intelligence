"""Copilot cash bridge context uses focus month, not only org close month."""

from __future__ import annotations

from decimal import Decimal

from app.services.reporting.export.board_commentary_service import (
    _monthly_cash_bridge_table_prompt,
    cash_reconciliation_prompt_blob,
)
from app.services.reporting.export.schemas import ReportingBundle


def _minimal_bundle(*, as_of: str = "2026-06") -> ReportingBundle:
    return ReportingBundle(
        organization_id="00000000-0000-0000-0000-000000000001",
        organization_name="SMPL",
        scenario="Combined",
        start_period="2026-01",
        end_period="2026-12",
        as_of_period=as_of,
        period_label="June 2026",
        comparison_waterfalls={},
    )


def test_cash_reconciliation_uses_focus_month_from_bridge_table():
    bundle = _minimal_bundle()
    bridge = {
        "Actual": {
            "2026-02": {
                "beginning_cash": 50_000_000.0,
                "collections": 11_000_000.0,
                "payroll": 2_500_000.0,
                "ending_cash": 51_010_000.0,
            },
            "2026-06": {
                "beginning_cash": 66_000_000.0,
                "collections": 12_000_000.0,
                "ending_cash": 70_612_122.0,
            },
        },
        "Budget": {
            "2026-02": {
                "beginning_cash": 49_500_000.0,
                "collections": 10_500_000.0,
                "ending_cash": 50_800_000.0,
            }
        },
    }
    blob = cash_reconciliation_prompt_blob(
        bundle,
        cash_bridge_table=bridge,
        focus_period="2026-02",
    )
    assert "2026-02" in blob
    assert "Collections" in blob
    assert "Budget" in blob
    assert "66,000,000" not in blob  # June bridge must not appear in February detail block


def test_monthly_cash_bridge_table_lists_all_months():
    bridge = {
        "Actual": {
            "2026-02": {"ending_cash": 51_010_000.0},
            "2026-06": {"ending_cash": 70_612_122.0},
        }
    }
    blob = _monthly_cash_bridge_table_prompt(
        bridge,
        start_period="2026-01",
        end_period="2026-06",
        currency="USD",
    )
    assert "2026-02" in blob
    assert "2026-06" in blob
