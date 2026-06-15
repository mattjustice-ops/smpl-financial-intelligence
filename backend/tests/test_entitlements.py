"""Unit tests for plan module entitlements."""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from app.models.organization import Organization
from app.services.entitlements import (
    modules_for_org,
    modules_for_plan,
    normalize_plan,
    org_has_module,
)
from app.services.organizations import get_organization_or_404


class _FakeSession:
    def get(self, _model, org_id):
        return Organization(id=org_id, name="Test Co", plan="starter")


def test_normalize_plan_aliases():
    assert normalize_plan(None) == "starter"
    assert normalize_plan("growth") == "professional"
    assert normalize_plan("Enterprise") == "enterprise"


def test_starter_modules_exclude_professional_tabs():
    starter = modules_for_plan("starter")
    assert "executive" in starter
    assert "management-pl" not in starter
    assert "workforce" not in starter
    assert "cash" not in starter
    assert "board_export" in starter


def test_professional_includes_forecast_modules():
    pro = modules_for_plan("professional")
    assert "management-pl" in pro
    assert "workforce" in pro
    assert "cash" in pro


def test_modules_for_org_uses_plan():
    org = Organization(id=uuid.uuid4(), name="Acme", plan="starter")
    assert "workforce" not in modules_for_org(org)
    org.plan = "professional"
    assert "workforce" in modules_for_org(org)


def test_org_has_module():
    org = Organization(id=uuid.uuid4(), name="Acme", plan="starter")
    assert org_has_module(org, "pipeline")
    assert not org_has_module(org, "cash")


def test_get_organization_or_404_blocks_gated_module():
    org_id = uuid.uuid4()
    db = _FakeSession()
    with pytest.raises(HTTPException) as exc:
        get_organization_or_404(db, org_id, module="workforce")
    assert exc.value.status_code == 403
    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert detail["code"] == "module_not_entitled"
    assert detail["module"] == "workforce"

    org = get_organization_or_404(db, org_id, module="executive")
    assert org.plan == "starter"
