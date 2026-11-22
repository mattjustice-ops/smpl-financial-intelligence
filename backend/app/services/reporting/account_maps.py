"""Account maps saved on the company, applied when the statements are built.

A map is the statement line for one account number. It is not a rewrite of the
loaded general ledger. The next statement build reads it. A freeze pack is not
required to save one.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

PL_MAP_LINES = frozenset({"revenue", "cogs", "sm", "rd", "ga"})
BS_MAP_LINES = {
    "cash": "cash",
    "ar": "accounts_receivable",
    "ap": "accounts_payable",
    "deferred_revenue": "deferred_revenue",
}
# Cash-bridge buckets: preferred over file account_group heuristics when set.
# other_operating is a customer classification target — never a compile plug.
BRIDGE_MAP_LINES = frozenset(
    {"payroll", "commission", "vendor", "interest", "tax", "other_operating"}
)
APPLY_LINES = PL_MAP_LINES | frozenset(BS_MAP_LINES) | BRIDGE_MAP_LINES | frozenset({"exclude"})


def load_account_maps(db: Session, organization_id: uuid.UUID) -> dict[str, str]:
    """Read maps from organizations.gl_account_maps without requiring every ORM column.

    Neon can lag Alembic (missing customer_number / deck_palette). Loading the full
    Organization row then fails and takes down every GL statement build. Prefer a
    narrow column read; fall back to ORM only when that works.
    """
    from sqlalchemy import text

    raw: Any = None
    try:
        raw = db.execute(
            text(
                """
                select gl_account_maps
                from organizations
                where id = :org
                """
            ),
            {"org": str(organization_id)},
        ).scalar()
    except Exception:
        raw = None
        try:
            from app.models.organization import Organization

            org = db.get(Organization, organization_id)
            raw = org.gl_account_maps if org is not None else None
        except Exception:
            raw = None
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for key, value in raw.items():
        account = str(key or "").strip()
        line = str(value.get("line") if isinstance(value, dict) else value or "").strip().lower()
        if account and line in APPLY_LINES:
            out[account] = line
    return out


def save_account_map(
    db: Session,
    organization_id: uuid.UUID,
    account_id: str,
    line: str,
) -> None:
    from app.models.organization import Organization

    account = str(account_id or "").strip()
    mapped = str(line or "").strip().lower()
    if not account or mapped not in APPLY_LINES:
        return
    org = db.get(Organization, organization_id)
    if org is None:
        return
    current = dict(org.gl_account_maps) if isinstance(org.gl_account_maps, dict) else {}
    current[account] = {"line": mapped}
    org.gl_account_maps = current
    db.add(org)
    db.commit()


def clear_account_map(db: Session, organization_id: uuid.UUID, account_id: str) -> None:
    from app.models.organization import Organization

    account = str(account_id or "").strip()
    if not account:
        return
    org = db.get(Organization, organization_id)
    if org is None or not isinstance(org.gl_account_maps, dict) or account not in org.gl_account_maps:
        return
    current = dict(org.gl_account_maps)
    current.pop(account, None)
    org.gl_account_maps = current
    db.add(org)
    db.commit()


def stamp_account_maps(rows: list[dict[str, Any]], maps: dict[str, str]) -> None:
    if not maps:
        return
    for row in rows:
        account = str(row.get("account_number") or "").strip()
        line = maps.get(account)
        if line:
            row["mapped_line"] = line
