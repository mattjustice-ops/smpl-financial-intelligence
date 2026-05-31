"""Reporting export unit tests (no database required)."""

from __future__ import annotations

from decimal import Decimal
from app.services.dashboard.schemas import ExecutiveFlowResponse, WaterfallResponse, WaterfallSummaryRow
from app.services.reporting.export.comparison_pivot import pivot_waterfall_abc
from app.services.reporting.export.excel_workbook import build_workbook_bytes
from app.services.reporting.export.period_comparisons import build_comparison_columns, variance
from app.services.reporting.export.schemas import CommentaryField, ExportValidationSummary, ReportingBundle
from app.services.reporting.export.validation_precheck import run_export_validation
from app.services.reporting.validation_service import ValidationCheck


def _minimal_bundle() -> ReportingBundle:
    row = WaterfallSummaryRow(
        organization_id="org",
        scenario="Actual",
        period="2026-05",
        waterfall_name="arr",
        waterfall_type="ending_arr",
        line_item="Ending ARR",
        line_item_order=900,
        amount=Decimal("1200000"),
        source_table="actual_mrr_waterfall",
        detail_count=0,
    )
    arr = WaterfallResponse(
        organization_id="org",
        scenario="Combined",
        start_period="2026-01",
        end_period="2026-05",
        waterfall_name="arr",
        rows=[row],
    )
    executive = ExecutiveFlowResponse(
        organization_id="org",
        scenario="Combined",
        start_period="2026-01",
        end_period="2026-05",
        waterfalls={"arr": arr},
    )
    return ReportingBundle(
        organization_id="org",
        scenario="Combined",
        start_period="2026-01",
        end_period="2026-05",
        as_of_period="2026-05",
        period_label="May 2026",
        executive_flow=executive,
        commentary_fields=[CommentaryField(section="Executive Summary", period="2026-05")],
        validation=ExportValidationSummary(status="pass"),
    )


def test_variance_calculation() -> None:
    diff, pct = variance(Decimal("110"), Decimal("100"))
    assert diff == Decimal("10")
    assert pct == Decimal("0.1000")


def test_comparison_columns_include_mtd_qtd_ytd() -> None:
    cols = build_comparison_columns("2026-05")
    keys = [c[0] for c in cols]
    assert "actual_mtd" in keys
    assert "actual_qtd" in keys
    assert "actual_ytd" in keys


def test_pivot_waterfall_abc_splits_scenarios() -> None:
    rows = [
        WaterfallSummaryRow(
            organization_id="org",
            scenario="Actual",
            period="2026-05",
            waterfall_name="arr",
            waterfall_type="ending_arr",
            line_item="Ending ARR",
            line_item_order=900,
            amount=Decimal("100"),
            source_table="actual_mrr_waterfall",
            detail_count=0,
        ),
        WaterfallSummaryRow(
            organization_id="org",
            scenario="Budget",
            period="2026-05",
            waterfall_name="arr",
            waterfall_type="ending_arr",
            line_item="Ending ARR",
            line_item_order=900,
            amount=Decimal("90"),
            source_table="budget_mrr_waterfall",
            detail_count=0,
        ),
        WaterfallSummaryRow(
            organization_id="org",
            scenario="Forecast",
            period="2026-05",
            waterfall_name="arr",
            waterfall_type="ending_arr",
            line_item="Ending ARR",
            line_item_order=900,
            amount=Decimal("110"),
            source_table="forecast_mrr_waterfall",
            detail_count=0,
        ),
    ]
    piv = pivot_waterfall_abc(rows, periods=["2026-05"])
    assert len(piv) == 1
    assert piv[0]["actual"] == Decimal("100")
    assert piv[0]["budget"] == Decimal("90")
    assert piv[0]["forecast"] == Decimal("110")


def test_excel_workbook_bytes_are_valid_xlsx() -> None:
    bundle = _minimal_bundle()
    bundle.comparison_waterfalls = {"arr": bundle.executive_flow.waterfalls["arr"].rows}
    content = build_workbook_bytes(bundle, sheet_names=["Executive Summary", "Validation Checks"])
    assert content[:2] == b"PK"


def test_export_validation_aggregates_executive_checks() -> None:
    check = ValidationCheck(
        scenario="Combined",
        period="2026-05",
        validation_name="arr_waterfall_ties",
        status="pass",
        source_tables_used=["mrr"],
    )
    executive = ExecutiveFlowResponse(
        organization_id="org",
        scenario="Combined",
        start_period="2026-01",
        end_period="2026-05",
        validation=[check],
    )
    summary = run_export_validation(executive, None)
    assert summary.passed_count >= 1
