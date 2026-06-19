"""Board Platform payload — live warehouse data for React board UI."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.services.forecast_version_service import get_active_forecast_version
from app.services.organizations import get_organization_or_404
from app.services.reporting.as_of_period import bind_as_of_period, reset_as_of_period
from app.services.reporting.export.board_commentary_service import build_all_slide_commentary
from app.services.reporting.export.data_collector import collect_reporting_bundle
from app.services.reporting.export.schemas import ExportValidationSummary
from app.services.reporting.org_reporting_settings import ensure_org_reporting_defaults, resolve_org_reporting_window
from app.services.reporting.period_utils import to_period
from app.services.reporting.three_statement_payload import build_ts_data
from app.services.reporting.validation_gate import raise_if_validation_blocked

IS_LINE_METRICS: dict[str, str] = {
    "Revenue": "revenue",
    "EBITDA": "ebitda",
    "Net Income": "net_income",
}


class BoardPlatformMeta(BaseModel):
    organization_id: str
    organization_name: str
    close_month: str
    fiscal_year_end_month: int
    start_period: str
    end_period: str
    scenario: str = "Combined"
    active_forecast_version_id: str | None = None
    active_forecast_version_name: str | None = None


class BoardPlatformPayload(BaseModel):
    meta: BoardPlatformMeta
    executive: dict[str, Any]
    validation: ExportValidationSummary
    time_series: dict[str, Any] = Field(default_factory=dict)
    three_statement: dict[str, Any] = Field(default_factory=dict)
    commentary: dict[str, dict[str, str]] = Field(default_factory=dict)


def _decimal_to_json(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: _decimal_to_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_decimal_to_json(v) for v in value]
    return value


def _build_time_series(bundle) -> dict[str, Any]:
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if fs is None:
        return {}
    actual: dict[str, dict[str, float | None]] = {}
    forecast: dict[str, dict[str, float | None]] = {}
    budget: dict[str, dict[str, float | None]] = {}
    periods: set[str] = set()

    for row in fs.income_statement.rows:
        period = to_period(row.period)
        periods.add(period)
        metric = IS_LINE_METRICS.get(row.line_item)
        if not metric:
            continue
        if row.scenario == "Actual":
            bucket = actual
        elif row.scenario == "Forecast":
            bucket = forecast
        else:
            bucket = budget
        target = bucket.setdefault(period, {})
        target[metric] = float(row.amount) if row.amount is not None else None

    return {
        "periods": sorted(periods),
        "Actual": actual,
        "Forecast": forecast,
        "Budget": budget,
    }


def build_board_platform_payload(
    db: Session,
    organization_id: uuid.UUID,
    *,
    include_commentary: bool = False,
    block_on_validation: bool = True,
) -> BoardPlatformPayload:
    org = get_organization_or_404(db, organization_id, module="board_export")
    ensure_org_reporting_defaults(db, org)
    as_of, start_period, end_period = resolve_org_reporting_window(db, org)
    active = get_active_forecast_version(db, org)

    token = bind_as_of_period(as_of)
    try:
        bundle = collect_reporting_bundle(
            db,
            organization_id,
            scenario="Combined",
            start_period=start_period,
            end_period=end_period,
            as_of_period=as_of,
            include_ai_commentary=False,
        )
    finally:
        reset_as_of_period(token)

    if block_on_validation:
        raise_if_validation_blocked(bundle.validation, action="Board Platform load")

    three_statement = build_ts_data(
        db, organization_id, as_of=as_of, start_period=start_period, end_period=end_period
    )

    commentary: dict[str, dict[str, str]] = {}
    if include_commentary:
        slides = build_all_slide_commentary(bundle, use_ai=False)
        for key, slide in slides.items():
            commentary[key] = {
                "what_happened": slide.what_happened,
                "why_it_happened": slide.why_it_happened,
                "impact": slide.impact,
                "favorable": slide.favorable,
                "unfavorable": slide.unfavorable,
                "leadership_watch": slide.leadership_watch,
            }

    meta = BoardPlatformMeta(
        organization_id=str(org.id),
        organization_name=org.name,
        close_month=as_of,
        fiscal_year_end_month=int(org.fiscal_year_end_month or 12),
        start_period=start_period,
        end_period=end_period,
        active_forecast_version_id=str(active.id) if active else None,
        active_forecast_version_name=active.version_name if active else None,
    )

    return BoardPlatformPayload(
        meta=meta,
        executive=_decimal_to_json(bundle.executive_flow.model_dump(mode="json")),
        validation=bundle.validation,
        time_series=_build_time_series(bundle),
        three_statement=three_statement,
        commentary=commentary,
    )
