"""Workforce recompute route tests."""

from __future__ import annotations

import uuid
from datetime import date

from app.services.workforce.schemas import WorkforceValidationRow


def test_validation_row_accepts_engine_payload() -> None:
    payload = {
        "period": date(2026, 1, 1),
        "validation_name": "workforce_source_data_missing",
        "status": "warning",
        "message": "Upload workforce_employees",
    }
    payload["scenario"] = "Forecast"
    row = WorkforceValidationRow(**payload)
    assert row.validation_name == "workforce_source_data_missing"


def test_build_validations_like_service() -> None:
    version = "Forecast"
    engine_items = [
        {
            "scenario": "Forecast",
            "period": date(2026, 1, 1),
            "validation_name": "workforce_source_data_missing",
            "status": "warning",
            "message": "test",
        }
    ]
    out = []
    for item in engine_items:
        payload = dict(item)
        payload["scenario"] = version
        out.append(WorkforceValidationRow(**payload))
    assert len(out) == 1
