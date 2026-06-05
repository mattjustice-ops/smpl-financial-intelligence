"""Seed a pending_user_invites row for local Auth.js login testing."""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


def load_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return url
    env_file = BACKEND_ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "postgresql+psycopg://sfi:sfi_dev_password@127.0.0.1:5432/sfi"


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed pending_user_invites for login testing")
    parser.add_argument("--email", required=True)
    parser.add_argument("--organization-id", required=True)
    parser.add_argument("--role", default="admin")
    args = parser.parse_args()

    org_id = uuid.UUID(args.organization_id)
    email = args.email.strip().lower()

    engine = create_engine(load_database_url())
    with engine.begin() as conn:
        org = conn.execute(
            text("SELECT id, name FROM organizations WHERE id = :id"),
            {"id": str(org_id)},
        ).first()
        if org is None:
            print(f"ERROR: Organization not found: {org_id}", file=sys.stderr)
            sys.exit(1)

        existing = conn.execute(
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
        if existing and existing.status == "active":
            print(f"OK: {email} already has active access to org {org.name} ({org_id})")
            print("Sign in at http://localhost:3002/login and request a fresh magic link.")
            return

        # Clear stale pending rows, then always add a fresh pending invite when not active.
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

    print(f"OK: pending invite for {email} on org {org.name} ({org_id})")
    print("Sign in at http://localhost:3002/login")
    print("Request a NEW magic link, then click it while the backend stays running on port 8001.")


if __name__ == "__main__":
    main()
