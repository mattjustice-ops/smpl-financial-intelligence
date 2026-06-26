"""Board-ready slide commentary: operational drivers + strategic context."""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.core.config import get_settings
from app.services.board_package.package import fmt_money
from app.services.commentary.llm_factory import build_commentary_llm_client
from app.services.reporting.export.board_chart_service import _wf
from app.services.reporting.export.board_metrics_snapshot import BoardMetricsSnapshot, build_metrics_snapshot
from app.services.reporting.export.company_context import strategic_context_for_prompt
from app.services.reporting.export.export_sheet_registry import (
    monthly_close_requirements_prompt,
    requirements_prompt_block,
)
from app.services.reporting.export.saas_semantic_reporting import (
    OpportunityMovementType,
    build_movement_attribution,
)
from app.services.reporting.export.schemas import ReportingBundle
from app.services.reporting.period_utils import period_range, to_period

_MONTH_NAME_TO_NUM: dict[str, int] = {
    name.lower(): i for i, name in enumerate(calendar.month_name[1:], start=1)
}
_MONTH_ABBR_TO_NUM: dict[str, int] = {
    abbr.lower(): i for i, abbr in enumerate(calendar.month_abbr[1:], start=1)
}
_GA_DEPT_HINTS = ("g&a", "g & a", "general", "admin", "finance", "legal", "hr", "people")


@dataclass
class SlideCommentary:
    what_happened: str = ""
    why_it_happened: str = ""
    impact: str = ""
    favorable: str = ""
    unfavorable: str = ""
    recommended_actions: str = ""
    leadership_watch: str = ""
    bullets: list[str] = field(default_factory=list)

    def bullets_favorable_unfavorable_watch(self) -> list[str]:
        out: list[str] = []
        if self.favorable:
            out.append(self.favorable)
        if self.unfavorable:
            out.append(self.unfavorable)
        if self.leadership_watch:
            out.append(f"Watch: {self.leadership_watch}")
        return out

    def narrative_block(self) -> str:
        parts = [self.what_happened, self.why_it_happened]
        return " ".join(p for p in parts if p).strip()


def _pipeline_movement_commentary(bundle: ReportingBundle, m: BoardMetricsSnapshot) -> SlideCommentary:
    cur = bundle.currency
    attr = build_movement_attribution(bundle)
    new_n = attr.count(OpportunityMovementType.NEW_CREATED)
    adv_n = attr.count(OpportunityMovementType.EXISTING_ADVANCED)
    prior_won = attr.count(OpportunityMovementType.PRIOR_PERIOD_CLOSED_WON)
    deferred = attr.count(OpportunityMovementType.DEFERRED)
    return SlideCommentary(
        what_happened=(
            f"{new_n} new opportunities, {adv_n} advanced, {prior_won} prior-period wins, "
            f"{deferred} deferred — {fmt_money(attr.arr(OpportunityMovementType.PRIOR_PERIOD_CLOSED_WON), cur)} "
            "ARR from deals not created this month."
        ),
        why_it_happened=(
            "Movement lineage separates same-month creation from in-period execution on older pipeline — "
            "avoid treating all closed won as new demand."
        ),
        impact="Forecast confidence improves when prior-period wins are distinguished from new pipeline creation.",
        leadership_watch="Reconcile movement counts to CRM stage history before updating coverage ratios.",
    )


def _field_for(bundle: ReportingBundle, needle: str) -> str:
    for f in bundle.mda_commentary or bundle.commentary_fields:
        if needle.lower() in f.section.lower():
            parts = [f.what_changed, f.variance_driver, f.favorable, f.unfavorable]
            return " ".join(p for p in parts if p).strip()
    return ""


def _commentary_executive(bundle: ReportingBundle, m) -> SlideCommentary:
    text = _field_for(bundle, "Executive") or _field_for(bundle, "SaaS MD&A")
    what = text or (
        f"Ending ARR reached {fmt_money(m.ending_arr, m.currency)} with "
        f"net new ARR of {fmt_money(m.net_new_arr, m.currency)} in {m.as_of}."
    )
    why = ""
    if m.new_arr_budget and m.new_arr_actual != m.new_arr_budget:
        delta = m.new_arr_actual - m.new_arr_budget
        why = (
            f"Growth variance versus budget is {fmt_money(delta, m.currency)}, "
            f"driven by new business and expansion in the MRR waterfall."
        )
    elif m.expansion or m.churn:
        why = (
            f"Expansion of {fmt_money(m.expansion, m.currency)} and churn of "
            f"{fmt_money(m.churn, m.currency)} shaped net retention for the period."
        )
    favorable = (
        "Enterprise expansion and integrated GTM-to-finance visibility remain strategic advantages "
        "when pipeline quality and forecast confidence hold."
    )
    unfavorable = ""
    if m.churn and m.ending_arr and (m.churn / m.ending_arr) > Decimal("0.04"):
        unfavorable = (
            "Churn concentration — particularly in SMB — pressures GRR and forecast accuracy; "
            "aligns with leadership focus on retention and pipeline discipline."
        )
    if m.slipped:
        unfavorable = (unfavorable + " " if unfavorable else "") + (
            f"Deferred pipeline of {fmt_money(m.slipped, m.currency)} should be reviewed before next-quarter coverage planning."
        )
    return SlideCommentary(
        what_happened=what,
        why_it_happened=why,
        impact="Liquidity, pipeline coverage, and hiring pace collectively determine whether growth converts to cash and operating leverage.",
        favorable=favorable,
        unfavorable=unfavorable.strip(),
        leadership_watch="Monitor forecast confidence by segment, collections timing, and validation status before board distribution.",
        recommended_actions="Confirm waterfall tie-outs; prioritize enterprise expansion plays and channel reallocation from efficiency rankings.",
    )


