import os
import sys
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo / "backend"))

from sqlalchemy import create_engine, text

db = "postgresql+psycopg://sfi:sfi_dev_password@localhost:5432/sfi"
demo_org = "8571e520-0687-4516-bdee-379f37c58c1f"
email = "mattjustice@smpl-ai.com"
plan = "enterprise"
out = repo / "scripts" / "local-enterprise-update.log"

lines = []
try:
    engine = create_engine(db)
    with engine.begin() as conn:
        orgs = conn.execute(text("SELECT id::text, name, COALESCE(plan, 'starter') FROM organizations ORDER BY name")).all()
        lines.append("Organizations before:")
        for o in orgs:
            lines.append(f"  {o[1]} | {o[2]} | {o[0]}")
        conn.execute(
            text("UPDATE organizations SET plan = :plan WHERE id = CAST(:oid AS uuid)"),
            {"plan": plan, "oid": demo_org},
        )
        after = conn.execute(
            text("SELECT name, plan FROM organizations WHERE id = CAST(:oid AS uuid)"),
            {"oid": demo_org},
        ).first()
        lines.append(f"Updated: {after[0]} -> plan={after[1]}")
        user = conn.execute(text("SELECT id::text FROM users WHERE email = :email"), {"email": email}).first()
        if user:
            member = conn.execute(
                text(
                    """
                    SELECT om.status FROM organization_members om
                    JOIN users u ON u.id = om.user_id
                    WHERE u.email = :email AND om.organization_id = CAST(:oid AS uuid)
                    """
                ),
                {"email": email, "oid": demo_org},
            ).first()
            lines.append(f"Membership for {email}: {member[0] if member else 'MISSING'}")
        else:
            lines.append(f"User {email} not found in local auth DB")
    lines.append("SUCCESS")
except Exception as e:
    lines.append(f"ERROR: {e}")

out.write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
