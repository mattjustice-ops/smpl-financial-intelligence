"""Tests for poc-4 organization membership enforcement."""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps.request_context import reset_request_user_id, set_request_user_id
from app.db.base import Base
from app.models.organization import Organization
from app.models.user import OrganizationMember, User
from app.services.organizations import get_organization_or_404


@pytest.fixture()
def membership_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Organization.__table__,
            User.__table__,
            OrganizationMember.__table__,
        ],
    )
    factory = sessionmaker(bind=engine)
    session = factory()

    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    user_a = uuid.uuid4()

    session.add_all(
        [
            Organization(id=org_a, name="Org A", plan="enterprise", status="active"),
            Organization(id=org_b, name="Org B", plan="enterprise", status="active"),
            User(id=user_a, email="member@example.com"),
            OrganizationMember(
                organization_id=org_a,
                user_id=user_a,
                role="admin",
                status="active",
            ),
        ]
    )
    session.commit()

    yield session, user_a, org_a, org_b
    session.close()


def test_get_organization_or_404_allows_member(membership_db):
    db, user_id, org_a, _org_b = membership_db
    token = set_request_user_id(user_id)
    try:
        org = get_organization_or_404(db, org_a)
        assert org.name == "Org A"
    finally:
        reset_request_user_id(token)


def test_get_organization_or_404_blocks_cross_org(membership_db):
    db, user_id, _org_a, org_b = membership_db
    token = set_request_user_id(user_id)
    try:
        with pytest.raises(HTTPException) as exc:
            get_organization_or_404(db, org_b)
        assert exc.value.status_code == 403
        assert exc.value.detail == "You do not have access to this organization."
    finally:
        reset_request_user_id(token)


def test_get_organization_or_404_skips_membership_without_user_header(membership_db):
    db, _user_id, _org_a, org_b = membership_db
    org = get_organization_or_404(db, org_b)
    assert org.name == "Org B"


def test_dashboard_route_blocks_cross_org_via_header(membership_db):
    from fastapi.testclient import TestClient

    from app.db.session import get_db
    from app.main import app

    db, user_id, _org_a, org_b = membership_db

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        blocked = client.get(
            f"/api/v1/dashboard/as-of-period?organization_id={org_b}",
            headers={"X-SFI-User-Id": str(user_id)},
        )
        assert blocked.status_code == 403
        assert blocked.json()["detail"] == "You do not have access to this organization."
    finally:
        app.dependency_overrides.clear()
