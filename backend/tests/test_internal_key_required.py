"""With BILLING_INTERNAL_API_KEY set, only health checks and build pings skip the key."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import PUBLIC_PATHS, app

client = TestClient(app)

KEY = "k" * 64
ORG = str(uuid.uuid4())

PROTECTED = [
    ("GET", f"/api/v1/reporting/outlook?organization_id={ORG}"),
    ("GET", f"/api/v1/billing/account?organization_id={ORG}"),
    ("GET", f"/api/v1/workspace/summary?organization_id={ORG}"),
    ("POST", "/api/v1/quotes/submit"),
    ("GET", "/docs"),
    ("GET", "/openapi.json"),
    ("GET", "/"),
]


@pytest.fixture()
def key_set(monkeypatch):
    monkeypatch.setenv("BILLING_INTERNAL_API_KEY", KEY)


@pytest.mark.parametrize("method,path", PROTECTED)
def test_unkeyed_request_is_rejected(key_set, method, path):
    res = client.request(method, path)
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid internal API key"


@pytest.mark.parametrize("method,path", PROTECTED)
def test_wrong_key_is_rejected(key_set, method, path):
    res = client.request(method, path, headers={"X-Billing-Internal-Key": "wrong"})
    assert res.status_code == 401


@pytest.mark.parametrize("path", sorted(PUBLIC_PATHS))
def test_public_paths_skip_the_key(key_set, path):
    assert client.get(path).status_code != 401


def test_public_path_still_rejects_unkeyed_user_header(key_set):
    res = client.get("/health", headers={"X-SFI-User-Id": str(uuid.uuid4())})
    assert res.status_code == 401


@pytest.mark.parametrize("key_header", ["X-Billing-Internal-Key", "X-Smpl-Internal-Key"])
def test_keyed_request_passes(key_set, key_header):
    assert client.get("/openapi.json", headers={key_header: KEY}).status_code == 200


def test_without_configured_key_nothing_is_locked(monkeypatch):
    monkeypatch.delenv("BILLING_INTERNAL_API_KEY", raising=False)
    assert client.get("/openapi.json").status_code == 200
