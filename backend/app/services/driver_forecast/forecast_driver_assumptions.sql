-- dbt-style model: forecast_driver_assumptions
--
-- Purpose:
--   Scenario-aware driver assumptions for institutional FP&A forecast models.
--   Assumptions are period-effective and can override default service-layer
--   assumptions by organization/scenario.

select
    organization_id,
    scenario_name,
    effective_period,
    assumption_name,
    assumption_category,
    actual_value,
    forecast_value,
    created_at,
    updated_at
from {{ ref('forecast_driver_assumptions') }}

-- Recommended downstream models:
--   int_billing_forecast
--   int_cash_collections_forecast
--   int_deferred_revenue_waterfall
--   int_working_capital_forecast
--   fct_operating_cash_flow_bridge
--   fct_forecast_cash_flow
--   fct_forecast_balance_sheet
