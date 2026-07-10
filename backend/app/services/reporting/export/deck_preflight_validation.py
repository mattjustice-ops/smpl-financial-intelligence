"""Pre-flight validation for Prompt 5 deck payload — catches COGS/revenue swaps before Claude."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.services.reporting.export.is_line_resolver import fs_sum_periods
from app.services.reporting.export.schemas import ReportingBundle

ZERO = Decimal("0")


def _parse_money(s: str | None) -> Decimal | None:
    if not s or s in ("n/a", "—", "-"):
        return None
    t = s.replace("$", "").replace(",", "").strip()
    if t.endswith("M"):
        return Decimal(t[:-1]) * Decimal("1000000")
    if t.endswith("K"):
        return Decimal(t[:-1]) * Decimal("1000")
    try:
        return Decimal(t)
    except Exception:
        return None


def validate_prompt5_payload(
    payload: dict[str, Any],
    bundle: ReportingBundle,
) -> dict[str, Any]:
    """Run sanity checks; return errors (block) and warnings (append to payload)."""
    errors: list[str] = []
    warnings: list[str] = []
    as_of = bundle.as_of_period
    cm = int(as_of[5:7])

    matrix = payload.get("period_matrix") or {}
    rev_row = next((r for r in matrix.get("rows") or [] if r.get("metric") == "Revenue"), {})
    cash_row = next((r for r in matrix.get("rows") or [] if r.get("metric") == "Ending Cash"), {})
    pl = payload.get("pl_detail") or {}
    pl_cm_rev = ((pl.get("cm") or {}).get("revenue") or {}).get("actual")
    pl_ytd_rev = ((pl.get("ytd") or {}).get("revenue") or {}).get("actual")

    rev_cm = _parse_money((rev_row.get("cm") or {}).get("actual"))
    rev_ytd = _parse_money((rev_row.get("ytd") or {}).get("actual"))
    cogs_cm = fs_sum_periods(bundle, [as_of], "Actual", "cogs")
    cash_cm = _parse_money((cash_row.get("cm") or {}).get("actual"))

    if rev_cm is not None and cogs_cm and rev_cm < cogs_cm:
        errors.append(
            f"FATAL: CM revenue ({rev_row.get('cm', {}).get('actual')}) < COGS ({cogs_cm}) — likely field swap"
        )
    if rev_cm is not None and rev_cm < Decimal("1000000"):
        errors.append(
            f"FATAL: CM revenue {rev_row.get('cm', {}).get('actual')} below $1M — likely COGS or sub-line"
        )
    if pl_cm_rev and rev_row.get("cm", {}).get("actual") != pl_cm_rev:
        errors.append(
            f"FATAL: period_matrix Revenue CM ({rev_row.get('cm', {}).get('actual')}) "
            f"≠ pl_detail ({pl_cm_rev}) — executive summary must match P&L slide"
        )
    if pl_ytd_rev and rev_row.get("ytd", {}).get("actual") != pl_ytd_rev:
        errors.append(
            f"FATAL: period_matrix YTD Revenue ({rev_row.get('ytd', {}).get('actual')}) "
            f"≠ pl_detail ({pl_ytd_rev})"
        )

    if rev_cm and rev_ytd:
        lo = rev_cm * Decimal(str(cm - 1)) * Decimal("0.6")
        hi = rev_cm * Decimal(str(cm + 1)) * Decimal("1.4")
        if rev_ytd < lo or rev_ytd > hi:
            warnings.append(
                f"WARN: YTD revenue {rev_row.get('ytd', {}).get('actual')} outside expected "
                f"range for month {cm} (CM ~{rev_row.get('cm', {}).get('actual')})"
            )

    arr_eoy = _parse_money((payload.get("fy_outlook") or {}).get("arr_eoy", {}).get("budget"))
    if arr_eoy and arr_eoy > Decimal("200000000"):
        errors.append(f"FATAL: FY ARR budget {arr_eoy} looks like cumulative sum — use Dec EoY point value")

    fy_rev = _parse_money((payload.get("fy_outlook") or {}).get("revenue_fy", {}).get("outlook"))
    if rev_cm and fy_rev and fy_rev < rev_cm * 8:
        errors.append(f"FATAL: FY revenue outlook too low vs CM — check revenue field mapping")

    gm_row = next((r for r in matrix.get("rows") or [] if r.get("metric") == "Gross Margin %"), {})
    gm_s = (gm_row.get("cm") or {}).get("actual", "")
    if gm_s and gm_s != "n/a":
        try:
            gm = float(gm_s.replace("%", ""))
            if gm < 50 or gm > 90:
                warnings.append(f"WARN: Gross margin {gm_s} outside 50–90% — verify")
        except ValueError:
            pass

    return {
        "passed": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "platform_crosscheck": {
            "revenue_cm": rev_row.get("cm", {}).get("actual"),
            "revenue_ytd": rev_row.get("ytd", {}).get("actual"),
            "cash_cm": cash_row.get("cm", {}).get("actual"),
            "pl_detail_revenue_cm": pl_cm_rev,
            "pl_detail_revenue_ytd": pl_ytd_rev,
            "note": "period_matrix must match pl_detail — same source as board platform P&L tab",
        },
    }
