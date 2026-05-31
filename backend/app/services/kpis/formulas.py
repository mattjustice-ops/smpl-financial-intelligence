"""Formula reference for the SaaS KPI engine.

These docstrings are the spec the engine implements. Each formula notes its
denominator-zero behavior (the engine returns None for undefined values).

MRR / ARR
---------
- MRR  = sum(active_subscription.current_mrr)
- ARR  = MRR * 12

Retention
---------
- NRR  = (beginning_mrr + expansion_mrr + reactivation_mrr
          - contraction_mrr - churn_mrr) / beginning_mrr
- GRR  = (beginning_mrr - contraction_mrr - churn_mrr) / beginning_mrr
- Logo churn       = churned_customers / active_customers_beginning
- Gross MRR churn  = churn_mrr / beginning_mrr
- Net MRR churn    = 1 - NRR   (positive = net contraction, negative = net growth)

Unit economics
--------------
- ARPA  = revenue / active_customers_avg
- CAC   = sales_and_marketing_expense / new_customers
- CAC payback (months) = CAC / (new_mrr_per_new_customer * gross_margin)
        where new_mrr_per_new_customer = new_mrr / new_customers
- LTV   = ARPA_monthly * gross_margin / monthly_gross_mrr_churn_rate
        where ARPA_monthly = (revenue / period_months) / active_customers_avg
- LTV / CAC ratio = LTV / CAC

Growth / efficiency
-------------------
- Revenue growth rate (period-over-period)
              = (revenue - prior_period_revenue) / prior_period_revenue
- Operating margin   = (revenue - operating_expense) / revenue
- Rule of 40 (%) = (revenue_growth_rate + operating_margin) * 100
- SaaS Magic Number (quarterly)
              = (current_qtr_revenue - prior_qtr_revenue) * 4
              / prior_qtr_sales_marketing_expense
- Sales efficiency (a.k.a. CAC ratio) = new_bookings_arr / sales_marketing_expense
- Pipeline coverage = total_pipeline / target_bookings
- Burn multiple = net_burn / net_new_arr   (net burn is positive when burning)
"""
