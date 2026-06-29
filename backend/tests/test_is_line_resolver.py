"""Tests for IS line resolver — revenue vs COGS disambiguation."""

from decimal import Decimal

from app.services.dashboard.schemas import ExecutiveFlowResponse
from app.services.reporting.export.is_line_resolver import fs_by_period, fs_sum_periods, line_item_matches
from app.services.reporting.export.schemas import ReportingBundle


def test_line_item_matches_revenue_not_cogs():
    assert line_item_matches("revenue", "Revenue")
    assert line_item_matches("revenue", "Subscription Revenue")
    assert not line_item_matches("revenue", "Cost of Revenue")
    assert line_item_matches("cogs", "Cost of Revenue")


def test_fs_by_period_picks_revenue_not_cogs():
    from datetime import date

    from app.services.financial_statements.financial_statement_service import (
        NormalizedStatementLine,
        NormalizedStatementResponse,
        SummaryResponse,
    )

    period = date(2026, 6, 1)
    rev = Decimal("7300000")
    cogs = Decimal("2200000")
    rows = [
        NormalizedStatementLine(
            organization_id="t",
            scenario="Actual",
            period=period,
            line_item="Revenue",
            line_item_order=1,
            section="revenue",
            amount=rev,
            source_table="t",
            source_column="c",
        ),
        NormalizedStatementLine(
            organization_id="t",
            scenario="Actual",
            period=period,
            line_item="Cost of Revenue",
            line_item_order=2,
            section="cogs",
            amount=cogs,
            source_table="t",
            source_column="c",
        ),
    ]
    empty = NormalizedStatementResponse(
        organization_id="t",
        scenario="Combined",
        start_period=period,
        end_period=period,
        statement_type="cf",
        rows=[],
    )
    fs = SummaryResponse(
        organization_id="t",
        scenario="Combined",
        start_period=period,
        end_period=period,
        income_statement=NormalizedStatementResponse(
            organization_id="t",
            scenario="Combined",
            start_period=period,
            end_period=period,
            statement_type="is",
            rows=rows,
        ),
        balance_sheet=empty,
        cash_flow=empty,
        validation=[],
    )
    bundle = ReportingBundle(
        organization_id="t",
        scenario="Combined",
        start_period="2026-01",
        end_period="2026-12",
        as_of_period="2026-06",
        period_label="June 2026",
        executive_flow=ExecutiveFlowResponse(
            organization_id="t",
            scenario="Combined",
            start_period="2026-01",
            end_period="2026-12",
            as_of_period="2026-06",
        ),
        comparison_financial_statements=fs,
    )
    by_p = fs_by_period(bundle, "revenue", "Actual")
    assert by_p["2026-06"] == rev
    assert fs_sum_periods(bundle, ["2026-06"], "Actual", "cogs") == cogs
