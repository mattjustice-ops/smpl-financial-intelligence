"""Request-scoped usage attribution (org + feature) for LLM instrumentation."""

from __future__ import annotations

import uuid
from contextvars import ContextVar, Token

_organization_id: ContextVar[uuid.UUID | None] = ContextVar("usage_organization_id", default=None)
_feature: ContextVar[str | None] = ContextVar("usage_feature", default=None)


def set_usage_context(
    *,
    organization_id: uuid.UUID | None = None,
    feature: str | None = None,
) -> tuple[Token, Token]:
    org_token = _organization_id.set(organization_id)
    feature_token = _feature.set(feature)
    return org_token, feature_token


def reset_usage_context(tokens: tuple[Token, Token]) -> None:
    org_token, feature_token = tokens
    _organization_id.reset(org_token)
    _feature.reset(feature_token)


def get_usage_context() -> tuple[uuid.UUID | None, str | None]:
    return _organization_id.get(), _feature.get()
