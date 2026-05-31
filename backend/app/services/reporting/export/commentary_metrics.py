"""Pre-fill commentary metric_context from comparison datasets."""

from __future__ import annotations

from decimal import Decimal

from app.services.financial_statements.financial_statement_service import SummaryResponse
from app.services.marketing.schemas import ActualBudgetForecastResponse, MarketingMetricRow
from app.services.reporting.export.commentary_templates import commentary_fields_for_period
from app.services.reporting.export.comparison_pivot import pivot_waterfall_abc
from app.services.reporting.export.schemas import CommentaryField, GlDetailRow, WaterfallSummaryRow
from app.services.reporting.period_utils import to_period


def _fmt_money(value: Decimal) -> str:
    if value == 0:
        return "$0"
    sign = "-" if value < 0 else ""
    v = abs(value)
    if v >= Decimal("1000000"):
        return f"{sign}${v / Decimal('1000000'):,.2f}M"
    if v >= Decimal("1000"):
        return f"{sign}${v / Decimal('1000'):,.1f}K"
    return f"{sign}${v:,.0f}"


def _line_amount(
    financial: SummaryResponse | None,
    line_match: str,
    scenario: str,
    period: str,
) -> Decimal:
    if financial is None:
        return Decimal("0")
    needle = line_match.lower()
    for row in financial.income_statement.rows:
        if row.scenario != scenario or to_period(str(row.period)) != period:
            continue
        if needle in row.line_item.lower():
            return row.amount
    return Decimal("0")


def _waterfall_amount(
    rows: list[WaterfallSummaryRow],
    waterfall_type: str,
    scenario: str,
    period: str,
) -> Decimal:
    total = Decimal("0")
    for row in rows:
        if row.waterfall_type == waterfall_type and row.scenario == scenario and to_period(row.period) == period:
            total += row.amount
    return total


def _marketing_total(
    rows: list[MarketingMetricRow],
    period: str,
    field: str,
) -> Decimal:
    total = Decimal("0")
    for row in rows:
        if to_period(row.period) != period:
            continue
        total += getattr(row, field, Decimal("0"))
    return total


