"""Reconcile every warehouse cash/P&L source against the balance sheet and cash
flow statement, which are the declared source of truth.

Reports each period and scenario where a source publishes a number that does not
tie, so the deterministic logic underneath can be fixed rather than papered over.

Usage:
    python scripts/reconcile_to_statements.py [--org UUID]
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.session import SessionLocal

DEFAULT_ORG = "8571e520-0687-4516-bdee-379f37c58c1f"
SCENARIOS = ("actual", "budget", "forecast")
# A dollar of slack absorbs load-time rounding without hiding a real break.
TOL = Decimal("1")
M = Decimal("1e6")


def dec(v: object) -> Decimal:
    if v is None or v == "":
        return Decimal("0")
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def fmt(x: Decimal) -> str:
    return f"{x / M:>9,.3f}M"


class Report:
    def __init__(self) -> None:
        self.breaks: list[tuple[str, str, str, Decimal]] = []
        self.checked = 0

    def add(self, check: str, scenario: str, period: str, delta: Decimal) -> None:
        self.checked += 1
        if abs(delta) > TOL:
            self.breaks.append((check, scenario, period, delta))


def table_exists(db, name: str) -> bool:
    return bool(
        db.execute(
            text(
                "select 1 from information_schema.tables "
                "where table_schema='public' and table_name=:n"
            ),
            {"n": name},
        ).first()
    )


def rows_by_period(db, table: str, cols: str, org: str) -> dict[str, tuple]:
    if not table_exists(db, table):
        return {}
    sql = f"select substr(period::text,1,7) as p, {cols} from {table} where organization_id = :org"
    out: dict[str, tuple] = {}
    for r in db.execute(text(sql), {"org": org}):
        out[r[0]] = tuple(r[1:])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--org", default=DEFAULT_ORG)
    args = ap.parse_args()
    org = args.org

    db = SessionLocal()
    rep = Report()
    try:
        for scen in SCENARIOS:
            bs = rows_by_period(db, f"{scen}_balance_sheet", "cash::numeric", org)
            cfs = rows_by_period(
                db,
                f"{scen}_cash_flow_statement",
                "ending_cash::numeric, beginning_cash::numeric, "
                "net_change_in_cash::numeric, net_cash_from_operating_activities::numeric, "
                "net_cash_from_investing_activities::numeric, "
                "net_cash_from_financing_activities::numeric",
                org,
            )
            bridge = rows_by_period(
                db,
                f"{scen}_cash_flow_bridge",
                "ending_cash::numeric, beginning_cash::numeric, "
                "cash_collections_from_invoices::numeric, payroll_cash_out::numeric, "
                "commission_cash_out::numeric, vendor_cash_out_n30::numeric, "
                "tax_cash_out::numeric, interest_cash_out::numeric, "
                "other_operating_cash_out::numeric, capex::numeric, "
                "financing_to_maintain_cash_floor::numeric",
                org,
            )

            print(f"\n{'=' * 92}")
            print(f"SCENARIO: {scen.upper()}")
            print(f"{'=' * 92}")
            print(
                f"{'period':9} {'BS cash':>11} {'CFS end':>11} {'bridge end':>11} "
                f"{'CFS-BS':>10} {'bridge-BS':>11}  flags"
            )

            for period in sorted(set(bs) | set(cfs) | set(bridge)):
                bs_cash = dec(bs.get(period, (None,))[0]) if period in bs else None
                cfs_row = cfs.get(period)
                br_row = bridge.get(period)

                cfs_end = dec(cfs_row[0]) if cfs_row else None
                br_end = dec(br_row[0]) if br_row else None

                flags: list[str] = []

                # 1. Cash flow statement ending cash must equal balance sheet cash.
                if bs_cash is not None and cfs_end is not None:
                    d = cfs_end - bs_cash
                    rep.add("cfs_ending_vs_bs_cash", scen, period, d)
                    if abs(d) > TOL:
                        flags.append("CFS!=BS")

                # 2. Bridge ending cash must equal balance sheet cash.
                if bs_cash is not None and br_end is not None:
                    d = br_end - bs_cash
                    rep.add("bridge_ending_vs_bs_cash", scen, period, d)
                    if abs(d) > TOL:
                        flags.append("BRIDGE!=BS")

                # 3. Bridge must be internally consistent, outflows subtracted.
                if br_row:
                    (
                        b_end,
                        b_beg,
                        coll,
                        pay,
                        comm,
                        ven,
                        tax,
                        inte,
                        oth,
                        cap,
                        fin,
                    ) = [dec(v) for v in br_row]
                    outflows = pay + comm + ven + tax + inte + oth + cap
                    computed = b_beg + coll - outflows + fin
                    d = computed - b_end
                    rep.add("bridge_internal_rollforward", scen, period, d)
                    if abs(d) > TOL:
                        flags.append("BRIDGE_INTERNAL")

                # 4. Cash flow statement must roll: beginning + net change = ending.
                if cfs_row:
                    c_end, c_beg, c_net, ocf, icf, fcf = [dec(v) for v in cfs_row]
                    d = (c_beg + c_net) - c_end
                    rep.add("cfs_rollforward", scen, period, d)
                    if abs(d) > TOL:
                        flags.append("CFS_ROLL")
                    d2 = (ocf + icf + fcf) - c_net
                    rep.add("cfs_net_change_components", scen, period, d2)
                    if abs(d2) > TOL:
                        flags.append("CFS_COMPONENTS")

                print(
                    f"{period:9} "
                    f"{fmt(bs_cash) if bs_cash is not None else '        --':>11} "
                    f"{fmt(cfs_end) if cfs_end is not None else '        --':>11} "
                    f"{fmt(br_end) if br_end is not None else '        --':>11} "
                    f"{fmt(cfs_end - bs_cash) if (bs_cash is not None and cfs_end is not None) else '        --':>10} "
                    f"{fmt(br_end - bs_cash) if (bs_cash is not None and br_end is not None) else '        --':>11}"
                    f"  {' '.join(flags)}"
                )

            # 5. Period-over-period continuity of the bridge chain.
            periods = sorted(bridge)
            for prev, cur in zip(periods, periods[1:]):
                prev_end = dec(bridge[prev][0])
                cur_beg = dec(bridge[cur][1])
                d = cur_beg - prev_end
                rep.add("bridge_chain_continuity", scen, f"{prev}->{cur}", d)

        print(f"\n{'=' * 92}")
        print("SUMMARY")
        print(f"{'=' * 92}")
        print(f"comparisons run: {rep.checked}")
        print(f"breaks found:    {len(rep.breaks)}")
        if rep.breaks:
            by_check: dict[str, list[tuple[str, str, Decimal]]] = {}
            for check, scen, period, delta in rep.breaks:
                by_check.setdefault(check, []).append((scen, period, delta))
            for check, items in sorted(by_check.items()):
                worst = max(abs(d) for _, _, d in items)
                print(f"\n  {check}  ({len(items)} break(s), worst {fmt(worst)})")
                for scen, period, delta in items[:14]:
                    print(f"      {scen:9} {period:14} off by {fmt(delta)}")
                if len(items) > 14:
                    print(f"      ... and {len(items) - 14} more")
        else:
            print("\n  Everything ties to the balance sheet and cash flow statement.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