def build_slide_commentary(bundle: ReportingBundle, slide_key: str) -> SlideCommentary:
    m = build_metrics_snapshot(bundle)
    as_of = bundle.as_of_period
    cur = m.currency

    builders = {
        "executive_summary": lambda: _commentary_executive(bundle, m),
        "mda_summary": lambda: SlideCommentary(
            what_happened=_field_for(bundle, "SaaS MD&A")
            or f"Operational finance close for {as_of} connects GTM activity to ARR, revenue recognition, and cash.",
            why_it_happened=(
                "ARR changes trace to opportunity movements; pipeline activity is validated against the pipeline "
                "waterfall (not marketing_pipeline alone); cash ending balance ties to the balance sheet."
            ),
            favorable=_field_for(bundle, "Pipeline") or "GTM efficiency and expansion ARR support the growth narrative.",
            unfavorable="SMB churn and slippage remain the primary forecast risks entering the next quarter.",
            recommended_actions="Improve forecast accuracy, enterprise ARR growth, and cash conversion per strategic plan.",
        ),
        "gtm_performance": lambda: SlideCommentary(
            what_happened=(
                f"Marketing invested {fmt_money(m.marketing_spend, cur)} to create "
                f"{fmt_money(m.pipeline_from_marketing, cur)} of pipeline ARR."
            ),
            why_it_happened=(
                "Volume (MQL→SQL) and dollar efficiency (pipeline/spend) move independently — "
                "strong efficiency can coexist with softer top-of-funnel volume."
            ),
            impact="GTM efficiency directly affects CAC payback and the credibility of bookings forecasts.",
            favorable=(
                f"Closed won ARR of {fmt_money(m.closed_won_arr_mkt or m.closed_won, cur)} supports new business in the ARR waterfall."
                if (m.closed_won_arr_mkt or m.closed_won)
                else ""
            ),
            leadership_watch="Separate funnel counts from ARR charts when diagnosing conversion changes.",
        ),
        "marketing_channels": lambda: SlideCommentary(
            what_happened="Channel mix shifted period-over-period; ranked efficiency highlights where spend converts to pipeline and bookings.",
            why_it_happened=(
                "Partner and paid search often outperform on pipe/spend when lead quality is high; "
                "content syndication may inflate pipeline without comparable close rates."
            ),
            recommended_actions="Reallocate 10–15% of spend from bottom-quartile channels into top performers after two-week conversion review.",
        ),
        "funnel_conversion": lambda: SlideCommentary(
            what_happened=(
                f"Funnel progressed {int(m.mql)} MQLs to {int(m.sql)} SQLs with opportunities created in-period."
            ),
            why_it_happened=(
                "Conversion deterioration usually appears between SQL→SAL or SAL→opportunity — "
                "not at closed won ARR, which is shown separately."
            ),
            impact="Stage conversion changes lead or lag pipeline coverage by 1–2 quarters.",
        ),
        "pipeline_health": lambda: SlideCommentary(
            what_happened=(
                f"Active pipeline activity: {fmt_money(m.pipeline_created, cur)} created, "
                f"{fmt_money(m.closed_won, cur)} closed won, {fmt_money(m.slipped, cur)} deferred."
            ),
            why_it_happened=(
                "Period activity metrics are more actionable than cumulative beginning/ending balances "
                "for executive pipeline quality reviews."
            ),
            leadership_watch="Use aging buckets and forecast confidence alongside coverage — not ending pipeline alone.",
        ),
        "pipeline_movement": lambda: _pipeline_movement_commentary(bundle, m),
        "opportunity_drilldown": lambda: SlideCommentary(
            what_happened="Named opportunities drove material ARR and pipeline deltas this period.",
            why_it_happened="Spotlight deals explain variance versus forecast at the customer and billing-terms level.",
            recommended_actions="Review deferred and top forecast opportunities with owners before updating board outlook.",
        ),
        "arr_waterfall": lambda: SlideCommentary(
            what_happened=(
                f"ARR closed at {fmt_money(m.ending_arr, cur)} after net new "
                f"{fmt_money(m.net_new_arr, cur)} and retention movements."
            ),
            why_it_happened=(
                "Underlying opportunities (segment, billing terms, close timing) explain waterfall components; "
                "renewals are retention context — not additive net-new ARR."
            ),
            impact="ARR progression sets the anchor for billings, deferred revenue, and GAAP revenue outlook.",
        ),
        "retention_churn": lambda: SlideCommentary(
            what_happened=(
                f"Churn ARR {fmt_money(m.churn, cur)} vs expansion {fmt_money(m.expansion, cur)}."
            ),
            why_it_happened="Concentrated logo churn in one segment reads differently than broad-based contraction.",
            favorable="Expansion exceeding churn supports net retention when enterprise accounts expand on schedule.",
            unfavorable="Elevated churn in SMB segments aligns with known forecast risk areas." if m.churn > m.expansion else "",
        ),
        "gaap_revenue": lambda: SlideCommentary(
            what_happened=(
                f"GAAP revenue {fmt_money(m.revenue_actual, cur)} vs budget {fmt_money(m.revenue_budget, cur)}."
            ),
            why_it_happened=(
                "Operational ARR and billings flow into deferred revenue recognition — "
                "revenue lags bookings depending on contract terms and recognition rules."
            ),
            impact="Revenue bridge explains how GTM execution becomes accounting performance.",
        ),
        "deferred_revenue": lambda: SlideCommentary(
            what_happened="Billings and recognition moved deferred revenue, shaping forward revenue visibility.",
            why_it_happened="Upfront billings improve cash; recognized revenue follows delivery and contract structure.",
            leadership_watch="Collections timing must align to billings and payment terms for cash forecast credibility.",
        ),
        "cash_forecast": lambda: SlideCommentary(
            what_happened=f"Ending cash {fmt_money(m.cash_actual, cur)} (forecast {fmt_money(m.cash_forecast, cur)}).",
            why_it_happened=(
                "Collections, payroll, and vendor disbursements drive the operating bridge — "
                "financing is secondary unless liquidity falls below policy floor."
            ),
            impact="Working capital discipline and billing terms determine runway without incremental financing.",
            leadership_watch="Ending cash must tie to balance sheet; bridge is source of truth.",
        ),
        "headcount": lambda: SlideCommentary(
            what_happened=f"Ending headcount {m.headcount} FTE across departments.",
            why_it_happened="Hiring ahead of plan increases opex before ARR capacity converts — monitor revenue and ARR per employee.",
            recommended_actions="Align open roles to quota capacity and engineering roadmap tied to enterprise ARR goals.",
        ),
        "department_spend": lambda: SlideCommentary(
            what_happened="Department actuals vs budget show where operational leverage is improving or eroding.",
            why_it_happened="Material variances trace to vendor timing, hiring, and GTM programs — not spreadsheet noise.",
            recommended_actions="Investigate unfavorable variances above threshold with GL owner confirmation.",
        ),
        "risks_opportunities": lambda: SlideCommentary(
            what_happened="Executive risk register spans GTM, forecast, liquidity, and hiring.",
            recommended_actions="Each item needs owner, financial impact estimate, and mitigation timeline before board review.",
        ),
        "validation": lambda: SlideCommentary(
            what_happened=f"Validation status: {bundle.validation.status.upper()} ({bundle.validation.failed_count} failed).",
            why_it_happened="Failed tie-outs between waterfalls, opportunities, and cash reduce forecast defensibility.",
            recommended_actions="Resolve failed checks in appendix before distributing externally.",
        ),
    }

    builder = builders.get(slide_key)
    if builder:
        return builder()
    return SlideCommentary(what_happened=f"Review {slide_key} detail in the MD&A workbook export.")


