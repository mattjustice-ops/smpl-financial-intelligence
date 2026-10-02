"""FastAPI dependencies for authenticated org-scoped requests (PR1 skeleton)."""

from __future__ import annotations

import hmac
import os
import uuid

from fastapi import Header, HTTPException

from app.models.organization import Organization
from app.models.user import OrganizationMember, User
from app.services.auth.service import AuthService


def internal_key_matches(provided: str | None) -> bool:
    """True when the caller presented the proxy's internal key.

    With BILLING_INTERNAL_API_KEY unset (local dev, tests) every caller matches;
    Vercel and Railway must set the same value or leave both unset.
    """
    expected = os.environ.get("BILLING_INTERNAL_API_KEY", "").strip()
    if not expected:
        return True
    return hmac.compare_digest((provided or "").strip().encode(), expected.encode())


def require_internal_auth_key(
    x_billing_internal_key: str | None = Header(default=None),
    x_smpl_internal_key: str | None = Header(default=None),
) -> None:
    if not internal_key_matches(x_smpl_internal_key or x_billing_internal_key):
        raise HTTPException(status_code=401, detail="Invalid internal API key")


class AuthenticatedMember:
    def __init__(self, user: User, member: OrganizationMember, organization: Organization):
        self.user = user
        self.member = member
        self.organization = organization


def get_authenticated_member(
    db,
    *,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> AuthenticatedMember:
    auth = AuthService(db)
    row = auth.get_member(user_id=user_id, organization_id=organization_id)
    if row is None:
        raise HTTPException(status_code=403, detail="You do not have access to this organization.")
    member, org = row
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=403, detail="User not found.")
    if org.status not in ("active", "trialing", "past_due"):
        raise HTTPException(status_code=403, detail="This organization is not active.")
    return AuthenticatedMember(user=user, member=member, organization=org)
