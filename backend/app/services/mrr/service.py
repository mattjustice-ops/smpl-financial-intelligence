"""High-level orchestration: load inputs, run engine, optionally persist."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.services.mrr.engine import (
    CompanyMrrSummary,
    CustomerMrrMovement,
    compute_waterfall,
    summarize_company,
)
from app.services.mrr.metrics import ArrBridge, PeriodMetrics, arr_bridge, compute_period_metrics
from app.services.mrr.repository import (
    customer_mrr_for_month,
    historical_active_customers,
    month_start,
    previous_month_start,
    upsert_mrr_waterfall_rows,
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

    customer_rows = compute_waterfall(
        period=current_period,
        prior_mrr_by_customer=prior_mrr,
        current_mrr_by_customer=current_mrr,
        historical_active_customers=history,
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