def metrics_prompt_blob(bundle: ReportingBundle) -> str:
    """Rich metric context for board Claude prompts."""
    m = build_metrics_snapshot(bundle)
    cur = m.currency
    gm_act = None
    gm_bud = None
    if m.revenue_actual and m.revenue_actual > 0:
        fs = bundle.comparison_financial_statements or bundle.financial_statements
        if fs:
            for row in fs.income_statement.rows:
                p = str(row.period)[:7]
                if p != m.as_of:
                    continue
                if "gross margin" in row.line_item.lower() or row.line_item.lower() == "gm":
                    if row.scenario == "Actual":
                        gm_act = row.amount
                    elif row.scenario == "Budget":
                        gm_bud = row.amount
    lines = [
        f"Close month: {m.as_of} ({bundle.period_label})",
        (
            f"Ending ARR {fmt_money(m.ending_arr, cur)}; net new {fmt_money(m.net_new_arr, cur)} "
            f"(budget {fmt_money(m.new_arr_budget, cur)}); expansion {fmt_money(m.expansion, cur)}; "
            f"churn {fmt_money(m.churn, cur)}"
        ),
        (
            f"Revenue {fmt_money(m.revenue_actual, cur)} actual vs {fmt_money(m.revenue_budget, cur)} budget; "
            f"EBITDA {fmt_money(m.ebitda_actual, cur)} actual vs {fmt_money(m.ebitda_budget, cur)} budget"
        ),
        f"Cash {fmt_money(m.cash_actual, cur)}; pipeline created {fmt_money(m.pipeline_created, cur)}; deferred {fmt_money(m.slipped, cur)}",
        f"Headcount {m.headcount}; marketing spend {fmt_money(m.marketing_spend, cur)}",
    ]
    if m.grr is not None:
        lines.append(f"GRR {float(m.grr):.3f}")
    if m.nrr is not None:
        lines.append(f"NRR {float(m.nrr):.3f}")
    if gm_act is not None and gm_bud is not None:
        lines.append(f"Gross margin actual {gm_act} vs budget {gm_bud}")
    return "\n".join(lines)


_CASH_BRIDGE_ITEMS: tuple[tuple[str, str], ...] = (
    ("beginning_cash", "Beginning cash"),
    ("cash_collections", "Collections"),
    ("collections", "Collections"),
    ("payroll_cash_out", "Payroll"),
    ("vendor_cash_out", "Vendor payments"),
    ("commission_cash_out", "Commissions"),
    ("tax_cash_out", "Tax"),
    ("interest_cash_out", "Interest"),
    ("other_operating_cash_out", "Other operating"),
    ("capex", "Capex"),
    ("financing", "Financing"),
    ("ending_cash", "Ending cash"),
)

