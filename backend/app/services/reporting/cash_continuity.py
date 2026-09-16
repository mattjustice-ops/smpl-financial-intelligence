"""Cash continuity validation across BS, CFS, bridge, and forecast pickup.

Product rule (one cash spine):
  BS cash → CFS beginning / ending / net_change → bridge foots to that net change.
  Forecast month-1 beginning cash = last closed actual ending cash.

Line-item recreation of CFS from IS+BS is allowed to carry small mapping residuals
(SBC, capex definition); the cash spine itself must match.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.services.reporting.period_utils import to_period
from app.services.reporting.three_statement_payload import (
    BS_FIELD_SPECS,
    CFS_FIELD_SPECS,
    IS_FIELD_SPECS,
    _calculate_cfs_row,
    _enrich_is,
    _normalize_bs_display,
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
    is_data = _period_dict_from_field_specs(
        _read_statement_table(db, organization_id, f"{prefix}_income_statement"),
        IS_FIELD_SPECS,
    )
    for row in is_data.values():
        _enrich_is(row)
    bs_data = _period_dict_from_field_specs(
        _read_statement_table(db, organization_id, f"{prefix}_balance_sheet"),
        BS_FIELD_SPECS,
    )
    for row in bs_data.values():
        _normalize_bs_display(row)
    cfs_data = _period_dict_from_field_specs(
        _read_statement_table(db, organization_id, f"{prefix}_cash_flow_statement"),
        CFS_FIELD_SPECS,
    )
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
            prior = _resolve_prior_bs(period, bs_data, cross_scenario_bs=cross)
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
            # Bridge footing: beg + collections - outflows ≈ ending (disclose residual)
            beg = brow.get("beginning_cash")
            end = brow.get("ending_cash")
            if beg is None or end is None:
                continue
            collections = brow.get("collections") or 0.0
            outflows = sum(
                abs(brow.get(k) or 0.0)
                for k in (
                    "payroll",
                    "commission",
                    "vendor",
                    "tax",
                    "interest",
                    "other_operating",
                    "capex",
                )
            )
            financing = brow.get("financing") or 0.0
            implied = beg + collections - outflows + financing
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
        _add(
            report,
            code="C5",
            period=first_fc,
            scenario="Forecast",
            label=f"Forecast opens on actual {as_of_p} ending cash",
            left=fc_beg,
            right=close_end,
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
