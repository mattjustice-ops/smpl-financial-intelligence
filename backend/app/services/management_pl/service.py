"""Management P&L — FY outlook vs full-year budget, GL hierarchy, executive KPIs."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.financial_statements.financial_statement_service import (
    fetch_rows,
    month_start,
    parse_period,
    period_range,
    q,
    row_value,
    scenarios_for,
    table_exists,
)
from app.services.management_pl.gl_hierarchy import (
    MANAGEMENT_HIERARCHY,
    GlEntry,
    classify_raw_gl_row,
    resolve_section_and_group,
)
from app.services.management_pl.period_engine import (
    PeriodContext,
    build_period_context,
    fy_budget,
    sum_metric,
    variance,
)
from app.services.management_pl.schemas import (
    CommentaryBlock,
    DepartmentSummaryRow,
    DepartmentVariance,
    GlAccountRow,
    KpiCard,
    ManagementPlDashboardResponse,
    MetricSlice,
    MonthlySeries,
    PlLine,
    ValidationWarning,
    WaterfallStep,
)
from app.services.mrr.repository import fetch_persisted_summary
from app.services.reporting.period_utils import to_period

DEPARTMENTS = [
    "Total Company",
    "Sales & Marketing",
    "R&D",
    "G&A",
    "Customer Success",
    "Product",
    "Finance",
    "Operations",
]

DEPT_TO_SECTION = {
    "Sales & Marketing": "sales_and_marketing",
    "R&D": "research_and_development",
    "G&A": "general_and_administrative",
    "Customer Success": "customer_success",
    "Product": "research_and_development",
    "Finance": "general_and_administrative",
    "Operations": "general_and_administrative",
}

def _is_key(section: str) -> str:
    return "cost_of_revenue" if section == "cogs" else section


def _gl_period_has_data(row: dict[str, Decimal]) -> bool:
    if not row:
        return False
    return any(abs(row.get(key, Decimal("0"))) > 0 for key in METRIC_KEYS)


def _income_maps_from_gl(
    gl: dict[tuple[str, str, str, str], Decimal],
    periods: tuple[str, ...] | None = None,
) -> dict[str, dict[str, Decimal]]:
    """Roll classified GL into income-statement-shaped monthly maps."""
    period_filter = set(periods) if periods else None
    out: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
    section_to_key = {
        "revenue": "revenue",
        "cogs": "cost_of_revenue",
        "sales_and_marketing": "sales_and_marketing",
        "research_and_development": "research_and_development",
        "general_and_administrative": "general_and_administrative",
        "customer_success": "customer_success",
    }
    for (period, sec, _ag, _ac), amt in gl.items():
        if period_filter is not None and period not in period_filter:
            continue
        key = section_to_key.get(sec)
        if not key:
            continue
        if key == "revenue":
            out[period][key] += amt
        else:
            out[period][key] += abs(amt)
    for period, row in out.items():
        rev = row.get("revenue", Decimal("0"))
        cogs = row.get("cost_of_revenue", Decimal("0"))
        opex = (
            row.get("sales_and_marketing", Decimal("0"))
            + row.get("research_and_development", Decimal("0"))
            + row.get("general_and_administrative", Decimal("0"))
            + row.get("customer_success", Decimal("0"))
        )
        row["gross_profit"] = rev - cogs
        row["total_opex"] = opex
        row["ebitda"] = row["gross_profit"] - opex
    return {p: dict(v) for p, v in out.items()}


def _ensure_derived_metrics(row: dict[str, Decimal]) -> None:
    rev = row.get("revenue", Decimal("0"))
    cogs = row.get("cost_of_revenue", Decimal("0"))
    opex = (
        row.get("sales_and_marketing", Decimal("0"))
        + row.get("research_and_development", Decimal("0"))
        + row.get("general_and_administrative", Decimal("0"))
        + row.get("customer_success", Decimal("0"))
    )
    row["gross_profit"] = rev - cogs
    row["total_opex"] = opex
    row["ebitda"] = row["gross_profit"] - opex


def _merge_gl_primary(
    is_maps: dict[str, dict[str, Decimal]],
    gl_maps: dict[str, dict[str, Decimal]],
    periods: tuple[str, ...],
) -> dict[str, dict[str, Decimal]]:
    """When GL has classified rows for a period, use the full GL roll-up; else income statement fallback."""
    merged: dict[str, dict[str, Decimal]] = {}
    for period in periods:
        gl_row = gl_maps.get(period, {})
        if _gl_period_has_data(gl_row):
            row = dict(gl_row)
            _ensure_derived_metrics(row)
            merged[period] = row
        else:
            row = dict(is_maps.get(period, {}))
            if row:
                _ensure_derived_metrics(row)
            merged[period] = row
    return merged


def _gl_warehouse_ready(
    raw_gl_count: int,
    gl_outlook_maps: dict[str, dict[str, Decimal]],
    gl_budget_maps: dict[str, dict[str, Decimal]],
    ctx: PeriodContext,
) -> bool:
    if raw_gl_count <= 0:
        return False
    outlook_periods = sum(1 for p in ctx.fy_periods if _gl_period_has_data(gl_outlook_maps.get(p, {})))
    budget_periods = sum(1 for p in ctx.fy_periods if _gl_period_has_data(gl_budget_maps.get(p, {})))
    closed_with_gl = sum(
        1 for p in ctx.closed_periods if _gl_period_has_data(gl_outlook_maps.get(p, {}))
    )
    return outlook_periods > 0 and budget_periods > 0 and closed_with_gl >= max(1, len(ctx.closed_periods) // 2)


def _merge_gl_preferred(
    is_maps: dict[str, dict[str, Decimal]],
    gl_maps: dict[str, dict[str, Decimal]],
    periods: tuple[str, ...],
    *,
    workforce_mode: bool = False,
    open_periods: set[str] | None = None,
) -> dict[str, dict[str, Decimal]]:
    """Prefer GL detail per period when classified rows exist; fall back to income statement."""
    merged: dict[str, dict[str, Decimal]] = {p: dict(is_maps.get(p, {})) for p in periods}
    opex_keys = (
        "sales_and_marketing",
        "research_and_development",
        "general_and_administrative",
        "customer_success",
        "total_opex",
        "ebitda",
    )
    for period in periods:
        gl_row = gl_maps.get(period, {})
        if not _gl_period_has_data(gl_row):
            continue
        row = merged.setdefault(period, {})
        skip_opex = workforce_mode and open_periods is not None and period in open_periods
        for key in ("revenue", "cost_of_revenue"):
            if gl_row.get(key, Decimal("0")) != 0:
                row[key] = gl_row[key]
        if not skip_opex:
            for key in opex_keys:
                if gl_row.get(key, Decimal("0")) != 0:
                    row[key] = gl_row[key]
            if gl_row.get("gross_profit", Decimal("0")) != 0:
                row["gross_profit"] = gl_row["gross_profit"]
        else:
            rev = row.get("revenue", Decimal("0"))
            cogs = row.get("cost_of_revenue", Decimal("0"))
            row["gross_profit"] = rev - cogs
            opex = (
                row.get("sales_and_marketing", Decimal("0"))
                + row.get("research_and_development", Decimal("0"))
                + row.get("general_and_administrative", Decimal("0"))
                + row.get("customer_success", Decimal("0"))
            )
            row["total_opex"] = opex
            row["ebitda"] = row["gross_profit"] - opex
    return merged


METRIC_KEYS = (
    "revenue",
    "cost_of_revenue",
    "sales_and_marketing",
    "research_and_development",
    "general_and_administrative",
    "customer_success",
    "gross_profit",
    "total_opex",
    "ebitda",
)


def _period_scope_label(ctx: PeriodContext, period_mode: str) -> str:
    if period_mode == "ytd":
        return f"YTD through {ctx.as_of_period[5:7]}/{ctx.as_of_period[:4]}"
    if period_mode == "qtd":
        return f"QTD · {ctx.as_of_period}"
    if period_mode == "fy":
        return f"May {ctx.as_of_period[:4]} (KPI month)"
    month_names = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    m = int(ctx.as_of_period[5:7]) - 1
    return f"{month_names[m]} {ctx.as_of_period[:4]}"


def _period_str(d: date) -> str:
    return to_period(d)


def _pct_change(current: Decimal, prior: Decimal) -> Decimal | None:
    if prior == 0:
        return None
    return ((current - prior) / abs(prior)).quantize(Decimal("0.0001"))


def _safe_div(num: Decimal, den: Decimal) -> Decimal | None:
    if den == 0:
        return None
    return (num / den).quantize(Decimal("0.0001"))


def _display_amount(section_key: str, value: Decimal) -> Decimal:
    if section_key in ("gross_margin_pct", "ebitda_margin_pct"):
        return value
    if section_key == "revenue":
        return value
    return abs(value)


def _load_income_maps(
    session: Session,
    organization_id: uuid.UUID,
    scenario: str,
    start: date,
    end: date,
) -> dict[str, dict[str, Decimal]]:
    out: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
    for scenario_name, s, e in scenarios_for(scenario, start, end):
        table = f"{scenario_name.lower()}_income_statement"
        for raw in fetch_rows(session, table, organization_id, s, e):
            period = _period_str(raw["period"])
            rev = row_value(raw, "revenue")
            cogs = row_value(raw, "cost_of_revenue")
            sm = row_value(raw, "sales_and_marketing")
            rd = row_value(raw, "research_and_development")
            ga = row_value(raw, "general_and_administrative")
            cs = row_value(raw, "customer_success") if "customer_success" in raw else Decimal("0")
            opex = sm + rd + ga + cs
            gp = rev - cogs
            row = out[period]
            row["revenue"] += rev
            row["cost_of_revenue"] += cogs
            row["sales_and_marketing"] += sm
            row["research_and_development"] += rd
            row["general_and_administrative"] += ga
            row["customer_success"] += cs
            row["gross_profit"] += gp
            row["total_opex"] += opex
            row["ebitda"] += gp - opex
            row["tax_expense"] += row_value(raw, "tax_expense")
            row["net_income"] += row_value(raw, "net_income")
            row["depreciation_and_amortization"] += row_value(raw, "depreciation_and_amortization")
            row["interest_expense"] += row_value(raw, "interest_expense")
            row["services_revenue"] += row_value(raw, "services_revenue")
    return {p: dict(v) for p, v in out.items()}


def _merge_outlook_maps(
    actual: dict[str, dict[str, Decimal]],
    forecast: dict[str, dict[str, Decimal]],
    ctx: PeriodContext,
) -> dict[str, dict[str, Decimal]]:
    merged: dict[str, dict[str, Decimal]] = {}
    for p in ctx.fy_periods:
        src = actual if p in ctx.closed_periods else forecast
        merged[p] = dict(src.get(p, {}))
    return merged


def _merge_income_maps(
    primary: dict[str, dict[str, Decimal]],
    fill: dict[str, dict[str, Decimal]],
) -> dict[str, dict[str, Decimal]]:
    merged: dict[str, dict[str, Decimal]] = {p: dict(v) for p, v in primary.items()}
    for period, metrics in fill.items():
        row = merged.setdefault(period, {})
        for key, value in metrics.items():
            if row.get(key, Decimal("0")) == 0:
                row[key] = value
    return merged


def _load_gl_raw(session: Session, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if table_exists(session, "gl_actuals"):
        rows.extend(
            session.execute(
                text('select * from "gl_actuals" where organization_id = :oid'),
                {"oid": str(organization_id)},
            ).mappings()
        )
    from app.services.forecast_gl_detail.service import forecast_gl_rows_as_gl_raw

    forecast_rows = forecast_gl_rows_as_gl_raw(session, organization_id)
    if forecast_rows:
        existing_keys = {
            (
                str(r.get("version") or r.get("scenario")),
                str(r.get("period"))[:7],
                str(r.get("account_number") or ""),
                str(r.get("department") or ""),
            )
            for r in rows
        }
        for raw in forecast_rows:
            key = (
                str(raw.get("version") or "Forecast"),
                str(raw.get("period"))[:7],
                str(raw.get("account_number") or ""),
                str(raw.get("department") or ""),
            )
            if key not in existing_keys:
                rows.append(raw)
    return rows


def _gl_version_label(raw: dict[str, Any], *, default: str) -> str:
    version = str(raw.get("version") or default).strip()
    return version or default


def _version_in(version: str, allowed: tuple[str, ...]) -> bool:
    lower = version.lower()
    return any(lower == a.lower() for a in allowed)


def _pick_gl_rows_for_version(
    rows: list[dict[str, Any]],
    *,
    preferred: tuple[str, ...],
    fallback: tuple[str, ...],
) -> list[dict[str, Any]]:
    if not rows:
        return []
    for bucket in (preferred, fallback):
        picked = [r for r in rows if _version_in(_gl_version_label(r, default=preferred[0]), bucket)]
        if picked:
            return picked
    return rows


def _gl_rows_by_fy_period(raw_rows: list[dict[str, Any]], ctx: PeriodContext) -> dict[str, list[dict[str, Any]]]:
    by_period: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in raw_rows:
        period = parse_period(raw.get("period"))
        if period is None:
            continue
        ps = _period_str(period)
        if ps in ctx.fy_periods:
            by_period[ps].append(raw)
    return by_period


def _append_classified_gl_entries(
    entries: list[GlEntry],
    rows: list[dict[str, Any]],
    *,
    view_mode: str,
    default_version: str,
) -> None:
    for raw in rows:
        data = dict(raw)
        data["version"] = _gl_version_label(raw, default=default_version)
        entry = classify_raw_gl_row(data)
        if not entry:
            continue
        if view_mode == "management" and (entry.is_sbc or entry.is_restruct or entry.is_non_op):
            continue
        entries.append(entry)


def _gl_entries_for_outlook(
    raw_rows: list[dict[str, Any]],
    ctx: PeriodContext,
    view_mode: str,
) -> list[GlEntry]:
    """FY outlook GL: prefer Actual in closed months, Forecast in open; fall back when only one version exists."""
    by_period = _gl_rows_by_fy_period(raw_rows, ctx)
    entries: list[GlEntry] = []
    for ps in ctx.fy_periods:
        rows = by_period.get(ps, [])
        if not rows:
            continue
        if ps in ctx.closed_periods:
            chosen = _pick_gl_rows_for_version(
                rows, preferred=("Actual",), fallback=("Forecast", "Budget")
            )
            default_version = "Actual"
        else:
            chosen = _pick_gl_rows_for_version(
                rows, preferred=("Forecast",), fallback=("Actual", "Budget")
            )
            default_version = "Forecast"
        _append_classified_gl_entries(
            entries, chosen, view_mode=view_mode, default_version=default_version
        )
    return entries


def _gl_entries_budget(raw_rows: list[dict[str, Any]], ctx: PeriodContext, view_mode: str) -> list[GlEntry]:
    by_period = _gl_rows_by_fy_period(raw_rows, ctx)
    entries: list[GlEntry] = []
    for ps in ctx.fy_periods:
        rows = by_period.get(ps, [])
        if not rows:
            continue
        chosen = _pick_gl_rows_for_version(rows, preferred=("Budget",), fallback=("Actual", "Forecast"))
        _append_classified_gl_entries(entries, chosen, view_mode=view_mode, default_version="Budget")
    return entries


def _gl_entries_actual(raw_rows: list[dict[str, Any]], ctx: PeriodContext, view_mode: str) -> list[GlEntry]:
    """Actual GL only — closed months for period/YTD drilldown columns."""
    by_period = _gl_rows_by_fy_period(raw_rows, ctx)
    entries: list[GlEntry] = []
    for ps in ctx.closed_periods:
        rows = by_period.get(ps, [])
        if not rows:
            continue
        chosen = _pick_gl_rows_for_version(rows, preferred=("Actual",), fallback=("Budget", "Forecast"))
        _append_classified_gl_entries(entries, chosen, view_mode=view_mode, default_version="Actual")
    return entries


def _gl_entries_forecast(raw_rows: list[dict[str, Any]], ctx: PeriodContext, view_mode: str) -> list[GlEntry]:
    """Forecast GL only — open months for H2 forecast drilldown column."""
    by_period = _gl_rows_by_fy_period(raw_rows, ctx)
    entries: list[GlEntry] = []
    for ps in ctx.open_periods:
        rows = by_period.get(ps, [])
        if not rows:
            continue
        chosen = _pick_gl_rows_for_version(rows, preferred=("Forecast",), fallback=("Actual", "Budget"))
        _append_classified_gl_entries(entries, chosen, view_mode=view_mode, default_version="Forecast")
    return entries


def _aggregate_gl(
    entries: list[GlEntry],
) -> dict[tuple[str, str, str, str], Decimal]:
    out: dict[tuple[str, str, str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    for e in entries:
        out[(e.period, e.section_key, e.account_group, e.account_name)] += e.amount
    return out


def _aggregate_gl_by_department(
    entries: list[GlEntry],
) -> dict[tuple[str, str, str], Decimal]:
    """Sum by period, source department, and real account_name for GL drilldown."""
    out: dict[tuple[str, str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    for e in entries:
        out[(e.period, e.source_department, e.account_name)] += e.amount
    return out


def _is_amount(
    maps: dict[str, dict[str, Decimal]],
    periods: tuple[str, ...],
    key: str,
) -> Decimal:
    return sum_metric(maps, periods, key)


def _fy_outlook_from_map(
    outlook: dict[str, dict[str, Decimal]],
    ctx: PeriodContext,
    key: str,
) -> Decimal:
    """FY outlook total from the GL-merged outlook map (actual + forecast path)."""
    return sum_metric(outlook, ctx.fy_periods, key)


def _gl_amount(
    gl: dict[tuple[str, str, str, str], Decimal],
    periods: tuple[str, ...],
    section: str,
    account_group: str | None = None,
    account: str | None = None,
) -> Decimal:
    total = Decimal("0")
    for (p, sec, ag, ac), amt in gl.items():
        if p not in periods or sec != section:
            continue
        if account_group and ag != account_group:
            continue
        if account and ac != account:
            continue
        total += amt
    return total


def _metric_slice(
    *,
    section: str,
    outlook: dict[str, dict[str, Decimal]],
    budget: dict[str, dict[str, Decimal]],
    actual: dict[str, dict[str, Decimal]],
    forecast: dict[str, dict[str, Decimal]],
    gl_out: dict[tuple[str, str, str, str], Decimal],
    gl_bud: dict[tuple[str, str, str, str], Decimal],
    ctx: PeriodContext,
    account_group: str | None = None,
    account: str | None = None,
    workforce_mode: bool = False,
) -> MetricSlice:
    def pull_is(src: dict[str, dict[str, Decimal]], periods: tuple[str, ...]) -> Decimal:
        if account or account_group:
            return Decimal("0")
        return _is_amount(src, periods, _is_key(section))

    def pull_gl(src: dict, periods: tuple[str, ...]) -> Decimal:
        amount = _gl_amount(src, periods, section, account_group, account)
        if section == "revenue":
            return amount
        return abs(amount) if amount else Decimal("0")

    def combined_outlook_periods(periods: tuple[str, ...]) -> Decimal:
        g = pull_gl(gl_out, periods)
        if g != 0:
            return g
        return pull_is(outlook, periods)

    def combined_budget_periods(periods: tuple[str, ...]) -> Decimal:
        g = pull_gl(gl_bud, periods)
        if g != 0:
            return g
        return pull_is(budget, periods)

    fy_o = combined_outlook_periods(ctx.fy_periods)
    fy_b = combined_budget_periods(ctx.fy_periods)
    var_d, var_p = variance(fy_o, fy_b)
    cur = combined_outlook_periods(ctx.current_month)
    act = sum_metric(actual, ctx.current_month, section) + pull_gl(
        {k: v for k, v in gl_out.items() if k[0] in ctx.closed_periods}, ctx.current_month
    )
    fcast = sum_metric(forecast, ctx.current_month, section)
    rev_base = _is_amount(outlook, ctx.fy_periods, "revenue") or Decimal("1")
    return MetricSlice(
        actual=_display_amount(section, act),
        budget=_display_amount(section, fy_b),
        forecast=_display_amount(section, fcast),
        outlook=_display_amount(section, fy_o),
        variance=_display_amount(section, var_d),
        variance_pct=var_p,
        pct_of_revenue=_safe_div(fy_o, rev_base) if section not in ("gross_margin_pct", "ebitda_margin_pct") else None,
    )


def _build_section_children(
    section_key: str,
    template_groups: tuple[str, ...],
    outlook: dict[str, dict[str, Decimal]],
    budget: dict[str, dict[str, Decimal]],
    actual: dict[str, dict[str, Decimal]],
    forecast: dict[str, dict[str, Decimal]],
    gl_out: dict[tuple[str, str, str, str], Decimal],
    gl_bud: dict[tuple[str, str, str, str], Decimal],
    ctx: PeriodContext,
    department_filter: str,
    *,
    workforce_mode: bool = False,
) -> list[PlLine]:
    discovered: dict[str, set[str]] = defaultdict(set)
    for (_p, sec, ag, ac) in gl_out:
        if sec == section_key:
            discovered[ag].add(ac)
    for (_p, sec, ag, ac) in gl_bud:
        if sec == section_key:
            discovered[ag].add(ac)

    groups = list(template_groups) + [g for g in sorted(discovered) if g not in template_groups]
    children: list[PlLine] = []
    for ag in groups:
        accounts = sorted(discovered.get(ag, ()))
        if not accounts and _gl_amount(gl_out, ctx.fy_periods, section_key, ag) == 0:
            continue
        acct_lines: list[PlLine] = []
        for ac in accounts:
            m = _metric_slice(
                section=section_key,
                outlook=outlook,
                budget=budget,
                actual=actual,
                forecast=forecast,
                gl_out=gl_out,
                gl_bud=gl_bud,
                ctx=ctx,
                account_group=ag,
                account=ac,
            )
            if m.outlook == 0 and m.budget == 0:
                continue
            acct_lines.append(
                PlLine(
                    id=f"{section_key}:{ag}:{ac}",
                    label=ac,
                    line_type="subdetail",
                    section_key=section_key,
                    indent=2,
                    metrics=m,
                )
            )
        gm = _metric_slice(
            section=section_key,
            outlook=outlook,
            budget=budget,
            actual=actual,
            forecast=forecast,
            gl_out=gl_out,
            gl_bud=gl_bud,
            ctx=ctx,
            account_group=ag,
        )
        if gm.outlook == 0 and gm.budget == 0 and not acct_lines:
            continue
        children.append(
            PlLine(
                id=f"{section_key}:{ag}",
                label=ag,
                line_type="detail",
                section_key=section_key,
                indent=1,
                expandable=bool(acct_lines),
                metrics=gm if acct_lines else gm,
                children=acct_lines,
            )
        )

    is_fy = _is_amount(outlook, ctx.fy_periods, _is_key(section_key))
    gl_fy = abs(_gl_amount(gl_out, ctx.fy_periods, section_key))
    if not children and is_fy != 0 and gl_fy == 0:
        children.append(
            PlLine(
                id=f"{section_key}:is-detail",
                label="Per income statement (no GL accounts mapped to this section)",
                line_type="detail",
                section_key=section_key,
                indent=1,
                metrics=_metric_slice(
                    section=section_key,
                    outlook=outlook,
                    budget=budget,
                    actual=actual,
                    forecast=forecast,
                    gl_out=gl_out,
                    gl_bud=gl_bud,
                    ctx=ctx,
                    workforce_mode=workforce_mode,
                ),
                driver="income_statement",
            )
        )
    return children


def _section_visible(section_key: str, department_filter: str) -> bool:
    if department_filter == "Total Company":
        return True
    return DEPT_TO_SECTION.get(department_filter) == section_key


def _append_section(
    lines: list[PlLine],
    tmpl_key: str,
    outlook: dict[str, dict[str, Decimal]],
    budget: dict[str, dict[str, Decimal]],
    actual: dict[str, dict[str, Decimal]],
    forecast: dict[str, dict[str, Decimal]],
    gl_out: dict[tuple[str, str, str, str], Decimal],
    gl_bud: dict[tuple[str, str, str, str], Decimal],
    ctx: PeriodContext,
    department_filter: str,
    *,
    workforce_mode: bool = False,
) -> None:
    tmpl = next((t for t in MANAGEMENT_HIERARCHY if t.section_key == tmpl_key), None)
    if not tmpl or not _section_visible(tmpl.section_key, department_filter):
        return
    children = _build_section_children(
        tmpl.section_key,
        tmpl.account_groups,
        outlook,
        budget,
        actual,
        forecast,
        gl_out,
        gl_bud,
        ctx,
        department_filter,
        workforce_mode=workforce_mode,
    )
    metrics = _metric_slice(
        section=tmpl.section_key,
        outlook=outlook,
        budget=budget,
        actual=actual,
        forecast=forecast,
        gl_out=gl_out,
        gl_bud=gl_bud,
        ctx=ctx,
        workforce_mode=workforce_mode,
    )
    lines.append(
        PlLine(
            id=tmpl.section_key,
            label=tmpl.section_label,
            line_type="section",
            section_key=tmpl.section_key,
            indent=0,
            expandable=bool(children),
            metrics=metrics,
            children=children,
        )
    )


def _sync_pl_section_fy(
    lines: list[PlLine],
    section_key: str,
    outlook: dict[str, dict[str, Decimal]],
    budget: dict[str, dict[str, Decimal]],
    ctx: PeriodContext,
) -> None:
    """Align section FY outlook/budget with GL-merged maps (matches monthly path chart)."""
    metric_key = _is_key(section_key)
    fy_o = _fy_outlook_from_map(outlook, ctx, metric_key)
    fy_b = sum_metric(budget, ctx.fy_periods, metric_key)
    var_d, var_p = variance(fy_o, fy_b)
    rev_base = _fy_outlook_from_map(outlook, ctx, "revenue") or Decimal("1")
    for line in lines:
        if line.section_key != section_key:
            continue
        line.metrics = MetricSlice(
            outlook=_display_amount(section_key, fy_o),
            budget=_display_amount(section_key, fy_b),
            variance=_display_amount(section_key, var_d),
            variance_pct=var_p,
            pct_of_revenue=_safe_div(fy_o, rev_base),
        )
        break


def _build_pl_lines(
    outlook: dict[str, dict[str, Decimal]],
    budget: dict[str, dict[str, Decimal]],
    actual: dict[str, dict[str, Decimal]],
    forecast: dict[str, dict[str, Decimal]],
    gl_out: dict[tuple[str, str, str, str], Decimal],
    gl_bud: dict[tuple[str, str, str, str], Decimal],
    ctx: PeriodContext,
    department_filter: str,
    *,
    workforce_mode: bool = False,
) -> list[PlLine]:
    lines: list[PlLine] = []
    for key in ("revenue", "cogs"):
        _append_section(
            lines, key, outlook, budget, actual, forecast, gl_out, gl_bud, ctx, department_filter, workforce_mode=workforce_mode
        )
    _sync_pl_section_fy(lines, "revenue", outlook, budget, ctx)
    _sync_pl_section_fy(lines, "cogs", outlook, budget, ctx)

    rev = _metric_slice(section="revenue", outlook=outlook, budget=budget, actual=actual, forecast=forecast, gl_out=gl_out, gl_bud=gl_bud, ctx=ctx, workforce_mode=workforce_mode)
    cogs = _metric_slice(
        section="cogs",
        outlook=outlook,
        budget=budget,
        actual=actual,
        forecast=forecast,
        gl_out=gl_out,
        gl_bud=gl_bud,
        ctx=ctx,
        workforce_mode=workforce_mode,
    )
    gp_val_o = _fy_outlook_from_map(outlook, ctx, "gross_profit") or (rev.outlook - cogs.outlook)
    gp_val_b = sum_metric(budget, ctx.fy_periods, "gross_profit") or (rev.budget - cogs.budget)
    rev_fy_o = _fy_outlook_from_map(outlook, ctx, "revenue")
    rev_fy_b = sum_metric(budget, ctx.fy_periods, "revenue")
    gp_var, gp_var_pct = variance(gp_val_o, gp_val_b)
    gp = MetricSlice(
        outlook=gp_val_o,
        budget=gp_val_b,
        variance=gp_var,
        variance_pct=gp_var_pct,
        pct_of_revenue=_safe_div(gp_val_o, rev_fy_o or Decimal("1")),
    )
    lines.append(
        PlLine(
            id="gross_profit",
            label="Gross Profit",
            line_type="total",
            section_key="gross_profit",
            is_bold=True,
            metrics=gp,
        )
    )
    gm_pct = MetricSlice(
        outlook=_safe_div(gp_val_o, rev_fy_o) or Decimal("0"),
        budget=_safe_div(gp_val_b, rev_fy_b) or Decimal("0"),
        variance=(_safe_div(gp_val_o, rev_fy_o) or Decimal("0"))
        - (_safe_div(gp_val_b, rev_fy_b) or Decimal("0")),
    )
    lines.append(
        PlLine(
            id="gross_margin_pct",
            label="Gross Margin %",
            line_type="margin",
            section_key="gross_margin_pct",
            metrics=gm_pct,
        )
    )

    for key in (
        "sales_and_marketing",
        "research_and_development",
        "general_and_administrative",
        "customer_success",
    ):
        _append_section(
            lines, key, outlook, budget, actual, forecast, gl_out, gl_bud, ctx, department_filter, workforce_mode=workforce_mode
        )

    opex_sections = [l for l in lines if l.section_key in DEPT_TO_SECTION.values()]
    opex_o = _fy_outlook_from_map(outlook, ctx, "total_opex") or sum((l.metrics.outlook for l in opex_sections), Decimal("0"))
    opex_b = sum_metric(budget, ctx.fy_periods, "total_opex") or sum((l.metrics.budget for l in opex_sections), Decimal("0"))
    opex_var, opex_var_pct = variance(opex_o, opex_b)
    lines.append(
        PlLine(
            id="total_opex",
            label="Total OpEx",
            line_type="total",
            section_key="total_opex",
            is_bold=True,
            metrics=MetricSlice(outlook=opex_o, budget=opex_b, variance=opex_var, variance_pct=opex_var_pct),
        )
    )

    ebitda_o = _fy_outlook_from_map(outlook, ctx, "ebitda") or (gp_val_o - opex_o)
    ebitda_b = sum_metric(budget, ctx.fy_periods, "ebitda") or (gp_val_b - opex_b)
    e_var, e_var_pct = variance(ebitda_o, ebitda_b)
    lines.append(
        PlLine(
            id="ebitda",
            label="EBITDA",
            line_type="total",
            section_key="ebitda",
            is_bold=True,
            is_ebitda=True,
            metrics=MetricSlice(outlook=ebitda_o, budget=ebitda_b, variance=e_var, variance_pct=e_var_pct),
        )
    )
    lines.append(
        PlLine(
            id="ebitda_margin_pct",
            label="EBITDA Margin %",
            line_type="margin",
            section_key="ebitda_margin_pct",
            metrics=MetricSlice(
                outlook=_safe_div(ebitda_o, rev_fy_o) or Decimal("0"),
                budget=_safe_div(ebitda_b, rev_fy_b) or Decimal("0"),
                variance=(_safe_div(ebitda_o, rev_fy_o) or Decimal("0"))
                - (_safe_div(ebitda_b, rev_fy_b) or Decimal("0")),
            ),
        )
    )
    return lines


def _opex_stacks_for_period(entries: list[GlEntry], period: str) -> tuple[Decimal, Decimal, Decimal]:
    from app.services.management_pl.gl_hierarchy import (
        OPEX_STACK_GA_DEPTS,
        OPEX_STACK_RD_DEPTS,
        OPEX_STACK_SM_DEPTS,
    )

    sm = rd = ga = Decimal("0")
    for e in entries:
        if e.period != period or e.section_key in ("revenue", "cogs"):
            continue
        amt = abs(e.amount)
        if e.source_department in OPEX_STACK_SM_DEPTS:
            sm += amt
        elif e.source_department in OPEX_STACK_RD_DEPTS:
            rd += amt
        elif e.source_department in OPEX_STACK_GA_DEPTS:
            ga += amt
    return sm, rd, ga


def _monthly_series(
    outlook: dict[str, dict[str, Decimal]],
    budget: dict[str, dict[str, Decimal]],
    actual: dict[str, dict[str, Decimal]],
    forecast: dict[str, dict[str, Decimal]],
    ctx: PeriodContext,
    *,
    gl_entries: list[GlEntry] | None = None,
) -> list[MonthlySeries]:
    series: list[MonthlySeries] = []
    for p in ctx.fy_periods:
        o = outlook.get(p, {})
        b = budget.get(p, {})
        a = actual.get(p, {})
        f = forecast.get(p, {})
        closed = p in ctx.closed_periods
        rev_o = o.get("revenue", Decimal("0"))
        rev_b = b.get("revenue", Decimal("0"))
        rev_a = a.get("revenue", Decimal("0")) if closed else Decimal("0")
        rev_f = f.get("revenue", Decimal("0")) if not closed else Decimal("0")
        if not closed and rev_f == 0:
            rev_f = rev_o
        if closed and rev_a == 0:
            rev_a = rev_o
        cogs_o = o.get("cost_of_revenue", Decimal("0"))
        cogs_b = b.get("cost_of_revenue", Decimal("0"))
        gp_o = o.get("gross_profit", Decimal("0")) or (rev_o - cogs_o)
        gp_b = b.get("gross_profit", Decimal("0")) or (rev_b - cogs_b)
        gp_a = (a.get("gross_profit", Decimal("0")) or (rev_a - a.get("cost_of_revenue", Decimal("0")))) if closed else Decimal("0")
        if closed and gp_a == 0:
            gp_a = gp_o
        gp_f = (f.get("gross_profit", Decimal("0")) or (rev_f - f.get("cost_of_revenue", Decimal("0")))) if not closed else Decimal("0")
        if not closed and gp_f == 0:
            gp_f = gp_o
        opex = o.get("total_opex", Decimal("0"))
        ebitda_o = o.get("ebitda", Decimal("0")) or (gp_o - opex)
        ebitda_a = (a.get("ebitda", Decimal("0")) or (gp_a - a.get("total_opex", Decimal("0")))) if closed else Decimal("0")
        if closed and ebitda_a == 0:
            ebitda_a = ebitda_o
        ebitda_f = (f.get("ebitda", Decimal("0")) or (gp_f - f.get("total_opex", Decimal("0")))) if not closed else Decimal("0")
        if not closed and ebitda_f == 0:
            ebitda_f = ebitda_o
        rev_for_margin = rev_a if closed else rev_f or rev_o
        gp_for_margin = gp_a if closed else gp_f or gp_o
        ebitda_for_margin = ebitda_a if closed else ebitda_f or ebitda_o
        gm_pct_a = (gp_for_margin / rev_for_margin) if rev_for_margin else Decimal("0")
        gm_pct_b = (gp_b / rev_b) if rev_b else Decimal("0")
        ebitda_margin_a = (ebitda_for_margin / rev_for_margin) if rev_for_margin else Decimal("0")
        ebitda_b_period = b.get("ebitda", Decimal("0")) or (gp_b - b.get("total_opex", Decimal("0")))
        ebitda_margin_b_val = (ebitda_b_period / rev_b) if rev_b else Decimal("0")
        stack_sm, stack_rd, stack_ga = (
            _opex_stacks_for_period(gl_entries, p) if gl_entries else (Decimal("0"), Decimal("0"), Decimal("0"))
        )
        if stack_sm == 0 and stack_rd == 0 and stack_ga == 0:
            stack_sm = o.get("sales_and_marketing", Decimal("0"))
            stack_rd = o.get("research_and_development", Decimal("0"))
            stack_ga = (
                o.get("general_and_administrative", Decimal("0"))
                + o.get("customer_success", Decimal("0"))
            )
        series.append(
            MonthlySeries(
                period=p,
                label=p[5:],
                is_closed=closed,
                revenue_actual=rev_a,
                revenue_forecast=rev_f,
                revenue_budget=rev_b,
                revenue_outlook=rev_o,
                cogs_outlook=cogs_o,
                cogs_budget=cogs_b,
                gross_profit_actual=gp_a,
                gross_profit_forecast=gp_f,
                gross_profit_budget=gp_b,
                gross_profit_outlook=gp_o,
                ebitda_actual=ebitda_a,
                ebitda_forecast=ebitda_f,
                ebitda_outlook=ebitda_o,
                total_opex=opex,
                opex_stack_sm=stack_sm,
                opex_stack_rd=stack_rd,
                opex_stack_ga=stack_ga,
                sm=o.get("sales_and_marketing", Decimal("0")),
                rd=o.get("research_and_development", Decimal("0")),
                ga=o.get("general_and_administrative", Decimal("0")),
                cs=o.get("customer_success", Decimal("0")),
                gm_pct_actual=gm_pct_a,
                gm_pct_budget=gm_pct_b,
                ebitda_margin_actual=ebitda_margin_a,
                ebitda_margin_budget=ebitda_margin_b_val,
            )
        )
    return series


def _ebitda_waterfall(
    rev: Decimal,
    cogs: Decimal,
    sm: Decimal,
    rd: Decimal,
    ga: Decimal,
) -> list[WaterfallStep]:
    gp = rev - cogs
    ebitda = gp - sm - rd - ga
    running = gp
    steps = [
        WaterfallStep(label="Revenue", value=rev, running_total=rev, step_type="total"),
        WaterfallStep(label="COGS", value=-abs(cogs), running_total=gp, step_type="subtract"),
        WaterfallStep(label="Gross Profit", value=gp, running_total=gp, step_type="total"),
    ]
    for label, amt in (("S&M", sm), ("R&D", rd), ("G&A", ga)):
        running -= abs(amt)
        steps.append(WaterfallStep(label=label, value=-abs(amt), running_total=running, step_type="subtract"))
    steps.append(WaterfallStep(label="EBITDA", value=ebitda, running_total=ebitda, step_type="total"))
    return steps


def _department_gl_variances(
    gl_act: dict[tuple[str, str, str], Decimal],
    gl_bud: dict[tuple[str, str, str], Decimal],
    ctx: PeriodContext,
) -> list[DepartmentVariance]:
    from app.services.management_pl.gl_hierarchy import GL_DRILLDOWN_DEPARTMENTS

    rows: list[DepartmentVariance] = []
    total_o = Decimal("0")
    for dept in GL_DRILLDOWN_DEPARTMENTS:
        o = _gl_dept_spend(gl_act, dept, ctx.current_month)
        b = _gl_dept_spend(gl_bud, dept, ctx.current_month)
        if o == 0 and b == 0:
            continue
        var, var_pct = variance(o, b)
        total_o += o
        rows.append(DepartmentVariance(department=dept, outlook=o, budget=b, variance=var, variance_pct=var_pct))
    for r in rows:
        r.pct_of_opex = _safe_div(r.outlook, total_o)
    return sorted(rows, key=lambda x: abs(x.variance), reverse=True)


def _headcount_by_department(
    session: Session,
    organization_id: uuid.UUID,
    ctx: PeriodContext,
    start: date,
    end: date,
) -> dict[str, Decimal]:
    from app.services.workforce.legacy_headcount import load_legacy_headcount_rows

    by_dept: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    try:
        snaps = load_legacy_headcount_rows(
            session,
            organization_id,
            scenario="Actual",
            start_period=start,
            end_period=end,
        )
    except Exception:
        return {}
    for snap in snaps:
        if snap.period not in ctx.current_month:
            continue
        by_dept[snap.department] += snap.headcount
    return dict(by_dept)


def _gl_dept_spend(
    gl: dict[tuple[str, str, str], Decimal],
    dept: str,
    periods: tuple[str, ...],
) -> Decimal:
    accounts = {ac for (_p, d, ac) in gl if d == dept}
    return sum(abs(gl.get((p, dept, ac), Decimal("0"))) for p in periods for ac in accounts)


def _department_variances(
    outlook: dict[str, dict[str, Decimal]],
    budget: dict[str, dict[str, Decimal]],
    ctx: PeriodContext,
    gl_act: dict[tuple[str, str, str], Decimal] | None = None,
    gl_bud: dict[tuple[str, str, str], Decimal] | None = None,
) -> list[DepartmentVariance]:
    if gl_act and gl_bud:
        return _department_gl_variances(gl_act, gl_bud, ctx)
    rows: list[DepartmentVariance] = []
    total_o = Decimal("0")
    for dept, key in DEPT_TO_SECTION.items():
        o = _is_amount(outlook, ctx.current_month, key)
        b = _is_amount(budget, ctx.current_month, key)
        var, var_pct = variance(o, b)
        total_o += o
        rows.append(DepartmentVariance(department=dept, outlook=o, budget=b, variance=var, variance_pct=var_pct))
    for r in rows:
        r.pct_of_opex = _safe_div(r.outlook, total_o)
    return sorted(rows, key=lambda x: abs(x.variance), reverse=True)


def _gl_by_department(
    gl_actual: dict[tuple[str, str, str], Decimal],
    gl_bud: dict[tuple[str, str, str], Decimal],
    ctx: PeriodContext,
    gl_forecast: dict[tuple[str, str, str], Decimal] | None = None,
) -> dict[str, list[GlAccountRow]]:
    from app.services.management_pl.gl_hierarchy import GL_DRILLDOWN_DEPARTMENTS

    by_dept: dict[str, dict[str, GlAccountRow]] = defaultdict(dict)
    accounts: set[tuple[str, str]] = set()
    for (_p, src_dept, ac) in gl_actual:
        accounts.add((src_dept, ac))
    for (_p, src_dept, ac) in gl_bud:
        accounts.add((src_dept, ac))
    if gl_forecast:
        for (_p, src_dept, ac) in gl_forecast:
            accounts.add((src_dept, ac))

    for src_dept, ac in sorted(accounts):
        if src_dept not in GL_DRILLDOWN_DEPARTMENTS:
            continue
        period_a = sum(abs(gl_actual.get((p, src_dept, ac), Decimal("0"))) for p in ctx.current_month)
        period_b = sum(abs(gl_bud.get((p, src_dept, ac), Decimal("0"))) for p in ctx.current_month)
        ytd_a = sum(abs(gl_actual.get((p, src_dept, ac), Decimal("0"))) for p in ctx.ytd_periods)
        h2_f = Decimal("0")
        if gl_forecast:
            h2_f = sum(abs(gl_forecast.get((p, src_dept, ac), Decimal("0"))) for p in ctx.open_periods)
        if period_a == 0 and period_b == 0 and ytd_a == 0 and h2_f == 0:
            continue
        var, var_pct = variance(period_a, period_b)
        ytd_b = sum(abs(gl_bud.get((p, src_dept, ac), Decimal("0"))) for p in ctx.ytd_periods)
        is_non_recurring = "accounting true-up" in ac.lower()
        by_dept[src_dept][ac] = GlAccountRow(
            account=ac,
            account_group=src_dept,
            outlook=period_a,
            budget=period_b,
            variance=var,
            variance_pct=var_pct,
            ytd_outlook=ytd_a,
            ytd_variance=ytd_a - ytd_b,
            h2_forecast=h2_f,
            is_non_recurring=is_non_recurring,
        )

    return {d: list(by_dept[d].values()) for d in GL_DRILLDOWN_DEPARTMENTS if d in by_dept}


def _net_new_arr_ytd(session: Session, organization_id: uuid.UUID, ctx: PeriodContext) -> Decimal:
    if not table_exists(session, "mrr_waterfall"):
        return Decimal("0")
    total = Decimal("0")
    for p in ctx.ytd_periods:
        d = month_start(p)
        try:
            s = fetch_persisted_summary(session, organization_id, d)
        except Exception:
            continue
        nn = (
            s["new_mrr"]
            + s["expansion_mrr"]
            - s["contraction_mrr"]
            - s["churn_mrr"]
            + s["reactivation_mrr"]
        ) * Decimal("12")
        total += nn
    return total


def _validations(
    outlook: dict[str, dict[str, Decimal]],
    budget: dict[str, dict[str, Decimal]],
    gl_out: dict[tuple[str, str, str, str], Decimal],
    ctx: PeriodContext,
    *,
    raw_gl_count: int = 0,
    gl_outlook_entry_count: int = 0,
    gl_outlook_maps: dict[str, dict[str, Decimal]] | None = None,
    workforce_mode: bool = False,
    gl_primary: bool = False,
) -> list[ValidationWarning]:
    warnings: list[ValidationWarning] = []
    if gl_primary:
        warnings.append(
            ValidationWarning(
                code="gl_primary",
                message=(
                    "P&L Summary is sourced from GL detail (Actual/Budget in gl_actuals, Forecast in forecast_gl_detail). "
                    "Income statement CSVs are fallback only for months without classified GL."
                ),
                severity="warning",
            )
        )
    if workforce_mode:
        warnings.append(
            ValidationWarning(
                code="workforce_pnl_overlay",
                message=(
                    "Open-month people costs use workforce pnl_people_cost_lines; GL payroll rows excluded to prevent double-count."
                ),
                severity="warning",
            )
        )
    cogs = _is_amount(outlook, ctx.fy_periods, "cost_of_revenue")
    if cogs == 0:
        warnings.append(
            ValidationWarning(
                code="cogs_missing",
                message="COGS is zero on FY outlook — verify cost_of_revenue in income statements or GL.",
                severity="warning",
            )
        )
    rev_gl_periods = 0
    cogs_gl_periods = 0
    opex_only_gl_periods: list[str] = []
    if gl_outlook_maps:
        for p in ctx.fy_periods:
            gl_row = gl_outlook_maps.get(p, {})
            if not _gl_period_has_data(gl_row):
                continue
            has_rev = gl_row.get("revenue", Decimal("0")) != 0
            has_cogs = gl_row.get("cost_of_revenue", Decimal("0")) != 0
            has_opex = any(
                gl_row.get(k, Decimal("0")) != 0
                for k in (
                    "sales_and_marketing",
                    "research_and_development",
                    "general_and_administrative",
                    "customer_success",
                    "total_opex",
                )
            )
            if has_rev:
                rev_gl_periods += 1
            if has_cogs:
                cogs_gl_periods += 1
            if has_opex and not has_rev:
                opex_only_gl_periods.append(p)
        if opex_only_gl_periods:
            sample = ", ".join(opex_only_gl_periods[:4])
            suffix = "…" if len(opex_only_gl_periods) > 4 else ""
            warnings.append(
                ValidationWarning(
                    code="gl_revenue_missing",
                    message=(
                        f"GL has OpEx for {len(opex_only_gl_periods)} month(s) ({sample}{suffix}) but no classified "
                        "revenue rows — revenue/GP for those months still use income statement totals."
                    ),
                    severity="warning",
                )
            )
        if rev_gl_periods == 0 and gl_out:
            warnings.append(
                ValidationWarning(
                    code="gl_revenue_unclassified",
                    message=(
                        "No GL rows classified as revenue for this fiscal year. Check statement_category, "
                        "line_type, account_group, and management_view_include on revenue accounts."
                    ),
                    severity="warning",
                )
            )
        elif rev_gl_periods < len(ctx.closed_periods) and gl_out:
            warnings.append(
                ValidationWarning(
                    code="gl_revenue_partial",
                    message=(
                        f"GL revenue covers {rev_gl_periods}/{len(ctx.fy_periods)} FY months "
                        f"({cogs_gl_periods} with COGS). Missing months use income statement fallback."
                    ),
                    severity="warning",
                )
            )
    if not gl_out:
        if raw_gl_count == 0:
            warnings.append(
                ValidationWarning(
                    code="gl_empty",
                    message=(
                        "No gl_actuals rows for this organization. Upload Actual_gl_detail.csv, "
                        "Budget_gl_detail.csv, and Forecast_gl_detail.csv — section totals and charts "
                        "fall back to income statement CSVs until GL is loaded."
                    ),
                    severity="warning",
                )
            )
        elif gl_outlook_entry_count == 0:
            warnings.append(
                ValidationWarning(
                    code="gl_unclassified",
                    message=(
                        f"Found {raw_gl_count} gl_actuals rows but none could be classified for FY "
                        f"{ctx.fiscal_year} (check period, amount, and account fields)."
                    ),
                    severity="warning",
                )
            )
        else:
            warnings.append(
                ValidationWarning(
                    code="gl_sparse",
                    message=(
                        f"GL detail is limited ({gl_outlook_entry_count} classified lines from {raw_gl_count} "
                        f"warehouse rows). Periods without classified GL still use income statement totals."
                    ),
                    severity="warning",
                )
            )
    rev_o = _is_amount(outlook, ctx.fy_periods, "revenue")
    rev_b = fy_budget(budget, ctx, "revenue")
    if rev_b and rev_o:
        ytd_a = sum_metric(outlook, ctx.ytd_periods, "revenue")
        if abs(ytd_a - rev_b) / abs(rev_b) > Decimal("0.5"):
            warnings.append(
                ValidationWarning(
                    code="compare_scope",
                    message="KPIs compare FY Outlook (Actual+Forecast) vs full-year Budget — not YTD Actual vs FY Budget.",
                    severity="warning",
                )
            )
    return warnings


def build_management_pl_dashboard(
    session: Session,
    organization_id: uuid.UUID,
    *,
    start_period: date,
    end_period: date,
    as_of_period: date | None = None,
    period_mode: str = "fy",
    view_mode: str = "management",
    department: str = "Total Company",
    **_legacy: Any,
) -> ManagementPlDashboardResponse:
    start = month_start(start_period)
    end = month_start(end_period)
    as_of = month_start(as_of_period or end_period)
    fy_periods_dt = period_range(start, end)
    fiscal_year = as_of.year
    ctx = build_period_context(fiscal_year=fiscal_year, as_of_period=_period_str(as_of), period_mode=period_mode)

    from app.services.forecast_gl_detail.service import aggregate_forecast_gl_to_income_maps
    from app.services.workforce import integration as wf_integration

    actual_is = _load_income_maps(session, organization_id, "Actual", start, end)
    forecast_is = _load_income_maps(session, organization_id, "Forecast", start, end)
    forecast_is = _merge_income_maps(
        forecast_is,
        aggregate_forecast_gl_to_income_maps(session, organization_id, start=start, end=end),
    )
    budget_is = _load_income_maps(session, organization_id, "Budget", start, end)

    wf_active = wf_integration.workforce_source_present(session, organization_id, scenario="Forecast")
    open_periods: set[str] = set()
    raw_gl = _load_gl_raw(session, organization_id)
    gl_out_entries = _gl_entries_for_outlook(raw_gl, ctx, view_mode)

    overlay: dict[str, dict[str, Decimal]] = {}
    non_payroll: dict[str, dict[str, Decimal]] | None = None
    if wf_active:
        open_periods = {p for p in ctx.fy_periods if p not in ctx.closed_periods}
        overlay = wf_integration.pnl_overlay_by_period(
            session, organization_id, scenario="Forecast", start_period=start, end_period=end
        )
        non_payroll = wf_integration.non_payroll_gl_by_period_section(gl_out_entries, open_periods)
        gl_out_entries = wf_integration.exclude_payroll_gl_entries(gl_out_entries, open_periods)

    gl_bud_entries = _gl_entries_budget(raw_gl, ctx, view_mode)
    gl_act_entries = _gl_entries_actual(raw_gl, ctx, view_mode)
    gl_fcst_entries = _gl_entries_forecast(raw_gl, ctx, view_mode)
    gl_out = _aggregate_gl(gl_out_entries)
    gl_bud = _aggregate_gl(gl_bud_entries)

    gl_outlook_maps = _income_maps_from_gl(gl_out, tuple(ctx.fy_periods))
    gl_budget_maps = _income_maps_from_gl(gl_bud, tuple(ctx.fy_periods))
    gl_actual_maps = _income_maps_from_gl(
        {k: v for k, v in gl_out.items() if k[0] in ctx.closed_periods},
        tuple(ctx.closed_periods),
    )

    gl_primary = _gl_warehouse_ready(len(raw_gl), gl_outlook_maps, gl_budget_maps, ctx)
    is_outlook = _merge_outlook_maps(actual_is, forecast_is, ctx)

    if gl_primary:
        outlook = _merge_gl_primary(is_outlook, gl_outlook_maps, tuple(ctx.fy_periods))
        budget = _merge_gl_primary(budget_is, gl_budget_maps, tuple(ctx.fy_periods))
        actual = _merge_gl_primary(actual_is, gl_actual_maps, tuple(ctx.closed_periods))
        if wf_active:
            outlook = wf_integration.apply_workforce_pnl_to_income_map(
                outlook, overlay, open_periods, non_payroll_gl=non_payroll
            )
        forecast = forecast_is
    else:
        if wf_active:
            forecast_is = wf_integration.apply_workforce_pnl_to_income_map(
                forecast_is, overlay, open_periods, non_payroll_gl=non_payroll
            )
        outlook = _merge_outlook_maps(actual_is, forecast_is, ctx)
        outlook = _merge_gl_preferred(
            outlook,
            gl_outlook_maps,
            tuple(ctx.fy_periods),
            workforce_mode=wf_active,
            open_periods=open_periods,
        )
        budget = _merge_gl_preferred(budget_is, gl_budget_maps, tuple(ctx.fy_periods))
        actual = _merge_gl_preferred(actual_is, gl_actual_maps, tuple(ctx.closed_periods))
        forecast = forecast_is

    pl_lines = _build_pl_lines(outlook, budget, actual, forecast, gl_out, gl_bud, ctx, department, workforce_mode=wf_active)
    gl_act_agg = _aggregate_gl_by_department(gl_act_entries)
    gl_bud_agg = _aggregate_gl_by_department(gl_bud_entries)
    gl_fcst_agg = _aggregate_gl_by_department(gl_fcst_entries)
    dept_summary: list[DepartmentSummaryRow] = []
    if gl_primary:
        from app.services.management_pl.pl_builder import build_department_summary, build_spec_pl_lines

        pl_lines = build_spec_pl_lines(
            ctx=ctx,
            gl_act=gl_act_agg,
            gl_bud=gl_bud_agg,
            gl_fcst=gl_fcst_agg,
            outlook=outlook,
            budget=budget,
            actual_is=actual,
            forecast_is=forecast,
        )
        dept_summary = [
            DepartmentSummaryRow(**row)  # type: ignore[arg-type]
            for row in build_department_summary(
                ctx=ctx,
                gl_act=gl_act_agg,
                gl_bud=gl_bud_agg,
                headcount_by_dept=_headcount_by_department(session, organization_id, ctx, start, end),
            )
        ]
    monthly = _monthly_series(
        outlook,
        budget,
        actual,
        {p: dict(outlook.get(p, {})) for p in ctx.open_periods} if gl_primary else forecast,
        ctx,
        gl_entries=gl_out_entries,
    )

    rev_o = _fy_outlook_from_map(outlook, ctx, "revenue")
    rev_b = fy_budget(budget, ctx, "revenue")
    cogs_o = _fy_outlook_from_map(outlook, ctx, "cost_of_revenue")
    opex_o = _fy_outlook_from_map(outlook, ctx, "total_opex")
    if opex_o == 0:
        opex_o = (
            _fy_outlook_from_map(outlook, ctx, "sales_and_marketing")
            + _fy_outlook_from_map(outlook, ctx, "research_and_development")
            + _fy_outlook_from_map(outlook, ctx, "general_and_administrative")
            + _fy_outlook_from_map(outlook, ctx, "customer_success")
        )
    gp_o = _fy_outlook_from_map(outlook, ctx, "gross_profit") or (rev_o - cogs_o)
    ebitda_o = _fy_outlook_from_map(outlook, ctx, "ebitda") or (gp_o - opex_o)
    ebitda_b = fy_budget(budget, ctx, "ebitda")
    if ebitda_b == 0:
        ebitda_b = fy_budget(budget, ctx, "gross_profit") - fy_budget(budget, ctx, "total_opex")

    kpi_periods = ctx.current_month if period_mode != "fy" else (ctx.as_of_period,)
    kpi_rev = _is_amount(outlook, kpi_periods, "revenue")
    kpi_rev_b = _is_amount(budget, kpi_periods, "revenue")
    kpi_cogs = _is_amount(outlook, kpi_periods, "cost_of_revenue")
    kpi_gp = _is_amount(outlook, kpi_periods, "gross_profit") or (kpi_rev - kpi_cogs)
    kpi_gp_b = _is_amount(budget, kpi_periods, "gross_profit") or (kpi_rev_b - _is_amount(budget, kpi_periods, "cost_of_revenue"))
    kpi_opex = _is_amount(outlook, kpi_periods, "total_opex")
    if kpi_opex == 0:
        kpi_opex = (
            _is_amount(outlook, kpi_periods, "sales_and_marketing")
            + _is_amount(outlook, kpi_periods, "research_and_development")
            + _is_amount(outlook, kpi_periods, "general_and_administrative")
            + _is_amount(outlook, kpi_periods, "customer_success")
        )
    kpi_opex_b = _is_amount(budget, kpi_periods, "total_opex") or (
        _is_amount(budget, kpi_periods, "sales_and_marketing")
        + _is_amount(budget, kpi_periods, "research_and_development")
        + _is_amount(budget, kpi_periods, "general_and_administrative")
        + _is_amount(budget, kpi_periods, "customer_success")
    )
    kpi_ebitda = _is_amount(outlook, kpi_periods, "ebitda") or (kpi_gp - kpi_opex)
    kpi_ebitda_b = _is_amount(budget, kpi_periods, "ebitda") or (kpi_gp_b - kpi_opex_b)
    kpi_gm_pct = (_safe_div(kpi_gp, kpi_rev) or Decimal("0")) * 100
    kpi_gm_pct_b = (_safe_div(kpi_gp_b, kpi_rev_b) or Decimal("0")) * 100
    kpi_sm = _is_amount(outlook, kpi_periods, "sales_and_marketing")
    kpi_sm_b = _is_amount(budget, kpi_periods, "sales_and_marketing")
    kpi_sm_pct = (_safe_div(kpi_sm, kpi_rev) or Decimal("0")) * 100
    kpi_sm_pct_b = (_safe_div(kpi_sm_b, kpi_rev_b) or Decimal("0")) * 100

    rev_prior = sum_metric(outlook, ctx.prior_month, "revenue") if ctx.prior_month else Decimal("0")
    rev_cur = sum_metric(outlook, ctx.current_month, "revenue")
    rev_growth = _pct_change(rev_cur, rev_prior)
    gm_pct = _safe_div(gp_o, rev_o)
    ebitda_margin = _safe_div(ebitda_o, rev_o)
    rev_var, rev_var_pct = variance(rev_o, rev_b)
    ebitda_var, ebitda_var_pct = variance(ebitda_o, ebitda_b)

    def kpi(
        key: str,
        label: str,
        value: Decimal,
        fmt: str = "currency",
        compare: Decimal | None = None,
        delta: str = "",
        tone: str = "neu",
        spark: list[Decimal] | None = None,
        compare_label: str = "vs Budget",
    ) -> KpiCard:
        return KpiCard(
            key=key,
            label=label,
            value=value,
            value_format=fmt,  # type: ignore[arg-type]
            compare_value=compare,
            compare_label=compare_label,
            delta_label=delta,
            tone=tone,  # type: ignore[arg-type]
            sparkline=spark or [],
        )

    spark_rev = [m.revenue_outlook for m in monthly]
    kpis = [
        kpi("revenue", "Revenue", kpi_rev, compare=kpi_rev_b, spark=spark_rev),
        kpi("gross_profit", "Gross Profit", kpi_gp, compare=kpi_gp_b),
        kpi("gross_margin_pct", "Gross Margin %", kpi_gm_pct, "percent", compare=kpi_gm_pct_b),
        kpi("total_opex", "Total OpEx", kpi_opex, compare=kpi_opex_b),
        kpi("ebitda", "EBITDA", kpi_ebitda, compare=kpi_ebitda_b),
        kpi(
            "sm_pct_rev",
            "S&M % Rev",
            kpi_sm_pct,
            "percent",
            compare=kpi_sm_pct_b,
            delta=f"{float(kpi_sm_pct - kpi_sm_pct_b):+.1f}pp",
            compare_label="vs budget",
        ),
    ]

    bridge_sm = bridge_rd = bridge_ga = Decimal("0")
    for p in ctx.current_month:
        s, r, g = _opex_stacks_for_period(gl_out_entries, p)
        bridge_sm += s
        bridge_rd += r
        bridge_ga += g
    if bridge_sm == 0 and bridge_rd == 0 and bridge_ga == 0:
        bridge_sm = kpi_sm
        bridge_rd = _is_amount(outlook, ctx.current_month, "research_and_development")
        bridge_ga = (
            _is_amount(outlook, ctx.current_month, "general_and_administrative")
            + _is_amount(outlook, ctx.current_month, "customer_success")
        )

    outlook_label = (
        f"GL detail · {_period_scope_label(ctx, period_mode)} vs budget"
        if gl_primary
        else f"FY Outlook (Actual through {ctx.as_of_period} + Forecast)"
    )
    commentary = [
        CommentaryBlock(
            section="Management P&L",
            observation=(
                f"{outlook_label}: revenue {_fmt_money(rev_o)} vs budget {_fmt_money(rev_b)} "
                f"({float((rev_var_pct or 0) * 100):+.1f}%). Gross margin {float((gm_pct or 0) * 100):.1f}%."
            ),
            implication=f"EBITDA {_fmt_money(ebitda_o)} vs budget {_fmt_money(ebitda_b)} on a full-year comparable basis.",
            recommendation="Prioritize departments with favorable FY outlook vs budget variance and stable gross margin.",
        )
    ]

    return ManagementPlDashboardResponse(
        organization_id=str(organization_id),
        as_of_period=ctx.as_of_period,
        period_mode=period_mode,
        view_mode=view_mode,  # type: ignore[arg-type]
        department_filter=department,
        outlook_label=outlook_label,
        kpis=kpis,
        monthly_series=monthly,
        pl_lines=pl_lines,
        ebitda_waterfall=_ebitda_waterfall(kpi_rev, kpi_cogs, bridge_sm, bridge_rd, bridge_ga),
        department_variances=_department_variances(outlook, budget, ctx, gl_act_agg, gl_bud_agg),
        department_summary=dept_summary,
        gl_by_department=_gl_by_department(
            _aggregate_gl_by_department(gl_act_entries),
            _aggregate_gl_by_department(gl_bud_entries),
            ctx,
            gl_forecast=_aggregate_gl_by_department(gl_fcst_entries),
        ),
        commentary=commentary,
        validations=_validations(
            outlook,
            budget,
            gl_out,
            ctx,
            raw_gl_count=len(raw_gl),
            gl_outlook_entry_count=len(gl_out_entries),
            gl_outlook_maps=gl_outlook_maps,
            workforce_mode=wf_active,
            gl_primary=gl_primary,
        ),
        metadata={
            "comparison": "period_actual_vs_period_budget",
            "period_scope_label": _period_scope_label(ctx, period_mode),
            "closed_periods": list(ctx.closed_periods),
            "selected_period": ctx.as_of_period if period_mode == "month" else None,
            "gl_primary_mode": gl_primary,
            "primary_source": "gl_detail" if gl_primary else "hybrid_income_statement",
            "closed_through": ctx.as_of_period,
            "gl_actuals_row_count": len(raw_gl),
            "gl_outlook_entry_count": len(gl_out_entries),
            "workforce_pnl_overlay": wf_active,
            "outlook_gl_periods": sum(1 for p in ctx.fy_periods if _gl_period_has_data(gl_outlook_maps.get(p, {}))),
            "budget_gl_periods": sum(1 for p in ctx.fy_periods if _gl_period_has_data(gl_budget_maps.get(p, {}))),
            "gl_revenue_periods": sum(
                1 for p in ctx.fy_periods if gl_outlook_maps.get(p, {}).get("revenue", Decimal("0")) != 0
            ),
            "gl_cogs_periods": sum(
                1 for p in ctx.fy_periods if gl_outlook_maps.get(p, {}).get("cost_of_revenue", Decimal("0")) != 0
            ),
            "sources": (
                [
                    "gl_actuals",
                    "forecast_gl_detail",
                    "mrr_waterfall",
                ]
                + (["income_statement_fallback"] if not gl_primary else [])
                + (["workforce_pnl_people_cost_lines"] if wf_active else [])
            ),
        },
    )


def _fmt_money(value: Decimal) -> str:
    v = float(value)
    if abs(v) >= 1_000_000:
        return f"${v / 1_000_000:.2f}M"
    if abs(v) >= 1_000:
        return f"${v / 1_000:.0f}K"
    return f"${v:,.0f}"
