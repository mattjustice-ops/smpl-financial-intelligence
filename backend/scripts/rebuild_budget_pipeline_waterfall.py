"""Rebuild budget_pipeline_waterfall on the same rule the actuals use.

The budget series was authored under the old cumulative definition: it climbs every
month and never falls ($49.4M in Jan to $120.9M in Dec), because closed and slipped
pipeline was never removed from the balance. Its bridge does not tie under any reading
-- Jan is beginning $44.0M + created $3.46M - outflows = $41.6M against a stated ending
of $49.4M.

The actuals were rebuilt to forward coverage and land on it exactly. Each motion carries
its own coverage multiple against that month's ARR component, and every month of 2026
hits them to the cent:

    New Business 3.00x   Expansion 2.40x   Reactivation 1.60x
    Contraction  1.20x   Churn     1.00x

Putting budget on that same rule is what makes the deck's Actual-vs-Budget pipeline
bridge a real comparison. Today it reads as a 9x miss that is entirely an artifact of
the two columns measuring different things.

The budget table has no opportunity_type breakdown, so the buckets are summed into the
single monthly row it does have. budget_mrr_waterfall carries the same ARR components
as the actual side, so the same multiples apply directly.

Definition applied here, mirroring actuals:
    beginning[m] = sum over buckets of multiple[bucket] * abs(budget_arr[bucket][m])
    ending[m]    = beginning[m+1]        (final month holds flat, as actuals do at close)
    closed_won[m] = sum over buckets of abs(budget_arr[bucket][m])
    closed_lost[m], slipped[m] = closed_won * the rate the business actually runs at,
                                 averaged over the closed months of the year
    created[m]   = ending - beginning + won + lost + slipped   (plug, so the bridge ties)

The old budget's ratios are not carried forward. Its loss rate was sane (1.25x won
against an actual 1.29x) but its slip rate was 1.80x won against an actual 0.31x --
inflated to service the cumulative balance. Rescaled onto a correctly sized pipeline
that implies 77% of pipeline slipping every month, and shows up on the deck as a
$5.6M favourable slippage variance that never happened.

Usage:
    python scripts/rebuild_budget_pipeline_waterfall.py --organization-id <uuid>
    python scripts/rebuild_budget_pipeline_waterfall.py --organization-id <uuid> --apply
"""

from __future__ import annotations

import argparse
from decimal import Decimal

from sqlalchemy import text

from app.core.config import get_settings
from app.core.db_guard import describe_target
from app.db.session import SessionLocal

# Coverage multiple per motion, measured off the actuals and identical in every month
# of 2026. Verify with scripts/verify_pipeline_coverage.py before changing these.
COVERAGE = {
    "new_business_arr": Decimal("3.0"),
    "expansion_arr": Decimal("2.4"),
    "reactivation_arr": Decimal("1.6"),
    "contraction_arr": Decimal("1.2"),
    "churn_arr": Decimal("1.0"),
}
TABLE = "budget_pipeline_waterfall"
ARR_TABLE = "budget_mrr_waterfall"


def _num(v) -> Decimal:
    if v is None or str(v).strip() == "":
        return Decimal("0")
    return Decimal(str(v).replace(",", "").replace("$", ""))


