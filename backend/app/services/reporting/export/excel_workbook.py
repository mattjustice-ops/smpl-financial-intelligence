"""FP&A-style Excel workbook export (periods across columns, Actual vs Budget)."""

from __future__ import annotations

import io
import re
from decimal import Decimal
from typing import Any

_INVALID_EXCEL_SHEET_CHARS = re.compile(r"[\[\]:*?/\\]")

from app.services.reporting.export.comparison_pivot import pivot_statement_wide, pivot_waterfall_wide
from app.services.reporting.export.excel_wide import (
    _write_period_header_row,
    _write_wide_amounts,
    layout_for_rows,
    subtitle_for_bundle,
)
from app.services.reporting.export.period_column_layout import (
    build_display_by_period,
    build_wide_period_layout,
    export_periods_for_bundle,
    scenario_presence_by_period,
)
from app.services.reporting.export.semantic_model import classify_gl_row
from app.services.reporting.export.schemas import ReportingBundle
from app.services.reporting.period_utils import to_period


def sanitize_excel_sheet_name(name: str, *, used: set[str] | None = None) -> str:
    """Excel tab names: max 31 chars; no [] : * ? / \\."""
    base = _INVALID_EXCEL_SHEET_CHARS.sub("-", name).strip() or "Sheet"
    base = base[:31]
    if used is None:
        return base
    candidate = base
    n = 2
    while candidate in used:
        suffix = f" ({n})"
        candidate = f"{base[: 31 - len(suffix)]}{suffix}"
        n += 1
    used.add(candidate)
    return candidate


def _import_xlsxwriter():
    try:
        import xlsxwriter
    except ImportError as exc:
        raise ImportError(
            "xlsxwriter is required for Excel exports. "
            "Activate your backend venv and run: pip install xlsxwriter==3.2.9"
        ) from exc
    return xlsxwriter


class _Formats:
    def __init__(self, workbook: Any) -> None:
        x = workbook
        self.header = x.add_format(
            {"bold": True, "bg_color": "#1F497D", "font_color": "#FFFFFF", "border": 1}
        )
        self.subheader = x.add_format({"bold": True, "bg_color": "#DCE6F1", "border": 1})
        self.currency = x.add_format({"num_format": "$#,##0", "border": 1})
        self.pct = x.add_format({"num_format": "0.0%", "border": 1})
        self.text = x.add_format({"border": 1, "text_wrap": True})
        self.var_fav = x.add_format({"num_format": "$#,##0", "font_color": "#006100", "bg_color": "#C6EFCE"})
        self.var_unfav = x.add_format({"num_format": "$#,##0", "font_color": "#9C0006", "bg_color": "#FFC7CE"})
        self.title = x.add_format({"bold": True, "font_size": 14})


def _write_title(ws, title: str, subtitle: str, fmt: _Formats) -> int:
    ws.write(0, 0, title, fmt.title)
    ws.write(1, 0, subtitle, fmt.text)
    return 3


def _waterfall_rows(bundle: ReportingBundle, waterfall_key: str):
    if bundle.comparison_waterfalls.get(waterfall_key):
        return bundle.comparison_waterfalls[waterfall_key]
    wf = bundle.executive_flow.waterfalls.get(waterfall_key)
    return wf.rows if wf else []


def _financial_block(bundle: ReportingBundle, statement_key: str):
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    if fs is None:
        return None
    return getattr(fs, statement_key)


def _write_waterfall_sheet(
    ws,
    bundle: ReportingBundle,
    waterfall_key: str,
    sheet_title: str,
    fmt: _Formats,
    *,
    type_filter: set[str] | None = None,
) -> None:
    row0 = _write_title(ws, sheet_title, subtitle_for_bundle(bundle), fmt)
    rows = _waterfall_rows(bundle, waterfall_key)
    if type_filter:
        rows = [
            r
            for r in rows
            if r.waterfall_type in type_filter or any(token in r.waterfall_type for token in type_filter)
        ]
    if not rows:
        ws.write(row0, 0, "No data — see Data Sources tab for required CSV tables.", fmt.text)
        return
    periods, layout, presence = layout_for_rows(bundle, rows, label_column_count=1)
    _write_period_header_row(ws, row0, ["Line Item"], layout, fmt)
    ws.freeze_panes(row0 + 1, 1)
    wide = pivot_waterfall_wide(rows, periods)
    r = row0 + 1
    for item in wide:
        display = build_display_by_period(item["by_period"], periods, presence, bundle.as_of_period)
        ws.write(r, 0, item["line_item"], fmt.text)
        _write_wide_amounts(ws, r, 1, layout, display, fmt, as_of_period=bundle.as_of_period)
        r += 1
    ws.set_column(0, 0, 36)


