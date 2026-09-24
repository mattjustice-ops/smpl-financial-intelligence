"""Seed Stripe TEST mode for Quick Demo Co archetype (idempotent first pass).

Uses CONNECTOR_STRIPE_SECRET_KEY only (never STRIPE_* product billing keys).
Writes customer_master.csv spine under backend/tmp/quick_demo_co/.
Does NOT ingest into any SMPL org (especially not SMPL Demo Co).

Usage (from repo root):
  backend\\.venv312\\Scripts\\python.exe backend\\scripts\\stripe_seed_quick_demo.py
  backend\\.venv312\\Scripts\\python.exe backend\\scripts\\stripe_seed_quick_demo.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import stripe

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stripe_quick_demo_common import (  # noqa: E402
    ARCHETYPE,
    QUICK_DEMO_DIR,
    SEED_MARKER,
    cents,
    load_connector_stripe_key,
    read_customer_master,
    write_customer_master,
)

PRODUCT_DEFS = [
    {
        "key": "platform",
        "name": "Quick Demo Platform Suite",
        "prices": {
            "smb": 400_00,
            "mm": 1000_00,
            "ent": 2500_00,
        },
    },
    {
        "key": "addon",
        "name": "Quick Demo Premium Add-On",
        "prices": {"default": 300_00},
    },
]


def _meta_base(extra: dict[str, str] | None = None) -> dict[str, str]:
    m = {
        "smpl_seed": SEED_MARKER,
        "smpl_archetype": ARCHETYPE,
    }
    if extra:
        m.update(extra)
    return m


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


def _find_product(key: str) -> stripe.Product | None:
    # Prefer Search when available; fall back to list+filter
    try:
        res = stripe.Product.search(
            query=f"metadata['smpl_seed']:'{SEED_MARKER}' AND metadata['smpl_product_key']:'{key}'",
            limit=1,
        )
        if res.data:
            return res.data[0]
    except stripe.InvalidRequestError:
        pass
    for p in stripe.Product.list(limit=100, active=True).auto_paging_iter():
        md = _md(p)
        if md.get("smpl_seed") == SEED_MARKER and md.get("smpl_product_key") == key:
            return p
    return None


def _ensure_product(key: str, name: str, dry_run: bool) -> stripe.Product | dict[str, Any]:
    existing = _find_product(key)
    if existing:
        print(f"  product reuse {key} -> {existing.id}")
        return existing
    if dry_run:
        print(f"  product CREATE {key} ({name})")
        return {"id": f"prod_dry_{key}", "metadata": _meta_base({"smpl_product_key": key})}
    prod = stripe.Product.create(
        name=name,
        metadata=_meta_base({"smpl_product_key": key}),
    )
    print(f"  product CREATE {key} -> {prod.id}")
    return prod


def _find_price(product_id: str, unit_amount: int, nickname: str) -> stripe.Price | None:
    want_nick = f"qdc_{nickname}"
    for price in stripe.Price.list(product=product_id, limit=100, active=True).auto_paging_iter():
        if getattr(price, "nickname", None) == want_nick:
            return price
        md = _md(price)
        if md.get("smpl_price_key") == nickname and md.get("smpl_seed") == SEED_MARKER:
            return price
        recurring = getattr(price, "recurring", None)
        interval = getattr(recurring, "interval", None) if recurring is not None else None
        if (
            md.get("smpl_seed") == SEED_MARKER
            and int(price.unit_amount or 0) == int(unit_amount)
            and interval == "month"
        ):
            return price
    return None


def _ensure_price(
    product: stripe.Product | dict[str, Any],
    price_key: str,
    unit_amount: int,
    dry_run: bool,
) -> stripe.Price | dict[str, Any]:
    product_id = product["id"] if isinstance(product, dict) else product.id
    if not dry_run:
        existing = _find_price(product_id, unit_amount, price_key)
        if existing:
            print(f"    price reuse {price_key} -> {existing.id}")
            return existing
    if dry_run:
        print(f"    price CREATE {price_key} ${unit_amount/100:.2f}")
        return {"id": f"price_dry_{price_key}", "unit_amount": unit_amount}
    price = stripe.Price.create(
        product=product_id,
        unit_amount=unit_amount,
        currency="usd",
        recurring={"interval": "month"},
        nickname=f"qdc_{price_key}",
        metadata=_meta_base({"smpl_price_key": price_key, "smpl_product_key": "platform" if "custom" in price_key or price_key in {"smb","mm","ent"} else "addon"}),
    )
    print(f"    price CREATE {price_key} -> {price.id}")
    return price


def _find_customer(smpl_id: str) -> stripe.Customer | None:
    try:
        res = stripe.Customer.search(
            query=f"metadata['smpl_seed']:'{SEED_MARKER}' AND metadata['smpl_customer_id']:'{smpl_id}'",
            limit=1,
        )
        if res.data:
            return res.data[0]
    except stripe.InvalidRequestError:
        pass
    for c in stripe.Customer.list(limit=100).auto_paging_iter():
        md = _md(c)
        if md.get("smpl_seed") == SEED_MARKER and md.get("smpl_customer_id") == smpl_id:
            return c
    return None


def _pay_latest_invoice(sub: stripe.Subscription) -> bool:
    """Finalize + mark paid out-of-band (no card / PM required)."""
    inv_ref = sub.latest_invoice
    if not inv_ref:
        return False
    inv_id = inv_ref if isinstance(inv_ref, str) else inv_ref.id
    inv = stripe.Invoice.retrieve(inv_id)
    if inv.status == "paid":
        return True
    if inv.status == "draft":
        inv = stripe.Invoice.finalize_invoice(inv_id)
    if inv.status in {"open", "uncollectible"}:
        stripe.Invoice.pay(inv_id, paid_out_of_band=True)
        return True
    return inv.status == "paid"


def _create_subscription(
    *,
    customer_id: str,
    price_id: str,
    metadata: dict[str, str],
) -> stripe.Subscription:
    sub = stripe.Subscription.create(
        customer=customer_id,
        items=[{"price": price_id}],
        collection_method="send_invoice",
        days_until_due=30,
        metadata=metadata,
        expand=["latest_invoice"],
    )
    _pay_latest_invoice(sub)
    return sub


def _find_subscription(customer_id: str, sub_key: str) -> stripe.Subscription | None:
    for sub in stripe.Subscription.list(customer=customer_id, status="all", limit=100).auto_paging_iter():
        md = _md(sub)
        if md.get("smpl_seed") == SEED_MARKER and md.get("smpl_sub_key") == sub_key:
            return sub
    return None


def _platform_price_key(mrr: float, plan_tier: str) -> str:
    tier_map = {"smb": 400.0, "mm": 1000.0, "ent": 2500.0}
    if plan_tier in tier_map and abs(mrr - tier_map[plan_tier]) < 0.01:
        return plan_tier
    # custom price slot
    as_int = int(round(mrr))
    return f"custom_{as_int}"


def seed(dry_run: bool = False) -> dict[str, Any]:
    master_path = write_customer_master()
    master = read_customer_master(master_path)
    print(f"customer_master -> {master_path} ({len(master)} rows)")

    key = load_connector_stripe_key()
    stripe.api_key = key
    if not dry_run:
        bal = stripe.Balance.retrieve()
        if getattr(bal, "livemode", None) is True:
            raise SystemExit("Stripe account is live — aborting. Test mode only.")
        print("Stripe ping: test mode OK (livemode=false)")

    # Products + prices
    price_ids: dict[str, str] = {}
    for pdef in PRODUCT_DEFS:
        prod = _ensure_product(pdef["key"], pdef["name"], dry_run)
        for pkey, amount in pdef["prices"].items():
            full_key = f"{pdef['key']}:{pkey}"
            price = _ensure_price(prod, full_key, amount, dry_run)
            price_ids[full_key] = price["id"] if isinstance(price, dict) else price.id

    # Ensure custom platform prices that appear in master
    platform_prod = _ensure_product("platform", "Quick Demo Platform Suite", dry_run)
    for row in master:
        mrr = float(row["platform_mrr"])
        pk = _platform_price_key(mrr, row["plan_tier"])
        full = f"platform:{pk}"
        if full not in price_ids:
            price = _ensure_price(platform_prod, full, cents(mrr), dry_run)
            price_ids[full] = price["id"] if isinstance(price, dict) else price.id

    counts = {
        "customers_created": 0,
        "customers_reused": 0,
        "subscriptions_created": 0,
        "subscriptions_reused": 0,
        "subscriptions_canceled": 0,
        "invoices_paid_approx": 0,
    }
    customer_map: dict[str, str] = {}

    for row in master:
        smpl_id = row["smpl_customer_id"]
        existing = None if dry_run else _find_customer(smpl_id)
        if existing:
            cust_id = existing.id
            counts["customers_reused"] += 1
            print(f"  customer reuse {smpl_id} -> {cust_id}")
        elif dry_run:
            cust_id = f"cus_dry_{smpl_id}"
            counts["customers_created"] += 1
            print(f"  customer CREATE {smpl_id} ({row['customer_name']})")
        else:
            meta = _meta_base(
                {
                    "smpl_customer_id": smpl_id,
                    "qbo_customer_ref_id": row.get("qbo_customer_ref_id") or "",
                    "segment": row.get("segment") or "",
                    "industry": row.get("industry") or "",
                }
            )
            email = f"{smpl_id.lower().replace('-', '.')}@quickdemo.example"
            cust = stripe.Customer.create(
                name=row["customer_name"],
                email=email,
                metadata=meta,
                description=f"{ARCHETYPE} | {smpl_id}",
            )
            cust_id = cust.id
            counts["customers_created"] += 1
            print(f"  customer CREATE {smpl_id} -> {cust_id}")
            time.sleep(0.15)

        customer_map[smpl_id] = cust_id

        # Platform subscription
        platform_mrr = float(row["platform_mrr"])
        pk = _platform_price_key(platform_mrr, row["plan_tier"])
        platform_price_id = price_ids[f"platform:{pk}"]
        sub_key = f"{smpl_id}:platform"
        existing_sub = None if dry_run else _find_subscription(cust_id, sub_key)
        want_cancel = (row.get("status") or "").lower() == "churned"

        if existing_sub:
            counts["subscriptions_reused"] += 1
            print(f"    sub reuse {sub_key} -> {existing_sub.id} ({existing_sub.status})")
            if want_cancel and existing_sub.status in {"active", "trialing", "past_due", "unpaid"}:
                if not dry_run:
                    stripe.Subscription.cancel(existing_sub.id)
                    counts["subscriptions_canceled"] += 1
                    print(f"    sub CANCEL {sub_key}")
        elif dry_run:
            counts["subscriptions_created"] += 1
            print(f"    sub CREATE {sub_key} price={platform_price_id}")
            if want_cancel:
                counts["subscriptions_canceled"] += 1
                print(f"    sub CANCEL {sub_key}")
        else:
            sub = _create_subscription(
                customer_id=cust_id,
                price_id=platform_price_id,
                metadata=_meta_base(
                    {
                        "smpl_customer_id": smpl_id,
                        "smpl_sub_key": sub_key,
                        "product": "Platform Suite",
                    }
                ),
            )
            counts["subscriptions_created"] += 1
            counts["invoices_paid_approx"] += 1
            print(f"    sub CREATE {sub_key} -> {sub.id}")
            if want_cancel:
                stripe.Subscription.cancel(sub.id)
                counts["subscriptions_canceled"] += 1
                print(f"    sub CANCEL {sub_key}")
            time.sleep(0.2)

        # Addon
        addon_mrr = float(row.get("addon_mrr") or 0)
        if addon_mrr > 0 and not want_cancel:
            addon_key = f"{smpl_id}:addon"
            addon_price_id = price_ids["addon:default"]
            existing_addon = None if dry_run else _find_subscription(cust_id, addon_key)
            if existing_addon:
                counts["subscriptions_reused"] += 1
                print(f"    sub reuse {addon_key} -> {existing_addon.id}")
            elif dry_run:
                counts["subscriptions_created"] += 1
                print(f"    sub CREATE {addon_key}")
            else:
                sub = _create_subscription(
                    customer_id=cust_id,
                    price_id=addon_price_id,
                    metadata=_meta_base(
                        {
                            "smpl_customer_id": smpl_id,
                            "smpl_sub_key": addon_key,
                            "product": "Premium Add-On",
                        }
                    ),
                )
                counts["subscriptions_created"] += 1
                counts["invoices_paid_approx"] += 1
                print(f"    sub CREATE {addon_key} -> {sub.id}")
                time.sleep(0.2)

    # Persist id map for export convenience
    map_path = QUICK_DEMO_DIR / "stripe_id_map.json"
    payload = {
        "seeded_at": datetime.now(timezone.utc).isoformat(),
        "archetype": ARCHETYPE,
        "smpl_seed": SEED_MARKER,
        "dry_run": dry_run,
        "counts": counts,
        "customers": customer_map,
        "prices": price_ids,
    }
    map_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"id_map -> {map_path}")
    print("counts:", json.dumps(counts))
    return payload


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed Stripe TEST mode for Quick Demo Co")
    ap.add_argument("--dry-run", action="store_true", help="Print actions without writing Stripe")
    args = ap.parse_args()
    seed(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
