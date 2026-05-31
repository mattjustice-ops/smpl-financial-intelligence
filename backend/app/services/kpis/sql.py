"""Reference SQL queries used by the KPI engine. All accept :organization_id."""

# --------------------------------------------------------------------------
# MRR waterfall summary for a period.
# --------------------------------------------------------------------------
MRR_SUMMARY_SQL = """
SELECT
    period,
    SUM(beginning_mrr)    AS beginning_mrr,
    SUM(new_mrr)          AS new_mrr,
    SUM(expansion_mrr)    AS expansion_mrr,
    SUM(contraction_mrr)  AS contraction_mrr,
    SUM(churn_mrr)        AS churn_mrr,
    SUM(reactivation_mrr) AS reactivation_mrr,
    SUM(ending_mrr)       AS ending_mrr
FROM mrr_waterfall
WHERE organization_id = :organization_id
  AND period           = :period
GROUP BY period;
"""

# --------------------------------------------------------------------------
# Customer counts derived from the waterfall.
# --------------------------------------------------------------------------
CUSTOMER_COUNTS_SQL = """
SELECT
    SUM(CASE WHEN beginning_mrr > 0 THEN 1 ELSE 0 END) AS active_customers_beginning,
    SUM(CASE WHEN ending_mrr    > 0 THEN 1 ELSE 0 END) AS active_customers_ending,
    SUM(CASE WHEN movement_type = 'new'   THEN 1 ELSE 0 END) AS new_customers,
    SUM(CASE WHEN movement_type = 'churn' THEN 1 ELSE 0 END) AS churned_customers
FROM mrr_waterfall
WHERE organization_id = :organization_id
  AND period           = :period;
"""

# --------------------------------------------------------------------------
# Revenue / S&M / OpEx from GL actuals.
# --------------------------------------------------------------------------
GL_BUCKETS_SQL = """
SELECT
    SUM(CASE WHEN LOWER(account_name) LIKE '%%revenue%%' THEN amount ELSE 0 END)
        AS revenue,
    SUM(CASE WHEN LOWER(category) IN ('sales','marketing','sales & marketing','s&m','sm')
              THEN amount ELSE 0 END)
        AS sales_marketing_expense,
    SUM(CASE WHEN LOWER(statement) IN ('income','income_statement','operating','opex')
              THEN amount ELSE 0 END)
        AS operating_expense
FROM gl_actuals
WHERE organization_id = :organization_id
  AND period BETWEEN :period_start AND :period_end;
"""

# --------------------------------------------------------------------------
# Pipeline + closed-won bookings.
# --------------------------------------------------------------------------
PIPELINE_AND_BOOKINGS_SQL = """
SELECT
    SUM(CASE WHEN stage NOT IN (
            'Closed Won', 'closed_won', 'won',
            'Closed Lost', 'closed_lost', 'lost'
        ) THEN amount_arr ELSE 0 END)                   AS total_pipeline,
    SUM(CASE WHEN stage IN ('Closed Won', 'closed_won', 'won')
              THEN amount_arr ELSE 0 END)               AS new_bookings_arr
FROM opportunities
WHERE organization_id = :organization_id
  AND expected_close_date BETWEEN :period_start AND :period_end;
"""

# --------------------------------------------------------------------------
# A single-row KPI snapshot (formulas inline). All ratios in 0..1.
# --------------------------------------------------------------------------
KPI_SNAPSHOT_SQL = """
WITH mrr AS (
    SELECT *
    FROM mrr_waterfall_summary -- view from MRR_SUMMARY_SQL
    WHERE organization_id = :organization_id AND period = :period
), gl AS (
    SELECT *
    FROM gl_buckets_summary    -- view from GL_BUCKETS_SQL
    WHERE organization_id = :organization_id
      AND period_start = :period_start
      AND period_end   = :period_end
)
SELECT
    mrr.ending_mrr * 12                                              AS arr,
    mrr.ending_mrr                                                   AS mrr,
    (mrr.beginning_mrr + mrr.expansion_mrr + mrr.reactivation_mrr
      - mrr.contraction_mrr - mrr.churn_mrr)
    / NULLIF(mrr.beginning_mrr, 0)                                   AS nrr,
    (mrr.beginning_mrr - mrr.contraction_mrr - mrr.churn_mrr)
    / NULLIF(mrr.beginning_mrr, 0)                                   AS grr,
    mrr.churn_mrr / NULLIF(mrr.beginning_mrr, 0)                     AS gross_mrr_churn_rate
FROM mrr, gl;
"""