def _write_statement_sheet(ws, bundle: ReportingBundle, statement_key: str, title: str, fmt: _Formats) -> None:
    row0 = _write_title(ws, title, subtitle_for_bundle(bundle), fmt)
    block = _financial_block(bundle, statement_key)
    if block is None or not block.rows:
        ws.write(row0, 0, "Upload Actual/Budget/Forecast statement CSVs — see Data Sources tab.", fmt.text)
        return
    periods, layout, presence = layout_for_rows(bundle, block.rows, label_column_count=2)
    _write_period_header_row(ws, row0, ["Section", "Line Item"], layout, fmt)
    ws.freeze_panes(row0 + 1, 2)
    wide = pivot_statement_wide(block.rows, periods)
    r = row0 + 1
    for item in wide:
        display = build_display_by_period(item["by_period"], periods, presence, bundle.as_of_period)
        ws.write(r, 0, item["section"], fmt.text)
        ws.write(r, 1, item["line_item"], fmt.text)
        _write_wide_amounts(ws, r, 2, layout, display, fmt, as_of_period=bundle.as_of_period)
        r += 1
    ws.set_column(1, 1, 36)


def _write_kpi_scorecard(ws, bundle: ReportingBundle, fmt: _Formats) -> None:
    row0 = _write_title(ws, "KPI Scorecard", subtitle_for_bundle(bundle), fmt)
    arr = _waterfall_rows(bundle, "arr")
    fs = bundle.comparison_financial_statements or bundle.financial_statements
    all_rows = list(arr)
    if fs:
        all_rows.extend(fs.income_statement.rows)

    periods, layout, presence = layout_for_rows(bundle, all_rows, label_column_count=1)
    _write_period_header_row(ws, row0, ["Metric"], layout, fmt)
    ws.freeze_panes(row0 + 1, 1)
    r = row0 + 1

    def write_waterfall_metric(label: str, wtypes: tuple[str, ...]) -> None:
        nonlocal r
        for wtype in wtypes:
            wide = pivot_waterfall_wide([row for row in arr if row.waterfall_type == wtype], periods)
            if not wide:
                continue
            display = build_display_by_period(wide[0]["by_period"], periods, presence, bundle.as_of_period)
            ws.write(r, 0, label, fmt.text)
            _write_wide_amounts(ws, r, 1, layout, display, fmt, as_of_period=bundle.as_of_period)
            r += 1
            return

    def write_fs_metric(label: str, needle: str) -> None:
        nonlocal r
        if not fs:
            return
        by_period = {
            p: {"actual": Decimal("0"), "budget": Decimal("0"), "forecast": Decimal("0")} for p in periods
        }
        for row in fs.income_statement.rows:
            p = to_period(str(row.period))
            if p not in by_period or needle not in row.line_item.lower():
                continue
            key = row.scenario.lower()
            if key in by_period[p]:
                by_period[p][key] = row.amount
        if not any(v["actual"] or v["budget"] for v in by_period.values()):
            return
        display = build_display_by_period(by_period, periods, presence, bundle.as_of_period)
        ws.write(r, 0, label, fmt.text)
        _write_wide_amounts(ws, r, 1, layout, display, fmt, as_of_period=bundle.as_of_period)
        r += 1

    if arr:
        write_waterfall_metric("Ending ARR", ("ending_arr", "ending"))
        write_waterfall_metric("New ARR", ("new_arr", "new_business"))
    if fs:
        write_fs_metric("Revenue", "revenue")
        write_fs_metric("EBITDA", "ebitda")


def _commentary_fields(bundle: ReportingBundle) -> list:
    if bundle.mda_commentary:
        return bundle.mda_commentary
    return bundle.commentary_fields


