"""List billing customers, subscriptions, and recent Stripe events in production Neon."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text


def main() -> None:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("DATABASE_URL not set")
        sys.exit(1)

    engine = create_engine(url)
    with engine.connect() as conn:
        subs = conn.execute(
            text(
                """
                SELECT bs.stripe_subscription_id, bs.plan, bs.billing_interval, bs.status,
                       bs.stripe_customer_id, bs.created_at::text,
                       o.name AS organization_name
                FROM billing_subscriptions bs
                JOIN organizations o ON o.id = bs.organization_id
                ORDER BY bs.created_at DESC
                LIMIT 20
                """
            )
        ).mappings().all()

        customers = conn.execute(
            text(
                """
                SELECT email, stripe_customer_id, company_name, created_at::text
                FROM billing_customers
                ORDER BY created_at DESC
                LIMIT 20
                """
            )
        ).mappings().all()

        events = conn.execute(
            text(
                """
                SELECT stripe_event_id, event_type, status, created_at::text
                FROM billing_events
                ORDER BY created_at DESC
                LIMIT 10
                """
            )
        ).mappings().all()

    print(f"billing_subscriptions: {len(subs)} row(s) shown (max 20)")
    for row in subs:
        print(
            f"  {row['status']:12} {row['plan']:14} {row['billing_interval']:8} "
            f"{row['stripe_subscription_id']}  org={row['organization_name']}"
        )

    print(f"\nbilling_customers: {len(customers)} row(s) shown (max 20)")
    for row in customers:
        print(f"  {row['email']:40} {row['stripe_customer_id'] or '(no stripe id)'}")

    print(f"\nbilling_events (recent): {len(events)} row(s)")
    for row in events:
        print(f"  {row['status']:10} {row['event_type']:40} {row['stripe_event_id']}")


if __name__ == "__main__":
    main()
