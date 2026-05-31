"""Pipeline opportunity movement drilldown helpers."""

from __future__ import annotations

from decimal import Decimal

from app.services.dashboard.pipeline_opportunity_drilldown_service import (
    normalize_pipeline_movement_type,
    signed_pipeline_movement_amount,
)


def test_normalize_pipeline_movement_labels() -> None:
    assert normalize_pipeline_movement_type("Pipeline Created") == "pipeline_created"
    assert normalize_pipeline_movement_type("Closed Won") == "closed_won"
    assert normalize_pipeline_movement_type("closed_lost") == "closed_lost"
    assert normalize_pipeline_movement_type("Slipped Pipeline") == "slipped_pipeline"


def test_signed_movement_amounts_match_waterfall() -> None:
    assert signed_pipeline_movement_amount("pipeline_created", Decimal("100")) == Decimal("100")
    assert signed_pipeline_movement_amount("closed_won", Decimal("100")) == Decimal("-100")