def _write_revenue_forecast_sheet(ws, bundle: ReportingBundle, fmt: _Formats) -> None:
    """GAAP revenue bridge from deferred revenue waterfall (source of truth)."""
    _write_waterfall_sheet(
        ws,
        bundle,
        "deferred_revenue",
        "Revenue Forecast",
        fmt,
        type_filter={"revenue_recognized", "total_gaap_revenue", "deferred", "beginning", "ending"},
    )


def _write_bookings_forecast_sheet(ws, bundle: ReportingBundle, fmt: _Formats) -> None:
    _write_waterfall_sheet(
        ws,
        bundle,
        "deferred_revenue",
        "Bookings Forecast",
        fmt,
        type_filter={"new_billings", "billings", "renewal", "expansion"},
    )


def _write_department_spend_sheet(ws, bundle: ReportingBundle, fmt: _Formats) -> None:
    row0 = _write_title(ws, "Department Spend / P&L", subtitle_for_bundle(bundle), fmt)
    headers = [
        "Period",
        "Department",
        "Account Group",
        "Expense Type",
        "Statement",
        "Section",
        "Actual",
        "Budget",
        "Commentary",
        "Owner",
    ]
    for col, h in enumerate(headers):
        ws.write(row0, col, h, fmt.header)
    ws.freeze_panes(row0 + 1, 2)
    if not bundle.gl_detail:
        ws.write(row0 + 1, 0, "Upload GL actuals with department and account group mappings.", fmt.text)
        return

    agg: dict[tuple[str, str, str, str], dict[str, Decimal]] = {}
    for row in bundle.gl_detail:
        tags = classify_gl_row(
            account=row.account,
            department=row.department,
            account_group=row.account_group,
            expense_type=row.expense_type,
            amount=row.amount,
        )
        key = (row.period, tags.department, tags.account_group, tags.expense_type)
        bucket = agg.setdefault(key, {"Actual": Decimal("0"), "Budget": Decimal("0")})
        scen = row.scenario if row.scenario in bucket else "Actual"
        bucket[scen] = bucket.get(scen, Decimal("0")) + row.amount

    r = row0 + 1
    for (period, dept, group, etype), amounts in sorted(agg.items()):
        tags = classify_gl_row(account=None, department=dept, account_group=group, expense_type=etype, amount=amounts["Actual"])
        ws.write(r, 0, period, fmt.text)
        ws.write(r, 1, dept, fmt.text)
        ws.write(r, 2, group, fmt.text)
        ws.write(r, 3, etype, fmt.text)
        ws.write(r, 4, tags.statement_category, fmt.text)
        ws.write(r, 5, tags.financial_section, fmt.text)
        if amounts.get("Actual"):
            ws.write(r, 6, float(amounts["Actual"]), fmt.currency)
        if amounts.get("Budget"):
            ws.write(r, 7, float(amounts["Budget"]), fmt.currency)
        r += 1


def _write_marketing_sheet(ws, bundle: ReportingBundle, fmt: _Formats) -> None:
    row0 = _write_title(ws, "Marketing Performance", subtitle_for_bundle(bundle), fmt)
    mkt = bundle.marketing_comparison
    if mkt is None:
        ws.write(row0, 0, "Upload actual/budget/forecast marketing pipeline CSVs.", fmt.text)
        return

    periods = export_periods_for_bundle(bundle.start_period, bundle.end_period, bundle.as_of_period)
    presence = {p: {"actual": False, "budget": False, "forecast": False} for p in periods}
    for row in mkt.actual:
        if row.period in presence:
            presence[row.period]["actual"] = True
    for row in mkt.budget:
        if row.period in presence:
            presence[row.period]["budget"] = True
    for row in mkt.forecast:
        if row.period in presence:
            presence[row.period]["forecast"] = True
    layout = build_wide_period_layout(periods, presence, as_of_period=bundle.as_of_period)
    layout.label_column_count = 2
    _write_period_header_row(ws, row0, ["Channel", "Metric"], layout, fmt)
    ws.freeze_panes(row0 + 1, 2)

    channels = sorted(
        {row.marketing_channel for row in (mkt.actual + mkt.budget + mkt.forecast) if row.marketing_channel}
    ) or [None]

    def values_for(period: str, channel, attr: str) -> dict[str, Decimal]:
        out = {"actual": Decimal("0"), "budget": Decimal("0"), "forecast": Decimal("0")}

        def pick(pool, scen: str) -> Decimal:
            for row in pool:
                if row.period != period:
                    continue
                if channel is not None and row.marketing_channel != channel:
                    continue
                return getattr(row, attr, Decimal("0"))
            return Decimal("0")

        out["actual"] = pick(mkt.actual, "Actual")
        out["budget"] = pick(mkt.budget, "Budget")
        out["forecast"] = pick(mkt.forecast, "Forecast")
        return out

    r = row0 + 1
    for channel in channels:
        for metric, attr, is_currency in (
            ("Marketing Spend", "marketing_spend", True),
            ("MQLs", "mqls", False),
            ("SQLs", "sqls", False),
            ("Pipeline ARR Created", "pipeline_arr_created", True),
        ):
            raw_by = {p: values_for(p, channel, attr) for p in periods}
            if not any(v["actual"] or v["budget"] or v["forecast"] for v in raw_by.values()):
                continue
            display = build_display_by_period(raw_by, periods, presence, bundle.as_of_period)
            ws.write(r, 0, channel or "All", fmt.text)
            ws.write(r, 1, metric, fmt.text)
            _write_wide_amounts(ws, r, 2, layout, display, fmt, use_currency=is_currency, as_of_period=bundle.as_of_period)
            r += 1


