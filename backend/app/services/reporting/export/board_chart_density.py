"""Chart/table density controls and axis formatting for executive decks."""

from __future__ import annotations

import math
from decimal import Decimal

from app.services.board_package.schemas import ChartSpec, TableSpec
from app.services.reporting.export.reporting_period_engine import trend_axis_labels


def _scale_series(values: list[float]) -> tuple[list[float], str]:
    """Scale to $K or $M for readable y-axis."""
    if not values:
        return values, ""
    peak = max(abs(v) for v in values)
    if peak >= 1_000_000:
        return [round(v / 1_000_000, 2) for v in values], "$M"
    if peak >= 10_000:
        return [round(v / 1_000, 1) for v in values], "$K"
    return [round(v, 0) for v in values], "$"


def thin_categories(categories: list[str], series: dict[str, list[float]], *, max_points: int = 8) -> tuple[list[str], dict[str, list[float]]]:
    if len(categories) <= max_points:
        return categories, series
    # keep first, last, and evenly spaced interior
    idxs = [0]
    step = (len(categories) - 1) / (max_points - 1)
    for i in range(1, max_points - 1):
        idxs.append(int(round(i * step)))
    idxs.append(len(categories) - 1)
    idxs = sorted(set(idxs))
    new_cats = [categories[i] for i in idxs]
    new_series: dict[str, list[float]] = {}
    for name, vals in series.items():
        new_series[name] = [vals[i] if i < len(vals) else 0.0 for i in idxs]
    return new_cats, new_series


def collapse_categories_top_other(
    categories: list[str],
    series: dict[str, list[float]],
    *,
    top_n: int = 5,
    other_label: str = "Other",
) -> tuple[list[str], dict[str, list[float]]]:
    if len(categories) <= top_n + 1:
        return categories, series
    totals = [sum(series.get(k, [0.0] * len(categories))[i] for k in series) for i in range(len(categories))]
    ranked = sorted(range(len(categories)), key=lambda i: abs(totals[i]), reverse=True)
    keep = ranked[:top_n]
    other_idx = [i for i in range(len(categories)) if i not in keep]
    new_cats = [categories[i] for i in keep] + [other_label]
    new_series: dict[str, list[float]] = {}
    for name, vals in series.items():
        kept_vals = [vals[i] if i < len(vals) else 0.0 for i in keep]
        other_val = sum(vals[i] if i < len(vals) else 0.0 for i in other_idx)
        new_series[name] = kept_vals + [other_val]
    return new_cats, new_series


def _is_percent_series(values: list[float], label: str) -> bool:
    if "%" in label.lower():
        return True
    if not values:
        return False
    peak = max(abs(v) for v in values)
    return peak <= 1.5 and all(abs(v) <= 1.5 for v in values)


def prepare_chart_for_executive(
    spec: ChartSpec,
    *,
    max_categories: int = 7,
    movement_type: str | None = None,
    is_time_series: bool = False,
) -> ChartSpec:
    """Apply density limits and axis-friendly scaling."""
    cats = list(spec.categories)
    series = {k: list(v) for k, v in spec.series.items()}
    if len(cats) > max_categories + 2:
        cats, series = collapse_categories_top_other(cats, series, top_n=max(4, max_categories - 2))
    cats, series = thin_categories(cats, series, max_points=max_categories)

    scaled: dict[str, list[float]] = {}
    unit = ""
    for name, vals in series.items():
        if _is_percent_series(vals, name) or _is_percent_series(vals, spec.y_axis_label or ""):
            scaled[name] = [round(v * 100, 1) if abs(v) <= 1.5 else round(v, 1) for v in vals]
            unit = "%"
        else:
            s, u = _scale_series(vals)
            scaled[name] = s
            if u and not unit:
                unit = u

    y_label = spec.y_axis_label or ""
    if unit == "%":
        y_label = "%" if not y_label or "$" in y_label else y_label
    elif unit and unit not in y_label:
        y_label = f"{y_label} ({unit})".strip() if y_label else unit

    from app.services.reporting.export.executive_reporting_governance import (
        chart_type_for_kind,
        select_chart_kind,
    )

    kind = select_chart_kind(
        category_count=len(cats),
        is_time_series=is_time_series or spec.chart_type == "line",
        movement_type=movement_type,
    )
    chart_type = chart_type_for_kind(kind)

    title = spec.title[:72]
    return spec.model_copy(
        update={
            "chart_type": chart_type,  # type: ignore[arg-type]
            "categories": cats,
            "series": scaled,
            "y_axis_label": y_label or spec.y_axis_label,
            "title": title,
            "max_categories": max_categories,
        }
    )


def prepare_trend_chart(
    title: str,
    periods: list[str],
    series: dict[str, list[float]],
    *,
    chart_type: str = "line",
    max_points: int = 8,
) -> ChartSpec:
    labels = trend_axis_labels(periods, max_points=max_points)
    if len(labels) != len(periods):
        # quarterly collapse — sum series into quarter buckets
        from collections import defaultdict

        buckets: dict[str, list[int]] = defaultdict(list)
        for i, p in enumerate(periods):
            month = int(p[5:7])
            q = (month - 1) // 3 + 1
            key = f"Q{q}'{p[2:4]}"
            buckets[key].append(i)
        new_series: dict[str, list[float]] = {}
        for name, vals in series.items():
            new_series[name] = [sum(vals[i] for i in idxs if i < len(vals)) for idxs in buckets.values()]
        cats = list(buckets.keys())[:max_points]
    else:
        cats = [_month_label(p) for p in periods[:max_points]]
        new_series = {k: v[: len(cats)] for k, v in series.items()}

    spec = ChartSpec(
        chart_type=chart_type,  # type: ignore[arg-type]
        title=title,
        categories=cats,
        series=new_series,
        y_axis_label="ARR",
    )
    return prepare_chart_for_executive(spec, max_categories=max_points)


def _month_label(period: str) -> str:
    m = int(period[5:7])
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return names[m - 1] if 1 <= m <= 12 else period[5:7]


def rank_table_top_movers(
    headers: list[str],
    rows: list[list[str]],
    *,
    max_rows: int = 5,
    value_col: int = 1,
) -> TableSpec:
    """Keep top rows by absolute numeric value in value_col."""
    if len(rows) <= max_rows:
        return TableSpec(headers=headers, rows=rows)

    def _mag(row: list[str]) -> float:
        if value_col >= len(row):
            return 0.0
        raw = row[value_col].replace("$", "").replace(",", "").replace("(", "-").replace(")", "")
        try:
            return abs(float(raw))
        except ValueError:
            return 0.0

    ranked = sorted(rows, key=_mag, reverse=True)
    kept = ranked[: max_rows - 1]
    kept.append(["Other", f"+{len(rows) - len(kept)} rows", "See appendix"])
    return TableSpec(headers=headers, rows=kept)


def truncate_bullet(text: str, *, max_len: int = 120) -> str:
    t = " ".join(text.split())
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"
