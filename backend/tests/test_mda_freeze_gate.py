"""Prompt 5 §4B freeze hard-block — COMPLETE/STALE allowed; missing pack → 409."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.export_routes import _require_servable_freeze_for_mda
from app.services.close_context.freeze_blob_service import FreezeContext


def test_require_servable_freeze_blocks_missing_pack() -> None:
    db = MagicMock()
    with patch(
        "app.services.close_context.freeze_blob_service.get_servable_freeze",
        return_value=None,
    ):
        with pytest.raises(HTTPException) as exc_info:
            _require_servable_freeze_for_mda(db, uuid.uuid4(), "2026-06")
    assert exc_info.value.status_code == 409
    detail = exc_info.value.detail
    assert isinstance(detail, dict)
    assert detail["code"] == "freeze_pack_required"


def test_require_servable_freeze_allows_stale() -> None:
    org_id = uuid.uuid4()
    freeze = FreezeContext(
        organization_id=org_id,
        as_of_period="2026-06",
        status="STALE",
        context_text="prior",
        built_at=datetime(2026, 7, 12, 6, 0, tzinfo=timezone.utc),
        validation_status="pass",
        stale=True,
    )
    db = MagicMock()
    with patch(
        "app.services.close_context.freeze_blob_service.get_servable_freeze",
        return_value=freeze,
    ):
        out = _require_servable_freeze_for_mda(db, org_id, "2026-06")
    assert out.status == "STALE"
    assert out.stale is True
