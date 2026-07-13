"""Persist LLM and export usage events for SMPL Ops."""

from __future__ import annotations

import logging
import time
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.usage_event import UsageEvent
from app.services.ops.usage_context import get_usage_context

logger = logging.getLogger(__name__)

# USD per 1M tokens — update when Anthropic pricing changes.
_MODEL_PRICING_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-sonnet-4-20250514": (3.0, 15.0),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.0),
}
_DEFAULT_PRICING = (3.0, 15.0)


def estimate_llm_cost_usd(
    model: str,
    *,
    input_tokens: int,
    output_tokens: int,
) -> Decimal:
    input_rate, output_rate = _MODEL_PRICING_PER_MTOK.get(model, _DEFAULT_PRICING)
    cost = (input_tokens / 1_000_000) * input_rate + (output_tokens / 1_000_000) * output_rate
    return Decimal(str(round(cost, 6)))


def record_usage_event(
    *,
    event_type: str,
    organization_id: uuid.UUID | None = None,
    feature: str | None = None,
    model: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    estimated_cost_usd: Decimal | float | None = None,
    duration_ms: int | None = None,
    metadata: dict[str, Any] | None = None,
    db: Session | None = None,
) -> None:
    ctx_org_id, ctx_feature = get_usage_context()
    org_id = organization_id if organization_id is not None else ctx_org_id
    resolved_feature = feature or ctx_feature

    owns_session = db is None
    session = db or SessionLocal()
    try:
        row = UsageEvent(
            event_type=event_type,
            organization_id=org_id,
            feature=resolved_feature,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=(
                Decimal(str(estimated_cost_usd)) if estimated_cost_usd is not None else None
            ),
            duration_ms=duration_ms,
            metadata_json=metadata,
        )
        session.add(row)
        session.commit()
    except Exception:
        logger.exception("Failed to record usage event %s", event_type)
        if owns_session:
            session.rollback()
    finally:
        if owns_session:
            session.close()


def record_llm_usage_from_anthropic_response(
    response: Any,
    *,
    model: str,
    feature: str | None = None,
    organization_id: uuid.UUID | None = None,
    duration_ms: int | None = None,
) -> None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    if input_tokens == 0 and output_tokens == 0:
        return
    cost = estimate_llm_cost_usd(model, input_tokens=input_tokens, output_tokens=output_tokens)
    record_usage_event(
        event_type="llm_call",
        organization_id=organization_id,
        feature=feature,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=cost,
        duration_ms=duration_ms,
        metadata={"provider": "anthropic"},
    )


def record_export_event(
    status: str,
    *,
    kind: str,
    organization_id: uuid.UUID | None,
    job_id: str,
    duration_ms: int | None = None,
    error: str | None = None,
    as_of_period: str | None = None,
    close_session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    event_type = {
        "queued": "export_start",
        "running": "export_start",
        "complete": "export_complete",
        "failed": "export_failed",
    }.get(status, f"export_{status}")
    payload: dict[str, Any] = {"job_id": job_id, "kind": kind}
    if as_of_period:
        payload["as_of_period"] = as_of_period
    if close_session_id:
        payload["close_session_id"] = close_session_id
    if metadata:
        payload.update(metadata)
    if error:
        payload["error"] = error[:2000]
    record_usage_event(
        event_type=event_type,
        organization_id=organization_id,
        feature=kind,
        duration_ms=duration_ms,
        metadata=payload,
    )


class LlmCallTimer:
    """Simple wall-clock timer for LLM calls."""

    def __init__(self) -> None:
        self._started = time.perf_counter()

    @property
    def duration_ms(self) -> int:
        return int((time.perf_counter() - self._started) * 1000)
