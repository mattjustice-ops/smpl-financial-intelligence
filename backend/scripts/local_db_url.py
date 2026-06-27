"""Normalize Railway/Neon DATABASE_URL for local scripts (psycopg v3 driver)."""

from __future__ import annotations

import os


def normalize_database_url(url: str) -> str:
    """Railway uses postgresql://; SQLAlchemy needs postgresql+psycopg:// for psycopg3."""
    stripped = url.strip()
    if stripped.startswith("postgresql://"):
        return "postgresql+psycopg://" + stripped[len("postgresql://") :]
    if stripped.startswith("postgres://"):
        return "postgresql+psycopg://" + stripped[len("postgres://") :]
    return stripped


def prepare_local_database_env() -> None:
    """Set DATABASE_URL before importing app.db.session (must run first)."""
    raw = os.environ.get("DATABASE_URL", "").strip()
    if raw:
        os.environ["DATABASE_URL"] = normalize_database_url(raw)
