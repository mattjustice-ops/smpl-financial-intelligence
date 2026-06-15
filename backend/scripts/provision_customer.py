"""Create or update a customer organization and pending invite (manual provisioning)."""

from __future__ import annotations

import argparse
import os
import re
import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

DEFAULT_DEMO_ORG_ID = "8571e520-0687-4516-bdee-379f37c58c1f"
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def load_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return url
    env_file = BACKEND_ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("DATABASE_URL is not set.")


def slugify_name(name: str) -> str:
    base = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    return (base[:80] or "org")


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision org + pending invite for customer login")
    parser.add_argument("--email", required=True)
    parser.add_argument("--organization-id", default="")
    parser.add_argument("--organization-name", default="")
    parser.add_argument("--plan", default="professional", choices=["starter", "professional", "enterprise"])
    parser.add_argument("--role", default="admin")
    args = parser.parse_args()

    email = args.email.strip().lower()
    org_name = args.organization_name.strip()
    org_id_str = args.organization_id.strip()

    if not org_id_str and not org_name:
        org_id_str = DEFAULT_DEMO_ORG_ID
        org_name = ""

    if org_id_str:
        org_id = uuid.UUID(org_id_str)
    else:
        org_id = uuid.uuid4()

    engine = create_engine(load_database_url())
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id, name, status, plan FROM organizations WHERE id = :id"),
            {"id": str(org_id)},
        ).first()

        if existing:
            org_name = existing.name
            print(f"Using existing organization: {existing.name} ({existing.id}) status={existing.status}")
        else:
            if not org_name:
                print("ERROR: --organization-name is required when creating a new org.", file=sys.stderr)
                sys.exit(1)

            slug_base = slugify_name(org_name)
            slug = slug_base
            suffix = 0
            while True:
                taken = conn.execute(
                    text("SELECT id FROM organizations WHERE slug = :slug LIMIT 1"),
                    {"slug": slug},
                ).first()
                if taken is None:
                    break
                suffix += 1
                slug = f"{slug_base}-{suffix}" if suffix < 20 else f"{slug_base}-{uuid.uuid4().hex[:6]}"

            conn.execute(
                text(
                    """
                    INSERT INTO organizations (id, name, slug, status, plan)
                    VALUES (:id, :name, :slug, 'active', :plan)
                    """
                ),
                {
                    "id": str(org_id),
                    "name": org_name,
                    "slug": slug,
                    "plan": args.plan,
                },
            )
            print(f"Created organization: {org_name} ({org_id}) plan={args.plan} slug={slug}")

        member = conn.execute(
            text(
                """
                SELECT om.status
                FROM organization_members om
                JOIN users u ON u.id = om.user_id
                WHERE u.email = :email AND om.organization_id = :organization_id
                """
            ),
            {"email": email, "organization_id": str(org_id)},
        ).first()
        if member and member.status == "active":
            print(f"OK: {email} already has active access to {org_name} ({org_id})")
            print("Prod login: https://smpl-financial-intelligence.vercel.app/login")
            return

        conn.execute(
            text(
                """
                UPDATE pending_user_invites
                SET status = 'canceled'
                WHERE organization_id = :organization_id
                  AND email = :email
                  AND status = 'pending'
                """
            ),
            {"organization_id": str(org_id), "email": email},
        )

        conn.execute(
            text(
                """
                INSERT INTO pending_user_invites (id, organization_id, email, role, status, created_at)
                VALUES (:id, :organization_id, :email, :role, 'pending', now())
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "organization_id": str(org_id),
                "email": email,
                "role": args.role,
            },
        )

    print(f"OK: pending invite for {email} on {org_name} ({org_id})")
    print("")
    print("Next:")
    print("  1. https://smpl-financial-intelligence.vercel.app/login")
    print(f"  2. Enter {email} and open the magic link")
    print("  3. Confirm /app shows the correct workspace")
    print("")
    print(f"Organization ID (for warehouse CSV load): {org_id}")


if __name__ == "__main__":
    main()
