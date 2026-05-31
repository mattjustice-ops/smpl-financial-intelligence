"""Board-ready slide commentary: operational drivers + strategic context."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.core.config import get_settings
from app.services.board_package.package import fmt_money
from app.services.commentary.openai_client import build_openai_commentary_client
from app.services.reporting.export.board_metrics_snapshot import BoardMetricsSnapshot, build_metrics_snapshot
from app.services.reporting.export.company_context import strategic_context_for_prompt
from app.services.reporting.export.saas_semantic_reporting import (
    OpportunityMovementType,
    build_movement_attribution,
)
from app.services.reporting.export.schemas import ReportingBundle


@dataclass
class SlideCommentary:
    what_happened: str = ""
    why_it_happened: str = ""
    impact: str = ""
    favorable: str = ""
    unfavorable: str = ""
    recommended_actions: str = ""
    leadership_watch: str = ""

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


def enrich_commentary_with_ai(bundle: ReportingBundle, slides: dict[str, SlideCommentary]) -> dict[str, SlideCommentary]:
    if not get_settings().openai_api_key:
        return slides
    try:
        m = build_metrics_snapshot(bundle)
        client = build_openai_commentary_client()
        metrics_blob = (
            f"ARR {fmt_money(m.ending_arr, m.currency)}, net new {fmt_money(m.net_new_arr, m.currency)}, "
            f"pipeline created {fmt_money(m.pipeline_created, m.currency)}, churn {fmt_money(m.churn, m.currency)}, "
            f"cash {fmt_money(m.cash_actual, m.currency)}."
        )
        prompt = (
            f"{strategic_context_for_prompt()}\n\n"
            f"Period: {bundle.period_label}. Metrics: {metrics_blob}\n"
            "Write JSON keys executive_summary, gtm_performance, pipeline_health, arr_waterfall, cash_forecast — "
            "each with what_happened, why_it_happened, favorable, unfavorable, recommended_actions. "
            "2-3 sentences each. Connect cause→effect→leadership implication. No generic filler."
        )
        raw = client.generate(
            system_prompt="You are a SaaS CFO writing a board operating review. Evidence-only.",
            user_prompt=prompt,
        )
        for key in raw:
            if key not in slides or not isinstance(raw[key], dict):
                continue
            block = raw[key]
            sc = slides[key]
            slides[key] = SlideCommentary(
                what_happened=str(block.get("what_happened", sc.what_happened)),
                why_it_happened=str(block.get("why_it_happened", sc.why_it_happened)),
                favorable=str(block.get("favorable", sc.favorable)),
                unfavorable=str(block.get("unfavorable", sc.unfavorable)),
                recommended_actions=str(block.get("recommended_actions", sc.recommended_actions)),
                leadership_watch=sc.leadership_watch,
                impact=sc.impact,
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
