"""Reference SQL for the bookings forecast.

These queries compute the same numbers the Python engine does, for ad-hoc
analysis or BI dashboards. All queries are parameterized on `:organization_id`.
"""

# --------------------------------------------------------------------------
# 1. Historical win rates by stage (from closed opportunities)
# --------------------------------------------------------------------------
WIN_RATES_BY_STAGE_SQL = """
WITH closed AS (
    SELECT
        stage,
        CASE WHEN stage IN ('Closed Won', 'closed_won', 'won') THEN 1 ELSE 0 END AS is_won
    FROM opportunities
    WHERE organization_id = :organization_id
      AND stage IN (
          'Closed Won', 'closed_won', 'won',
          'Closed Lost', 'closed_lost', 'lost'
      )
)
SELECT stage,
       COUNT(*)                                          AS n,
       SUM(is_won)                                       AS wins,
       (SUM(is_won)::numeric / NULLIF(COUNT(*), 0))::numeric(9,6) AS win_rate
FROM closed
GROUP BY stage
ORDER BY stage;
"""

# --------------------------------------------------------------------------
# 2. Historical win rates by segment
# --------------------------------------------------------------------------
WIN_RATES_BY_SEGMENT_SQL = """
WITH closed AS (
    SELECT
        COALESCE(segment, '') AS segment,
        CASE WHEN stage IN ('Closed Won', 'closed_won', 'won') THEN 1 ELSE 0 END AS is_won
    FROM opportunities
    WHERE organization_id = :organization_id
      AND stage IN (
          'Closed Won', 'closed_won', 'won',
          'Closed Lost', 'closed_lost', 'lost'
      )
)
SELECT segment,
       COUNT(*)                                          AS n,
       SUM(is_won)                                       AS wins,
       (SUM(is_won)::numeric / NULLIF(COUNT(*), 0))::numeric(9,6) AS win_rate
FROM closed
GROUP BY segment
ORDER BY segment;
"""

# --------------------------------------------------------------------------
# 3. Weighted bookings forecast in a window (per-opportunity rows).
# --------------------------------------------------------------------------
WEIGHTED_FORECAST_SQL = """
SELECT
    o.opportunity_id,
    o.customer_id,
    o.rep_id,
    o.segment,
    o.stage,
    o.amount_arr                                         AS amount,
    o.probability,
    o.expected_close_date,
    (o.amount_arr * o.probability)::numeric(18, 2)       AS forecast_value
FROM opportunities o
WHERE o.organization_id = :organization_id
  AND o.expected_close_date BETWEEN :period_start AND :period_end
  AND o.stage NOT IN (
      'Closed Won', 'closed_won', 'won',
      'Closed Lost', 'closed_lost', 'lost'
  );
"""

# --------------------------------------------------------------------------
# 4. Forecast by month / quarter / rep / segment / customer.
# --------------------------------------------------------------------------
FORECAST_AGGREGATES_SQL = """
WITH f AS (
    SELECT
        opportunity_id,
        customer_id,
        rep_id,
        segment,
        expected_close_date,
        (amount_arr * probability)::numeric(18, 2) AS forecast_value
    FROM opportunities
    WHERE organization_id = :organization_id
      AND expected_close_date BETWEEN :period_start AND :period_end
      AND stage NOT IN (
          'Closed Won', 'closed_won', 'won',
          'Closed Lost', 'closed_lost', 'lost'
      )
)
SELECT
    date_trunc('month',   expected_close_date)::date     AS month,
    to_char(expected_close_date, 'YYYY-"Q"Q')            AS quarter,
    rep_id,
    segment,
    customer_id,
    SUM(forecast_value)                                  AS forecast_value
FROM f
GROUP BY GROUPING SETS (
    (month),
    (quarter),
    (rep_id),
    (segment),
    (customer_id),
    ()
);
"""

# --------------------------------------------------------------------------
# 5. Pipeline coverage ratio: total pipeline / target (or vs forecast).
# --------------------------------------------------------------------------
COVERAGE_RATIO_SQL = """
SELECT
    SUM(amount_arr)                                          AS total_pipeline,
    SUM(amount_arr * probability)                            AS total_forecast,
    CASE
        WHEN :target_bookings::numeric IS NOT NULL AND :target_bookings::numeric > 0
            THEN SUM(amount_arr) / :target_bookings::numeric
        WHEN SUM(amount_arr * probability) > 0
            THEN SUM(amount_arr) / SUM(amount_arr * probability)
        ELSE NULL
    END                                                      AS coverage_ratio
FROM opportunities
WHERE organization_id = :organization_id
  AND expected_close_date BETWEEN :period_start AND :period_end
  AND stage NOT IN (
      'Closed Won', 'closed_won', 'won',
      'Closed Lost', 'closed_lost', 'lost'
  );
"""
