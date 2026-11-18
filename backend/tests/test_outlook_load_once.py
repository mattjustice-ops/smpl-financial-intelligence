"""Outlook reads are reused inside one build, and one build serves the next request."""

from __future__ import annotations

import uuid

from app.services.reporting.outlook_cache import forget_outlook, get_or_build
from app.services.reporting.read_cache import cached_read, outlook_read_scope


def test_a_build_reads_each_warehouse_query_once() -> None:
    calls = {"n": 0}

    def load() -> str:
        calls["n"] += 1
        return "rows"

    assert cached_read(("gl", "1"), load) == "rows"
    assert cached_read(("gl", "1"), load) == "rows"
    assert calls["n"] == 2
    with outlook_read_scope():
        assert cached_read(("gl", "1"), load) == "rows"
        assert cached_read(("gl", "1"), load) == "rows"
    assert calls["n"] == 3


def test_the_same_close_reuses_one_payload() -> None:
    org = str(uuid.uuid4())
    key = (org, "2026-07", "")
    calls = {"n": 0}
    forget_outlook(org)
    try:
        def build() -> dict[str, str]:
            calls["n"] += 1
            return {"close": "2026-07"}

        assert get_or_build(key, build)["close"] == "2026-07"
        assert get_or_build(key, build)["close"] == "2026-07"
        assert calls["n"] == 1
        forget_outlook(org)
        assert get_or_build(key, build)["close"] == "2026-07"
        assert calls["n"] == 2
    finally:
        forget_outlook(org)