_ARR_BRIDGE_ITEMS: tuple[tuple[str, str], ...] = (
    ("beginning", "Beginning ARR"),
    ("new_business", "New business ARR"),
    ("expansion", "Expansion ARR"),
    ("churn", "Churn ARR"),
    ("contraction", "Contraction ARR"),
    ("reactivation", "Reactivation ARR"),
    ("ending", "Ending ARR"),
    ("ending_arr", "Ending ARR"),
)

_PIPELINE_ITEMS: tuple[tuple[str, str], ...] = (
    ("beginning_pipeline", "Beginning pipeline ARR"),
    ("pipeline_created", "Pipeline created ARR"),
    ("closed_won", "Closed won ARR"),
    ("closed_lost", "Closed lost ARR"),
    ("slipped_pipeline", "Slipped pipeline ARR"),
    ("ending_pipeline", "Ending pipeline ARR"),
)

_DEFERRED_ITEMS: tuple[tuple[str, str], ...] = (
    ("beginning_deferred_revenue", "Beginning deferred revenue"),
    ("new_billings", "Billings"),
    ("billings", "Billings"),
    ("revenue_recognized", "Revenue recognized"),
    ("deferred_revenue_recognized", "Deferred revenue recognized"),
    ("total_gaap_revenue", "Total GAAP revenue"),
    ("ending_deferred_revenue", "Ending deferred revenue"),
)

_CASH_BRIDGE_TABLE_FIELDS: tuple[tuple[str, str], ...] = (
    ("beginning_cash", "Beginning cash"),
    ("collections", "Collections"),
    ("payroll", "Payroll"),
    ("vendor", "Vendor payments"),
    ("commission", "Commissions"),
    ("tax", "Tax"),
    ("interest", "Interest"),
    ("other_operating", "Other operating"),
    ("capex", "Capex"),
    ("ending_cash", "Ending cash"),
)


def _scenario_amount_parts(
    bundle: ReportingBundle,
    waterfall_key: str,
    waterfall_type: str,
    *,
    period: str | None = None,
    scenarios: tuple[str, ...] = ("Actual", "Budget", "Forecast"),
) -> list[str]:
    cur = bundle.currency
    detail = to_period(period or bundle.as_of_period)
    parts: list[str] = []
    for scenario in scenarios:
        amt = _wf(bundle, waterfall_key, waterfall_type, detail, scenario)
        if amt != 0 or waterfall_type in {"beginning_cash", "ending_cash", "beginning", "ending", "ending_arr"}:
            parts.append(f"{scenario} {fmt_money(amt, cur)}")
    return parts


def _waterfall_section_lines(
    bundle: ReportingBundle,
    title: str,
    waterfall_key: str,
    items: tuple[tuple[str, str], ...],
    *,
    period: str | None = None,
) -> list[str]:
    lines: list[str] = []
    seen_labels: set[str] = set()
    for wtype, label in items:
        if label in seen_labels:
            continue
        parts = _scenario_amount_parts(bundle, waterfall_key, wtype, period=period)
        if not parts:
            continue
        seen_labels.add(label)
        lines.append(f"  {label}: {'; '.join(parts)}")
    return [title, *lines] if lines else []


def _monthly_cash_bridge_table_prompt(
    cash_bridge_table: dict[str, dict[str, dict[str, float | None]]] | None,
    *,
    start_period: str,
    end_period: str,
    currency: str,
) -> str:
    """All months in the FY window — lets Copilot answer February, March, etc."""
    if not cash_bridge_table:
        return ""
    lines = [f"Monthly operational cash bridges ({start_period} → {end_period}):"]
    wrote = False
    for period in period_range(start_period, end_period):
        for scenario in ("Actual", "Budget", "Forecast"):
            period_row = (cash_bridge_table.get(scenario) or {}).get(period)
            if not period_row:
                continue
            parts: list[str] = []
            for field, label in _CASH_BRIDGE_TABLE_FIELDS:
                raw = period_row.get(field)
                if raw is None and field not in {"beginning_cash", "ending_cash"}:
                    continue
                parts.append(f"{label} {fmt_money(Decimal(str(raw or 0)), currency)}")
            if parts:
                lines.append(f"  {period} [{scenario}]: " + "; ".join(parts))
                wrote = True
    return "\n".join(lines) if wrote else ""


