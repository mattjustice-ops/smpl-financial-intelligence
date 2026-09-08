"""Re-anchor forecast_cash_flow_bridge to the actual close balance.

The forecast cash series was authored before the cash re-anchor and never rebased. The
actuals close June at $30.00M and the forecast opens July at a beginning balance of
$47.90M -- $17.90M of cash appearing overnight with no cash event behind it. The error
carries through every forecast month, so the deck reports an FY26 ending cash outlook of
$49.92M against a June actual of $30.00M and narrates it as "+109.3% vs budget" and
"strong cash generation" on three separate slides.

The monthly flows themselves are fine. Collections, payroll, vendor and capex all look
reasonable and the series only moves about $0.33M a month on net, which is why the fix is
a rebase and not a rebuild: hold every flow exactly as authored and shift the balances so
the first forecast month opens where the last actual month closed.

    shift        = forecast[first].beginning_cash - actual[close].ending_cash
    beginning'   = beginning - shift
    ending'      = ending    - shift

Every intra-month flow is untouched, so a bridge that tied before still ties after, and
the forecast becomes continuous with the actuals it follows.

Usage:
    python scripts/reanchor_forecast_cash_bridge.py --organization-id <uuid>
    python scripts/reanchor_forecast_cash_bridge.py --organization-id <uuid> --apply
"""

from __future__ import annotations

import argparse
from decimal import Decimal

from sqlalchemy import text

from app.core.config import get_settings
from app.core.db_guard import describe_target
from app.db.session import SessionLocal

TABLE = "forecast_cash_flow_bridge"
ACTUAL_TABLE = "actual_cash_flow_bridge"
# Balances move with the anchor; flows do not.
BALANCE_COLUMNS = ("beginning_cash", "ending_cash")


def _num(v) -> Decimal | None:
    if v is None or str(v).strip() == "":
        return None
    return Decimal(str(v).replace(",", "").replace("$", ""))


def _m(v: Decimal | None) -> str:
    return "     —    " if v is None else f"${v / Decimal('1e6'):9.2f}M"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--organization-id", required=True)
    ap.add_argument("--apply", action="store_true", help="write changes (default: report only)")
    args = ap.parse_args()
    org = args.organization_id

    print(f"Database: {describe_target(get_settings().database_url)}")
    print(f"Mode:     {'APPLY' if args.apply else 'dry run (no writes)'}\n")

    db = SessionLocal()
    try:
        actual = db.execute(
            text(
                f"select period, ending_cash from {ACTUAL_TABLE} "
                "where organization_id = :o and nullif(ending_cash,'') is not null "
                "order by period desc limit 1"
            ),
            {"o": org},
        ).fetchone()
        if not actual:
            print(f"No actual rows in {ACTUAL_TABLE} for this organization — aborting.")
            return
        close_period, close_cash = actual[0], _num(actual[1])
        print(f"Actual close:   {close_period}  ending cash {_m(close_cash)}")

        rows = db.execute(
            text(
                f"select period, beginning_cash, ending_cash from {TABLE} "
                "where organization_id = :o order by period"
            ),
            {"o": org},
        ).fetchall()
        if not rows:
            print(f"No rows in {TABLE} for this organization — nothing to do.")
            return

        first = rows[0]
        first_beg = _num(first[1])
        if first_beg is None:
            print(f"Forecast {first[0]} has no beginning_cash — cannot measure the anchor.")
            return
        print(f"Forecast start: {first[0]}  beginning cash {_m(first_beg)}")

        shift = first_beg - close_cash
        print(f"\nDiscontinuity to remove: {_m(shift)}\n")
        if shift == 0:
            print("Forecast already opens on the actual close — nothing to do.")
            return

        print(f"{'period':10} {'beginning':>12} {'-> ':>4}{'':>10} {'ending':>12} {'->':>4}{'':>10}")
        print("-" * 66)
        updates: list[dict[str, object]] = []
        for period, beg_raw, end_raw in rows:
            beg, end = _num(beg_raw), _num(end_raw)
            nbeg = None if beg is None else beg - shift
            nend = None if end is None else end - shift
            print(
                f"{period:10} {_m(beg):>12} {'':>4}{_m(nbeg):>10} {_m(end):>12} {'':>4}{_m(nend):>10}"
            )
            updates.append(
                {
                    "o": org,
                    "p": period,
                    "beg": None if nbeg is None else str(nbeg),
                    "end": None if nend is None else str(nend),
                }
            )

        # A rebase must not push the plan through its own floor.
        floors = db.execute(
            text(
                f"select period, cash_floor from {TABLE} "
                "where organization_id = :o and nullif(cash_floor,'') is not null"
            ),
            {"o": org},
        ).fetchall()
        breaches = []
        for period, floor_raw in floors:
            floor = _num(floor_raw)
            new_end = next(
                (u["end"] for u in updates if u["p"] == period and u["end"] is not None), None
            )
            if floor is not None and new_end is not None and Decimal(str(new_end)) < floor:
                breaches.append(f"  {period}: ending {_m(Decimal(str(new_end)))} < floor {_m(floor)}")
        if breaches:
            print("\nWARNING — rebased balances fall below the stated cash floor:")
            for b in breaches:
                print(b)
        else:
            print("\nAll rebased balances stay above the stated cash floor.")

        if not args.apply:
            print("\nDry run — no writes. Re-run with --apply to commit.")
            return

        for u in updates:
            db.execute(
                text(
                    f"update {TABLE} set beginning_cash = :beg, ending_cash = :end "
                    "where organization_id = :o and period = :p"
                ),
                u,
            )
        db.commit()
        print(f"\nApplied to {len(updates)} rows in {TABLE}.")

        check = db.execute(
            text(
                f"select beginning_cash from {TABLE} "
                "where organization_id = :o order by period limit 1"
            ),
            {"o": org},
        ).scalar()
        print(
            f"Forecast now opens at {_m(_num(check))} against an actual close of {_m(close_cash)}."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
