"""Income statement revenue from customer ARR (used by build_customer_history.py; writes nothing itself).

Rules:
  * Recurring revenue (subscription and recurring services: summary revenue less implementation fees) runs at the
    ratio the Actual history shows to customer ARR at the month end / 12, over the twelve months before the first
    rebuilt Actual month.
  * A rebuilt month's revenue = that ratio x the version's customer ARR at the month end / 12 (Forecast: expected
    ARR), plus the month's implementation fees. Rebuilt: the simulated Actual months and every Budget and Forecast
    month.
  * Each cost line (cost of revenue, S&M, R&D, G&A, D&A) keeps the source month's ratio to revenue on its cash
    part; stock comp ({V}_SBC_Schedule.csv) stays as scheduled. Interest stays; income tax is recomputed with the
    GL (rebuild_gl_to_summary.py).
"""

from __future__ import annotations

from decimal import Decimal

from build_v5_dataset import ZERO, num, q
from build_workforce import SBC_LINES as SBC_COLUMNS

COST_LINES = (*SBC_COLUMNS, "depreciation_and_amortization")
OPEX = ("sales_and_marketing", "research_and_development", "general_and_administrative")
BELOW_EBITDA = ("depreciation_and_amortization", "interest_expense", "tax_expense")


def recurring_ratio(rows: list[dict[str, str]], impl: dict[str, Decimal], eop: dict[str, dict[str, Decimal]],
                    window: list[str]) -> Decimal:
    revenue = {r["period"][:7]: num(r["revenue"]) for r in rows}
    missing = [p for p in window if p not in revenue or p not in eop]
    if missing:
        raise ValueError(f"no revenue or customer ARR to measure the recurring revenue ratio in {missing}")
    recurring = sum((revenue[p] - impl.get(p, ZERO) for p in window), ZERO)
    mrr = sum((sum(eop[p].values(), ZERO) for p in window), ZERO) / 12
    return recurring / mrr


def rebase(rows: list[dict[str, str]], sbc: dict[str, dict[str, str]], impl: dict[str, Decimal],
           eop: dict[str, dict[str, Decimal]], months: list[str], ratio: Decimal) -> tuple[Decimal, Decimal]:
    """Rewrites ``rows`` in place for ``months``; returns (revenue before, revenue after) over those months."""
    before = after = ZERO
    done = set()
    for r in rows:
        p = r["period"][:7]
        if p not in months:
            continue
        old = num(r["revenue"])
        new = q(ratio * sum(eop[p].values(), ZERO) / 12) + impl.get(p, ZERO)
        for line in COST_LINES:
            stock = num(sbc[p][SBC_COLUMNS[line]]) if line in SBC_COLUMNS and p in sbc else ZERO
            r[line] = f"{stock + q((num(r[line]) - stock) * new / old):.2f}"
        r["revenue"] = f"{new:.2f}"
        gp = new - num(r["cost_of_revenue"])
        ebitda = gp - sum((num(r[k]) for k in OPEX), ZERO)
        r.update({"gross_profit": f"{gp:.2f}", "ebitda": f"{ebitda:.2f}",
                  "net_income": f"{ebitda - sum((num(r[k]) for k in BELOW_EBITDA if k in r), ZERO):.2f}"})
        before, after = before + old, after + new
        done.add(p)
    if set(months) - done:
        raise ValueError(f"no income statement rows for {sorted(set(months) - done)}")
    return before, after
