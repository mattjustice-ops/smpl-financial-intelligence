"""Unit tests for plan usage caps (SMPL Ops Phase 3)."""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from app.models.organization import Organization
from app.services.ops.usage_limits import (
    DEFAULT_USAGE_LIMITS,
    MonthlyUsageTotals,
    assert_within_usage_limits,
    limits_for_plan,
    monthly_usage_status_payload,
)


def test_limits_flat_for_all_plans() -> None:
    for plan in ("starter", "professional", "enterprise", None):
        limits = limits_for_plan(plan)
        assert limits == DEFAULT_USAGE_LIMITS


def test_assert_blocks_export_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    org = Organization(id=uuid.uuid4(), name="Acme", plan="starter")
    usage = MonthlyUsageTotals(
        month="2026-06",
        ai_cost_usd=0.0,
        llm_calls=0,
        exports_complete=10,
    )
    monkeypatch.setattr(
        "app.services.ops.usage_limits.monthly_usage_totals",
        lambda _db, _org_id: usage,
    )

    with pytest.raises(HTTPException) as exc:
        assert_within_usage_limits(None, org, require_export=True)

    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert detail["code"] == "usage_limit_exceeded"
    assert detail["metric"] == "exports_monthly"
    assert detail["limit"] == 10
    assert detail["used"] == 10


def test_assert_blocks_ai_cost_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    org = Organization(id=uuid.uuid4(), name="Acme", plan="starter")
    usage = MonthlyUsageTotals(
        month="2026-06",
        ai_cost_usd=10.0,
        llm_calls=1,
        exports_complete=0,
    )
    monkeypatch.setattr(
        "app.services.ops.usage_limits.monthly_usage_totals",
        lambda _db, _org_id: usage,
    )

    with pytest.raises(HTTPException) as exc:
        assert_within_usage_limits(None, org, require_ai=True)

    assert exc.value.detail["metric"] == "ai_cost_usd_monthly"
    assert exc.value.detail["limit"] == 10.0


def test_assert_blocks_llm_calls_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    org = Organization(id=uuid.uuid4(), name="Acme", plan="starter")
    usage = MonthlyUsageTotals(
        month="2026-06",
        ai_cost_usd=1.0,
        llm_calls=10,
        exports_complete=0,
    )
    monkeypatch.setattr(
        "app.services.ops.usage_limits.monthly_usage_totals",
        lambda _db, _org_id: usage,
    )

    with pytest.raises(HTTPException) as exc:
        assert_within_usage_limits(None, org, require_ai=True)

    assert exc.value.detail["metric"] == "llm_calls_monthly"
    assert exc.value.detail["limit"] == 10


def test_assert_enterprise_same_caps(monkeypatch: pytest.MonkeyPatch) -> None:
    org = Organization(id=uuid.uuid4(), name="Big Co", plan="enterprise")
    usage = MonthlyUsageTotals(
        month="2026-06",
        ai_cost_usd=0.0,
        llm_calls=0,
        exports_complete=10,
    )
    monkeypatch.setattr(
        "app.services.ops.usage_limits.monthly_usage_totals",
        lambda _db, _org_id: usage,
    )

    with pytest.raises(HTTPException) as exc:
        assert_within_usage_limits(None, org, require_export=True)

    assert exc.value.detail["limit"] == 10


def test_assert_skipped_when_limits_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    org = Organization(id=uuid.uuid4(), name="Acme", plan="starter")
    usage = MonthlyUsageTotals(
        month="2026-06",
        ai_cost_usd=999.0,
        llm_calls=999,
        exports_complete=999,
    )
    monkeypatch.setattr(
        "app.services.ops.usage_limits.monthly_usage_totals",
        lambda _db, _org_id: usage,
    )

    class _Settings:
        smpl_usage_limits_enabled = False

    monkeypatch.setattr(
        "app.services.ops.usage_limits.get_settings",
        lambda: _Settings(),
    )

    assert_within_usage_limits(None, org, require_export=True, require_ai=True)


def test_monthly_usage_status_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    org = Organization(id=uuid.uuid4(), name="Acme", plan="professional")
    usage = MonthlyUsageTotals(
        month="2026-06",
        ai_cost_usd=5.0,
        llm_calls=5,
        exports_complete=5,
    )
    monkeypatch.setattr(
        "app.services.ops.usage_limits.monthly_usage_totals",
        lambda _db, _org_id: usage,
    )

    payload = monthly_usage_status_payload(None, org)

    assert payload["plan"] == "professional"
    assert payload["usage"]["ai_cost_usd"] == 5.0
    assert payload["limits"]["exports_monthly"] == 10
    assert payload["percent_used"]["ai_cost_usd_monthly"] == 50.0
    assert payload["percent_used"]["exports_monthly"] == 50.0
    assert payload["percent_used"]["llm_calls_monthly"] == 50.0
