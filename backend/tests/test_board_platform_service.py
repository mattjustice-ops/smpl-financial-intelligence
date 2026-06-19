"""Board platform payload helpers."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.dashboard.schemas import ExecutiveFlowResponse
from app.services.board_platform_service import _build_time_series
from app.services.financial_statements.financial_statement_service import (
    NormalizedStatementLine,
    NormalizedStatementResponse,
    SummaryResponse,
)
from app.services.reporting.export.schemas import ExportValidationSummary, ReportingBundle


def _line(scenario: str, period: str, line_item: str, amount: str) -> NormalizedStatementLine:
    y, m = period.split("-")
    return NormalizedStatementLine(
        organization_id="8571e520-0687-4516-bdee-379f37c58c1f",
        scenario=scenario,
        period=date(int(y), int(m), 1),
        line_item=line_item,
        line_item_order=100,
        section="Revenue",
        amount=Decimal(amount),
        source_table="actual_income_statement",
        source_column="revenue",
    )


def test_build_time_series_from_normalized_statement_rows() -> None:
    income = NormalizedStatementResponse(
        organization_id="8571e520-0687-4516-bdee-379f37c58c1f",
        scenario="Combined",
        start_period=date(2026, 1, 1),
        end_period=date(2026, 3, 1),
        statement_type="income_statement",
        rows=[
            _line("Actual", "2026-01", "Revenue", "1000000"),
            _line("Actual", "2026-01", "EBITDA", "200000"),
            _line("Forecast", "2026-02", "Revenue", "1100000"),
        ],
    )
    summary = SummaryResponse(
        organization_id="8571e520-0687-4516-bdee-379f37c58c1f",
        scenario="Combined",
        start_period=date(2026, 1, 1),
        end_period=date(2026, 3, 1),
        income_statement=income,
        balance_sheet=income,
        cash_flow=income,
        validation=[],
    )
    bundle = ReportingBundle(
        organization_id="8571e520-0687-4516-bdee-379f37c58c1f",
        organization_name="SMPL Demo Co",
        scenario="Combined",
        start_period="2026-01",
        end_period="2026-03",
        as_of_period="2026-01",
        period_label="January 2026",
        executive_flow=ExecutiveFlowResponse(
            organization_id="8571e520-0687-4516-bdee-379f37c58c1f",
            scenario="Combined",
            start_period="2026-01",
            end_period="2026-03",
            as_of_period="2026-01",
        ),
        validation=ExportValidationSummary(status="pass"),
        comparison_financial_statements=summary,
    )

    ts = _build_time_series(bundle)

    assert ts["periods"] == ["2026-01", "2026-02"]
    assert ts["Actual"]["2026-01"]["revenue"] == 1_000_000.0
    assert ts["Actual"]["2026-01"]["ebitda"] == 200_000.0
    assert ts["Forecast"]["2026-02"]["revenue"] == 1_100_000.0
