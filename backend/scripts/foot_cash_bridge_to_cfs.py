"""Make bridge flows foot to the CFS cash spine (one demo series).

Balances on *_cash_flow_bridge are already aligned to CFS. This rebuilds the
flow pack so:

  collections - |operating outflows| + financing = ending - beginning = CFS net

Operating detail (payroll, vendor, commission, tax, interest, other, capex) keeps
its relative mix; the pack is scaled to the statement net. Any leftover that
cannot be expressed as positive outflows lands in financing_to_maintain_cash_floor
(cash in when positive).

Usage:
  python -m scripts.foot_cash_bridge_to_cfs --organization-id <uuid> --scenario budget
  python -m scripts.foot_cash_bridge_to_cfs --organization-id <uuid> --scenario forecast --apply
"""

from __future__ import annotations

import argparse
import uuid
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import text

from app.db.session import SessionLocal

SCENARIOS = ("budget", "forecast", "actual")
OUTFLOW_COLS = (
    "payroll_cash_out",
    "commission_cash_out",
    "vendor_cash_out_n30",
    "tax_cash_out",
    "interest_cash_out",
    "other_operating_cash_out",
    "capex",
)
CENT = Decimal("0.01")


def _num(v) -> Decimal:
    if v in (None, ""):
        return Decimal("0")
    return Decimal(str(v))


def _q(v: Decimal) -> Decimal:
    return v.quantize(CENT, rounding=ROUND_HALF_UP)


def _m(v: Decimal) -> str:
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
                       coalesce(nullif(b.cash_collections_from_invoices,''), nullif(b.collections,''), nullif(b.cash_collections,''), '0'),
                       b.payroll_cash_out, b.commission_cash_out, b.vendor_cash_out_n30,
                       b.tax_cash_out, b.interest_cash_out, b.other_operating_cash_out, b.capex,
                       b.financing_to_maintain_cash_floor,
                       s.beginning_cash, s.ending_cash, s.net_change_in_cash
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
            print(f"No {bridge_t} rows.")
            return

        print(
            f"{'period':8} {'cfs_net':>9} {'old_net':>9} {'new_net':>9} "
            f"{'coll':>9} {'outs':>9} {'fin':>9}"
        )
        print("-" * 72)
        updates: list[dict[str, object]] = []
        for row in rows:
            (
                period,
                beg_b,
                end_b,
                coll_raw,
                payroll,
                commission,
                vendor,
                tax,
                interest,
                other,
                capex,
                financing_old,
                beg_c,
                end_c,
                net_c,
            ) = row
            period = str(period)[:7]
            beg = _num(beg_c if beg_c not in (None, "") else beg_b)
            end = _num(end_c if end_c not in (None, "") else end_b)
            cfs_net = _num(net_c) if net_c not in (None, "") else (end - beg)

            coll = _num(coll_raw)
            outs = {
                "payroll_cash_out": abs(_num(payroll)),
                "commission_cash_out": abs(_num(commission)),
                "vendor_cash_out_n30": abs(_num(vendor)),
                "tax_cash_out": abs(_num(tax)),
                "interest_cash_out": abs(_num(interest)),
                "other_operating_cash_out": abs(_num(other)),
                "capex": abs(_num(capex)),
            }
            outs_total = sum(outs.values(), Decimal("0"))
            old_net = coll - outs_total + _num(financing_old)

            # Target: coll - outs_new + financing_new = cfs_net
            # Prefer keeping collections, scale outflows; financing absorbs sign leftovers.
            financing_new = Decimal("0")
            outs_target = coll - cfs_net  # if positive, need this much outflow
            if outs_target < 0:
                # Net cash generation exceeds collections alone — zero ops outflows
                # and record the excess as financing inflow (demo reconciling).
                outs_new = {k: Decimal("0") for k in outs}
                financing_new = _q(-outs_target)  # cfs_net - coll
                coll_new = coll
            elif outs_total == 0:
                outs_new = {k: Decimal("0") for k in outs}
                # Put required outflow into other_operating
                outs_new["other_operating_cash_out"] = _q(outs_target)
                coll_new = coll
            else:
                scale = outs_target / outs_total
                outs_new = {k: _q(v * scale) for k, v in outs.items()}
                # Fix cent drift on other_operating
                drift = _q(outs_target - sum(outs_new.values(), Decimal("0")))
                outs_new["other_operating_cash_out"] = _q(
                    outs_new["other_operating_cash_out"] + drift
                )
                coll_new = coll

            new_outs_total = sum(outs_new.values(), Decimal("0"))
            new_net = coll_new - new_outs_total + financing_new
            print(
                f"{period:8} {_m(cfs_net):>9} {_m(old_net):>9} {_m(new_net):>9} "
                f"{_m(coll_new):>9} {_m(new_outs_total):>9} {_m(financing_new):>9}"
            )
            updates.append(
                {
                    "o": org,
                    "p": period,
                    "beg": str(_q(beg)),
                    "end": str(_q(end)),
                    "coll": str(_q(coll_new)),
                    "fin": str(_q(financing_new)),
                    "check": "0",
                    "note": (
                        "Flows rebuilt to CFS spine — one demo cash series "
                        f"(net {_m(cfs_net)})."
                    ),
                    **{k: str(v) for k, v in outs_new.items()},
                }
            )

        if not args.apply:
            print(f"\nDry run — {len(updates)} {prefix} periods. Re-run with --apply.")
            return

        for u in updates:
            db.execute(
                text(
                    f"""
                    update {bridge_t} set
                      beginning_cash = :beg,
                      ending_cash = :end,
                      cash_collections_from_invoices = :coll,
                      collections = :coll,
                      cash_collections = :coll,
                      payroll_cash_out = :payroll_cash_out,
                      commission_cash_out = :commission_cash_out,
                      vendor_cash_out_n30 = :vendor_cash_out_n30,
                      tax_cash_out = :tax_cash_out,
                      interest_cash_out = :interest_cash_out,
                      other_operating_cash_out = :other_operating_cash_out,
                      capex = :capex,
                      financing_to_maintain_cash_floor = :fin,
                      bridge_check = :check,
                      notes = :note
                    where organization_id = :o and left(period::text, 7) = :p
                    """
                ),
                u,
            )
        db.commit()
        print(f"\nApplied: {len(updates)} {prefix} bridge periods now foot to CFS net.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
