"""Forecast drilldown counts follow the close month on the call.

The deck export passes as_of_period and does not bind the request context.
Counting against the context instead of that close month reports every
forecast section as empty.
"""

from __future__ import annotations

import uuid

from app.services.dashboard.cash_flow_gl_drilldown_service import cash_flow_gl_detail_counts
from app.services.dashboard.pipeline_opportunity_drilldown_service import (
    pipeline_movement_detail_counts,
)
from app.services.reporting.as_of_period import bind_as_of_period, reset_as_of_period


def test_cash_counts_use_the_close_month_not_the_request_context(monkeypatch):
    seen: list[str] = []

    def fake_lines(session, organization_id, *, period, source_scenario, waterfall_type):
        del session, organization_id, period
        seen.append(source_scenario)
        if waterfall_type == "payroll_cash_out":
            return [object()]
        return []

    monkeypatch.setattr(
        "app.services.dashboard.cash_flow_gl_drilldown_service.cash_flow_drilldown_lines",
        fake_lines,
    )
    token = bind_as_of_period("2026-12")
    try:
        counts = cash_flow_gl_detail_counts(
            None,
            uuid.uuid4(),
            scenario="Combined",
            start_period="2026-07",
            end_period="2026-07",
            as_of_period="2026-06",
        )
    finally:
        reset_as_of_period(token)

    assert set(seen) == {"Forecast"}
    assert counts[("Forecast", "2026-07", "payroll_cash_out")] == 1


def test_pipeline_counts_pass_the_close_month(monkeypatch):
    seen: dict[str, str | None] = {}

    def fake_fetch(db, organization_id, **kwargs):
        del db, organization_id
        seen["as_of_period"] = kwargs.get("as_of_period")
        return [
            (
                "Forecast",
                "2026-07",
                "forecast_opportunity_movements",
                {"pipeline_movement_type": "closed_won"},
            )
        ]

    monkeypatch.setattr(
        "app.services.dashboard.pipeline_opportunity_drilldown_service.fetch_scenario_rows",
        fake_fetch,
    )
    token = bind_as_of_period("2026-12")
    try:
        counts = pipeline_movement_detail_counts(
            None,
            uuid.uuid4(),
            scenario="Combined",
            start_period="2026-07",
            end_period="2026-07",
            as_of_period="2026-06",
        )
    finally:
        reset_as_of_period(token)

    assert seen["as_of_period"] == "2026-06"
    assert counts[("Forecast", "2026-07", "closed_won")] == 1