def cash_reconciliation_prompt_blob(
    bundle: ReportingBundle,
    *,
    cash_bridge_table: dict[str, dict[str, dict[str, float | None]]] | None = None,
    focus_period: str | None = None,
) -> str:
    """Operational cash bridge for focus month (or org close month)."""
    detail = to_period(focus_period or bundle.as_of_period)
    cur = bundle.currency
    section_lines = _waterfall_section_lines(
        bundle,
        f"Cash reconciliation ({detail}) — operational cash bridge:",
        "cash_flow",
        _CASH_BRIDGE_ITEMS,
        period=detail,
    )
    if len(section_lines) <= 1 and cash_bridge_table:
        for scenario in ("Actual", "Budget", "Forecast"):
            period_row = (cash_bridge_table.get(scenario) or {}).get(detail)
            if not period_row:
                continue
            scenario_lines: list[str] = []
            seen: set[str] = set()
            for field, label in _CASH_BRIDGE_TABLE_FIELDS:
                if label in seen:
                    continue
                raw = period_row.get(field)
                if raw is None and field not in {"beginning_cash", "ending_cash"}:
                    continue
                seen.add(label)
                scenario_lines.append(f"  {label} ({scenario}): {fmt_money(Decimal(str(raw or 0)), cur)}")
            if scenario_lines:
                if not section_lines:
                    section_lines = [f"Cash reconciliation ({detail}) — operational cash bridge:"]
                section_lines.extend(scenario_lines)

    if len(section_lines) <= 1:
        return ""

    beg = _wf(bundle, "cash_flow", "beginning_cash", detail, "Actual")
    end = _wf(bundle, "cash_flow", "ending_cash", detail, "Actual")
    if beg == 0 and cash_bridge_table:
        actual_row = (cash_bridge_table.get("Actual") or {}).get(detail) or {}
        beg = Decimal(str(actual_row.get("beginning_cash") or 0))
        end = Decimal(str(actual_row.get("ending_cash") or end))
    if beg and end:
        section_lines.append(
            f"  Reconciliation check: beginning {fmt_money(beg, cur)} → ending {fmt_money(end, cur)} "
            "(collections and disbursements above should bridge opening to closing)."
        )
    return "\n".join(section_lines)


def _decimal_amount(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _financial_statements_prompt(bundle: ReportingBundle, *, focus_period: str | None = None) -> str:
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if fs is None:
        return ""
    detail_period = to_period(focus_period or bundle.as_of_period)
    cur = bundle.currency
    lines = [f"Financial statements ({detail_period}):"]
    for stmt_label, stmt in (
        ("Income statement", fs.income_statement),
        ("Balance sheet", fs.balance_sheet),
        ("Cash flow statement", fs.cash_flow),
    ):
        stmt_lines: list[str] = []
        for row in stmt.rows:
            if str(row.period)[:7] != detail_period:
                continue
            if row.amount == 0:
                continue
            stmt_lines.append(f"  {row.line_item} ({row.scenario}): {fmt_money(row.amount, cur)}")
        if stmt_lines:
            lines.append(f"  {stmt_label}:")
            lines.extend(stmt_lines[:24])
    return "\n".join(lines) if len(lines) > 1 else ""


def _three_statement_prompt(
    ts_data: dict[str, Any] | None,
    as_of: str,
    cur: str,
    *,
    focus_period: str | None = None,
) -> str:
    if not ts_data:
        return ""
    detail_period = to_period(focus_period or as_of)
    lines = [f"Three-statement warehouse (detail month {detail_period}):"]
    for scenario in ("Actual", "Budget", "Forecast"):
        block = ts_data.get(scenario)
        if not isinstance(block, dict):
            continue
        is_row = (block.get("is") or {}).get(detail_period) or {}
        bs_row = (block.get("bs") or {}).get(detail_period) or {}
        cfs_row = (block.get("cfs") or {}).get(detail_period) or {}
        if not any((is_row, bs_row, cfs_row)):
            continue
        lines.append(f"  [{scenario}]")
        for label, row in (("IS", is_row), ("BS", bs_row), ("CFS", cfs_row)):
            if not row:
                continue
            parts = [
                f"{key} {fmt_money(_decimal_amount(val), cur)}"
                for key, val in sorted(row.items())
                if key != "is_actual" and val not in (None, 0, 0.0)
            ]
            if parts:
                lines.append(f"    {label}: " + "; ".join(parts[:18]))
    return "\n".join(lines) if len(lines) > 1 else ""


def _monthly_trends_prompt(bundle: ReportingBundle) -> str:
    cur = bundle.currency
    lines = [f"Monthly Actual trends ({bundle.start_period} → {bundle.as_of_period}):"]
    for period in period_range(bundle.start_period, bundle.as_of_period):
        ending_arr = _wf(bundle, "arr", "ending", period, "Actual") or _wf(
            bundle, "arr", "ending_arr", period, "Actual"
        )
        ending_cash = _wf(bundle, "cash_flow", "ending_cash", period, "Actual")
        ending_pipe = _wf(bundle, "pipeline", "ending_pipeline", period, "Actual")
        net_new = _wf(bundle, "arr", "new_business", period, "Actual") or _wf(
            bundle, "arr", "new_arr", period, "Actual"
        )
        if not any((ending_arr, ending_cash, ending_pipe, net_new)):
            continue
        lines.append(
            f"  {period}: ARR {fmt_money(ending_arr, cur)}; net new {fmt_money(net_new, cur)}; "
            f"cash {fmt_money(ending_cash, cur)}; pipeline {fmt_money(ending_pipe, cur)}"
        )
    return "\n".join(lines) if len(lines) > 1 else ""


def _headcount_prompt(bundle: ReportingBundle, *, focus_period: str | None = None) -> str:
    detail = to_period(focus_period or bundle.as_of_period)
    rows = [r for r in bundle.headcount if r.period == detail]
    if not rows:
        return ""
    lines = [f"Headcount ({detail}):"]
    for row in sorted(rows, key=lambda r: (r.scenario, r.department or ""))[:24]:
        lines.append(
            f"  {row.department or 'All'} ({row.scenario}): HC {int(row.headcount or 0)}; "
            f"open roles {int(row.open_roles or 0)}"
        )
    return "\n".join(lines)


def _marketing_prompt(bundle: ReportingBundle, *, focus_period: str | None = None) -> str:
    mkt = bundle.marketing_comparison
    if not mkt:
        return ""
    detail = to_period(focus_period or bundle.as_of_period)
    cur = bundle.currency
    lines = [f"GTM / marketing funnel ({detail}):"]
    for row in mkt.actual:
        if row.period != detail:
            continue
        lines.append(
            f"  Actual — MQL {int(row.mqls)}; SQL {int(row.sqls)}; SAL {int(row.sals)}; "
            f"opps created {int(row.opportunities_created)}; pipeline ARR created {fmt_money(row.pipeline_arr_created, cur)}; "
            f"closed won ARR {fmt_money(row.closed_won_arr, cur)}; spend {fmt_money(row.marketing_spend, cur)}"
        )
    for row in mkt.budget:
        if row.period != detail:
            continue
        lines.append(
            f"  Budget — MQL {int(row.mqls)}; pipeline ARR created {fmt_money(row.pipeline_arr_created, cur)}; "
            f"spend {fmt_money(row.marketing_spend, cur)}"
        )
    return "\n".join(lines) if len(lines) > 1 else ""


def parse_focus_period_from_question(
    question: str,
    *,
    default: str,
    start_period: str,
    end_period: str,
) -> str:
    """Infer YYYY-MM from the user question when they ask about a prior close month."""
    default_p = to_period(default)
    start_p = to_period(start_period)
    end_p = to_period(end_period)
    text = question.strip()

    iso = re.search(r"\b(20\d{2})-(0[1-9]|1[0-2])\b", text)
    if iso:
        candidate = iso.group(0)
        if start_p <= candidate <= end_p:
            return candidate

    for pattern in (
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})\b",
        r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(20\d{2})\b",
    ):
        for match in re.finditer(pattern, text, flags=re.I):
            month_token = match.group(1).lower().rstrip(".")
            year = match.group(2)
            month_num = _MONTH_NAME_TO_NUM.get(month_token) or _MONTH_ABBR_TO_NUM.get(month_token[:3])
            if not month_num:
                continue
            candidate = f"{year}-{month_num:02d}"
            if start_p <= candidate <= end_p:
                return candidate

    return default_p


