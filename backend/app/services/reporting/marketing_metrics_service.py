"""Shared marketing and GTM metric calculations."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

MONEY = Decimal("0.01")
RATIO = Decimal("0.0001")


def q_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def safe_div(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return Decimal("0")
    return numerator / denominator


def calculate_cost_per_mql(marketing_spend: Decimal, mqls: Decimal) -> Decimal:
    return q_money(safe_div(marketing_spend, mqls))


def calculate_cost_per_sql(marketing_spend: Decimal, sqls: Decimal) -> Decimal:
    return q_money(safe_div(marketing_spend, sqls))


def calculate_pipeline_per_spend(pipeline_arr_created: Decimal, marketing_spend: Decimal) -> Decimal:
    return safe_div(pipeline_arr_created, marketing_spend).quantize(RATIO, rounding=ROUND_HALF_UP)


def calculate_marketing_cac_proxy(marketing_spend: Decimal, closed_won_arr: Decimal) -> Decimal:
    return safe_div(marketing_spend, closed_won_arr).quantize(RATIO, rounding=ROUND_HALF_UP)


def calculate_win_rate_on_pipeline_created(closed_won_arr: Decimal, pipeline_arr_created: Decimal) -> Decimal:
    return safe_div(closed_won_arr, pipeline_arr_created).quantize(RATIO, rounding=ROUND_HALF_UP)


def calculate_pipeline_coverage(pipeline_arr_created: Decimal, closed_won_arr: Decimal) -> Decimal:
    return safe_div(pipeline_arr_created, closed_won_arr).quantize(RATIO, rounding=ROUND_HALF_UP)


def calculate_pipeline_waterfall(
    beginning_pipeline_arr: Decimal,
    pipeline_arr_created: Decimal,
    closed_won_arr: Decimal,
    closed_lost_arr: Decimal,
    slipped_pipeline_arr: Decimal,
) -> Decimal:
    return beginning_pipeline_arr + pipeline_arr_created - closed_won_arr - closed_lost_arr - slipped_pipeline_arr
