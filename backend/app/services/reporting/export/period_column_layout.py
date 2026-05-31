"""Wide export layout with Actual (closed) + Forecast (open) and summary rollups."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.services.reporting.export.effective_periods import (
    export_fiscal_periods,
    include_forecast_column,
    is_closed_period,
    period_display_values,
)
from app.services.reporting.export.period_comparisons import variance
from app.services.reporting.period_utils import period_to_date, to_period

ScenarioPresence = dict[str, bool]


@dataclass(frozen=True)
class PeriodColumnSpec:
    key: str
    header: str


@dataclass
class PeriodColumnGroup:
    period: str
    columns: list[PeriodColumnSpec] = field(default_factory=list)


@dataclass
class WidePeriodLayout:
    periods: list[str]
    groups: list[PeriodColumnGroup]
    label_column_count: int
    summary_columns: list[PeriodColumnSpec] = field(default_factory=list)
    trailing_columns: list[str] = field(default_factory=lambda: ["Commentary", "Driver / Explanation", "Owner"])

    @property
    def headers(self) -> list[str]:
        row: list[str] = []
        for group in self.groups:
            row.extend(col.header for col in group.columns)
        row.extend(col.header for col in self.summary_columns)
        row.extend(self.trailing_columns)
        return row


def period_short_label(period: str, *, anchor_year: int | None = None) -> str:
    dt = period_to_date(period)
    if anchor_year is not None and dt.year != anchor_year:
        return dt.strftime("%b %y")
    return dt.strftime("%b")


def scenario_presence_by_period(
    rows: list,
    periods: list[str],
    *,
    period_attr: str = "period",
    scenario_attr: str = "scenario",
) -> dict[str, ScenarioPresence]:
    wanted = set(periods)
    out: dict[str, ScenarioPresence] = {
        p: {"actual": False, "budget": False, "forecast": False} for p in periods
    }
    for row in rows:
        raw_period = getattr(row, period_attr, None)
        if raw_period is None:
            continue
        period = to_period(str(raw_period)[:7] if not isinstance(raw_period, str) else raw_period)
        if period not in wanted:
            continue
        scenario = str(getattr(row, scenario_attr, "")).strip().lower()
        if scenario == "actual":
            out[period]["actual"] = True
        elif scenario == "budget":
            out[period]["budget"] = True
        elif scenario == "forecast":
            out[period]["forecast"] = True
    return out


def build_wide_period_layout(
    periods: list[str],
    presence_by_period: dict[str, ScenarioPresence],
    *,
    as_of_period: str,
    include_summary: bool = True,
) -> WidePeriodLayout:
    anchor_year = period_to_date(periods[0]).year if periods else None
    as_of = to_period(as_of_period)
    groups: list[PeriodColumnGroup] = []

    for period in periods:
        presence = presence_by_period.get(period, {"actual": False, "budget": False, "forecast": False})
        short = period_short_label(period, anchor_year=anchor_year)
        cols: list[PeriodColumnSpec] = []
        closed = is_closed_period(period, as_of, has_actual_rows=presence.get("actual", False))

        if closed:
            cols.append(PeriodColumnSpec("actual", f"{short} Actual"))
            if presence.get("budget"):
                cols.append(PeriodColumnSpec("budget", f"{short} Budget"))
                cols.append(PeriodColumnSpec("var_bud", f"{short} Var $"))
                cols.append(PeriodColumnSpec("var_bud_pct", f"{short} Var %"))
            if include_forecast_column(
                period, as_of, has_actual_rows=True, has_forecast_rows=presence.get("forecast", False)
            ):
                cols.append(PeriodColumnSpec("forecast", f"{short} Fcst"))
                cols.append(PeriodColumnSpec("var_fc", f"{short} Act vs Fcst $"))
                cols.append(PeriodColumnSpec("var_fc_pct", f"{short} Act vs Fcst %"))
        else:
            if presence.get("budget"):
                cols.append(PeriodColumnSpec("budget", f"{short} Budget"))
            if presence.get("forecast"):
                cols.append(PeriodColumnSpec("forecast", f"{short} Outlook"))
                cols.append(PeriodColumnSpec("outlook", f"{short} Outlook"))

        if cols:
            groups.append(PeriodColumnGroup(period=period, columns=cols))

    summary: list[PeriodColumnSpec] = []
    if include_summary:
        summary = [
            PeriodColumnSpec("cm_actual", "CM Actual"),
            PeriodColumnSpec("cm_budget", "CM Budget"),
            PeriodColumnSpec("cm_var_bud", "CM Var $"),
            PeriodColumnSpec("mom_delta", "MoM Δ"),
            PeriodColumnSpec("qtd_actual", "QTD Actual"),
            PeriodColumnSpec("qtd_budget", "QTD Budget"),
            PeriodColumnSpec("qtd_var_bud", "QTD Var $"),
            PeriodColumnSpec("ytd_actual", "YTD Actual"),
            PeriodColumnSpec("ytd_budget", "YTD Budget"),
            PeriodColumnSpec("ytd_var_bud", "YTD Var $"),
        ]

    return WidePeriodLayout(
        periods=periods,
        groups=groups,
        label_column_count=1,
        summary_columns=summary,
    )


def build_display_by_period(
    raw_by_period: dict[str, dict[str, Decimal]],
    periods: list[str],
    presence_by_period: dict[str, ScenarioPresence],
    as_of_period: str,
) -> dict[str, dict[str, Decimal | None]]:
    """Apply effective Actual/Forecast rules — no misleading $0 forecast on closed months."""
    out: dict[str, dict[str, Decimal | None]] = {}
    for period in periods:
        raw = raw_by_period.get(period, {"actual": Decimal("0"), "budget": Decimal("0"), "forecast": Decimal("0")})
        presence = presence_by_period.get(period, {"actual": False, "budget": False, "forecast": False})
        display = period_display_values(
            raw.get("actual", Decimal("0")),
            raw.get("budget", Decimal("0")),
            raw.get("forecast", Decimal("0")),
            period=period,
            as_of_period=as_of_period,
            has_actual_rows=presence.get("actual", False),
            has_budget_rows=presence.get("budget", False),
            has_forecast_rows=presence.get("forecast", False),
        )
        var_bud, var_bud_pct = variance(
            display.get("actual") or Decimal("0"),
            display.get("budget") or Decimal("0"),
        )
        var_fc, var_fc_pct = variance(
            display.get("actual") or Decimal("0"),
            display.get("forecast") or Decimal("0"),
        )
        out[period] = {
            **display,
            "var_bud": var_bud if display.get("actual") is not None and display.get("budget") is not None else None,
            "var_bud_pct": var_bud_pct,
            "var_fc": var_fc if display.get("forecast") is not None and display.get("actual") is not None else None,
            "var_fc_pct": var_fc_pct,
        }
    return out


def export_periods_for_bundle(start_period: str, end_period: str, as_of_period: str) -> list[str]:
    return export_fiscal_periods(start_period, end_period)