def _is_ga_related(row) -> bool:
    blob = " ".join(
        str(getattr(row, field, "") or "")
        for field in ("department", "account", "account_group", "expense_type")
    ).lower()
    return any(hint in blob for hint in _GA_DEPT_HINTS)


def _monthly_is_opex_prompt(
    ts_data: dict[str, Any] | None,
    *,
    start_period: str,
    end_period: str,
    currency: str,
) -> str:
    if not ts_data:
        return ""
    lines = [f"Monthly income statement — opex & G&A ({start_period} → {end_period}):"]
    for period in period_range(start_period, end_period):
        act = ((ts_data.get("Actual") or {}).get("is") or {}).get(period) or {}
        bud = ((ts_data.get("Budget") or {}).get("is") or {}).get(period) or {}
        ga_a = _decimal_amount(act.get("ga"))
        ga_b = _decimal_amount(bud.get("ga"))
        rev_a = _decimal_amount(act.get("revenue"))
        rev_b = _decimal_amount(bud.get("revenue"))
        if not any((ga_a, ga_b, rev_a, rev_b)):
            continue
        ga_var = ga_a - ga_b if ga_a and ga_b else None
        var_txt = f"; G&A variance {fmt_money(ga_var, currency)}" if ga_var is not None else ""
        lines.append(
            f"  {period}: revenue actual {fmt_money(rev_a, currency)} vs budget {fmt_money(rev_b, currency)}; "
            f"G&A actual {fmt_money(ga_a, currency)} vs budget {fmt_money(ga_b, currency)}{var_txt}; "
            f"SM actual {fmt_money(_decimal_amount(act.get('sm')), currency)} vs budget "
            f"{fmt_money(_decimal_amount(bud.get('sm')), currency)}; "
            f"R&D actual {fmt_money(_decimal_amount(act.get('rd')), currency)} vs budget "
            f"{fmt_money(_decimal_amount(bud.get('rd')), currency)}"
        )
    return "\n".join(lines) if len(lines) > 1 else ""


def _gl_spend_prompt(bundle: ReportingBundle, *, focus_period: str | None = None) -> str:
    cur = bundle.currency
    if not bundle.gl_detail:
        return ""

    focus = to_period(focus_period or bundle.as_of_period)
    lines: list[str] = []

    ga_by_period: dict[str, Decimal] = {}
    for row in bundle.gl_detail:
        if row.scenario != "Actual" or not row.amount or not _is_ga_related(row):
            continue
        ga_by_period[row.period] = ga_by_period.get(row.period, Decimal("0")) + row.amount

    if ga_by_period:
        lines.append(f"G&A-related GL actuals by month ({bundle.start_period} → {bundle.as_of_period}):")
        for period in period_range(bundle.start_period, bundle.as_of_period):
            total = ga_by_period.get(period)
            if total:
                lines.append(f"  {period}: {fmt_money(total, cur)}")

    actual_rows = [
        r
        for r in bundle.gl_detail
        if r.period == focus and r.scenario == "Actual" and r.amount != 0
    ]
    if actual_rows:
        actual_rows.sort(key=lambda r: abs(r.amount), reverse=True)
        lines.append(f"GL actuals detail ({focus}, top lines — use for driver analysis):")
        for row in actual_rows[:25]:
            label = row.account or row.account_group or row.expense_type or row.department or "Line"
            dept = f" / {row.department}" if row.department else ""
            lines.append(f"  {label}{dept}: {fmt_money(row.amount, cur)}")
    elif focus != bundle.as_of_period:
        lines.append(
            f"GL actuals detail ({focus}): no GL rows in warehouse for this month "
            "(use Monthly income statement opex lines above for G&A actual vs budget)."
        )

    return "\n".join(lines)


