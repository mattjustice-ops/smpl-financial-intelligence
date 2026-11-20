"""Who the company is, as the company recorded it (organization_profiles).

Commentary prompts and exports read this record. A field the company has not filled in is
reported as not provided; nothing is assumed in its place. The company name is the profile's
display name, else the organization's name.
"""

from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

PROFILE_TABLE = "organization_profiles"

TEXT_FIELDS: dict[str, str] = {
    "display_name": "Company name",
    "legal_name": "Legal name",
    "tagline": "Tagline",
    "industry": "Industry",
    "business_model": "Business model",
    "stage": "Stage",
    "description": "Product and market",
    "strengths": "Strengths",
    "weaknesses": "Weaknesses",
    "opportunities": "Opportunities",
    "threats": "Threats",
    "leadership_posture": "Leadership posture",
    "currency": "Reporting currency",
}
LIST_FIELDS: dict[str, str] = {
    "strategic_priorities": "Strategic priorities",
    "favorable_themes": "Favorable themes",
    "unfavorable_themes": "Unfavorable themes",
}
COMPETITORS = "competitors"
CASH_FLOOR = "cash_floor"
FIELD_LABELS: dict[str, str] = {**TEXT_FIELDS, **LIST_FIELDS, COMPETITORS: "Competitors", CASH_FLOOR: "Cash floor"}