def _write_gl_sheet(ws, bundle: ReportingBundle, fmt: _Formats) -> None:
    row0 = _write_title(ws, "GL Detail by Department", bundle.period_label, fmt)
    headers = [
        "Scenario",
        "Period",
        "Department",
        "Account",
        "Account Group",
        "Expense Type",
        "Amount",
        "Commentary",
        "Owner",
    ]
    for col, h in enumerate(headers):
        ws.write(row0, col, h, fmt.header)
    ws.freeze_panes(row0 + 1, 3)
    r = row0 + 1
    for row in sorted(bundle.gl_detail, key=lambda x: (x.scenario, x.department or "", x.period)):
        ws.write(r, 0, row.scenario, fmt.text)
        ws.write(r, 1, row.period, fmt.text)
        ws.write(r, 2, row.department or "", fmt.text)
        ws.write(r, 3, row.account or "", fmt.text)
        ws.write(r, 4, row.account_group or "", fmt.text)
        ws.write(r, 5, row.expense_type or "", fmt.text)
        ws.write(r, 6, float(row.amount), fmt.currency)
        r += 1


def _write_headcount_sheet(ws, bundle: ReportingBundle, fmt: _Formats) -> None:
    row0 = _write_title(ws, "Headcount & Hiring", bundle.period_label, fmt)
    headers = [
        "Scenario",
        "Period",
        "Department",
        "Headcount",
        "Open Roles",
        "Hiring Plan",
        "Commentary",
        "Owner",
    ]
    for col, h in enumerate(headers):
        ws.write(row0, col, h, fmt.header)
    ws.freeze_panes(row0 + 1, 2)
    r = row0 + 1
    for row in bundle.headcount:
        ws.write(r, 0, row.scenario, fmt.text)
        ws.write(r, 1, row.period, fmt.text)
        ws.write(r, 2, row.department or "", fmt.text)
        if row.headcount is not None:
            ws.write(r, 3, float(row.headcount), fmt.currency)
        if row.open_roles is not None:
            ws.write(r, 4, float(row.open_roles), fmt.currency)
        if row.hiring_plan is not None:
            ws.write(r, 5, float(row.hiring_plan), fmt.currency)
        r += 1


