"""Smoke test gl-3 plan module entitlements against Neon + optional hosted API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.entitlements import modules_for_plan  # noqa: E402
from app.services.organizations import get_organization_or_404  # noqa: E402


DEFAULT_ORG_ID = "8571e520-0687-4516-bdee-379f37c58c1f"


def load_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return url
    raise SystemExit("DATABASE_URL is not set.")


def normalize_db_url(url: str) -> str:
    u = url.strip().strip('"').strip("'")
    if u.startswith("postgresql://"):
        return u.replace("postgresql://", "postgresql+psycopg://", 1)
    if u.startswith("postgres://"):
        return u.replace("postgres://", "postgresql+psycopg://", 1)
    return u


def fetch_org_plan(conn, org_id: str) -> tuple[bool, str]:
    row = conn.execute(
        text(
            """
            SELECT COALESCE(plan, 'starter') AS plan
            FROM organizations
            WHERE id = CAST(:id AS uuid)
            """
        ),
        {"id": org_id},
    ).first()
    if row is None:
        return False, "starter"
    return True, str(row[0])


def set_plan(conn, org_id: str, plan: str) -> None:
    conn.execute(
        text("UPDATE organizations SET plan = :plan WHERE id = CAST(:id AS uuid)"),
        {"id": org_id, "plan": plan},
    )


def api_get_health(api_base: str) -> tuple[int, dict]:
    url = f"{api_base.rstrip('/')}/health"
    req = Request(url, method="GET")
    try:
        with urlopen(req, timeout=30) as resp:
            import json as json_mod

            body = json_mod.loads(resp.read(4096).decode("utf-8"))
            return resp.status, body
    except HTTPError as exc:
        return exc.code, {}


def api_get_workforce_plan(api_base: str, org_id: str) -> tuple[int, str]:
    qs = urlencode(
        {
            "organization_id": org_id,
            "scenario": "Combined",
            "start_period": "2026-01-01",
            "end_period": "2026-12-31",
            "persist": "false",
        }
    )
    url = f"{api_base.rstrip('/')}/api/v1/workforce/plan?{qs}"
    req = Request(url, method="GET")
    try:
        with urlopen(req, timeout=60) as resp:
            return resp.status, resp.read(500).decode("utf-8", errors="replace")
    except HTTPError as exc:
        body = exc.read(500).decode("utf-8", errors="replace")
        return exc.code, body


class FakeSession:
    def __init__(self, org):
        self.org = org

    def get(self, _model, org_id):
        if str(org_id) == str(self.org.id):
            return self.org
        return None


def set_plan_committed(engine, org_id: str, plan: str) -> None:
    """Persist plan so hosted API (separate DB connection) sees the update."""
    with engine.begin() as conn:
        set_plan(conn, org_id, plan)


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test plan module entitlements")
    parser.add_argument("--organization-id", default=DEFAULT_ORG_ID)
    parser.add_argument(
        "--api-base",
        default=os.environ.get("SFI_BACKEND_URL", "http://127.0.0.1:8001"),
        help="FastAPI base URL (Railway prod or local)",
    )
    parser.add_argument("--skip-api", action="store_true")
    parser.add_argument("--keep-plan", choices=["starter", "professional", "enterprise", "restore"], default="restore")
    args = parser.parse_args()

    org_id = args.organization_id.strip()
    engine = create_engine(normalize_db_url(load_database_url()))

    print("")
    print("=== gl-3 smoke test: plan entitlements ===")
    print(f"Org:  {org_id}")
    print(f"API:  {args.api_base}")
    print("")

    failures: list[str] = []

    if not args.skip_api:
        health_status, health = api_get_health(args.api_base)
        entitlements_build = health.get("entitlements_build") if health else None
        print(f"API /health: HTTP {health_status} build={health.get('build') if health else 'n/a'}")
        if entitlements_build:
            print(f"  entitlements_build={entitlements_build}")
        else:
            print(
                "HINT: Railway is still on pre-gl-3 code (no entitlements_build in /health).",
                file=sys.stderr,
            )
            print(
                "      Push latest backend to GitHub and redeploy sfi-api on Railway, then re-run.",
                file=sys.stderr,
            )
            failures.append(
                "Railway API missing gl-3 (check /health for entitlements_build). Deploy backend first."
            )

    with engine.begin() as conn:
        exists, original_plan = fetch_org_plan(conn, org_id)
        if not exists:
            available = conn.execute(
                text(
                    """
                    SELECT id::text, name, COALESCE(plan, 'starter')
                    FROM organizations
                    ORDER BY created_at
                    """
                )
            ).all()
            print(f"ERROR: organization not found: {org_id}", file=sys.stderr)
            if available:
                print("\nOrganizations in this database:", file=sys.stderr)
                for row_id, row_name, row_plan in available:
                    print(f"  {row_id}  {row_name}  (plan={row_plan})", file=sys.stderr)
                print(
                    f"\nRe-run with: --organization-id {available[0][0]}",
                    file=sys.stderr,
                )
            else:
                print(
                    "\nNo organizations in this database. "
                    "Run setup-prod-auth-db.ps1 or provision-prod-customer.ps1 first.",
                    file=sys.stderr,
                )
            sys.exit(1)
    print(f"Original plan: {original_plan}")

    # --- Starter ---
    set_plan_committed(engine, org_id, "starter")
    starter_modules = modules_for_plan("starter")
    print(f"Starter modules ({len(starter_modules)}): {', '.join(starter_modules)}")
    if "workforce" in starter_modules:
        failures.append("starter modules should not include workforce")
    if "management-pl" not in starter_modules:
        pass
    if "executive" not in starter_modules:
        failures.append("starter modules should include executive")

    from app.models.organization import Organization

    starter_org = Organization(id=uuid.UUID(org_id), name="Smoke Test", plan="starter")
    fake_db = FakeSession(starter_org)
    try:
        get_organization_or_404(fake_db, uuid.UUID(org_id), module="workforce")
        failures.append("DB gate: starter org should block workforce module")
    except Exception:
        print("OK: DB gate blocks workforce on starter")

    if not args.skip_api:
        if failures:
            print("Skipping workforce API checks until Railway has gl-3 deployed.")
        else:
            status, body = api_get_workforce_plan(args.api_base, org_id)
            print(f"API workforce/plan on starter: HTTP {status}")
            if status != 403:
                failures.append(
                    f"expected HTTP 403 for workforce on starter, got {status}. "
                    "Redeploy Railway sfi-api from latest main."
                )
            elif "module_not_entitled" not in body:
                failures.append("403 body missing module_not_entitled")
            else:
                print("OK: API returns 403 module_not_entitled for starter")

    # --- Professional ---
    set_plan_committed(engine, org_id, "professional")
    pro_modules = modules_for_plan("professional")
    print(f"Professional modules ({len(pro_modules)}): includes workforce={('workforce' in pro_modules)}")
    if "workforce" not in pro_modules:
        failures.append("professional modules should include workforce")

    pro_org = Organization(id=uuid.UUID(org_id), name="Smoke Test", plan="professional")
    fake_db_pro = FakeSession(pro_org)
    try:
        get_organization_or_404(fake_db_pro, uuid.UUID(org_id), module="workforce")
        print("OK: DB gate allows workforce on professional")
    except Exception as exc:
        failures.append(f"DB gate should allow workforce on professional: {exc}")

    if not args.skip_api and not failures:
        status, body = api_get_workforce_plan(args.api_base, org_id)
        print(f"API workforce/plan on professional: HTTP {status}")
        if status == 403:
            failures.append(f"professional should not get 403 on workforce: {body[:200]}")
        else:
            print("OK: API does not return 403 for professional (may be 200/422/500 if data missing)")

    # Restore plan
    if args.keep_plan == "restore":
        set_plan_committed(engine, org_id, original_plan)
        print(f"Restored plan: {original_plan}")
    else:
        set_plan_committed(engine, org_id, args.keep_plan)
        print(f"Left plan as: {args.keep_plan} (re-login on prod to refresh session)")

    print("")
    if failures:
        print("FAILED:")
        for item in failures:
            print(f"  - {item}")
        print("")
        sys.exit(1)

    print("All automated checks passed.")
    print("")
    print("Manual UI check:")
    print("  1. Sign out at https://smpl-financial-intelligence.vercel.app/login")
    if args.keep_plan == "starter":
        print("  2. Plan is starter — re-login and confirm 6 tabs + upgrade banner")
    else:
        print("  2. Re-login and confirm nav matches your org plan")
    print("")


if __name__ == "__main__":
    main()