class CompanyProfileRejected(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _has_table(db: Session, name: str) -> bool:
    try:
        return inspect(db.get_bind()).has_table(name)
    except Exception:
        return False


def _has_column(db: Session, table: str, column: str) -> bool:
    try:
        return column in {c["name"] for c in inspect(db.get_bind()).get_columns(table)}
    except Exception:
        return False


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    out = str(value).strip()
    return out or None


def _clean_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [s for s in (_clean_text(v) for v in value) if s]


def _clean_competitors(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    out: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            name = _clean_text(item.get("name"))
            if name:
                out.append({"name": name, "positioning": _clean_text(item.get("positioning")) or ""})
        elif _clean_text(item):
            out.append({"name": _clean_text(item) or "", "positioning": ""})
    return out


def _clean_amount(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        amount = Decimal(str(value).replace(",", "").replace("$", "").strip())
    except (InvalidOperation, ValueError) as exc:
        raise CompanyProfileRejected("Cash floor needs a dollar amount, like 10000000.") from exc
    if amount < 0:
        raise CompanyProfileRejected("Cash floor cannot be negative.")
    return f"{amount.quantize(Decimal('0.01'))}"


def normalize_profile(raw: dict[str, Any]) -> dict[str, Any]:
    """Keep the known fields, trimmed. Blank text, empty lists and unknown keys are dropped."""
    out: dict[str, Any] = {}
    for key in TEXT_FIELDS:
        value = _clean_text(raw.get(key))
        if value is not None:
            out[key] = value
    for key in LIST_FIELDS:
        values = _clean_list(raw.get(key))
        if values:
            out[key] = values
    competitors = _clean_competitors(raw.get(COMPETITORS))
    if competitors:
        out[COMPETITORS] = competitors
    floor = _clean_amount(raw.get(CASH_FLOOR))
    if floor is not None:
        out[CASH_FLOOR] = floor
    if "currency" in out:
        out["currency"] = out["currency"].upper()[:3]
    return out


def profile_record(organization_name: str | None, stored: dict[str, Any]) -> dict[str, Any]:
    """The profile the outputs read: stored fields, the company name, and what is not provided."""
    fields = normalize_profile(stored)
    name = fields.get("display_name") or _clean_text(organization_name)
    return {
        "company_name": name,
        "fields": fields,
        "missing": [key for key in FIELD_LABELS if key not in fields and not (key == "display_name" and name)],
    }


def load_company_profile(db: Session, organization_id: uuid.UUID) -> dict[str, Any]:
    from app.models.organization import Organization

    org = db.get(Organization, organization_id)
    stored: dict[str, Any] = {}
    if _has_table(db, PROFILE_TABLE):
        row = db.execute(
            text(f"select * from {PROFILE_TABLE} where organization_id = :org"), {"org": str(organization_id)}
        ).mappings().first()
        if row is not None:
            stored = {k: v for k, v in dict(row).items() if k in FIELD_LABELS}
    return profile_record(getattr(org, "name", None), stored)


def upsert_company_profile(
    db: Session,
    organization_id: uuid.UUID,
    updates: dict[str, Any],
    *,
    commit: bool = False,
) -> dict[str, Any]:
    """Write normalized profile fields. Caller owns the transaction unless ``commit`` is True."""
    import json

    if not _has_table(db, PROFILE_TABLE):
        raise CompanyProfileRejected("The company profile table is not set up yet.")
    fields = normalize_profile(updates)
    columns = list(FIELD_LABELS)
    values = {k: fields.get(k) for k in columns}
    for key in (*LIST_FIELDS, COMPETITORS):
        if values[key] is not None:
            values[key] = json.dumps(values[key])
    assignments = ", ".join(f"{c} = excluded.{c}" for c in columns)
    json_cols = set(LIST_FIELDS) | {COMPETITORS}
    placeholders = ", ".join(f"cast(:{c} as json)" if c in json_cols else f":{c}" for c in columns)
    db.execute(
        text(
            f"insert into {PROFILE_TABLE} (organization_id, {', '.join(columns)}) "
            f"values (:org, {placeholders}) "
            f"on conflict (organization_id) do update set {assignments}, updated_at = now()"
        ),
        {"org": str(organization_id), **values},
    )
    if commit:
        db.commit()
    else:
        db.flush()
    return load_company_profile(db, organization_id)


def save_company_profile(db: Session, organization_id: uuid.UUID, updates: dict[str, Any]) -> dict[str, Any]:
    """Replace the company's profile with ``updates`` (normalized). Requires the profile table."""
    return upsert_company_profile(db, organization_id, updates, commit=True)


def is_demo_organization(db: Session, organization_id: uuid.UUID) -> bool:
    """True only for an organization flagged as the demo company. Unflagged or unknown is False."""
    if not _has_column(db, "organizations", "is_demo"):
        return False
    found = db.execute(
        text("select is_demo from organizations where id = :org"), {"org": str(organization_id)}
    ).first()
    return bool(found and found[0])


def company_name(profile: dict[str, Any] | None) -> str:
    return str((profile or {}).get("company_name") or "")


def company_context_for_prompt(profile: dict[str, Any] | None) -> str:
    """Company context for an LLM prompt: what the company recorded, and what it has not provided."""
    profile = profile or {}
    fields = profile.get("fields") or {}
    lines = ["COMPANY CONTEXT (from the company's profile)"]
    name = company_name(profile)
    lines.append(f"Company: {name}" if name else "Company: not provided")
    for key, label in TEXT_FIELDS.items():
        if key == "display_name" or key not in fields:
            continue
        lines.append(f"{label}: {fields[key]}")
    if COMPETITORS in fields:
        lines.append("Competitors: " + "; ".join(
            f"{c['name']} ({c['positioning']})" if c.get("positioning") else c["name"] for c in fields[COMPETITORS]
        ))
    for key, label in LIST_FIELDS.items():
        if key in fields:
            lines.append(f"{label}:")
            lines.extend(f"{i}. {item}" for i, item in enumerate(fields[key], 1))
    if CASH_FLOOR in fields:
        lines.append(f"Cash floor: {fields[CASH_FLOOR]} {fields.get('currency') or ''}".rstrip())
    missing = [FIELD_LABELS[k] for k in profile.get("missing") or [] if k in FIELD_LABELS]
    if missing:
        lines.append("Not provided by the company: " + ", ".join(missing) + ".")
        lines.append("Do not assume anything about an item that is not provided; leave it out.")
    return "\n".join(lines)