def _write_opportunity_sheet(ws, bundle: ReportingBundle, fmt: _Formats) -> None:
    row0 = _write_title(ws, "Opportunity Drilldown", bundle.period_label, fmt)
    headers = [
        "Movement",
        "Opportunity",
        "Customer",
        "Owner",
        "Region",
        "Stage",
        "Close Date",
        "Contract Start",
        "Billing Cadence",
        "Payment Terms",
        "ARR Impact",
        "Commentary",
    ]
    for col, h in enumerate(headers):
        ws.write(row0, col, h, fmt.header)
    ws.freeze_panes(row0 + 1, 1)
    r = row0 + 1
    for movement, payload in bundle.pipeline_drilldown.items():
        for opp in payload.get("opportunities") or []:
            ws.write(r, 0, movement, fmt.text)
            ws.write(r, 1, opp.get("opportunity_name") or opp.get("opportunity_id") or "", fmt.text)
            ws.write(r, 2, opp.get("customer_name") or "", fmt.text)
            ws.write(r, 3, opp.get("owner") or "", fmt.text)
            ws.write(r, 4, opp.get("region") or "", fmt.text)
            ws.write(r, 5, opp.get("stage") or "", fmt.text)
            ws.write(r, 6, opp.get("close_date") or "", fmt.text)
            ws.write(r, 7, opp.get("contract_start_date") or "", fmt.text)
            ws.write(r, 8, opp.get("billing_cadence") or "", fmt.text)
            ws.write(r, 9, opp.get("payment_terms") or "", fmt.text)
            ws.write(r, 10, float(opp.get("arr_impact") or 0), fmt.currency)
            r += 1


def _write_commentary_sheet(ws, bundle: ReportingBundle, fmt: _Formats) -> None:
    row0 = _write_title(
        ws,
        "Variance Commentary",
        f"{subtitle_for_bundle(bundle)} — Forecast columns appear only for open months or close-month actual vs forecast.",
        fmt,
    )
    headers = [
        "Section",
        "Metric Context (from API)",
        "What Changed?",
        "Variance Driver",
        "Favorable",
        "Unfavorable",
        "Leadership Attention",
        "Recommended Actions",
        "Owner",
        "Source",
    ]
    for col, h in enumerate(headers):
        ws.write(row0, col, h, fmt.header)
    ws.freeze_panes(row0 + 1, 1)
    r = row0 + 1
    for field in _commentary_fields(bundle):
        ws.write(r, 0, field.section, fmt.text)
        ws.write(r, 1, field.metric_context, fmt.text)
        ws.write(r, 2, field.what_changed, fmt.text)
        ws.write(r, 3, field.variance_driver, fmt.text)
        ws.write(r, 4, field.favorable, fmt.text)
        ws.write(r, 5, field.unfavorable, fmt.text)
        ws.write(r, 6, field.leadership_attention, fmt.text)
        ws.write(r, 7, field.recommended_actions, fmt.text)
        ws.write(r, 8, field.owner, fmt.text)
        ws.write(r, 9, field.source, fmt.text)
        r += 1


def _write_data_sources_sheet(ws, bundle: ReportingBundle, fmt: _Formats) -> None:
    row0 = _write_title(ws, "Data Sources & Gaps", "Where to find missing export data", fmt)
    headers = ["Section", "Scenario", "Status", "Expected Source", "Message", "Action"]
    for col, h in enumerate(headers):
        ws.write(row0, col, h, fmt.header)
    ws.freeze_panes(row0 + 1, 0)
    r = row0 + 1
    for gap in bundle.data_gaps:
        ws.write(r, 0, gap.section, fmt.text)
        ws.write(r, 1, gap.scenario, fmt.text)
        ws.write(r, 2, gap.status, fmt.text)
        ws.write(r, 3, gap.expected_source, fmt.text)
        ws.write(r, 4, gap.message, fmt.text)
        ws.write(r, 5, gap.action, fmt.text)
        r += 1
    ws.set_column(3, 3, 48)
    ws.set_column(4, 5, 40)


def _write_validation_sheet(ws, bundle: ReportingBundle, fmt: _Formats) -> None:
    row0 = _write_title(ws, "Validation Checks", f"Status: {bundle.validation.status.upper()}", fmt)
    headers = ["Scenario", "Period", "Check", "Status", "Expected", "Actual", "Variance", "Sources"]
    for col, h in enumerate(headers):
        ws.write(row0, col, h, fmt.header)
    ws.freeze_panes(row0 + 1, 0)
    r = row0 + 1
    for check in bundle.validation.checks:
        ws.write(r, 0, check.scenario, fmt.text)
        ws.write(r, 1, check.period, fmt.text)
        ws.write(r, 2, check.validation_name, fmt.text)
        ws.write(r, 3, check.status, fmt.text)
        if check.expected_value is not None:
            ws.write(r, 4, float(check.expected_value), fmt.currency)
        if check.actual_value is not None:
            ws.write(r, 5, float(check.actual_value), fmt.currency)
        if check.variance is not None:
            ws.write(r, 6, float(check.variance), fmt.currency)
        ws.write(r, 7, ", ".join(check.source_tables_used or []), fmt.text)
        r += 1


