"""Tests for workspace load-domain status mapping."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.workspace.load_domains import ENTITY_TO_DOMAIN, build_load_domain_status


def test_entity_maps_to_crm_domain() -> None:
    assert ENTITY_TO_DOMAIN["opportunities"] == "crm"
    assert ENTITY_TO_DOMAIN["gl_actuals"] == "erp_gl"


def test_build_load_domain_status_marks_loaded() -> None:
    org_id = uuid.uuid4()
    batch = SimpleNamespace(
        entity_type="opportunities",
        period="2026-06",
        source="api",
        status="complete",
        rows_imported=50,
        rows_rejected=0,
        created_at=datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
        metadata_json={"source_system": "Salesforce"},
    )
    db = MagicMock()

    def _scalars(stmt):  # noqa: ANN001
        result = MagicMock()
        sql = str(stmt).lower()
        if "ingest_batches" in sql or "ingestbatch" in sql:
            result.all.return_value = [batch]
        else:
            result.all.return_value = []
        return result

    db.scalars.side_effect = _scalars
    payload = build_load_domain_status(db, org_id, as_of_period="2026-06")
    crm = next(d for d in payload["domains"] if d["id"] == "crm")
    assert crm["status"] == "loaded"
    assert crm["source_system"] == "Salesforce"
    assert crm["api_batches"] == 1
