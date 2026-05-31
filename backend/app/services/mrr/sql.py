"""Reference SQL for the MRR waterfall.

These statements compute the same result the Python engine does, useful when
you want to run the math directly in PostgreSQL (BI tools, ad-hoc analysis).
"""

# --------------------------------------------------------------------------
# 1. Per-customer MRR for every month a subscription was active.
# --------------------------------------------------------------------------
CUSTOMER_MONTHLY_MRR_SQL = """
WITH months AS (
    SELECT generate_series(
        date_trunc('month', :start_period)::date,
        date_trunc('month', :end_period)::date,
        INTERVAL '1 month'
    )::date AS period
),
customer_month AS (
    SELECT
        s.organization_id,
        s.customer_id,
        m.period,
        COALESCE(SUM(s.current_mrr), 0)::numeric(18, 2) AS mrr
    FROM months m
    JOIN subscriptions s
      ON s.organization_id = :organization_id
     AND s.start_date <= (m.period + INTERVAL '1 month - 1 day')::date
     AND (s.end_date IS NULL OR s.end_date >= m.period)
    GROUP BY 1, 2, 3
)
SELECT
    customer_id,
    period,
    mrr AS current_mrr,
    COALESCE(
        LAG(mrr) OVER (PARTITION BY customer_id ORDER BY period),
        0
    )::numeric(18, 2) AS prior_mrr
FROM customer_month;
"""

# --------------------------------------------------------------------------
# 2. Customer-level MRR waterfall classification, derived from the above.
#    Matches the Python engine's classification rules.
# --------------------------------------------------------------------------
CUSTOMER_WATERFALL_SQL = """
WITH cm AS (
    -- (Substitute CUSTOMER_MONTHLY_MRR_SQL as a CTE here, or join the
    -- existing customer_month materialization.)
    SELECT customer_id, period, current_mrr, prior_mrr FROM customer_monthly_mrr
),
historical AS (
    SELECT
        customer_id,
        period,
        EXISTS (
            SELECT 1 FROM cm h
            WHERE h.customer_id = cm.customer_id
              AND h.period < cm.period
              AND h.current_mrr > 0
        ) AS had_historical_mrr
    FROM cm
)
SELECT
    cm.customer_id,
    cm.period,
    cm.prior_mrr   AS beginning_mrr,
    CASE WHEN cm.prior_mrr = 0 AND cm.current_mrr > 0 AND NOT h.had_historical_mrr
         THEN cm.current_mrr ELSE 0 END AS new_mrr,
    CASE WHEN cm.prior_mrr > 0 AND cm.current_mrr > cm.prior_mrr
         THEN cm.current_mrr - cm.prior_mrr ELSE 0 END AS expansion_mrr,
    CASE WHEN cm.prior_mrr > 0 AND cm.current_mrr < cm.prior_mrr AND cm.current_mrr > 0
         THEN cm.prior_mrr - cm.current_mrr ELSE 0 END AS contraction_mrr,
    CASE WHEN cm.prior_mrr > 0 AND cm.current_mrr = 0
         THEN cm.prior_mrr ELSE 0 END AS churn_mrr,
    CASE WHEN cm.prior_mrr = 0 AND cm.current_mrr > 0 AND h.had_historical_mrr
         THEN cm.current_mrr ELSE 0 END AS reactivation_mrr,
    cm.current_mrr AS ending_mrr,
    CASE
        WHEN cm.prior_mrr = 0 AND cm.current_mrr > 0 AND NOT h.had_historical_mrr THEN 'new'
        WHEN cm.prior_mrr = 0 AND cm.current_mrr > 0 AND h.had_historical_mrr    THEN 'reactivation'
        WHEN cm.prior_mrr > 0 AND cm.current_mrr = 0                              THEN 'churn'
        WHEN cm.prior_mrr > 0 AND cm.current_mrr > cm.prior_mrr                   THEN 'expansion'
        WHEN cm.prior_mrr > 0 AND cm.current_mrr < cm.prior_mrr                   THEN 'contraction'
        ELSE 'unchanged'
    END AS movement_type
FROM cm
JOIN historical h ON h.customer_id = cm.customer_id AND h.period = cm.period
WHERE NOT (cm.prior_mrr = 0 AND cm.current_mrr = 0);
"""

# --------------------------------------------------------------------------
# 3. Company-level summary + NRR / GRR (per period).
# --------------------------------------------------------------------------
COMPANY_SUMMARY_SQL = """
SELECT
    period,
    SUM(beginning_mrr)    AS beginning_mrr,
    SUM(new_mrr)          AS new_mrr,
    SUM(expansion_mrr)    AS expansion_mrr,
    SUM(contraction_mrr)  AS contraction_mrr,
    SUM(churn_mrr)        AS churn_mrr,
    SUM(reactivation_mrr) AS reactivation_mrr,
    SUM(ending_mrr)       AS ending_mrr,
    -- ARR bridge
    SUM(beginning_mrr)    * 12 AS beginning_arr,
    SUM(ending_mrr)       * 12 AS ending_arr,
    -- Retention
    CASE WHEN SUM(beginning_mrr) = 0 THEN NULL
         ELSE (SUM(beginning_mrr) + SUM(expansion_mrr) + SUM(reactivation_mrr)
               - SUM(contraction_mrr) - SUM(churn_mrr))
              / SUM(beginning_mrr) END AS nrr,
    CASE WHEN SUM(beginning_mrr) = 0 THEN NULL
         ELSE (SUM(beginning_mrr) - SUM(contraction_mrr) - SUM(churn_mrr))
              / SUM(beginning_mrr) END AS grr,
    CASE WHEN SUM(beginning_mrr) = 0 THEN NULL
         ELSE SUM(churn_mrr) / SUM(beginning_mrr) END AS gross_mrr_churn_rate,
    CASE WHEN SUM(beginning_mrr) = 0 THEN NULL
         ELSE SUM(expansion_mrr) / SUM(beginning_mrr) END AS expansion_rate
FROM mrr_waterfall
WHERE organization_id = :organization_id
GROUP BY period
ORDER BY period;
"""