def enrich_commentary_fields(
    fields: list[CommentaryField],
    *,
    as_of_period: str,
    comparison_waterfalls: dict[str, list[WaterfallSummaryRow]],
    financial: SummaryResponse | None,
    marketing: ActualBudgetForecastResponse | None,
    gl_detail: list[GlDetailRow] | None = None,
) -> list[CommentaryField]:
    period = to_period(as_of_period)
    arr = comparison_waterfalls.get("arr", [])
    pipeline = comparison_waterfalls.get("pipeline", [])
    cash = comparison_waterfalls.get("cash_flow", [])
    deferred = comparison_waterfalls.get("deferred_revenue", [])

    ending = pivot_waterfall_abc(
        [r for r in arr if r.waterfall_type in {"ending", "ending_arr"}],
        periods=[period],
    )
    new_arr = pivot_waterfall_abc(
        [r for r in arr if r.waterfall_type in {"new_business", "new_arr"}],
        periods=[period],
    )

    section_metrics: dict[str, str] = {}

    period_list = sorted(
        {
            to_period(row.period)
            for rows in comparison_waterfalls.values()
            for row in rows
        }
    )
    if period_list:
        section_metrics.setdefault(
            "Executive Summary",
            f"Comparison window: {period_list[0]} – {period_list[-1]} (monthly Actual vs Budget in export tabs).",
        )

    if ending:
        e = ending[0]
        section_metrics["MRR / ARR Waterfall"] = (
            f"Ending ARR ({as_of_period}) — Actual: {_fmt_money(e['actual'])}, Budget: {_fmt_money(e['budget'])}."
        )
    if new_arr:
        n = new_arr[0]
        section_metrics["MRR / ARR Waterfall"] = (
            section_metrics.get("MRR / ARR Waterfall", "")
            + f" New ARR — Actual: {_fmt_money(n['actual'])}, Budget: {_fmt_money(n['budget'])}, "
            f"Forecast: {_fmt_money(n['forecast'])}."
        ).strip()

    rev_a = _line_amount(financial, "revenue", "Actual", period)
    rev_b = _line_amount(financial, "revenue", "Budget", period)
    rev_f = _line_amount(financial, "revenue", "Forecast", period)
    if any((rev_a, rev_b, rev_f)):
        section_metrics["Income Statement"] = (
            f"Revenue — Actual: {_fmt_money(rev_a)}, Budget: {_fmt_money(rev_b)}, Forecast: {_fmt_money(rev_f)}."
        )
        section_metrics["Executive Summary"] = section_metrics["Income Statement"]

    ebitda_a = _line_amount(financial, "ebitda", "Actual", period)
    ebitda_b = _line_amount(financial, "ebitda", "Budget", period)
    if ebitda_a or ebitda_b:
        section_metrics["Executive Summary"] = (
            (section_metrics.get("Executive Summary", "") + f" EBITDA — Actual: {_fmt_money(ebitda_a)}, Budget: {_fmt_money(ebitda_b)}.").strip()
        )

    for label, wf_type in (
        ("Pipeline created", "pipeline_created"),
        ("Closed won", "closed_won"),
        ("Slipped", "slipped_pipeline"),
    ):
        a = _waterfall_amount(pipeline, wf_type, "Actual", period)
        b = _waterfall_amount(pipeline, wf_type, "Budget", period)
        f = _waterfall_amount(pipeline, wf_type, "Forecast", period)
        if a or b or f:
            section_metrics["Pipeline Waterfall"] = (
                section_metrics.get("Pipeline Waterfall", "")
                + f" {label} ARR — Actual: {_fmt_money(a)}, Budget: {_fmt_money(b)}, Forecast: {_fmt_money(f)}."
            ).strip()

    cash_end_a = _waterfall_amount(cash, "ending_cash", "Actual", period)
    cash_end_f = _waterfall_amount(cash, "ending_cash", "Forecast", period)
    if cash_end_a or cash_end_f:
        section_metrics["Cash Forecast"] = (
            f"Ending cash — Actual: {_fmt_money(cash_end_a)}, Forecast: {_fmt_money(cash_end_f)}."
        )

    def_rev = _waterfall_amount(deferred, "deferred_revenue_recognized", "Forecast", period)
    total_gaap = _waterfall_amount(deferred, "total_gaap_revenue", "Actual", period) or _waterfall_amount(
        deferred, "total_gaap_revenue", "Forecast", period
    )
    if def_rev or total_gaap:
        section_metrics["Deferred Revenue"] = (
            f"Total GAAP revenue: {_fmt_money(total_gaap)}; Deferred recognized (forecast month): {_fmt_money(def_rev)}."
        )

    if gl_detail:
        for scen, label in (("Actual", "Actual"), ("Budget", "Budget")):
            spend = sum(
                row.amount
                for row in gl_detail
                if row.scenario == scen and row.period == period and (row.expense_type or row.account_group)
            )
            if spend:
                section_metrics.setdefault("Department Spend / P&L", "")
                section_metrics["Department Spend / P&L"] += f" {label} GL spend: {_fmt_money(spend)};"
        section_metrics["Department Spend / P&L"] = section_metrics.get("Department Spend / P&L", "").strip()

    if marketing:
        spend_a = _marketing_total(marketing.actual, period, "marketing_spend")
        spend_b = _marketing_total(marketing.budget, period, "marketing_spend")
        spend_f = _marketing_total(marketing.forecast, period, "marketing_spend")
        if spend_a or spend_b or spend_f:
            section_metrics["GTM Performance"] = (
                f"Marketing spend — Actual: {_fmt_money(spend_a)}, Budget: {_fmt_money(spend_b)}, "
                f"Forecast: {_fmt_money(spend_f)}."
            )

    for field in fields:
        if field.section in section_metrics:
            field.metric_context = section_metrics[field.section]
    return fields


def build_commentary_fields_for_export(
    as_of_period: str,
    comparison_waterfalls: dict[str, list[WaterfallSummaryRow]],
    financial: SummaryResponse | None,
    marketing: ActualBudgetForecastResponse | None,
    gl_detail: list[GlDetailRow] | None = None,
) -> list[CommentaryField]:
    base = commentary_fields_for_period(as_of_period)
    return enrich_commentary_fields(
        base,
        as_of_period=as_of_period,
        comparison_waterfalls=comparison_waterfalls,
        financial=financial,
        marketing=marketing,
        gl_detail=gl_detail,
    )
