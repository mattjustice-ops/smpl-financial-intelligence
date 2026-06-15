"""List organizations in production Neon (for ops scripts)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


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
    engine = create_engine(load_database_url())
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id::text, name, COALESCE(plan, 'starter') AS plan, status
                FROM organizations
                ORDER BY created_at
                """
            )
        ).all()

    if not rows:
        print("No organizations in this database.")
        print("Run: .\\scripts\\setup-prod-auth-db.ps1 -DatabaseUrl \"...\"")
        return

    print(f"Found {len(rows)} organization(s):\n")
    for org_id, name, plan, status in rows:
        print(f"  {org_id}")
        print(f"    name:   {name}")
        print(f"    plan:   {plan}")
        print(f"    status: {status}")
        print("")


if __name__ == "__main__":
    main()
