"""Shared wide-format Excel writers (periods as columns)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.services.reporting.export.comparison_pivot import pivot_waterfall_wide
from app.services.reporting.export.period_column_layout import (
    ScenarioPresence,
    WidePeriodLayout,
    build_display_by_period,
    build_wide_period_layout,
    export_periods_for_bundle,
    scenario_presence_by_period,
)
from app.services.reporting.export.period_views import build_summary_metrics
from app.services.reporting.export.schemas import ReportingBundle


def _write_period_header_row(ws, row: int, label_headers: list[str], layout: WidePeriodLayout, fmt: Any) -> None:
    col = 0
    for label in label_headers:
        ws.write(row, col, label, fmt.header)
        col += 1
    for header in layout.headers:
        ws.write(row, col, header, fmt.header)
        col += 1


def _write_cell(ws, row: int, col: int, value: Decimal | None, spec_key: str, fmt: Any, *, use_currency: bool) -> None:
    if value is None:
        return
    if spec_key.endswith("_pct"):
        ws.write(row, col, float(value), fmt.pct)
    elif spec_key in {"var_bud", "var_fc", "cm_var_bud", "qtd_var_bud", "ytd_var_bud", "mom_delta"}:
        vfmt = fmt.var_fav if value >= 0 else fmt.var_unfav
        ws.write(row, col, float(value), vfmt)
    else:
        ws.write(row, col, float(value), fmt.currency if use_currency else fmt.text)


def _write_wide_amounts(
    ws,
    row: int,
    col_start: int,
    layout: WidePeriodLayout,
    by_period: dict[str, dict[str, Decimal | None]],
    fmt: Any,
    *,
    use_currency: bool = True,
    as_of_period: str,
) -> None:
    col = col_start
    for group in layout.groups:
        raw = by_period.get(group.period, {})
        for spec in group.columns:
            _write_cell(ws, row, col, raw.get(spec.key), spec.key, fmt, use_currency=use_currency)
            col += 1

    summary = build_summary_metrics(by_period, as_of_period)
    for spec in layout.summary_columns:
        key = spec.key
        if key == "cm_actual":
            val = summary["actual"]["current_month"]
        elif key == "cm_budget":
            val = summary["budget"]["current_month"]
        elif key == "cm_var_bud":
            a, b = summary["actual"]["current_month"], summary["budget"]["current_month"]
            val = (a - b) if a is not None and b is not None else None
        elif key == "mom_delta":
            val = summary["actual"]["mom_delta"]
        elif key == "qtd_actual":
            val = summary["actual"]["qtd"]
        elif key == "qtd_budget":
            val = summary["budget"]["qtd"]
        elif key == "qtd_var_bud":
            a, b = summary["actual"]["qtd"], summary["budget"]["qtd"]
            val = (a - b) if a is not None and b is not None else None
        elif key == "ytd_actual":
            val = summary["actual"]["ytd"]
        elif key == "ytd_budget":
            val = summary["budget"]["ytd"]
        elif key == "ytd_var_bud":
            a, b = summary["actual"]["ytd"], summary["budget"]["ytd"]
            val = (a - b) if a is not None and b is not None else None
        else:
            val = None
        _write_cell(ws, row, col, val, key, fmt, use_currency=use_currency)
        col += 1


def layout_for_rows(
    bundle: ReportingBundle,
    rows: list,
    *,
    label_column_count: int = 1,
) -> tuple[list[str], WidePeriodLayout, dict[str, ScenarioPresence]]:
    periods = export_periods_for_bundle(bundle.start_period, bundle.end_period, bundle.as_of_period)
    presence = scenario_presence_by_period(rows, periods)
    layout = build_wide_period_layout(periods, presence, as_of_period=bundle.as_of_period)
    layout.label_column_count = label_column_count
    return periods, layout, presence


def build_display_rows(
    raw_rows: list,
    periods: list[str],
    presence: dict,
    as_of_period: str,
    *,
    pivot_fn,
) -> dict[str, dict[str, dict[str, Decimal | None]]]:
    """line_key -> display by_period."""
    wide = pivot_fn(raw_rows, periods)
    out: dict[str, dict] = {}
    for item in wide:
        key = item.get("line_item") or item.get("waterfall_type") or item.get("section")
        raw_by = item["by_period"]
        out[str(key)] = build_display_by_period(raw_by, periods, presence, as_of_period)
    return out


def subtitle_for_bundle(bundle: ReportingBundle) -> str:
    as_of = bundle.as_of_period
    return (
        f"{bundle.organization_name or bundle.organization_id} | "
        f"Actual through {as_of} vs Budget | Forecast outlook for open months | MD&A export"
    )
