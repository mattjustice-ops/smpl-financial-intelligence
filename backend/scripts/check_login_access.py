"""Check pending invites and memberships for a login email."""

from __future__ import annotations

import argparse
import os
import sys
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
    parser = argparse.ArgumentParser(description="Inspect login access for an email")
    parser.add_argument("--email", required=True)
    parser.add_argument("--organization-id", default="8571e520-0687-4516-bdee-379f37c58c1f")
    args = parser.parse_args()

    email = args.email.strip().lower()
    org_id = args.organization_id.strip()

    engine = create_engine(load_database_url())
    with engine.connect() as conn:
        org = conn.execute(
            text("SELECT id, name, status FROM organizations WHERE id = :id"),
            {"id": org_id},
        ).first()
        print(f"Organization {org_id}: {org}")

        invites = conn.execute(
            text(
                """
                SELECT status, role, created_at
                FROM pending_user_invites
                WHERE email = :email AND organization_id = :organization_id
                ORDER BY created_at DESC
                """
            ),
            {"email": email, "organization_id": org_id},
        ).all()
        print(f"Invites for {email}: {invites or 'NONE'}")

        user = conn.execute(
            text("SELECT id, email FROM users WHERE email = :email"),
            {"email": email},
        ).first()
        print(f"User row: {user or 'NONE'}")

        if user:
            members = conn.execute(
                text(
                    """
                    SELECT om.status, om.role, o.name
                    FROM organization_members om
                    JOIN organizations o ON o.id = om.organization_id
                    WHERE om.user_id = :user_id
                    """
                ),
                {"user_id": str(user.id)},
            ).all()
            print(f"Memberships: {members or 'NONE'}")


if __name__ == "__main__":
    main()
