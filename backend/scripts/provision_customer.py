"""Create or update a customer organization: customer number + profile + pending invite."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

DEFAULT_DEMO_ORG_ID = "8571e520-0687-4516-bdee-379f37c58c1f"


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
    parser = argparse.ArgumentParser(
        description="Provision customer number + org + company profile + pending invite"
    )
    parser.add_argument("--email", required=True, help="Primary user email (admin invite)")
    parser.add_argument("--emails", default="", help="Extra emails, comma-separated")
    parser.add_argument("--customer-number", default="", help="Sales account id, e.g. CUST-0042")
    parser.add_argument("--organization-id", default="")
    parser.add_argument("--organization-name", default="")
    parser.add_argument("--contract-ref", default="")
    parser.add_argument("--contract-signed-on", default="", help="YYYY-MM-DD")
    parser.add_argument("--plan", default="professional", choices=["starter", "professional", "enterprise"])
    parser.add_argument("--role", default="admin")
    parser.add_argument("--fiscal-year-end-month", type=int, default=None)
    parser.add_argument(
        "--profile-json",
        default="",
        help='Company profile JSON, e.g. \'{"industry":"SaaS","stage":"Series B"}\'',
    )
    parser.add_argument(
        "--use-demo-org",
        action="store_true",
        help="Invite onto the SMPL demo org (no new customer number required)",
    )
    args = parser.parse_args()

    emails = [args.email, *[e.strip() for e in args.emails.split(",") if e.strip()]]
    org_id_str = args.organization_id.strip()
    org_name = args.organization_name.strip()
    customer_number = args.customer_number.strip()
    profile: dict = {}
    if args.profile_json.strip():
        try:
            profile = json.loads(args.profile_json)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid --profile-json: {exc}") from exc
        if not isinstance(profile, dict):
            raise SystemExit("--profile-json must be a JSON object")

    if args.use_demo_org and not org_id_str:
        org_id_str = DEFAULT_DEMO_ORG_ID

    # Legacy path A: invite to an existing org without a customer number.
    if org_id_str and not customer_number and not org_name:
        from app.models.organization import Organization
        from app.services.ops.customer_provision import (
            CustomerProvisionRejected,
            _ensure_pending_invites,
            _clean_emails,
        )

        engine = create_engine(load_database_url())
        Session = sessionmaker(bind=engine)
        db = Session()
        try:
            org = db.get(Organization, uuid.UUID(org_id_str))
            if org is None:
                raise SystemExit(f"Organization not found: {org_id_str}")
            invite_emails = _clean_emails(emails)
            result = _ensure_pending_invites(
                db,
                organization_id=org.id,
                emails=invite_emails,
                role=args.role,
            )
            db.commit()
            print(f"Using existing organization: {org.name} ({org.id})")
            if result["already_members"]:
                print(f"Already members: {', '.join(result['already_members'])}")
            if result["invited"]:
                print(f"OK: pending invite(s) for {', '.join(result['invited'])}")
            else:
                print("OK: no new invites needed")
            print(f"ORGANIZATION_ID={org.id}")
        except CustomerProvisionRejected as exc:
            raise SystemExit(exc.message) from exc
        finally:
            db.close()
        return

    if not customer_number:
        raise SystemExit("--customer-number is required for new customer onboarding (or pass --use-demo-org / --organization-id).")
    if not org_name and not org_id_str:
        raise SystemExit("--organization-name is required when creating a new customer.")

    from app.services.ops.customer_provision import CustomerProvisionRejected, provision_customer_onboarding

    engine = create_engine(load_database_url())
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        result = provision_customer_onboarding(
            db,
            customer_number=customer_number,
            organization_name=org_name,
            emails=emails,
            profile=profile or None,
            contract_ref=args.contract_ref.strip() or None,
            contract_signed_on=args.contract_signed_on.strip() or None,
            plan=args.plan,
            role=args.role,
            organization_id=uuid.UUID(org_id_str) if org_id_str else None,
            fiscal_year_end_month=args.fiscal_year_end_month,
        )
    except CustomerProvisionRejected as exc:
        raise SystemExit(exc.message) from exc
    finally:
        db.close()

    action = "Created" if result["created"] else "Updated"
    print(f"{action} organization: {result['organization_name']} ({result['organization_id']})")
    print(f"Customer number: {result['customer_number']}")
    if result.get("contract_ref"):
        print(f"Contract: {result['contract_ref']}")
    invites = result.get("invites") or {}
    if invites.get("already_members"):
        print(f"Already members: {', '.join(invites['already_members'])}")
    if invites.get("invited"):
        print(f"OK: pending invite(s) for {', '.join(invites['invited'])}")
    else:
        print("OK: no new invites needed")
    print("")
    print("Next:")
    print("  1. https://smpl-financial-intelligence.vercel.app/login")
    print(f"  2. Enter invited email and open the magic link")
    print("  3. Confirm /app shows the correct workspace")
    print("")
    print(f"ORGANIZATION_ID={result['organization_id']}")


if __name__ == "__main__":
    main()
