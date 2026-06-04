"""Organization slug helpers."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Organization

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify_name(name: str) -> str:
    base = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    return base[:80] or "org"


def unique_org_slug(db: Session, company_name: str) -> str:
    base = slugify_name(company_name)
    candidate = base
    suffix = 0
    while True:
        existing = db.scalar(select(Organization.id).where(Organization.slug == candidate).limit(1))
        if existing is None:
            return candidate
        suffix += 1
        candidate = f"{base}-{suffix}" if suffix < 20 else f"{base}-{uuid.uuid4().hex[:6]}"
