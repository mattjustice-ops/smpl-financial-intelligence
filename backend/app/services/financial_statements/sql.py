"""Reference SQL for financial statements sourced from gl_actuals."""

GL_BY_STATEMENT_SQL = """
SELECT
    period,
    account_number,
    account_name,
    statement,
    category,
    amount,
    currency,
    subsidiary
FROM gl_actuals
WHERE organization_id = :organization_id
  AND period BETWEEN :period_start AND :period_end
ORDER BY period, account_number;
"""

INCOME_STATEMENT_SQL = """
SELECT
    category,
    account_number,
    account_name,
    SUM(amount) AS amount
FROM gl_actuals
WHERE organization_id = :organization_id
  AND period BETWEEN :period_start AND :period_end
  AND LOWER(REPLACE(statement, '_', ' ')) LIKE '%income%'
GROUP BY category, account_number, account_name
ORDER BY category, account_number;
"""

BALANCE_SHEET_SNAPSHOT_SQL = """
SELECT
    category,
    account_number,
    account_name,
    amount
FROM gl_actuals
WHERE organization_id = :organization_id
  AND period = :as_of_period
  AND LOWER(REPLACE(statement, '_', ' ')) LIKE '%balance%'
ORDER BY category, account_number;
"""
