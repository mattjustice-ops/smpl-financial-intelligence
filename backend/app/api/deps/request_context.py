"""Per-request user context from proxy headers (poc-4 membership checks)."""

from __future__ import annotations

import uuid
from contextvars import ContextVar, Token

_request_user_id: ContextVar[uuid.UUID | None] = ContextVar("request_user_id", default=None)


def set_request_user_id(user_id: uuid.UUID) -> Token:
    return _request_user_id.set(user_id)


def reset_request_user_id(token: Token) -> None:
    _request_user_id.reset(token)


def get_request_user_id() -> uuid.UUID | None:
    return _request_user_id.get()
