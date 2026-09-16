"""Rebuild *_cash_flow_bridge balances onto matching *_cash_flow_statement.

Keeps payroll/vendor/commission/capex/collections line items (only source of that
detail) but forces beginning_cash / ending_cash to the CFS spine so Board cash
no longer contradicts the 3-statement tab. A disclosed residual remains in the
footing until flows are regenerated from collections/GL.

Usage:
  python -m scripts.rebuild_budget_cash_bridge_to_cfs --organization-id <uuid>
  python -m scripts.rebuild_budget_cash_bridge_to_cfs --organization-id <uuid> --scenario forecast --apply
  python -m scripts.rebuild_budget_cash_bridge_to_cfs --organization-id <uuid> --scenario budget --apply
"""

from __future__ import annotations

import argparse
import uuid
from decimal import Decimal

from sqlalchemy import text

from app.db.session import SessionLocal

SCENARIOS = ("budget", "forecast", "actual")


def _num(v) -> Decimal | None:
    if v in (None, ""):
        return None
    return Decimal(str(v))


def _m(v: Decimal | None) -> str:
    if v is None:
        return "-"
    return f"${float(v) / 1e6:.2f}M"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--organization-id", required=True)
    parser.add_argument("--scenario", choices=SCENARIOS, default="budget")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    org = str(uuid.UUID(args.organization_id))
    prefix = args.scenario
    bridge_t = f"{prefix}_cash_flow_bridge"
    cfs_t = f"{prefix}_cash_flow_statement"

    db = SessionLocal()
    try:
        rows = db.execute(
            text(
                f"""
                select b.period::text,
                       b.beginning_cash, b.ending_cash,
                       s.beginning_cash as cfs_beg, s.ending_cash as cfs_end
                from {bridge_t} b
                left join {cfs_t} s
                  on s.organization_id = b.organization_id
                 and left(s.period::text, 7) = left(b.period::text, 7)
                where b.organization_id = :o
                order by left(b.period::text, 7)
                """
            ),
            {"o": org},
        ).fetchall()
        if not rows:
            print(f"No {bridge_t} rows for org.")
            return

        print(f"{'period':10} {'bridge_beg':>12} {'->':>4} {'cfs_beg':>12} {'bridge_end':>12} {'->':>4} {'cfs_end':>12}")
        print("-" * 72)
        updates = []
        for period, beg, end, cfs_beg, cfs_end in rows:
            b0, e0 = _num(beg), _num(end)
            c0, c1 = _num(cfs_beg), _num(cfs_end)
            print(
                f"{str(period):10} {_m(b0):>12} {'':>4}{_m(c0):>12} {_m(e0):>12} {'':>4}{_m(c1):>12}"
            )
            if c0 is None and c1 is None:
                continue
            updates.append(
                {
                    "o": org,
                    "p": str(period),
                    "beg": None if c0 is None else str(c0),
                    "end": None if c1 is None else str(c1),
                }
            )

        if not args.apply:
            print(
                f"\nDry run - {len(updates)} {prefix} periods would be aligned to CFS. "
                "Re-run with --apply."
            )
            return

        for u in updates:
            db.execute(
                text(
                    f"update {bridge_t} "
                    "set beginning_cash = coalesce(:beg, beginning_cash), "
                    "    ending_cash = coalesce(:end, ending_cash) "
                    "where organization_id = :o and left(period::text, 7) = left(:p, 7)"
                ),
                u,
            )
        db.commit()
        print(f"\nApplied: {len(updates)} {prefix} bridge periods now use CFS balances.")
        print(
            "Note: line items were not scaled. Bridge footing residuals remain until "
            "flows are rebuilt from collections/GL onto this spine."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