def _next_period(p: str) -> str:
    y, m = int(p[:4]), int(p[5:7])
    return f"{y + 1}-01" if m == 12 else f"{y}-{m + 1:02d}"


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
        sel = ", ".join(COVERAGE)
        arr = {
            r[0]: dict(zip(COVERAGE, (abs(_num(v)) for v in r[1:])))
            for r in db.execute(
                text(f"select period, {sel} from {ARR_TABLE} where organization_id = :o"),
                {"o": org},
            ).fetchall()
        }
        if not arr:
            print(f"No {ARR_TABLE} rows for this organization — nothing to drive the rebuild.")
            return

        def covered(period: str) -> Decimal:
            """Pipeline balance the motions of this month require."""
            comps = arr.get(period)
            if not comps:
                return Decimal("0")
            return sum((COVERAGE[c] * comps.get(c, Decimal("0")) for c in COVERAGE), Decimal("0"))

        def gross(period: str) -> Decimal:
            comps = arr.get(period) or {}
            return sum(comps.values(), Decimal("0"))

        observed = db.execute(
            text(
                "select sum(nullif(closed_won_arr,'')::numeric), "
                "       sum(nullif(closed_lost_arr,'')::numeric), "
                "       sum(nullif(slipped_pipeline_arr,'')::numeric) "
                "from actual_pipeline_waterfall where organization_id = :o and period >= :first"
            ),
            {"o": org, "first": min(arr)},
        ).fetchone()
        obs_won, obs_lost, obs_slip = (_num(v) for v in observed)
        if not obs_won:
            print("No closed actuals to measure loss and slip rates from — aborting.")
            return
        lost_ratio = obs_lost / obs_won
        slip_ratio = obs_slip / obs_won
        print(
            f"loss and slip rates measured off the closed months: "
            f"lost {lost_ratio:.2f}x won, slipped {slip_ratio:.2f}x won\n"
        )

        rows = db.execute(
            text(
                f"select period, beginning_pipeline_arr, pipeline_arr_created, closed_won_arr, "
                f"closed_lost_arr, slipped_pipeline_arr, ending_pipeline_arr "
                f"from {TABLE} where organization_id = :o order by period"
            ),
            {"o": org},
        ).fetchall()
        if not rows:
            print(f"No {TABLE} rows for this organization.")
            return

        periods = [r[0] for r in rows]
        last = periods[-1]

        print("proposed budget pipeline (all figures $)")
        print(
            f"  {'period':9}{'OLD begin':>14}{'NEW begin':>13}{'OLD end':>14}"
            f"{'NEW end':>13}{'NEW created':>13}{'ties':>7}"
        )

        updates = []
        for period, o_beg, o_created, o_won, o_lost, o_slip, o_end in rows:
            beginning = covered(period).quantize(Decimal("0.01"))
            if not beginning:
                print(f"  {period:9}  no budget ARR components — left unchanged")
                continue

            nxt = covered(_next_period(period)).quantize(Decimal("0.01"))
            # Final month has no following month to cover; hold flat exactly as the
            # actuals do at the close period rather than invent a following month.
            ending = beginning if (period == last or not nxt) else nxt

            won = gross(period).quantize(Decimal("0.01"))
            lost = (won * lost_ratio).quantize(Decimal("0.01"))
            slipped = (won * slip_ratio).quantize(Decimal("0.01"))
            created = (ending - beginning + won + lost + slipped).quantize(Decimal("0.01"))

            bridge = beginning + created - won - lost - slipped
            ties = abs(bridge - ending) < Decimal("1")
            print(
                f"  {period:9}{float(_num(o_beg)):>14,.0f}{float(beginning):>13,.0f}"
                f"{float(_num(o_end)):>14,.0f}{float(ending):>13,.0f}"
                f"{float(created):>13,.0f}{'yes' if ties else 'NO':>7}"
            )
            updates.append((period, beginning, created, won, lost, slipped, ending))

        if args.apply:
            for period, beginning, created, won, lost, slipped, ending in updates:
                db.execute(
                    text(
                        f"update {TABLE} set "
                        f"beginning_pipeline_arr = :beg, pipeline_arr_created = :created, "
                        f"closed_won_arr = :won, closed_lost_arr = :lost, "
                        f"slipped_pipeline_arr = :slip, ending_pipeline_arr = :end "
                        f"where organization_id = :o and period = :p"
                    ),
                    {
                        "beg": str(beginning),
                        "created": str(created),
                        "won": str(won),
                        "lost": str(lost),
                        "slip": str(slipped),
                        "end": str(ending),
                        "o": org,
                        "p": period,
                    },
                )
            db.commit()
            print(f"\nCommitted. {len(updates)} month(s) rebuilt.")
        else:
            print(f"\nDry run. {len(updates)} month(s) would be rebuilt. Re-run with --apply.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
