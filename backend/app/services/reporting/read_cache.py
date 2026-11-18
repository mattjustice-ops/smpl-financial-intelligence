"""Reuse warehouse reads inside one outlook build.

The outlook walks the same GL and the same loaded tables several times. Each
walk is a full scan. The cache lives only for the build that opened it, so the
next request still sees rows loaded after this one.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, TypeVar

_cache: ContextVar[dict[Any, Any] | None] = ContextVar("outlook_read_cache", default=None)

T = TypeVar("T")


@contextmanager
def outlook_read_scope():
    token = _cache.set({})
    try:
        yield
    finally:
        _cache.reset(token)


def cached_read(key: tuple[Any, ...], load: Callable[[], T]) -> T:
    box = _cache.get()
    if box is None:
        return load()
    if key not in box:
        box[key] = load()
    return box[key]
