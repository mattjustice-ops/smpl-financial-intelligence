"""The outlook route returns every block the payload builder produces."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.api import reporting_outlook_routes as routes
from app.db.session import get_db
from app.main import app

client = TestClient(app)
ORG = uuid.uuid4()

BLOCKS = ("meta", "TS_DATA", "SRC", "ARR_WATERFALL", "CASH_BRIDGE", "CASH_CONTINUITY", "baseline_engine", "_sources",
          "HISTORY", "FUNNEL", "WORKFORCE", "SD", "GTM")


@pytest.fixture()
def stubbed(monkeypatch):
    monkeypatch.delenv("BILLING_INTERNAL_API_KEY", raising=False)
    monkeypatch.setattr(routes, "get_organization_or_404", lambda db, org_id: None)
    monkeypatch.setattr(routes, "build_outlook_api_payload",
                        lambda db, org_id, as_of_period=None: {k: {"block": k} for k in BLOCKS})
    monkeypatch.setattr(routes, "build_shared_reporting_payload",
                        lambda db, org_id, **kw: {**{k: {"block": k} for k in BLOCKS}, "validation": {"status": "pass"}})
    app.dependency_overrides[get_db] = lambda: iter([None])
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_outlook_returns_every_built_block(stubbed):
    res = client.get(f"/api/v1/reporting/outlook?organization_id={ORG}")
    assert res.status_code == 200
    body = res.json()
    assert sorted(body) == sorted(BLOCKS)
    assert body["HISTORY"] == {"block": "HISTORY"}
    assert body["WORKFORCE"] == {"block": "WORKFORCE"}


def test_outlook_forwards_the_chosen_close(stubbed, monkeypatch):
    seen = {}

    def fake(db, org_id, as_of_period=None):
        seen["as_of"] = as_of_period
        return {k: {"block": k} for k in BLOCKS}

    monkeypatch.setattr(routes, "build_outlook_api_payload", fake)
    res = client.get(f"/api/v1/reporting/outlook?organization_id={ORG}&as_of_period=2026-05")
    assert res.status_code == 200
    assert seen["as_of"] == "2026-05"


def test_outlook_rejects_a_close_that_is_not_loaded(stubbed, monkeypatch):
    def fake(db, org_id, as_of_period=None):
        raise ValueError("That close period is not loaded")

    monkeypatch.setattr(routes, "build_outlook_api_payload", fake)
    res = client.get(f"/api/v1/reporting/outlook?organization_id={ORG}&as_of_period=2026-07")
    assert res.status_code == 400
    assert res.json()["detail"] == "That close period is not loaded"


def test_blocking_outlook_returns_every_built_block_and_validation(stubbed):
    res = client.get(f"/api/v1/reporting/outlook?organization_id={ORG}&block_on_validation=true")
    assert res.status_code == 200
    body = res.json()
    assert sorted(body) == sorted((*BLOCKS, "validation"))
