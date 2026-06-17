"""Verify warehouse row counts and login access for a direct-access POC org."""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

WAREHOUSE_TABLES = (
    "opportunities",
    "mrr_waterfall",
    "gl_actuals",
    "forecast_opportunities",
    "workforce_employees",
    "customers",
)

MIN_ROWS_DEFAULT = 1


def load_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise SystemExit("DATABASE_URL is not set.")
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify warehouse data for a POC organization")
    parser.add_argument("--organization-id", required=True)
    parser.add_argument("--email", default="", help="Optional: verify pending invite or active membership")
    parser.add_argument("--min-rows", type=int, default=MIN_ROWS_DEFAULT)
    args = parser.parse_args()

    org_id = args.organization_id.strip()
    email = args.email.strip().lower()
    min_rows = max(0, args.min_rows)

    engine = create_engine(load_database_url())
    failures: list[str] = []

    print("")
    print("=== poc-0 verify: direct-access warehouse ===")
    print(f"Org:   {org_id}")
    if email:
        print(f"Email: {email}")
    print("")

    with engine.connect() as conn:
        org = conn.execute(
            text(
                """
                SELECT name, COALESCE(plan, 'starter') AS plan, status
                FROM organizations
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": org_id},
        ).first()
        if org is None:
            failures.append(f"organization not found: {org_id}")
            print("FAILED:")
            for item in failures:
                print(f"  - {item}")
            sys.exit(1)

        name, plan, status = org
        print(f"Organization: {name}")
        print(f"Plan:         {plan}")
        print(f"Status:       {status}")
        print("")

        if email:
            user = conn.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": email},
            ).first()
            invite = conn.execute(
                text(
                    """
                    SELECT status FROM pending_user_invites
                    WHERE email = :email AND organization_id = CAST(:oid AS uuid)
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {"email": email, "oid": org_id},
            ).first()
            if user:
                member = conn.execute(
                    text(
                        """
                        SELECT status FROM organization_members
                        WHERE user_id = :uid AND organization_id = CAST(:oid AS uuid)
                        """
                    ),
                    {"uid": str(user.id), "oid": org_id},
                ).first()
                if member and member.status == "active":
                    print(f"OK: {email} has active membership")
                elif invite:
                    print(f"OK: {email} has invite status={invite.status} (login to accept)")
                else:
                    failures.append(f"no membership or invite for {email} on this org")
            elif invite:
                print(f"OK: {email} has pending invite (status={invite.status})")
            else:
                failures.append(f"no user or invite for {email}")

        print("Warehouse row counts:")
        tables_with_data = 0
        for table in WAREHOUSE_TABLES:
            try:
                count = int(
                    conn.execute(
                        text(f"SELECT count(*) FROM {table} WHERE organization_id = CAST(:oid AS uuid)"),
                        {"oid": org_id},
                    ).scalar()
                    or 0
                )
            except Exception as exc:
                print(f"  {table}: (skip) {exc}")
                continue
            print(f"  {table}: {count}")
            if count >= min_rows:
                tables_with_data += 1

        if tables_with_data == 0:
            failures.append(
                f"no warehouse tables have >= {min_rows} rows — run setup-prod-warehouse.ps1"
            )
        else:
            print("")
            print(f"OK: {tables_with_data} table(s) have data")

    print("")
    if failures:
        print("FAILED:")
        for item in failures:
            print(f"  - {item}")
        print("")
        sys.exit(1)

    print("All direct-access POC checks passed.")
    print("")
    print("Customer steps:")
    print("  1. https://smpl-financial-intelligence.vercel.app/login")
    if email:
        print(f"  2. Sign in as {email}")
    print("  3. Confirm /app shows data for this workspace")
    print("  4. Validation call: tie out ARR / revenue vs customer source")
    print("")


if __name__ == "__main__":
    main()
