"""12-slide SaaS MD&A board deck from live reporting bundle."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.board_package.package import fmt_money, fmt_pct
from app.services.board_package.schemas import BoardPackage, SlideContent, TableSpec
from app.services.reporting.export.commentary_engine import _fmt_money
from app.services.reporting.export.schemas import ReportingBundle
from app.services.reporting.period_utils import to_period


def _wf_amount(bundle: ReportingBundle, key: str, wtype: str, period: str, scenario: str = "Actual") -> Decimal:
    rows = bundle.comparison_waterfalls.get(key) or []
    for row in rows:
        if row.period == period and row.waterfall_type == wtype and row.scenario == scenario:
            return row.amount
    wf = bundle.executive_flow.waterfalls.get(key)
    if wf:
        for row in wf.rows:
            if row.period == period and row.waterfall_type == wtype:
                return row.amount
    return Decimal("0")


def _optional_table(headers: list[str], rows: list[list[str]] | None) -> TableSpec | None:
    """Build a table only when there are data rows (Pydantic rejects rows=None)."""
    if not rows:
        return None
    return TableSpec(headers=headers, rows=rows)


def _commentary_for(bundle: ReportingBundle, section: str) -> str:
    fields = bundle.mda_commentary or bundle.commentary_fields
    for f in fields:
        if section.lower() in f.section.lower():
            parts = [f.what_changed, f.variance_driver, f.favorable, f.unfavorable]
            return " ".join(p for p in parts if p).strip()
    return ""


def _slide_exec_summary(bundle: ReportingBundle) -> SlideContent:
    as_of = bundle.as_of_period
    arr = _wf_amount(bundle, "arr", "ending_arr", as_of) or _wf_amount(bundle, "arr", "ending", as_of)
    revenue = Decimal("0")
    ebitda = Decimal("0")
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if fs:
        for row in fs.income_statement.rows:
            p = to_period(str(row.period))
            if p != as_of or row.scenario != "Actual":
                continue
            if "revenue" in row.line_item.lower() and "deferred" not in row.line_item.lower():
                revenue = row.amount
            if "ebitda" in row.line_item.lower():
                ebitda = row.amount
    cash = _wf_amount(bundle, "cash_flow", "ending_cash", as_of)
    pipeline_end = _wf_amount(bundle, "pipeline", "ending_pipeline", as_of)
    closed_won = _wf_amount(bundle, "pipeline", "closed_won", as_of)
    coverage = (pipeline_end / closed_won) if closed_won else None
    hc = sum((r.headcount or Decimal("0")) for r in bundle.headcount if r.period == as_of and r.scenario == "Actual")

    bullets = [
        f"ARR: {fmt_money(arr, bundle.currency)}",
        f"Revenue (CM Actual): {fmt_money(revenue, bundle.currency)}",
        f"EBITDA (CM Actual): {fmt_money(ebitda, bundle.currency)}",
        f"Cash: {fmt_money(cash, bundle.currency)}",
        f"Ending pipeline: {fmt_money(pipeline_end, bundle.currency)}",
    ]
    if coverage:
        bullets.append(f"Pipeline coverage: {fmt_pct(coverage)}")
    if hc:
        bullets.append(f"Headcount: {int(hc):,}")

    risks = [g.message for g in bundle.data_gaps if g.status != "ok"][:3]
    return SlideContent(
        slide_id="executive_summary",
        title="Executive Summary",
        subtitle=f"{bundle.organization_name or 'Organization'} — {bundle.period_label}",
        bullets=bullets,
        narrative=_commentary_for(bundle, "Executive") or _commentary_for(bundle, "SaaS MD&A"),
        table=_optional_table(
            ["Risk / gap", "Action"],
            [[r, "Review data gap"] for r in risks],
        ),
    )


def _slide_mda_summary(bundle: ReportingBundle) -> SlideContent:
    narrative = _commentary_for(bundle, "SaaS MD&A") or _commentary_for(bundle, "Income")
    return SlideContent(
        slide_id="mda_summary",
        title="SaaS MD&A Summary",
        subtitle=bundle.period_label,
        bullets=[
            f"What changed: {_commentary_for(bundle, 'MRR') or _commentary_for(bundle, 'ARR')}",
            f"Pipeline: {_commentary_for(bundle, 'Pipeline')}",
            f"Cash: {_commentary_for(bundle, 'Cash')}",
        ],
        narrative=narrative or "Review Excel Variance Commentary for section drivers.",
    )


def _slide_gtm(bundle: ReportingBundle) -> SlideContent:
    as_of = bundle.as_of_period
    mkt = bundle.marketing_comparison
    rows: list[list[str]] = []
    if mkt:
        for row in mkt.actual:
            if row.period != as_of:
                continue
            rows.append(
                [
                    row.marketing_channel or "All",
                    _fmt_money(row.marketing_spend),
                    str(int(row.mqls or 0)),
                    str(int(row.sqls or 0)),
                    _fmt_money(row.pipeline_arr_created),
                ]
            )
    return SlideContent(
        slide_id="gtm_performance",
        title="GTM Performance",
        subtitle="Marketing pipeline supports GTM only — pipeline waterfall is source of truth for coverage",
        table=_optional_table(
            ["Channel", "Spend", "MQLs", "SQLs", "Pipeline Created"],
            rows[:8],
        ),
        bullets=[] if rows else ["Upload marketing performance CSVs for channel detail."],
    )


def _slide_pipeline(bundle: ReportingBundle) -> SlideContent:
    as_of = bundle.as_of_period
    types = (
        "beginning_pipeline",
        "pipeline_created",
        "closed_won",
        "closed_lost",
        "slipped_pipeline",
        "ending_pipeline",
    )
    rows = [[t.replace("_", " ").title(), fmt_money(_wf_amount(bundle, "pipeline", t, as_of), bundle.currency)] for t in types]
    return SlideContent(
        slide_id="pipeline_health",
        title="Pipeline Health",
        subtitle=_commentary_for(bundle, "Pipeline") or bundle.period_label,
        table=TableSpec(headers=["Movement", "Amount"], rows=rows),
    )


def _slide_opportunities(bundle: ReportingBundle) -> SlideContent:
    rows: list[list[str]] = []
    for movement, payload in bundle.pipeline_drilldown.items():
        for opp in (payload.get("opportunities") or [])[:4]:
            rows.append(
                [
                    movement,
                    opp.get("opportunity_name") or opp.get("customer_name") or "",
                    opp.get("region") or "",
                    opp.get("stage") or "",
                    fmt_money(Decimal(str(opp.get("arr_impact") or 0)), bundle.currency),
                ]
            )
    for opp in bundle.opportunity_attribution[:6]:
        rows.append(
            [
                opp.waterfall_type,
                opp.opportunity_name or opp.customer_name or "",
                opp.region or "",
                opp.stage or "",
                fmt_money(opp.arr_impact, bundle.currency),
            ]
        )
    return SlideContent(
        slide_id="opportunity_drilldown",
        title="Opportunity Drilldown",
        subtitle="Trace pipeline and ARR movements to source opportunities",
        table=_optional_table(
            ["Movement", "Opportunity", "Region", "Stage", "ARR"],
            rows[:12],
        ),
        bullets=[] if rows else ["No opportunity drilldown loaded for this period."],
    )


def _slide_arr_waterfall(bundle: ReportingBundle) -> SlideContent:
    as_of = bundle.as_of_period
    types = ("beginning_arr", "beginning", "new_arr", "new_business", "expansion_arr", "expansion", "contraction_arr", "contraction", "churn_arr", "churn", "reactivation_arr", "reactivation", "ending_arr", "ending")
    seen: set[str] = set()
    rows: list[list[str]] = []
    for t in types:
        if t in seen:
            continue
        amt = _wf_amount(bundle, "arr", t, as_of)
        if amt == 0 and t not in {"ending_arr", "ending", "beginning_arr", "beginning"}:
            continue
        label = t.replace("_arr", "").replace("_", " ").title()
        if label in seen:
            continue
        seen.add(label)
        rows.append([label, fmt_money(amt, bundle.currency)])
    return SlideContent(
        slide_id="arr_waterfall",
        title="MRR / ARR Waterfall",
        subtitle=_commentary_for(bundle, "MRR") or "MRR waterfall is source of truth for ARR movement",
        table=_optional_table(["Component", "ARR"], rows),
        bullets=[] if rows else ["Load MRR waterfall CSVs for ARR bridge detail."],
    )


def _slide_gaap_revenue(bundle: ReportingBundle) -> SlideContent:
    deferred = bundle.executive_flow.waterfalls.get("deferred_revenue")
    as_of = bundle.as_of_period
    rows: list[list[str]] = []
    if deferred:
        for row in sorted(deferred.rows, key=lambda x: x.line_item_order):
            if row.period == as_of:
                rows.append([row.line_item, fmt_money(row.amount, bundle.currency)])
    return SlideContent(
        slide_id="gaap_revenue_forecast",
        title="GAAP Revenue Forecast",
        subtitle="Deferred revenue waterfall — billings and recognition source of truth",
        table=_optional_table(["Component", "Amount"], rows[:14]),
        narrative=_commentary_for(bundle, "Income") or _commentary_for(bundle, "Revenue"),
    )


def _slide_cash(bundle: ReportingBundle) -> SlideContent:
    as_of = bundle.as_of_period
    types = (
        "beginning_cash",
        "cash_collections",
        "collections",
        "payroll_cash_out",
        "vendor_cash_out",
        "commission_cash_out",
        "capex",
        "financing",
        "ending_cash",
    )
    rows = [[t.replace("_", " ").title(), fmt_money(_wf_amount(bundle, "cash_flow", t, as_of), bundle.currency)] for t in types]
    return SlideContent(
        slide_id="cash_forecast",
        title="Cash Forecast",
        subtitle=_commentary_for(bundle, "Cash"),
        table=TableSpec(headers=["Line", "Amount"], rows=rows),
        bullets=["Cash flow bridge ending cash must tie to balance sheet cash (Validation slide)."],
    )


def _slide_headcount(bundle: ReportingBundle) -> SlideContent:
    rows = [
        [r.department or "All", r.scenario, str(int(r.headcount or 0)), str(int(r.open_roles or 0))]
        for r in bundle.headcount
        if r.period == bundle.as_of_period
    ][:12]
    return SlideContent(
        slide_id="headcount_hiring",
        title="Headcount & Hiring Plan",
        subtitle=bundle.period_label,
        table=_optional_table(["Department", "Scenario", "HC", "Open Roles"], rows),
        bullets=[] if rows else ["Upload headcount plan CSVs for hiring detail."],
    )


def _slide_department_spend(bundle: ReportingBundle) -> SlideContent:
    from collections import defaultdict

    agg: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in bundle.gl_detail:
        if row.period != bundle.as_of_period or row.scenario != "Actual":
            continue
        dept = row.department or "Unassigned"
        agg[dept] += row.amount
    rows = [[d, fmt_money(v, bundle.currency)] for d, v in sorted(agg.items(), key=lambda x: -abs(x[1]))[:10]]
    return SlideContent(
        slide_id="department_spend",
        title="Department Spend / P&L",
        subtitle="Semantic GL roll-up by department",
        table=_optional_table(["Department", "Actual"], rows),
        bullets=[] if rows else ["Upload GL actuals for department spend."],
    )


def _slide_risks(bundle: ReportingBundle) -> SlideContent:
    bullets = [g.message for g in bundle.data_gaps if g.status != "ok"]
    for f in bundle.mda_commentary or bundle.commentary_fields:
        if f.leadership_attention:
            bullets.append(f.leadership_attention)
    if bundle.validation.failed_count:
        bullets.insert(0, f"{bundle.validation.failed_count} validation check(s) failed — do not distribute until resolved.")
    return SlideContent(
        slide_id="risks_opportunities",
        title="Risks & Opportunities",
        subtitle=bundle.period_label,
        bullets=bullets[:8] or ["No material gaps flagged."],
    )


def _slide_validation(bundle: ReportingBundle) -> SlideContent:
    rows = [
        [
            c.validation_name,
            c.status,
            str(c.expected_value) if c.expected_value is not None else "",
            str(c.actual_value) if c.actual_value is not None else "",
            str(c.variance) if c.variance is not None else "",
            ", ".join(c.source_tables_used or []),
        ]
        for c in bundle.validation.checks[:18]
    ]
    return SlideContent(
        slide_id="validation",
        title="Validation / Data Quality",
        subtitle=f"Overall: {bundle.validation.status.upper()} — {bundle.validation.failed_count} failed",
        table=_optional_table(
            ["Check", "Status", "Expected", "Actual", "Variance", "Source"],
            rows,
        ),
        bullets=[
            "MRR waterfall ties (ARR source of truth)",
            "Pipeline waterfall ties (not marketing_pipeline)",
            "Cash bridge ↔ balance sheet cash",
            "Deferred revenue waterfall ties",
        ],
    )


def build_mda_board_package(bundle: ReportingBundle) -> BoardPackage:
    slides = [
        _slide_exec_summary(bundle),
        _slide_mda_summary(bundle),
        _slide_gtm(bundle),
        _slide_pipeline(bundle),
        _slide_opportunities(bundle),
        _slide_arr_waterfall(bundle),
        _slide_gaap_revenue(bundle),
        _slide_cash(bundle),
        _slide_headcount(bundle),
        _slide_department_spend(bundle),
        _slide_risks(bundle),
        _slide_validation(bundle),
    ]
    as_of = bundle.as_of_period
    prepared = date(int(as_of[:4]), int(as_of[5:7]), 1)
    return BoardPackage(
        organization_name=bundle.organization_name or "Organization",
        period_label=bundle.period_label,
        prepared_for="Board of Directors",
        prepared_date=prepared,
        currency=bundle.currency,
        slides=slides,
    )
