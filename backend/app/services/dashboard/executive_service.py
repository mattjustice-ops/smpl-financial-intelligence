"""Executive flow dashboard orchestration."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.services.dashboard.opportunity_attribution_service import closed_by_month, remaining_pipeline, stage_summary
from app.services.dashboard.query_utils import commentary_prompts
from app.services.dashboard.schemas import ExecutiveFlowResponse
from app.services.dashboard.waterfall_service import waterfall_response
from app.services.marketing.service import performance_summary


def executive_flow(db: Session, organization_id: uuid.UUID, **params) -> ExecutiveFlowResponse:
    marketing = performance_summary(
        db,
        organization_id,
        scenario=params["scenario"],
        start_period=params["start_period"],
        end_period=params["end_period"],
        marketing_channel=params.get("marketing_channel"),
    )
    waterfalls = {
        "pipeline": waterfall_response(db, organization_id, waterfall_name="pipeline", **params),
        "arr": waterfall_response(db, organization_id, waterfall_name="arr", **params),
        "deferred_revenue": waterfall_response(db, organization_id, waterfall_name="deferred_revenue", **params),
        "cash_flow": waterfall_response(db, organization_id, waterfall_name="cash_flow", **params),
    }
    opportunities = {
        "stage_summary": stage_summary(db, organization_id, **params),
        "closed_by_month": closed_by_month(db, organization_id, **params),
        "remaining_pipeline": remaining_pipeline(db, organization_id, **params),
    }
    validation = [*marketing.validation]
    for waterfall in waterfalls.values():
        validation.extend(waterfall.validation)
    return ExecutiveFlowResponse(
        organization_id=str(organization_id),
        scenario=params["scenario"],
        start_period=params["start_period"],
        end_period=params["end_period"],
        marketing_summary=marketing.model_dump(mode="json"),
        waterfalls=waterfalls,
        opportunities=opportunities,
        validation=validation,
        commentary_prompts=commentary_prompts(),
    )