def _pipeline_drilldown_prompt(bundle: ReportingBundle) -> str:
    if not bundle.pipeline_drilldown:
        return ""
    as_of = bundle.as_of_period
    cur = bundle.currency
    lines = [f"Pipeline opportunity drilldown ({as_of}):"]
    for movement, payload in bundle.pipeline_drilldown.items():
        opps = payload.get("opportunities") or []
        if not opps:
            continue
        lines.append(f"  {movement.replace('_', ' ')}: {len(opps)} opportunities")
        ranked = sorted(
            opps,
            key=lambda o: abs(_decimal_amount(o.get("arr_impact") or o.get("amount") or 0)),
            reverse=True,
        )
        for opp in ranked[:5]:
            name = opp.get("account_name") or opp.get("name") or opp.get("opportunity_name") or "Opportunity"
            amt = _decimal_amount(opp.get("arr_impact") or opp.get("amount") or opp.get("pipeline_arr"))
            if amt:
                lines.append(f"    - {name}: {fmt_money(amt, cur)}")
    return "\n".join(lines) if len(lines) > 1 else ""


def copilot_context_blob(
    bundle: ReportingBundle,
    *,
    cash_bridge_table: dict[str, dict[str, dict[str, float | None]]] | None = None,
    ts_data: dict[str, Any] | None = None,
    focus_period: str | None = None,
    max_chars: int = 32000,
) -> str:
    """Full warehouse context for SMPL Copilot Q&A across all board domains."""
    focus = to_period(focus_period or bundle.as_of_period)
    sections: list[str] = [
        metrics_prompt_blob(bundle),
        _monthly_trends_prompt(bundle),
        _monthly_is_opex_prompt(
            ts_data,
            start_period=bundle.start_period,
            end_period=bundle.as_of_period,
            currency=bundle.currency,
        ),
        _monthly_cash_bridge_table_prompt(
            cash_bridge_table,
            start_period=bundle.start_period,
            end_period=bundle.as_of_period,
            currency=bundle.currency,
        ),
        cash_reconciliation_prompt_blob(
            bundle,
            cash_bridge_table=cash_bridge_table,
            focus_period=focus,
        ),
        "\n".join(
            _waterfall_section_lines(
                bundle,
                f"ARR waterfall ({focus}):",
                "arr",
                _ARR_BRIDGE_ITEMS,
                period=focus,
            )
        ),
        "\n".join(
            _waterfall_section_lines(
                bundle,
                f"Pipeline waterfall ({focus}):",
                "pipeline",
                _PIPELINE_ITEMS,
                period=focus,
            )
        ),
        "\n".join(
            _waterfall_section_lines(
                bundle,
                f"Deferred revenue / GAAP bridge ({focus}):",
                "deferred_revenue",
                _DEFERRED_ITEMS,
                period=focus,
            )
        ),
        _financial_statements_prompt(bundle, focus_period=focus),
        _three_statement_prompt(
            ts_data,
            bundle.as_of_period,
            bundle.currency,
            focus_period=focus,
        ),
        _headcount_prompt(bundle, focus_period=focus),
        _marketing_prompt(bundle, focus_period=focus),
        _gl_spend_prompt(bundle, focus_period=focus),
        _pipeline_drilldown_prompt(bundle),
    ]
    if focus != bundle.as_of_period:
        sections.insert(
            1,
            f"Copilot focus month: {focus} (org close month is {bundle.as_of_period}). "
            "Answer using metrics for the focus month below.",
        )
    blob = "\n\n".join(section for section in sections if section and section.strip())
    if len(blob) <= max_chars:
        return blob
    return blob[:max_chars] + "\n\n[Context truncated — prioritize figures above for the question.]"


CFO_BOARD_NARRATIVE_SYSTEM = (
    "You are a seasoned SaaS CFO writing the Executive Takeaway for a board operating review. "
    "Evidence-only — use exact figures from the metrics provided. "
    "Write one flowing paragraph (4 sentences): specific dollars and bps; operational drivers (new business, "
    "expansion, margin, cash timing); one forward-looking risk or normalization; board-ready tone. "
    "No bullet points. Do not start with 'The data shows.' No generic consulting filler."
)