def _write_executive_summary_only(ws, bundle: ReportingBundle, fmt: _Formats) -> None:
    row0 = _write_title(ws, "Executive Summary", subtitle_for_bundle(bundle), fmt)
    ws.write(row0, 0, "Section", fmt.header)
    ws.write(row0, 1, "Notes (Actual vs Budget by month in detail tabs)", fmt.header)
    r = row0 + 1
    for field in _commentary_fields(bundle):
        note = field.what_changed or field.metric_context or field.leadership_attention
        if not note:
            continue
        ws.write(r, 0, field.section, fmt.text)
        ws.write(r, 1, note, fmt.text)
        r += 1
    if r == row0 + 1:
        ws.write(r, 0, "No comparison metrics loaded", fmt.text)
        ws.write(r, 1, "See Data Sources & Gaps tab", fmt.text)


def build_workbook_bytes(bundle: ReportingBundle, *, sheet_names: list[str] | None = None) -> bytes:
    xlsxwriter = _import_xlsxwriter()
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    fmt = _Formats(wb)

    all_sheets = {
        "Executive Summary": lambda ws: _write_executive_summary_only(ws, bundle, fmt),
        "KPI Scorecard": lambda ws: _write_kpi_scorecard(ws, bundle, fmt),
        "Income Statement": lambda ws: _write_statement_sheet(ws, bundle, "income_statement", "Income Statement", fmt),
        "Balance Sheet": lambda ws: _write_statement_sheet(ws, bundle, "balance_sheet", "Balance Sheet", fmt),
        "Cash Flow Statement": lambda ws: _write_statement_sheet(ws, bundle, "cash_flow", "Cash Flow Statement", fmt),
        "Cash Flow Bridge": lambda ws: _write_waterfall_sheet(ws, bundle, "cash_flow", "Cash Flow Bridge", fmt),
        "MRR ARR Waterfall": lambda ws: _write_waterfall_sheet(ws, bundle, "arr", "MRR / ARR Waterfall", fmt),
        "Pipeline Waterfall": lambda ws: _write_waterfall_sheet(ws, bundle, "pipeline", "Pipeline Waterfall", fmt),
        "Opportunity Drilldown": lambda ws: _write_opportunity_sheet(ws, bundle, fmt),
        "Marketing Performance": lambda ws: _write_marketing_sheet(ws, bundle, fmt),
        "Revenue Forecast": lambda ws: _write_revenue_forecast_sheet(ws, bundle, fmt),
        "Bookings Forecast": lambda ws: _write_bookings_forecast_sheet(ws, bundle, fmt),
        "Deferred Revenue Waterfall": lambda ws: _write_waterfall_sheet(
            ws, bundle, "deferred_revenue", "Deferred Revenue Waterfall", fmt
        ),
        "Headcount Hiring": lambda ws: _write_headcount_sheet(ws, bundle, fmt),
        "Headcount & Hiring": lambda ws: _write_headcount_sheet(ws, bundle, fmt),
        "Department Spend P&L": lambda ws: _write_department_spend_sheet(ws, bundle, fmt),
        "Department Spend - P&L": lambda ws: _write_department_spend_sheet(ws, bundle, fmt),
        "Department Spend / P&L": lambda ws: _write_department_spend_sheet(ws, bundle, fmt),
        "GL Detail by Department": lambda ws: _write_gl_sheet(ws, bundle, fmt),
        "Variance Commentary": lambda ws: _write_commentary_sheet(ws, bundle, fmt),
        "Data Sources Gaps": lambda ws: _write_data_sources_sheet(ws, bundle, fmt),
        "Validation Checks": lambda ws: _write_validation_sheet(ws, bundle, fmt),
    }

    selected = sheet_names or list(all_sheets.keys())
    used_tab_names: set[str] = set()
    for name in selected:
        writer = all_sheets.get(name)
        if writer is None and name == "Data Sources & Gaps":
            writer = all_sheets["Data Sources Gaps"]
        tab = sanitize_excel_sheet_name(name, used=used_tab_names)
        ws = wb.add_worksheet(tab)
        if writer:
            writer(ws)

    wb.close()
    buf.seek(0)
    return buf.getvalue()
