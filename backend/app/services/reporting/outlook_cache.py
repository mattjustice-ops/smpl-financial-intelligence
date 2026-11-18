"""One outlook build serves every engine that asks for the same close.

Board, Reporting, Forecast, and Budget each request the same payload. The
build is kept briefly so a refresh or the next engine does not scan the
warehouse again. A load or a remove drops it.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable
from typing import Any, TypeVar

TTL_SECONDS = 180

_guard = threading.Lock()
_cached: dict[tuple[str, str, str], tuple[float, dict[str, Any]]] = {}
_inflight: dict[tuple[str, str, str], threading.Event] = {}

T = TypeVar("T")


def forget_outlook(organization_id: uuid.UUID | str | None = None) -> None:
    """Drop cached outlooks. No organization drops every company."""
    org = str(organization_id) if organization_id is not None else None
    with _guard:
        if org is None:
            _cached.clear()
            return
        for key in [key for key in _cached if key[0] == org]:
            _cached.pop(key, None)


def get_or_build(key: tuple[str, str, str], build: Callable[[], T]) -> T:
    """Return the cached payload, or build it once while other callers wait."""
    now = time.monotonic()
    with _guard:
        hit = _cached.get(key)
        if hit is not None and now - hit[0] < TTL_SECONDS:
            return hit[1]
        waiting = _inflight.get(key)
        if waiting is None:
            waiting = threading.Event()
            _inflight[key] = waiting
            leader = True
        else:
            leader = False
    if not leader:
        waiting.wait(TTL_SECONDS + 30)
        with _guard:
            hit = _cached.get(key)
            if hit is not None and time.monotonic() - hit[0] < TTL_SECONDS:
                return hit[1]
        return build()
    try:
        payload = build()
    except Exception:
        raise
    else:
        with _guard:
            _cached[key] = (time.monotonic(), payload)
        return payload
    finally:
        with _guard:
            _inflight.pop(key, None)
        waiting.set()
