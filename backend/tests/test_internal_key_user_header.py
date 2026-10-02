"""X-SFI-User-Id is only trusted when the Next proxy's internal key comes with it."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

KEY = "k" * 64
USER_ROUTE = "/api/v1/predictive-planning/constraints"


@pytest.fixture()
def key_set(monkeypatch):
    monkeypatch.setenv("BILLING_INTERNAL_API_KEY", KEY)


def _user():
    return {"X-SFI-User-Id": str(uuid.uuid4())}


def test_user_header_without_key_is_rejected(key_set):
    res = client.get(USER_ROUTE, headers=_user())
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid internal API key"


def test_user_header_with_wrong_key_is_rejected(key_set):
    res = client.get(USER_ROUTE, headers={**_user(), "X-Billing-Internal-Key": "wrong"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid internal API key"


def test_malformed_user_header_without_key_is_rejected(key_set):
    res = client.get(USER_ROUTE, headers={"X-SFI-User-Id": "not-a-uuid"})
    assert res.status_code == 401


@pytest.mark.parametrize("key_header", ["X-Billing-Internal-Key", "X-Smpl-Internal-Key"])
def test_user_header_with_valid_key_is_accepted(key_set, key_header):
    res = client.get(USER_ROUTE, headers={**_user(), key_header: KEY})
    assert res.status_code == 200, res.text


def test_requests_without_user_header_are_unaffected(key_set):
    assert client.get("/health").status_code == 200
    res = client.get(USER_ROUTE)
    assert res.status_code == 401
    assert res.json()["detail"] == "Authentication required for Plan Assurance."


def test_internal_key_routes_reject_wrong_key(key_set):
    res = client.get(
        f"/api/v1/auth/organizations/{uuid.uuid4()}/seats",
        headers={"X-Billing-Internal-Key": "wrong"},
    )
    assert res.status_code == 401


def test_without_configured_key_user_header_is_trusted(monkeypatch):
    monkeypatch.delenv("BILLING_INTERNAL_API_KEY", raising=False)
    res = client.get(USER_ROUTE, headers=_user())
    assert res.status_code == 200, res.text
