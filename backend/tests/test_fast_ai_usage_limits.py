"""Usage limits must not block board AI/exports during SMPL_FAST_AI demos."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.ops.usage_limits import assert_prompt5_regen_cap, assert_within_usage_limits


def test_fast_ai_skips_ai_and_export_usage_caps(monkeypatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("SMPL_FAST_AI", "true")
    monkeypatch.setenv("SMPL_USAGE_LIMITS_ENABLED", "true")
    get_settings.cache_clear()
    try:
        org = SimpleNamespace(id=uuid.uuid4(), plan="growth")
        assert_within_usage_limits(MagicMock(), org, require_ai=True)
        assert_within_usage_limits(MagicMock(), org, require_export=True, require_ai=True)
        assert_prompt5_regen_cap(MagicMock(), org, "2026-06")
    finally:
        get_settings.cache_clear()