def enrich_slide_with_ai(
    bundle: ReportingBundle,
    slide_key: str,
    base: SlideCommentary,
) -> SlideCommentary:
    """LLM Key Takeaways for a single board slide (on-demand regenerate)."""
    from app.services.reporting.export.board_api_prompts import (
        BOARD_DECK_SLIDE_SYSTEM_PROMPT,
        board_deck_single_slide_user_message,
        format_key_takeaway_bullets,
        parse_board_deck_bullets_response,
        validate_and_trim_bullets,
    )
    from app.services.reporting.export.board_slide_commentary_payload import (
        BOARD_DECK_SLIDE_KEYS,
        build_single_slide_payload,
        slide_prompt_limits,
    )

    settings = get_settings()
    if not (settings.anthropic_api_key or settings.openai_api_key):
        return base

    if slide_key not in BOARD_DECK_SLIDE_KEYS:
        return _enrich_slide_with_ai_legacy(bundle, slide_key, base)

    try:
        client = build_commentary_llm_client()
        payload = build_single_slide_payload(bundle, slide_key)
        max_bullets, max_words, max_chars = slide_prompt_limits(slide_key)
        raw = client.generate(
            system_prompt=BOARD_DECK_SLIDE_SYSTEM_PROMPT,
            user_prompt=board_deck_single_slide_user_message(payload),
            max_tokens=2048,
        )
        bullets = parse_board_deck_bullets_response(raw, slide_key)
        bullets = validate_and_trim_bullets(
            bullets,
            max_bullets=max_bullets,
            max_words_per_bullet=max_words,
            max_chars_per_bullet=max_chars,
        )
        narrative = format_key_takeaway_bullets(bullets)
        if not narrative:
            return base
        return SlideCommentary(what_happened=narrative, bullets=bullets)
    except Exception:
        return base


def _enrich_slide_with_ai_legacy(
    bundle: ReportingBundle,
    slide_key: str,
    base: SlideCommentary,
) -> SlideCommentary:
    """Fallback narrative paragraph for non-board-deck slide keys."""
    try:
        client = build_commentary_llm_client()
        metrics_blob = metrics_prompt_blob(bundle)
        slide_label = slide_key.replace("_", " ")
        prompt = (
            f"{strategic_context_for_prompt()}\n\n"
            f"{requirements_prompt_block('board_slide_commentary')}\n\n"
            f"Board slide: {slide_label}.\n"
            f"Metrics:\n{metrics_blob}\n\n"
            'Respond with JSON only: {"narrative": "..."} — one paragraph, 4 sentences, board-ready.\n'
            "Use live metrics above; do not copy example numbers."
        )
        raw = client.generate(
            system_prompt=CFO_BOARD_NARRATIVE_SYSTEM,
            user_prompt=prompt,
            max_tokens=4096,
        )
        if not isinstance(raw, dict):
            return base
        narrative = str(raw.get("narrative") or raw.get("what_happened") or "").strip()
        if not narrative:
            return base
        return SlideCommentary(what_happened=narrative)
    except Exception:
        return base


def enrich_commentary_with_ai(bundle: ReportingBundle, slides: dict[str, SlideCommentary]) -> dict[str, SlideCommentary]:
    """LLM-enrich every narrative slide (full 17-slide board deck)."""
    from app.services.reporting.export.board_semantic_mappings import NARRATIVE_SLIDE_ORDER

    settings = get_settings()
    if not (settings.anthropic_api_key or settings.openai_api_key):
        return slides
    try:
        client = build_commentary_llm_client()
        slide_keys = [k for k in NARRATIVE_SLIDE_ORDER if k in slides]
        metrics_blob = copilot_context_blob(bundle)[:24000]
        key_list = ", ".join(slide_keys)
        prompt = (
            f"{strategic_context_for_prompt()}\n\n"
            f"{monthly_close_requirements_prompt()}\n\n"
            f"{requirements_prompt_block('mda_deck_pptx')}\n\n"
            f"Period: {bundle.period_label} ({bundle.as_of_period}). "
            f"Organization: {bundle.organization_name or 'SMPL'}.\n\n"
            f"Live metrics:\n{metrics_blob}\n\n"
            f"Write JSON with one object per slide key ({key_list}). "
            "Each slide object must include what_happened, why_it_happened, favorable, "
            "unfavorable, recommended_actions — 2-3 evidence-based sentences each. "
            "Connect cause→effect→leadership implication. No generic filler."
        )
        raw = client.generate(
            system_prompt=(
                "You are a SaaS CFO writing a board operating review deck. "
                "Evidence-only — cite exact figures from the metrics provided."
            ),
            user_prompt=prompt,
        )
        if not isinstance(raw, dict):
            return slides
        for key in slide_keys:
            block = raw.get(key)
            if not isinstance(block, dict):
                continue
            sc = slides[key]
            slides[key] = SlideCommentary(
                what_happened=str(block.get("what_happened") or sc.what_happened or "").strip(),
                why_it_happened=str(block.get("why_it_happened") or sc.why_it_happened or "").strip(),
                favorable=str(block.get("favorable") or sc.favorable or "").strip(),
                unfavorable=str(block.get("unfavorable") or sc.unfavorable or "").strip(),
                recommended_actions=str(
                    block.get("recommended_actions") or sc.recommended_actions or ""
                ).strip(),
                leadership_watch=str(block.get("leadership_watch") or sc.leadership_watch or "").strip(),
                impact=str(block.get("impact") or sc.impact or "").strip(),
            )
    except Exception:
        pass
    return slides


def build_all_slide_commentary(
    bundle: ReportingBundle,
    *,
    use_ai: bool = False,
) -> dict[str, SlideCommentary]:
    from app.services.reporting.export.board_semantic_mappings import NARRATIVE_SLIDE_ORDER

    out = {k: build_slide_commentary(bundle, k) for k in NARRATIVE_SLIDE_ORDER}
    if use_ai:
        out = enrich_commentary_with_ai(bundle, out)
    return out
