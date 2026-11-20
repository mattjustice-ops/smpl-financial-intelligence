"""Sales-led customer onboarding: customer number + org + profile + invites."""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.billing import PendingUserInvite
from app.models.organization import Organization
from app.models.user import OrganizationMember, User
from app.services.ops.customer_provision import (
    CustomerProvisionRejected,
    provision_customer_onboarding,
)


@pytest.fixture()
def provision_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Organization.__table__,
            User.__table__,
            OrganizationMember.__table__,
            PendingUserInvite.__table__,
        ],
    )
    factory = sessionmaker(bind=engine)
    session = factory()
    yield session
    session.close()


def _fake_profile(db, organization_id, updates, *, commit=False):
    return {
        "company_name": updates.get("display_name") or "Acme",
        "fields": {k: v for k, v in updates.items() if v is not None},
        "missing": [],
    }


def test_rejects_bad_customer_number(provision_db):
    with pytest.raises(CustomerProvisionRejected):
        provision_customer_onboarding(
            provision_db,
            customer_number="x",
            organization_name="Acme",
            emails=["admin@acme.com"],
        )


def test_rejects_missing_email(provision_db):
    with pytest.raises(CustomerProvisionRejected):
        provision_customer_onboarding(
            provision_db,
            customer_number="CUST-1",
            organization_name="Acme",
            emails=["  "],
        )


def test_creates_org_profile_and_invite(provision_db):
    with patch(
        "app.services.ops.customer_provision.upsert_company_profile",
        side_effect=_fake_profile,
    ):
        result = provision_customer_onboarding(
            provision_db,
            customer_number="cust-0042",
            organization_name="Acme Analytics",
            emails=["admin@acme.com", "admin@acme.com", "cfo@acme.com"],
            profile={"industry": "SaaS", "stage": "Series B"},
            contract_ref="MSA-2026-11",
            contract_signed_on="2026-11-01",
            plan="enterprise",
            fiscal_year_end_month=12,
        )

    assert result["created"] is True
    assert result["customer_number"] == "CUST-0042"
    assert result["contract_ref"] == "MSA-2026-11"
    assert result["contract_signed_on"] == "2026-11-01"
    assert result["plan"] == "enterprise"
    assert result["invites"]["invited"] == ["admin@acme.com", "cfo@acme.com"]

    org = provision_db.get(Organization, uuid.UUID(result["organization_id"]))
    assert org is not None
    assert org.customer_number == "CUST-0042"
    assert org.contract_signed_on == date(2026, 11, 1)

    invites = provision_db.scalars(
        select(PendingUserInvite).where(PendingUserInvite.organization_id == org.id)
    ).all()
    assert {i.email for i in invites} == {"admin@acme.com", "cfo@acme.com"}
    assert all(i.status == "pending" for i in invites)


def test_idempotent_on_customer_number(provision_db):
    with patch(
        "app.services.ops.customer_provision.upsert_company_profile",
        side_effect=_fake_profile,
    ):
        first = provision_customer_onboarding(
            provision_db,
            customer_number="CUST-9",
            organization_name="Acme",
            emails=["admin@acme.com"],
        )
        second = provision_customer_onboarding(
            provision_db,
            customer_number="CUST-9",
            organization_name="Acme Analytics",
            emails=["admin@acme.com", "ops@acme.com"],
            contract_ref="MSA-2",
        )

    assert first["organization_id"] == second["organization_id"]
    assert second["created"] is False
    assert second["organization_name"] == "Acme Analytics"
    assert second["contract_ref"] == "MSA-2"
    assert second["invites"]["invited"] == ["ops@acme.com"]
    assert second["invites"]["already_pending"] == ["admin@acme.com"]

    pending = provision_db.scalars(
        select(PendingUserInvite).where(
            PendingUserInvite.organization_id == uuid.UUID(first["organization_id"]),
            PendingUserInvite.status == "pending",
        )
    ).all()
    assert {i.email for i in pending} == {"admin@acme.com", "ops@acme.com"}


def test_skips_invite_when_already_active_member(provision_db):
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    provision_db.add_all(
        [
            Organization(id=org_id, name="Acme", plan="professional", status="active"),
            User(id=user_id, email="admin@acme.com"),
            OrganizationMember(
                organization_id=org_id,
                user_id=user_id,
                role="admin",
                status="active",
            ),
        ]
    )
    provision_db.commit()

    with patch(
        "app.services.ops.customer_provision.upsert_company_profile",
        side_effect=_fake_profile,
    ):
        result = provision_customer_onboarding(
            provision_db,
            customer_number="CUST-MEM",
            organization_name="Acme",
            emails=["admin@acme.com"],
            organization_id=org_id,
        )

    assert result["invites"]["already_members"] == ["admin@acme.com"]
    assert result["invites"]["invited"] == []
