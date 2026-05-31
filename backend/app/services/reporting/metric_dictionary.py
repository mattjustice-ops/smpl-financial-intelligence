"""Semantic metric dictionary for dashboard reporting."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricDefinition:
    metric_name: str
    display_name: str
    formula: str
    formatting_type: str
    section: str
    reporting_category: str


METRICS: dict[str, MetricDefinition] = {
    "marketing_spend": MetricDefinition("marketing_spend", "Marketing Spend", "sum(marketing_spend)", "currency", "Marketing Total Summary", "marketing"),
    "mqls": MetricDefinition("mqls", "MQLs", "sum(mqls)", "number", "Marketing Total Summary", "marketing"),
    "sqls": MetricDefinition("sqls", "SQLs", "sum(sqls)", "number", "Marketing Total Summary", "marketing"),
    "sals": MetricDefinition("sals", "SALs", "sum(sals)", "number", "Marketing Total Summary", "marketing"),
    "opportunities_created": MetricDefinition("opportunities_created", "Opportunities Created", "sum(opportunities_created)", "number", "Marketing Total Summary", "marketing"),
    "pipeline_arr_created": MetricDefinition("pipeline_arr_created", "Pipeline ARR Created", "sum(pipeline_arr_created)", "currency", "Pipeline", "gtm"),
    "closed_won_arr": MetricDefinition("closed_won_arr", "Closed Won ARR", "sum(closed_won_arr)", "currency", "Bookings", "gtm"),
    "pipeline_per_dollar_spend": MetricDefinition("pipeline_per_dollar_spend", "Pipeline per $ Spend", "pipeline_arr_created / marketing_spend", "multiple", "Efficiency", "marketing"),
    "marketing_cac_proxy": MetricDefinition("marketing_cac_proxy", "Marketing CAC Proxy", "marketing_spend / closed_won_arr", "multiple", "Efficiency", "marketing"),
    "win_rate_on_pipeline_created": MetricDefinition("win_rate_on_pipeline_created", "Win Rate on Pipeline Created", "closed_won_arr / pipeline_arr_created", "percent", "Efficiency", "marketing"),
    "pipeline_coverage_ratio": MetricDefinition("pipeline_coverage_ratio", "Pipeline Coverage Ratio", "pipeline_arr_created / closed_won_arr", "multiple", "Efficiency", "marketing"),
}


def metric_dictionary() -> list[MetricDefinition]:
    return list(METRICS.values())
