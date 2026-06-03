"""Shared reporting query params (Combined cutover, period windows)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.services.reporting.as_of_period import bind_as_of_period, resolve_as_of_period
from app.services.reporting.period_utils import to_period


def dashboard_params(
    scenario: str,
    start_period: str,
    end_period: str,
    period: str | None,
    quarter: str | None,
    fiscal_year: str | None,
    waterfall_type: str | None,
    marketing_channel: str | None,
    region: str | None,
    segment: str | None,
    owner: str | None,
) -> dict:
    start = to_period(period or start_period)
    end = to_period(period or end_period)
    if quarter and fiscal_year:
        q = int(quarter.upper().replace("Q", ""))
        start_month = (q - 1) * 3 + 1
        start = f"{int(fiscal_year):04d}-{start_month:02d}"
        end = f"{int(fiscal_year):04d}-{start_month + 2:02d}"
    elif fiscal_year:
        start = f"{int(fiscal_year):04d}-01"
        end = f"{int(fiscal_year):04d}-12"
    return {
        "scenario": scenario,
        "start_period": start,
        "end_period": end,
        "waterfall_type": waterfall_type,
        "marketing_channel": marketing_channel,
        "region": region,
        "segment": segment,
        "owner": owner,
    }


def enrich_reporting_params(
    db: Session,
    organization_id: uuid.UUID,
    params: dict,
    *,
    as_of_period: str | None = None,
) -> dict:
    resolved = resolve_as_of_period(
        db,
        organization_id,
        as_of_period=as_of_period,
        end_period=params.get("end_period"),
    )
    bind_as_of_period(resolved)
    return {**params, "as_of_period": resolved}
