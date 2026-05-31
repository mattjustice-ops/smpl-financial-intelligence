"""Orchestration for reporting exports."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.services.reporting.export.data_collector import collect_reporting_bundle
from app.services.reporting.export.excel_workbook import build_workbook_bytes
from app.services.reporting.export.pptx_report_builder import build_pptx_bytes
from app.services.reporting.export.schemas import ExportValidationSummary, ReportingBundle

CLOSE_PACKAGE_SHEETS = [
    "Executive Summary",
    "KPI Scorecard",
    "Income Statement",
    "Balance Sheet",
    "Cash Flow Statement",
    "Cash Flow Bridge",
    "MRR ARR Waterfall",
    "Pipeline Waterfall",
    "Opportunity Drilldown",
    "Marketing Performance",
    "Revenue Forecast",
    "Bookings Forecast",
    "Deferred Revenue Waterfall",
    "Headcount & Hiring",
    "GL Detail by Department",
    "Department Spend - P&L",
    "Variance Commentary",
    "Data Sources & Gaps",
    "Validation Checks",
]

MANAGEMENT_REVIEW_SHEETS = [
    "Executive Summary",
    "KPI Scorecard",
    "Income Statement",
    "MRR ARR Waterfall",
    "Pipeline Waterfall",
    "Cash Flow Bridge",
    "Marketing Performance",
    "Variance Commentary",
    "Data Sources & Gaps",
    "Validation Checks",
]

VARIANCE_SHEETS = ["Variance Commentary", "Validation Checks"]


def collect_bundle(
    db: Session,
    organization_id: uuid.UUID,
    *,
    include_ai_commentary: bool = False,
    **params,
) -> ReportingBundle:
    as_of = params.pop("as_of_period", None)
    return collect_reporting_bundle(
        db,
        organization_id,
        scenario=params["scenario"],
        start_period=params["start_period"],
        end_period=params["end_period"],
        as_of_period=as_of,
        include_ai_commentary=include_ai_commentary,
        waterfall_type=params.get("waterfall_type"),
        marketing_channel=params.get("marketing_channel"),
        region=params.get("region"),
        segment=params.get("segment"),
        owner=params.get("owner"),
    )


def run_export_validation(
    db: Session,
    organization_id: uuid.UUID,
    **params,
) -> ExportValidationSummary:
    bundle = collect_bundle(db, organization_id, include_ai_commentary=False, **params)
    return bundle.validation


def build_excel_close_package(bundle: ReportingBundle) -> bytes:
    return build_workbook_bytes(bundle, sheet_names=CLOSE_PACKAGE_SHEETS)


def build_excel_management_review(bundle: ReportingBundle) -> bytes:
    return build_workbook_bytes(bundle, sheet_names=MANAGEMENT_REVIEW_SHEETS)


def build_excel_variance_commentary(bundle: ReportingBundle) -> bytes:
    return build_workbook_bytes(bundle, sheet_names=VARIANCE_SHEETS)


def build_pptx_board_presentation(
    bundle: ReportingBundle,
    *,
    include_commentary: bool = True,
    include_validation_appendix: bool = True,
    use_ai_commentary: bool = False,
    scenario_mode: str | None = None,
    package_mode: str = "full_board",
) -> bytes:
    return build_pptx_bytes(
        bundle,
        include_commentary=include_commentary,
        include_validation_appendix=include_validation_appendix,
        use_ai_commentary=use_ai_commentary,
        scenario_mode=scenario_mode,
        package_mode=package_mode,  # type: ignore[arg-type]
    )
