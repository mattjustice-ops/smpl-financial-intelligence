"""Dashboard attribution service tests."""

from __future__ import annotations

from decimal import Decimal

from app.services.dashboard.waterfall_service import _validate
from app.services.dashboard.schemas import WaterfallSummaryRow


def row(waterfall_type: str, amount: str) -> WaterfallSummaryRow:
    return WaterfallSummaryRow(
        organization_id="org",
        scenario="Forecast",
        period="2026-06",
        waterfall_name="pipeline",
        waterfall_type=waterfall_type,
        line_item=waterfall_type,
        line_item_order=1,
        amount=Decimal(amount),
        source_table="forecast_pipeline_waterfall",
        detail_count=1,
    )


def test_pipeline_waterfall_validation_ties() -> None:
    checks = _validate(
        [
            row("beginning_pipeline", "100"),
            row("pipeline_created", "50"),
            row("closed_won", "-10"),
            row("closed_lost", "-20"),
            row("slipped_pipeline", "-5"),
            row("ending_pipeline", "115"),
        ],
        "pipeline",
    )
    assert checks[0].status == "pass"


def test_cash_waterfall_validation_ties() -> None:
    rows = [
        WaterfallSummaryRow(
            organization_id="org",
            scenario="Forecast",
            period="2026-06",
            waterfall_name="cash_flow",
            waterfall_type=waterfall_type,
            line_item=waterfall_type,
            line_item_order=1,
            amount=Decimal(amount),
            source_table="forecast_cash_flow_bridge",
            detail_count=1,
        )
        for waterfall_type, amount in [
            ("beginning_cash", "100"),
            ("cash_collections", "50"),
            ("payroll_cash_out", "-20"),
            ("commission_cash_out", "-5"),
            ("vendor_cash_out", "-10"),
            ("tax_cash_out", "-2"),
            ("capex", "-3"),
            ("financing", "0"),
            ("ending_cash", "110"),
        ]
    ]
    checks = _validate(rows, "cash_flow")
    assert checks[0].status == "pass"
