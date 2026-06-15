"""Ensure the demo organization row exists (for prod auth smoke tests)."""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

DEFAULT_ORG_ID = uuid.UUID("8571e520-0687-4516-bdee-379f37c58c1f")
DEFAULT_ORG_NAME = "SMPL Demo Co"


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Upsert demo organization for login testing")
    parser.add_argument("--organization-id", default=str(DEFAULT_ORG_ID))
    parser.add_argument("--name", default=DEFAULT_ORG_NAME)
    args = parser.parse_args()

    org_id = uuid.UUID(args.organization_id)
    engine = create_engine(load_database_url())
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id, name FROM organizations WHERE id = :id"),
            {"id": str(org_id)},
        ).first()
        if existing:
            print(f"OK: organization already exists — {existing.name} ({existing.id})")
            return

        conn.execute(
            text(
                """
                INSERT INTO organizations (id, name)
                VALUES (:id, :name)
                """
            ),
            {"id": str(org_id), "name": args.name},
        )

    print(f"OK: created organization {args.name} ({org_id})")


if __name__ == "__main__":
    main()
