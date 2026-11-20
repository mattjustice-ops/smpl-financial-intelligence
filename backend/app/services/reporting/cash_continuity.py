"""Cash continuity validation across BS, CFS, bridge, and forecast pickup.

Product rule (one cash spine):
  BS cash → CFS beginning / ending / net_change → bridge foots to that net change.
  Forecast month-1 beginning cash = last closed actual ending cash.
  Each open forecast month keeps its own cash movement and ARR movements (C6, C7).

Line-item recreation of CFS from IS+BS is allowed to carry small mapping residuals
(SBC, capex definition); the cash spine itself must match.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.services.reporting.gl_balance_sheet import gl_balance_sheet_and_cash_flow_by_period
from app.services.reporting.gl_income_statement import gl_income_statement_by_period
from app.services.reporting.period_utils import to_period
from app.services.reporting.three_statement_payload import (
    BS_FIELD_SPECS,
    CFS_FIELD_SPECS,
    _aggregate_mrr_by_period,
    _calculate_cfs_row,
    _enrich_is,
    _gl_statement_rows,
    _normalize_bs_display,
    _normalize_mrr_metrics,
    _period_dict_from_field_specs,
    _read_statement_table,
    _resolve_prior_bs,
    build_cash_bridge_data,
)


TOL_DOLLAR = 1.0  # $1 — spine must match to the cent in practice; $1 absorbs float noise


@dataclass
class CashCheck:
    code: str
    period: str
    scenario: str
    label: str
    left: float | None
    right: float | None
    ok: bool
    detail: str = ""


@dataclass
class CashContinuityReport:
    checks: list[CashCheck] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)

    @property
    def failures(self) -> list[CashCheck]:
        return [c for c in self.checks if not c.ok]

    def summary(self, *, max_failures: int = 12) -> str:
        fails = self.failures
        if not fails:
            return f"cash continuity ok ({len(self.checks)} checks)"
        head = "; ".join(
            f"[{c.code}] {c.scenario} {c.period} {c.label}: {c.left} vs {c.right}"
            for c in fails[:max_failures]
        )
        more = f" (+{len(fails) - max_failures} more)" if len(fails) > max_failures else ""
        return f"{len(fails)} cash continuity failures - {head}{more}"


def _close(a: float | None, b: float | None, tol: float = TOL_DOLLAR) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= tol


def _add(
    report: CashContinuityReport,
    *,
    code: str,
    period: str,
    scenario: str,
    label: str,
    left: float | None,
    right: float | None,
    detail: str = "",
) -> None:
    report.checks.append(
        CashCheck(
            code=code,
            period=period,
            scenario=scenario,
            label=label,
            left=left,
            right=right,
            ok=_close(left, right),
            detail=detail,
        )
    )


def _load_statements(
    db: Session, organization_id: uuid.UUID, prefix: str
) -> tuple[dict[str, dict[str, float | None]], dict[str, dict[str, float | None]], dict[str, dict[str, float | None]]]:
    is_data = gl_income_statement_by_period(db, organization_id, prefix)
    for row in is_data.values():
        _enrich_is(row)
    bs_rows, cfs_rows = _gl_statement_rows(db, organization_id, prefix)
    bs_data = _period_dict_from_field_specs(bs_rows, BS_FIELD_SPECS)
    for row in bs_data.values():
        _normalize_bs_display(row)
    cfs_data = _period_dict_from_field_specs(cfs_rows, CFS_FIELD_SPECS)
    return is_data, bs_data, cfs_data


def validate_cash_continuity(
    db: Session,
    organization_id: uuid.UUID,
    *,
    as_of: str,
    start_period: str,
    end_period: str,
) -> CashContinuityReport:
    """Run the cash-spine checks users should see on an Overview continuity panel."""
    report = CashContinuityReport()
    as_of_p = to_period(as_of)
    actual_is, actual_bs, actual_cfs = _load_statements(db, organization_id, "actual")
    budget_is, budget_bs, budget_cfs = _load_statements(db, organization_id, "budget")
    forecast_is, forecast_bs, forecast_cfs = _load_statements(db, organization_id, "forecast")

    # C1: CFS ending cash ↔ BS cash (statement SoT)
    for scenario, bs, cfs in (
        ("Actual", actual_bs, actual_cfs),
        ("Budget", budget_bs, budget_cfs),
        ("Forecast", forecast_bs, forecast_cfs),
    ):
        for period, crow in cfs.items():
            if not (start_period <= period <= end_period):
                continue
            if scenario == "Actual" and period > as_of_p:
                continue
            _add(
                report,
                code="C1",
                period=period,
                scenario=scenario,
                label="CFS ending_cash ↔ BS cash",
                left=crow.get("ending_cash"),
                right=(bs.get(period) or {}).get("cash"),
            )

    # C2: CFS cash spine ↔ IS+BS derivation (beg / end / net)
    for scenario, is_data, bs_data, cfs_data, cross in (
        ("Actual", actual_is, actual_bs, actual_cfs, None),
        ("Budget", budget_is, budget_bs, budget_cfs, actual_bs),
        ("Forecast", forecast_is, forecast_bs, forecast_cfs, actual_bs),
    ):
        for period, crow in cfs_data.items():
            if not (start_period <= period <= end_period):
                continue
            if scenario == "Actual" and period > as_of_p:
                continue
            prior = _resolve_prior_bs(
                period, bs_data, cross_scenario_bs=cross, closed_through=as_of_p if scenario == "Forecast" else None
            )
            derived = _calculate_cfs_row(is_data.get(period, {}), bs_data.get(period, {}), prior)
            for key, label in (
                ("beginning_cash", "CFS beg ↔ derived from prior BS cash"),
                ("ending_cash", "CFS end ↔ derived from BS cash"),
                ("net_change", "CFS net_change ↔ BS cash movement"),
            ):
                _add(
                    report,
                    code="C2",
                    period=period,
                    scenario=scenario,
                    label=label,
                    left=crow.get(key),
                    right=derived.get(key),
                )

    # C3: Bridge balances ↔ CFS (after alignment Budget should pass; raw bridge may fail)
    bridge = build_cash_bridge_data(
        db, organization_id, start_period=start_period, end_period=end_period
    )
    for scenario, cfs_data in (
        ("Actual", actual_cfs),
        ("Budget", budget_cfs),
        ("Forecast", forecast_cfs),
    ):
        for period, brow in (bridge.get(scenario) or {}).items():
            if scenario == "Actual" and period > as_of_p:
                continue
            crow = cfs_data.get(period) or {}
            if not crow:
                continue
            _add(
                report,
                code="C3",
                period=period,
                scenario=scenario,
                label="Bridge ending_cash ↔ CFS ending_cash",
                left=brow.get("ending_cash"),
                right=crow.get("ending_cash"),
            )
            # Actual bridge rows still use their own beginning and ending, so the
            # lines have to reach that ending. Budget and Forecast beginning and
            # ending are copied from the statement, and the lines are not rebuilt,
            # so a miss there is not a close item.
            if scenario != "Actual":
                continue
            beg = brow.get("beginning_cash")
            end = brow.get("ending_cash")
            if beg is None or end is None:
                continue
            collections = brow.get("collections") or 0.0
            # Payroll, vendor, tax, interest, and capex are outflows.
            # other_operating is signed: a negative amount is cash that came in.
            # Absolute value turns that inflow into an outflow and the bridge misses by twice it.
            other = brow.get("other_operating") or 0.0
            financing = brow.get("financing") or 0.0
            implied = (
                beg
                + collections
                - (brow.get("payroll") or 0.0)
                - (brow.get("commission") or 0.0)
                - (brow.get("vendor") or 0.0)
                - (brow.get("tax") or 0.0)
                - (brow.get("interest") or 0.0)
                - (brow.get("capex") or 0.0)
                - other
                + financing
            )
            _add(
                report,
                code="C4",
                period=period,
                scenario=scenario,
                label="Bridge foots (beg+collections-outflows+financing ↔ ending)",
                left=implied,
                right=end,
                detail="financing is the residual plug when present; ops flows should carry the CFS net",
            )

    # C5: Forecast picks up where actuals leave off
    next_periods = sorted(p for p in forecast_cfs if p > as_of_p)
    if next_periods:
        first_fc = next_periods[0]
        close_end = (actual_cfs.get(as_of_p) or {}).get("ending_cash")
        if close_end is None:
            close_end = (actual_bs.get(as_of_p) or {}).get("cash")
        fc_beg = (forecast_cfs.get(first_fc) or {}).get("beginning_cash")
        if fc_beg is None:
            fc_beg = (forecast_bs.get(first_fc) or {}).get("cash")
            # forecast BS cash is ending; prefer CFS/bridge beginning
            br = (bridge.get("Forecast") or {}).get(first_fc) or {}
            if br.get("beginning_cash") is not None:
                fc_beg = br.get("beginning_cash")
        if close_end is None:
            report.checks.append(
                CashCheck(
                    code="C5",
                    period=as_of_p,
                    scenario="Actual",
                    label="This close has no cash yet",
                    left=fc_beg,
                    right=None,
                    ok=False,
                    detail="A missing close balance is not zero.",
                )
            )
        else:
            _add(
                report,
                code="C5",
                period=first_fc,
                scenario="Forecast",
                label=f"Forecast opens on actual {as_of_p} ending cash",
                left=fc_beg,
                right=close_end,
            )

    # C6: An open forecast month moves cash by the forecast's own entries for that month, so opening it on the
    # close does not change what the forecast says the month does.
    _, planned_cfs = gl_balance_sheet_and_cash_flow_by_period(db, organization_id, "forecast")
    _, rolled_cfs = gl_balance_sheet_and_cash_flow_by_period(db, organization_id, "forecast", roll_from_close=True)
    for period in sorted(p for p in rolled_cfs if p > as_of_p and start_period <= p <= end_period):
        _add(
            report,
            code="C6",
            period=period,
            scenario="Forecast",
            label="Forecast month keeps its own cash movement",
            left=(rolled_cfs.get(period) or {}).get("net_change_in_cash"),
            right=(planned_cfs.get(period) or {}).get("net_change_in_cash"),
        )

    # C7: An open forecast ARR month adds up on its own: beginning plus its movements is its ending. The month is
    # rolled from the close by its change, so a row that does not add up, or a movement that is not loaded, fails here.
    forecast_mrr = _aggregate_mrr_by_period(_read_statement_table(db, organization_id, "forecast_mrr_waterfall"))
    for period in sorted(p for p in forecast_mrr if p > as_of_p and start_period <= p <= end_period):
        m = _normalize_mrr_metrics(forecast_mrr[period])
        parts = (m.get("arr_bop"), m.get("arr_nb"), m.get("arr_exp"), m.get("arr_react"), m.get("arr_cont"), m.get("arr_churn"))
        _add(
            report,
            code="C7",
            period=period,
            scenario="Forecast",
            label="Forecast ARR beginning plus movements equals its ending",
            left=None if None in parts else parts[0] + parts[1] + parts[2] + parts[3] - parts[4] - parts[5],
            right=m.get("arr_eop"),
        )

    return report


def cash_continuity_payload(report: CashContinuityReport) -> dict[str, Any]:
    return {
        "ok": report.ok,
        "summary": report.summary(),
        "checks_run": len(report.checks),
        "failures": [
            {
                "code": c.code,
                "period": c.period,
                "scenario": c.scenario,
                "label": c.label,
                "left": c.left,
                "right": c.right,
                "detail": c.detail,
            }
            for c in report.failures
        ],
    }
