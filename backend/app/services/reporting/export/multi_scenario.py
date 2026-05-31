"""Fetch Actual, Budget, and Forecast slices for export comparisons."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.services.dashboard.schemas import WaterfallSummaryRow
from app.services.dashboard.waterfall_service import waterfall_response
from app.services.financial_statements.financial_statement_service import (
    NormalizedStatementResponse,
    SummaryResponse,
    summary,
)
from app.services.marketing.schemas import ActualBudgetForecastResponse, MarketingMetricRow
from app.services.marketing.service import actual_budget_forecast
from app.services.reporting.export.schemas import DataGapNote
from app.services.reporting.period_utils import to_period

WATERFALL_NAMES: tuple[str, ...] = ("arr", "pipeline", "deferred_revenue", "cash_flow")
EXPORT_SCENARIOS: tuple[str, ...] = ("Actual", "Budget", "Forecast")


def _statement_dates(start_period: str, end_period: str) -> tuple[date, date]:
    import calendar

    start = date(int(start_period[:4]), int(start_period[5:7]), 1)
    y, m = int(end_period[:4]), int(end_period[5:7])
    end = date(y, m, calendar.monthrange(y, m)[1])
    return start, end


def collect_comparison_waterfalls(
    db: Session,
    organization_id: uuid.UUID,
    *,
    start_period: str,
    end_period: str,
    **filters,
) -> dict[str, list[WaterfallSummaryRow]]:
    """Merge waterfall rows from Actual, Budget, and Forecast API calls."""
    merged: dict[str, list[WaterfallSummaryRow]] = {}
    base = {
        "start_period": start_period,
        "end_period": end_period,
        **{k: v for k, v in filters.items() if k in {"waterfall_type", "marketing_channel", "region", "segment", "owner"}},
    }
    for waterfall_name in WATERFALL_NAMES:
        rows: list[WaterfallSummaryRow] = []
        for scenario in EXPORT_SCENARIOS:
            try:
                response = waterfall_response(
                    db,
                    organization_id,
                    waterfall_name=waterfall_name,
                    scenario=scenario,
                    **base,
                )
                rows.extend(response.rows)
            except Exception:
                continue
        merged[waterfall_name] = rows
    return merged


def collect_comparison_financial_statements(
    db: Session,
    organization_id: uuid.UUID,
    *,
    start_period: str,
    end_period: str,
) -> SummaryResponse | None:
    fs_start, fs_end = _statement_dates(start_period, end_period)
    income_rows = []
    balance_rows = []
    cash_rows = []
    periods: set[date] = set()
    validation = []
    loaded_any = False
    for scenario in EXPORT_SCENARIOS:
        try:
            block = summary(
                db,
                organization_id,
                scenario=scenario,
                start_period=fs_start,
                end_period=fs_end,
            )
            loaded_any = True
            income_rows.extend(block.income_statement.rows)
            balance_rows.extend(block.balance_sheet.rows)
            cash_rows.extend(block.cash_flow.rows)
            periods.update(block.income_statement.periods)
            validation.extend(block.validation)
        except Exception:
            continue
    if not loaded_any:
        return None
    org = str(organization_id)
    return SummaryResponse(
        organization_id=org,
        scenario="Comparison",
        start_period=fs_start,
        end_period=fs_end,
        income_statement=NormalizedStatementResponse(
            organization_id=org,
            scenario="Comparison",
            start_period=fs_start,
            end_period=fs_end,
            statement_type="income_statement",
            rows=income_rows,
            periods=sorted(periods),
        ),
        balance_sheet=NormalizedStatementResponse(
            organization_id=org,
            scenario="Comparison",
            start_period=fs_start,
            end_period=fs_end,
            statement_type="balance_sheet",
            rows=balance_rows,
            periods=sorted(periods),
        ),
        cash_flow=NormalizedStatementResponse(
            organization_id=org,
            scenario="Comparison",
            start_period=fs_start,
            end_period=fs_end,
            statement_type="cash_flow",
            rows=cash_rows,
            periods=sorted(periods),
        ),
        validation=validation,
    )


def collect_marketing_comparison(
    db: Session,
    organization_id: uuid.UUID,
    *,
    start_period: str,
    end_period: str,
    marketing_channel: str | None = None,
) -> ActualBudgetForecastResponse | None:
    try:
        return actual_budget_forecast(
            db,
            organization_id,
            start_period=start_period,
            end_period=end_period,
            marketing_channel=marketing_channel,
        )
    except Exception:
        return None


def assess_data_gaps(
    *,
    comparison_waterfalls: dict[str, list[WaterfallSummaryRow]],
    financial: SummaryResponse | None,
    marketing: ActualBudgetForecastResponse | None,
    gl_count: int,
    headcount_count: int,
    as_of_period: str,
) -> list[DataGapNote]:
    notes: list[DataGapNote] = []
    def scen_has(rows: list, scen: str, period: str) -> bool:
        return any(r.scenario == scen and to_period(r.period) == period and r.amount != 0 for r in rows)

    arr = comparison_waterfalls.get("arr", [])
    for scen, tables in (
        ("Actual", "actual_* CSVs (MRR waterfall, income statement, pipeline, etc.)"),
        ("Budget", "Budget_* CSVs (e.g. Budget_MRR_Waterfall.csv, Budget_income_statement.csv)"),
        ("Forecast", "Forecast_* CSVs (e.g. Forecast_MRR_Waterfall.csv, Forecast_income_statement.csv)"),
    ):
        if arr and not scen_has(arr, scen, as_of_period):
            notes.append(
                DataGapNote(
                    section="MRR / ARR Waterfall",
                    scenario=scen,
                    status="missing",
                    expected_source=tables,
                    message=f"No {scen} ARR waterfall rows for {as_of_period}.",
                    action=f"Upload {tables} via Demo CSV and reload the warehouse.",
                )
            )

    if financial is None:
        notes.append(
            DataGapNote(
                section="Financial Statements",
                scenario="All",
                status="missing",
                expected_source="Actual/Budget/Forecast income statement, balance sheet, cash flow CSVs",
                message="Financial statements could not be loaded.",
                action="Upload statement CSVs and call GET /financial-statements/summary to verify.",
            )
        )
    else:
        for scen in EXPORT_SCENARIOS:
            has_rev = any(
                r.scenario == scen
                and to_period(str(r.period)) == as_of_period
                and "revenue" in r.line_item.lower()
                and r.amount != 0
                for r in financial.income_statement.rows
            )
            if not has_rev:
                notes.append(
                    DataGapNote(
                        section="Income Statement",
                        scenario=scen,
                        status="partial",
                        expected_source=f"{scen}_income_statement.csv",
                        message=f"No {scen} revenue line for {as_of_period}.",
                        action="Confirm revenue column is populated in the income statement CSV.",
                    )
                )

    if marketing is None or not marketing.actual:
        notes.append(
            DataGapNote(
                section="Marketing Performance",
                scenario="All",
                status="missing",
                expected_source="actual_marketing_pipeline, budget_marketing_pipeline, forecast_marketing_pipeline tables",
                message="Marketing Actual/Budget/Forecast comparison not available.",
                action="Upload marketing pipeline CSVs (Actual, Budget, Forecast).",
            )
        )

    if gl_count == 0:
        notes.append(
            DataGapNote(
                section="GL Detail by Department",
                scenario="Actual/Budget",
                status="missing",
                expected_source="gl_actuals (from Actual_gl_detail.csv / Budget_gl_detail.csv)",
                message="No GL detail rows in range.",
                action="Upload GL detail CSVs with department and account columns.",
            )
        )

    if headcount_count == 0:
        notes.append(
            DataGapNote(
                section="Headcount & Hiring",
                scenario="Actual/Forecast",
                status="missing",
                expected_source="headcount_plan, forecast_headcount_plan",
                message="No headcount plan rows in range.",
                action="Upload Headcount_plan.csv and Forecast_headcount_plan.csv.",
            )
        )

    pipeline = comparison_waterfalls.get("pipeline", [])
    if pipeline and not any(r.waterfall_type == "closed_won" and to_period(r.period) == as_of_period for r in pipeline):
        notes.append(
            DataGapNote(
                section="Pipeline / Opportunity Drilldown",
                scenario="As loaded",
                status="partial",
                expected_source="pipeline waterfall + opportunity_movements CSVs",
                message=f"No closed-won pipeline movement for {as_of_period}.",
                action="Upload pipeline waterfall and opportunity movement files for drilldown commentary.",
            )
        )

    if not notes:
        notes.append(
            DataGapNote(
                section="All",
                scenario="All",
                status="ok",
                expected_source="API",
                message="Core comparison datasets present for export.",
                action="None",
            )
        )
    return notes
