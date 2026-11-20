"""Sales-led customer onboarding: customer number + org + profile + invites."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.billing import PendingUserInvite
from app.models.organization import Organization
from app.models.user import OrganizationMember, User
from app.services.billing.slug import unique_org_slug
from app.services.company_profile import CompanyProfileRejected, load_company_profile, upsert_company_profile

_CUSTOMER_NUMBER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,62}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CustomerProvisionRejected(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _clean_customer_number(value: str) -> str:
    raw = (value or "").strip().upper()
    if not raw or not _CUSTOMER_NUMBER_RE.match(raw):
        raise CustomerProvisionRejected(
            "Customer number must be 2–63 characters: letters, numbers, ., _, or - (e.g. CUST-0042)."
        )
    return raw


def _clean_emails(emails: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in emails:
        email = (raw or "").strip().lower()
        if not email:
            continue
        if not _EMAIL_RE.match(email):
            raise CustomerProvisionRejected(f"Invalid email: {raw!r}")
        if email in seen:
            continue
        seen.add(email)
        cleaned.append(email)
    if not cleaned:
        raise CustomerProvisionRejected("At least one user email is required.")
    return cleaned


def _parse_signed_on(value: date | datetime | str | None) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise CustomerProvisionRejected("contract_signed_on must be YYYY-MM-DD.") from exc


def _active_member_emails(db: Session, organization_id: uuid.UUID, emails: list[str]) -> set[str]:
    if not emails:
        return set()
    rows = db.execute(
        select(User.email)
        .join(OrganizationMember, OrganizationMember.user_id == User.id)
        .where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.status == "active",
            User.email.in_(emails),
        )
    ).scalars().all()
    return {str(e).lower() for e in rows}


def _ensure_pending_invites(
    db: Session,
    *,
    organization_id: uuid.UUID,
    emails: list[str],
    role: str,
) -> dict[str, list[str]]:
    already_members = _active_member_emails(db, organization_id, emails)
    invited: list[str] = []
    already_pending: list[str] = []
    skipped_members = sorted(already_members)

    for email in emails:
        if email in already_members:
            continue
        pending = db.scalars(
            select(PendingUserInvite).where(
                PendingUserInvite.organization_id == organization_id,
                PendingUserInvite.email == email,
                PendingUserInvite.status == "pending",
            )
        ).all()
        if pending:
            already_pending.append(email)
            continue
        db.add(
            PendingUserInvite(
                organization_id=organization_id,
                email=email,
                role=role,
                status="pending",
            )
        )
        invited.append(email)
    return {
        "invited": invited,
        "already_pending": already_pending,
        "already_members": skipped_members,
    }


def provision_customer_onboarding(
    db: Session,
    *,
    customer_number: str,
    organization_name: str,
    emails: list[str],
    profile: dict[str, Any] | None = None,
    contract_ref: str | None = None,
    contract_signed_on: date | datetime | str | None = None,
    plan: str = "professional",
    role: str = "admin",
    organization_id: uuid.UUID | None = None,
    fiscal_year_end_month: int | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Create or update a customer org from MSA/contract intake, then invite users.

    Idempotent on ``customer_number``: the same number updates that org and refreshes invites.
    """
    number = _clean_customer_number(customer_number)
    name = (organization_name or "").strip()
    invite_emails = _clean_emails(emails)
    plan_value = (plan or "professional").strip().lower() or "professional"
    role_value = (role or "admin").strip().lower() or "admin"
    signed_on = _parse_signed_on(contract_signed_on)
    contract = (contract_ref or "").strip() or None

    if fiscal_year_end_month is not None and not (1 <= int(fiscal_year_end_month) <= 12):
        raise CustomerProvisionRejected("fiscal_year_end_month must be 1–12.")

    by_number = db.scalar(select(Organization).where(Organization.customer_number == number).limit(1))
    org: Organization | None = None
    created = False

    if organization_id is not None:
        org = db.get(Organization, organization_id)
        if org is None:
            raise CustomerProvisionRejected("organization_id not found.")
        if by_number is not None and by_number.id != org.id:
            raise CustomerProvisionRejected(
                f"Customer number {number} already belongs to another organization ({by_number.id})."
            )
    elif by_number is not None:
        org = by_number
    else:
        if not name:
            raise CustomerProvisionRejected("Organization name is required.")
        org = Organization(
            name=name,
            slug=unique_org_slug(db, name),
            customer_number=number,
            status="active",
            plan=plan_value,
        )
        db.add(org)
        db.flush()
        created = True

    if name:
        org.name = name
    elif not org.name:
        raise CustomerProvisionRejected("Organization name is required.")
    org.customer_number = number
    org.status = "active"
    org.plan = plan_value
    if contract is not None:
        org.contract_ref = contract
    if signed_on is not None:
        org.contract_signed_on = signed_on
    if fiscal_year_end_month is not None:
        org.fiscal_year_end_month = int(fiscal_year_end_month)
    if not org.slug:
        org.slug = unique_org_slug(db, org.name)

    db.flush()

    profile_payload = dict(profile or {})
    if "display_name" not in profile_payload:
        profile_payload["display_name"] = org.name

    try:
        profile_record = upsert_company_profile(db, org.id, profile_payload, commit=False)
    except CompanyProfileRejected as exc:
        raise CustomerProvisionRejected(exc.message) from exc

    invite_result = _ensure_pending_invites(
        db,
        organization_id=org.id,
        emails=invite_emails,
        role=role_value,
    )

    if commit:
        db.commit()
        db.refresh(org)

    return {
        "created": created,
        "organization_id": str(org.id),
        "organization_name": org.name,
        "customer_number": org.customer_number,
        "contract_ref": org.contract_ref,
        "contract_signed_on": org.contract_signed_on.isoformat() if org.contract_signed_on else None,
        "plan": org.plan,
        "slug": org.slug,
        "fiscal_year_end_month": org.fiscal_year_end_month,
        "profile": profile_record,
        "invites": invite_result,
    }
