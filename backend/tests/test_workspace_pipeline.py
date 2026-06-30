"""Tests for customer workspace pipeline ledger helpers."""

from __future__ import annotations

import uuid

from datetime import datetime, timezone

from app.services.ops.usage_limits import DEFAULT_USAGE_LIMITS
from app.services.workspace.pipeline_ledger import batch_to_payload
from app.models.pipeline import IngestBatch


def test_batch_to_payload_shape() -> None:
    now = datetime.now(timezone.utc)
    batch = IngestBatch(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source="api",
        status="complete",
        entity_type="mrr_waterfall",
        rows_staged=10,
        rows_imported=9,
        rows_rejected=1,
        created_at=now,
        updated_at=now,
    )
    payload = batch_to_payload(batch)
    assert payload["source"] == "api"
    assert payload["rows_staged"] == 10
    assert payload["rows_imported"] == 9
    assert payload["rows_rejected"] == 1


def test_default_usage_limits_flat() -> None:
    assert DEFAULT_USAGE_LIMITS["ai_cost_usd_monthly"] == 10.0
    assert DEFAULT_USAGE_LIMITS["exports_monthly"] == 10
