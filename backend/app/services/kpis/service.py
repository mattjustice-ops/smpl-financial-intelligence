"""High-level orchestration for the KPI engine.

`run_kpis(...)` pulls every required input out of the DB (MRR waterfall,
opportunities, GL actuals) for a single month-or-quarter window, then runs
`calculate_kpis(...)`. The MRR waterfall must already be persisted for the
target period — call `POST /api/v1/mrr/run` first.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.services.kpis.engine import KpiInputs, KpiResults, calculate_kpis
from app.services.kpis.repository import (
    load_customer_counts,
    load_mrr_summary_for_period,
    load_pipeline_for_period,
    new_bookings_arr_for_period,
    operating_expense_for_period,
    revenue_for_period,
    sales_marketing_expense_for_period,
)
from app.services.mrr.repository import month_start, previous_month_start


def _months_between(start: date, end: date) -> int:
    return max(1, (end.year - start.year) * 12 + (end.month - start.month) + 1)


def run_kpis(
    session: Session,
    organization_id: uuid.UUID,
    *,
    period_start: date,
    period_end: date,
    target_bookings: Optional[Decimal] = None,
    gross_margin: Decimal = Decimal("0.7"),
    net_burn: Optional[Decimal] = None,
    prior_period_revenue: Optional[Decimal] = None,
    prior_period_sales_marketing_expense: Optional[Decimal] = None,
) -> KpiResults:
    p_start = month_start(period_start)

    mrr_summary = load_mrr_summary_for_period(session, organization_id, p_start)
    counts = load_customer_counts(session, organization_id, p_start)
    revenue = revenue_for_period(session, organization_id, period_start, period_end)
    sm_expense = sales_marketing_expense_for_period(session, organization_id, period_start, period_end)
    op_expense = operating_expense_for_period(session, organization_id, period_start, period_end)
    pipeline = load_pipeline_for_period(session, organization_id, period_start, period_end)
    bookings = new_bookings_arr_for_period(session, organization_id, period_start, period_end)

    # If caller didn't pass prior-period totals, derive them from the prior month's GL window.
    if prior_period_revenue is None:
        prior_start = previous_month_start(p_start)
        # Approximate prior window length as the same length as the current window.
        prior_end = date(prior_start.year, prior_start.month, period_end.day) if period_end.day <= 28 else prior_start
        prior_period_revenue = revenue_for_period(session, organization_id, prior_start, prior_end)
    if prior_period_sales_marketing_expense is None:
        prior_start = previous_month_start(p_start)
        prior_end = date(prior_start.year, prior_start.month, period_end.day) if period_end.day <= 28 else prior_start
        prior_period_sales_marketing_expense = sales_marketing_expense_for_period(
            session, organization_id, prior_start, prior_end
        )

    inputs = KpiInputs(
        period_start=period_start,
        period_end=period_end,
        beginning_mrr=mrr_summary["beginning_mrr"],
        ending_mrr=mrr_summary["ending_mrr"],
        new_mrr=mrr_summary["new_mrr"],
        expansion_mrr=mrr_summary["expansion_mrr"],
        contraction_mrr=mrr_summary["contraction_mrr"],
        churn_mrr=mrr_summary["churn_mrr"],
        reactivation_mrr=mrr_summary["reactivation_mrr"],
        active_customers_beginning=counts["active_customers_beginning"],
        active_customers_ending=counts["active_customers_ending"],
        new_customers=counts["new_customers"],
        churned_customers=counts["churned_customers"],
        new_bookings_arr=bookings,
        total_pipeline=pipeline,
        target_bookings=target_bookings,
        revenue=revenue,
        prior_period_revenue=prior_period_revenue,
        sales_marketing_expense=sm_expense,
        prior_period_sales_marketing_expense=prior_period_sales_marketing_expense,
        operating_expense=op_expense,
        gross_margin=gross_margin,
        net_burn=net_burn,
        period_months=_months_between(period_start, period_end),
    )

    results = calculate_kpis(inputs)
    object.__setattr__(
        results,
        "inputs_used",
        {
            "mrr": mrr_summary,
            "customer_counts": counts,
            "revenue": revenue,
            "sales_marketing_expense": sm_expense,
            "operating_expense": op_expense,
            "pipeline": pipeline,
            "new_bookings_arr": bookings,
            "prior_period_revenue": prior_period_revenue,
            "prior_period_sales_marketing_expense": prior_period_sales_marketing_expense,
            "gross_margin": gross_margin,
            "net_burn": net_burn,
            "period_months": _months_between(period_start, period_end),
        },
    )
    return results
