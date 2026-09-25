"""Export Stripe TEST Quick Demo Co seed → SMPL billing CSV shapes.

Reads CONNECTOR_STRIPE_SECRET_KEY only. Export-only — no org ingest
(especially not SMPL Demo Co).

Outputs under backend/tmp/stripe_export/:
  customers.csv, subscriptions.csv, invoices.csv, payments.csv,
  mrr_waterfall.csv, export_manifest.json

Also copies customer_master.csv into the export folder for the shared spine.

Usage (from repo root):
  backend\\.venv312\\Scripts\\python.exe backend\\scripts\\stripe_export_to_smpl.py
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import stripe

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stripe_quick_demo_common import (  # noqa: E402
    CUSTOMERS_HEADERS,
    INVOICES_HEADERS,
    MRR_WATERFALL_HEADERS,
    PAYMENTS_HEADERS,
    QUICK_DEMO_DIR,
    SEED_MARKER,
    SOURCE_SYSTEM,
    STRIPE_EXPORT_DIR,
    SUBSCRIPTIONS_HEADERS,
    load_connector_stripe_key,
    read_customer_master,
    write_csv,
    write_customer_master,
)


def _dt(ts: int | None) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).date().isoformat()


def _period_month(ts: int | None) -> str:
    if not ts:
        return ""
    d = datetime.fromtimestamp(int(ts), tz=timezone.utc).date()
    return f"{d.year:04d}-{d.month:02d}"


def _period_first(ts: int | None) -> str:
    if not ts:
        return ""
    d = datetime.fromtimestamp(int(ts), tz=timezone.utc).date()
    return date(d.year, d.month, 1).isoformat()


def _money(cents_val: int | None) -> str:
    if cents_val is None:
        return "0.00"
    return f"{Decimal(cents_val) / Decimal(100):.2f}"


def _md(obj: Any) -> dict[str, str]:
    raw = getattr(obj, "metadata", None)
    if raw is None:
        return {}
    if hasattr(raw, "to_dict"):
        data = raw.to_dict()
    elif isinstance(raw, dict):
        data = raw
    else:
        try:
            data = {k: raw[k] for k in raw.keys()}  # type: ignore[index]
        except Exception:
            data = {}
    return {str(k): str(v) for k, v in data.items() if v is not None}


def _list_seed_customers() -> list[stripe.Customer]:
    out: list[stripe.Customer] = []
    try:
        res = stripe.Customer.search(query=f"metadata['smpl_seed']:'{SEED_MARKER}'", limit=100)
        out.extend(res.data)
        while res.has_more:
            res = stripe.Customer.search(
                query=f"metadata['smpl_seed']:'{SEED_MARKER}'",
                limit=100,
                page=res.next_page,
            )
            out.extend(res.data)
        return out
    except stripe.InvalidRequestError:
        pass
    for c in stripe.Customer.list(limit=100).auto_paging_iter():
        if _md(c).get("smpl_seed") == SEED_MARKER:
            out.append(c)
    return out


def _sub_mrr_cents(sub: stripe.Subscription) -> int:
    total = 0
    items = sub["items"]["data"]
    for item in items:
        price = item.price
        if not price or not getattr(price, "recurring", None):
            continue
        amt = int(price.unit_amount or 0) * int(item.quantity or 1)
        interval = getattr(price.recurring, "interval", None)
        if interval == "year":
            amt = amt // 12
        elif interval == "week":
            amt = int(amt * 52 / 12)
        total += amt
    return total


def export(out_dir: Path) -> dict[str, Any]:
    key = load_connector_stripe_key()
    stripe.api_key = key
    bal = stripe.Balance.retrieve()
    if getattr(bal, "livemode", None) is True:
        raise SystemExit("Stripe account is live — aborting export.")

    master_path = write_customer_master()
    master = {r["smpl_customer_id"]: r for r in read_customer_master(master_path)}

    customers_api = _list_seed_customers()
    by_smpl: dict[str, stripe.Customer] = {}
    for c in customers_api:
        sid = _md(c).get("smpl_customer_id")
        if sid:
            by_smpl[sid] = c

    customers_rows: list[dict[str, Any]] = []
    subscriptions_rows: list[dict[str, Any]] = []
    invoices_rows: list[dict[str, Any]] = []
    payments_rows: list[dict[str, Any]] = []

    # Per-customer current MRR for waterfall synthesis
    current_mrr: dict[str, Decimal] = {}
    start_dates: dict[str, str] = {}
    statuses: dict[str, str] = {}

    for smpl_id, mrow in master.items():
        cust = by_smpl.get(smpl_id)
        stripe_id = cust.id if cust else ""
        status = mrow.get("status") or "active"
        if cust:
            # prefer live sub presence
            pass
        customers_rows.append(
            {
                "customer_id": smpl_id,
                "customer_name": mrow["customer_name"],
                "segment": mrow.get("segment") or "",
                "industry": mrow.get("industry") or "",
                "status": status,
                "start_date": mrow.get("start_date") or "",
                "billing_cadence": mrow.get("billing_cadence") or "monthly",
                "payment_terms": mrow.get("payment_terms") or "Net 30",
                "source_crm": "quick_demo_master",
                "netsuite_customer_id": "",
                "stripe_customer_id": stripe_id,
            }
        )
        start_dates[smpl_id] = mrow.get("start_date") or ""
        statuses[smpl_id] = status

        if not cust:
            # Still emit planned MRR from master for waterfall spine
            platform = Decimal(mrow.get("platform_mrr") or "0")
            addon = Decimal(mrow.get("addon_mrr") or "0")
            current_mrr[smpl_id] = platform + addon if status != "churned" else Decimal("0")
            continue

        mrr_total = 0
        for sub in stripe.Subscription.list(customer=cust.id, status="all", limit=100).auto_paging_iter():
            md = _md(sub)
            if md.get("smpl_seed") != SEED_MARKER:
                continue
            product = md.get("product") or "Platform Suite"
            mrr_c = _sub_mrr_cents(sub)
            active = sub.status in {"active", "trialing", "past_due"}
            if active:
                mrr_total += mrr_c
            end_date = _dt(sub.canceled_at) if sub.canceled_at else _dt(sub.ended_at)
            subscriptions_rows.append(
                {
                    "subscription_id": md.get("smpl_sub_key") or sub.id,
                    "customer_id": smpl_id,
                    "product": product,
                    "billing_cadence": "monthly",
                    "start_date": _dt(sub.start_date) or mrow.get("start_date") or "",
                    "end_date": end_date if not active else "",
                    "current_mrr": _money(mrr_c if active else 0),
                    "current_arr": _money((mrr_c if active else 0) * 12),
                    "status": "active" if active else "cancelled",
                    "currency": "USD",
                }
            )

        current_mrr[smpl_id] = Decimal(_money(mrr_total))

        for inv in stripe.Invoice.list(customer=cust.id, limit=100).auto_paging_iter():
            inv_md = _md(inv)
            if inv_md.get("smpl_seed") and inv_md.get("smpl_seed") != SEED_MARKER:
                continue
            # Include invoices for seeded customers even without invoice metadata
            status_map = {
                "paid": "paid",
                "open": "open",
                "draft": "draft",
                "uncollectible": "uncollectible",
                "void": "void",
            }
            pay_status = status_map.get(inv.status or "", inv.status or "open")
            amount_paid = int(getattr(inv, "amount_paid", 0) or 0)
            amount_due = int(getattr(inv, "amount_due", 0) or 0)
            invoices_rows.append(
                {
                    "invoice_id": inv.id,
                    "customer_id": smpl_id,
                    "invoice_period": _period_month(inv.created),
                    "invoice_date": _dt(inv.created),
                    "due_date": _dt(inv.due_date) or _dt(inv.created),
                    "invoice_amount": _money(amount_due if inv.status != "paid" else amount_paid),
                    "payment_status": pay_status,
                    "billing_cadence": "monthly",
                    "currency": (inv.currency or "usd").upper(),
                }
            )
            if inv.status == "paid" and amount_paid:
                charge = getattr(inv, "charge", None)
                pay_id = charge if isinstance(charge, str) and charge else f"pay_{inv.id}"
                transitions = getattr(inv, "status_transitions", None)
                paid_at = getattr(transitions, "paid_at", None) if transitions else None
                payments_rows.append(
                    {
                        "payment_id": pay_id,
                        "invoice_id": inv.id,
                        "customer_id": smpl_id,
                        "payment_date": _dt(paid_at or inv.created),
                        "payment_amount": _money(amount_paid),
                        "payment_method": "card",
                        "currency": (inv.currency or "usd").upper(),
                    }
                )

    # Synthesize customer-level mrr_waterfall for Jan–May 2026 from master start dates + current MRR.
    # Expansion/contraction/churn heuristics from master notes/status (first-pass).
    periods = [
        date(2026, 1, 1),
        date(2026, 2, 1),
        date(2026, 3, 1),
        date(2026, 4, 1),
        date(2026, 5, 1),
    ]
    # Planned beginning MRR before start: 0; at start = new; churned Apr for QDC-017
    planned_end: dict[str, dict[str, Decimal]] = defaultdict(dict)
    for smpl_id, mrow in master.items():
        start = date.fromisoformat(mrow["start_date"]) if mrow.get("start_date") else date(2026, 1, 1)
        target = current_mrr.get(smpl_id, Decimal("0"))
        if (mrow.get("status") or "").lower() == "churned":
            # was platform_mrr until Apr
            live = Decimal(mrow.get("platform_mrr") or "0") + Decimal(mrow.get("addon_mrr") or "0")
            for p in periods:
                if p < start:
                    planned_end[smpl_id][p.isoformat()] = Decimal("0")
                elif p < date(2026, 4, 1):
                    planned_end[smpl_id][p.isoformat()] = live
                else:
                    planned_end[smpl_id][p.isoformat()] = Decimal("0")
        else:
            for p in periods:
                planned_end[smpl_id][p.isoformat()] = target if p >= start else Decimal("0")

    # Special cases for movements (documented in master notes)
    # QDC-011 contracted: treat Jan–Mar as 1400, Apr+ as 1100
    if "QDC-011" in planned_end:
        for p in periods:
            if p < date(2026, 4, 1) and planned_end["QDC-011"][p.isoformat()] > 0:
                planned_end["QDC-011"][p.isoformat()] = Decimal("1400.00")
            elif p >= date(2026, 4, 1):
                planned_end["QDC-011"][p.isoformat()] = Decimal("1100.00")
    # QDC-004 expanded: Jan–Apr 2500+300, May+ 2800+300
    if "QDC-004" in planned_end:
        for p in periods:
            if p < date(2026, 5, 1) and p >= date(2026, 1, 1):
                planned_end["QDC-004"][p.isoformat()] = Decimal("2800.00")  # seed current; simplify
            # keep current target

    mrr_rows: list[dict[str, Any]] = []
    for smpl_id in master:
        prev = Decimal("0")
        for p in periods:
            ending = planned_end[smpl_id][p.isoformat()]
            beginning = prev
            delta = ending - beginning
            new_mrr = expansion = contraction = churn = reactivation = Decimal("0")
            movement = "flat"
            if beginning == 0 and ending > 0:
                # reactivation if previously churned earlier in series
                if any(planned_end[smpl_id][x.isoformat()] == 0 for x in periods if x < p) and any(
                    planned_end[smpl_id][x.isoformat()] > 0 for x in periods if x < p
                ):
                    reactivation = ending
                    movement = "reactivation"
                else:
                    new_mrr = ending
                    movement = "new"
            elif beginning > 0 and ending == 0:
                churn = beginning
                movement = "churn"
            elif delta > 0:
                expansion = delta
                movement = "expansion"
            elif delta < 0:
                contraction = abs(delta)
                movement = "contraction"
            else:
                movement = "flat"
            mrr_rows.append(
                {
                    "period": p.isoformat(),
                    "customer_id": smpl_id,
                    "beginning_mrr": f"{beginning:.2f}",
                    "new_mrr": f"{new_mrr:.2f}",
                    "expansion_mrr": f"{expansion:.2f}",
                    "contraction_mrr": f"{contraction:.2f}",
                    "churn_mrr": f"{churn:.2f}",
                    "reactivation_mrr": f"{reactivation:.2f}",
                    "ending_mrr": f"{ending:.2f}",
                    "movement_type": movement if movement != "flat" else "net",
                }
            )
            prev = ending

    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "customers.csv", CUSTOMERS_HEADERS, customers_rows)
    write_csv(out_dir / "subscriptions.csv", SUBSCRIPTIONS_HEADERS, subscriptions_rows)
    write_csv(out_dir / "invoices.csv", INVOICES_HEADERS, invoices_rows)
    write_csv(out_dir / "payments.csv", PAYMENTS_HEADERS, payments_rows)
    write_csv(out_dir / "mrr_waterfall.csv", MRR_WATERFALL_HEADERS, mrr_rows)
    shutil.copy2(master_path, out_dir / "customer_master.csv")

    manifest = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "archetype": "Quick Demo Co",
        "smpl_seed": SEED_MARKER,
        "source_system": SOURCE_SYSTEM,
        "livemode": False,
        "ingest": "export_only",
        "do_not_ingest_org": "SMPL Demo Co",
        "counts": {
            "customers": len(customers_rows),
            "subscriptions": len(subscriptions_rows),
            "invoices": len(invoices_rows),
            "payments": len(payments_rows),
            "mrr_waterfall": len(mrr_rows),
            "stripe_customers_found": len(customers_api),
        },
        "files": {
            "customers": str(out_dir / "customers.csv"),
            "subscriptions": str(out_dir / "subscriptions.csv"),
            "invoices": str(out_dir / "invoices.csv"),
            "payments": str(out_dir / "payments.csv"),
            "mrr_waterfall": str(out_dir / "mrr_waterfall.csv"),
            "customer_master": str(out_dir / "customer_master.csv"),
        },
        "alignment": {
            "spine": str(QUICK_DEMO_DIR / "customer_master.csv"),
            "qbo_link": "qbo_customer_ref_id on master ↔ invoices_staging.customer_ref_id",
            "qbo_gap": "QBO JE thin (6 gl_actuals rows); QBO sample display names are Intuit sandbox retail — SaaS names live on master",
            "mrr_waterfall": "Synthesized Jan–May 2026 from master start dates + Stripe current MRR (not full Stripe billing history)",
        },
        "notes": [
            "Compact demo_csv headers (detector EXPECTED).",
            "No org ingest performed.",
            "Uses CONNECTOR_STRIPE_* only.",
        ],
    }
    (out_dir / "export_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest["counts"], indent=2))
    print(f"export -> {out_dir}")
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description="Export Stripe Quick Demo Co → SMPL CSVs")
    ap.add_argument(
        "--out",
        type=Path,
        default=STRIPE_EXPORT_DIR,
        help="Output directory (default: backend/tmp/stripe_export)",
    )
    args = ap.parse_args()
    export(args.out)


if __name__ == "__main__":
    main()
