"""High-level orchestration: load inputs, run engine, optionally persist."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models.onboarding_readiness import OnboardingReadinessAnswers
from app.services.mrr.engine import (
    CompanyMrrSummary,
    CustomerMrrMovement,
    ReturnPolicy,
    compute_waterfall,
    summarize_company,
)
from app.services.mrr.metrics import ArrBridge, PeriodMetrics, arr_bridge, compute_period_metrics
from app.services.mrr.repository import (
    customer_departures,
    customer_mrr_for_month,
    historical_active_customers,
    month_start,
    previous_month_start,
    upsert_mrr_waterfall_rows,
)
from app.services.readiness.engine import normalize_answers


def return_policy(session: Session, organization_id: uuid.UUID) -> ReturnPolicy:
    """Onboarding answers 4.10 (winback window) and 4.11 (pauses); unanswered stays None."""
    row = session.get(OnboardingReadinessAnswers, organization_id)
    answers = normalize_answers(dict(row.answers) if row else {})
    window = answers.get("4.10")
    return ReturnPolicy(
        winback_window_months=int(window) if window and window.isdigit() else None,
        no_window=window == "no_window",
        pause_treatment=answers.get("4.11"),
    )


@dataclass(frozen=True)
class WaterfallResult:
    period: date
    customer_rows: list[CustomerMrrMovement]
    summary: CompanyMrrSummary
    arr_bridge: ArrBridge
    metrics: PeriodMetrics
    persisted_rows: int

    def as_dict(self) -> dict[str, object]:
        return {
            "period": self.period,
            "customer_rows": [r.as_dict() for r in self.customer_rows],
            "summary": self.summary.as_dict(),
            "arr_bridge": self.arr_bridge.as_dict(),
            "metrics": self.metrics.as_dict(),
            "persisted_rows": self.persisted_rows,
        }


def run_period_waterfall(
    session: Session,
    organization_id: uuid.UUID,
    period: date,
    *,
    persist: bool = True,
    prior_period: Optional[date] = None,
) -> WaterfallResult:
    """Compute the MRR waterfall for a single month, optionally persisting rows.

    `period` is normalized to the first of the month. `prior_period` defaults
    to the prior calendar month.
    """
    current_period = month_start(period)
    prior_period_start = month_start(prior_period) if prior_period else previous_month_start(current_period)

    prior_mrr = customer_mrr_for_month(session, organization_id, prior_period_start)
    current_mrr = customer_mrr_for_month(session, organization_id, current_period)
    history = historical_active_customers(session, organization_id, prior_period_start)
    returning = {c for c, v in current_mrr.items() if v > 0 and not prior_mrr.get(c) and c in history}

    customer_rows = compute_waterfall(
        period=current_period,
        prior_mrr_by_customer=prior_mrr,
        current_mrr_by_customer=current_mrr,
        historical_active_customers=history,
        departures=customer_departures(session, organization_id, current_period, returning),
        policy=return_policy(session, organization_id),
    )
    summary = summarize_company(current_period, customer_rows)
    bridge = arr_bridge(summary)
    metrics = compute_period_metrics(summary)

    persisted = 0
    if persist and customer_rows:
        persisted = upsert_mrr_waterfall_rows(session, organization_id, customer_rows)
        session.commit()

    return WaterfallResult(
        period=current_period,
        customer_rows=customer_rows,
        summary=summary,
        arr_bridge=bridge,
        metrics=metrics,
        persisted_rows=persisted,
    )
