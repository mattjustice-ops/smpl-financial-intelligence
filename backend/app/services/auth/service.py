"""Auth session sync — upsert user, accept invites, enforce seat limits."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.billing import PendingUserInvite
from app.models.organization import Organization
from app.models.user import OrganizationMember, User
from app.services.entitlements import normalize_plan, seat_limit_for_org, seats_available


class AuthSyncError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _membership_payload(member: OrganizationMember, org: Organization) -> dict[str, Any]:
    plan = normalize_plan(org.plan)
    return {
        "organizationId": str(org.id),
        "organizationName": org.name,
        "role": member.role,
        "status": member.status,
        "plan": plan,
        "seatLimit": seat_limit_for_org(org),
        "organizationStatus": org.status,
    }


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def sync_session(
        self,
        *,
        email: str,
        name: str | None = None,
        auth_subject: str | None = None,
    ) -> dict[str, Any]:
        normalized_email = email.strip().lower()
        if not normalized_email:
            raise AuthSyncError("invalid_email", "Email is required.")

        user = self.db.scalar(select(User).where(User.email == normalized_email))
        if user is None:
            user = User(email=normalized_email, name=name, auth_subject=auth_subject)
            self.db.add(user)
            self.db.flush()
        else:
            if name and name.strip():
                user.name = name.strip()
            if auth_subject:
                user.auth_subject = auth_subject
            user.updated_at = _utcnow()

        self._accept_pending_invites(user)
        # SessionLocal uses autoflush=False; membership rows must be flushed before reload.
        self.db.flush()
        memberships = self._load_active_memberships(user)

        if not memberships:
            raise AuthSyncError(
                "no_access",
                "No workspace access for this email. Use the address from your SMPL invite or checkout.",
            )

        now = _utcnow()
        for member, _org in memberships:
            member.last_active_at = now

        self.db.commit()
        self.db.refresh(user)

        org_payloads = [_membership_payload(member, org) for member, org in memberships]
        active_org_id = org_payloads[0]["organizationId"]

        return {
            "userId": str(user.id),
            "email": user.email,
            "name": user.name,
            "activeOrganizationId": active_org_id,
            "organizations": org_payloads,
        }

    def _accept_pending_invites(self, user: User) -> None:
        invites = self.db.scalars(
            select(PendingUserInvite)
            .where(
                PendingUserInvite.email == user.email,
                PendingUserInvite.status == "pending",
            )
            .order_by(PendingUserInvite.created_at.asc())
        ).all()

        for invite in invites:
            org = self.db.get(Organization, invite.organization_id)
            if org is None:
                invite.status = "canceled"
                continue

            existing = self.db.scalar(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == org.id,
                    OrganizationMember.user_id == user.id,
                )
            )

            if existing:
                if existing.status != "active":
                    if seats_available(self.db, org) <= 0:
                        raise AuthSyncError(
                            "seats_full",
                            f"{org.name} has reached its seat limit ({seat_limit_for_org(org)}). "
                            "Ask an admin to upgrade the plan or remove a user.",
                        )
                    existing.status = "active"
                    existing.role = invite.role or existing.role
                invite.status = "accepted"
                continue

            if seats_available(self.db, org) <= 0:
                raise AuthSyncError(
                    "seats_full",
                    f"{org.name} has reached its seat limit ({seat_limit_for_org(org)}). "
                    "Ask an admin to upgrade the plan or remove a user.",
                )

            self.db.add(
                OrganizationMember(
                    organization_id=org.id,
                    user_id=user.id,
                    role=invite.role or "member",
                    status="active",
                    last_active_at=_utcnow(),
                )
            )
            invite.status = "accepted"

    def _load_active_memberships(self, user: User) -> list[tuple[OrganizationMember, Organization]]:
        rows = self.db.execute(
            select(OrganizationMember, Organization)
            .join(Organization, Organization.id == OrganizationMember.organization_id)
            .where(
                OrganizationMember.user_id == user.id,
                OrganizationMember.status == "active",
            )
            .order_by(OrganizationMember.joined_at.asc())
        ).all()
        return [(member, org) for member, org in rows]

    def get_member(
        self,
        *,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> tuple[OrganizationMember, Organization] | None:
        row = self.db.execute(
            select(OrganizationMember, Organization)
            .join(Organization, Organization.id == OrganizationMember.organization_id)
            .where(
                OrganizationMember.user_id == user_id,
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.status == "active",
            )
        ).first()
        if not row:
            return None
        return row[0], row[1]
