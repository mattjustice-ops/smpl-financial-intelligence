"""Usage limits must not block interactive AI during SMPL_FAST_AI demos."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.ops.usage_limits import assert_within_usage_limits


def test_fast_ai_skips_ai_usage_caps(monkeypatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("SMPL_FAST_AI", "true")
    monkeypatch.setenv("SMPL_USAGE_LIMITS_ENABLED", "true")
    get_settings.cache_clear()
    try:
        org = SimpleNamespace(id=uuid.uuid4(), plan="growth")
        # Would normally trip if called with require_ai against 10 llm calls.
        assert_within_usage_limits(MagicMock(), org, require_ai=True)
    finally:
        get_settings.cache_clear()
