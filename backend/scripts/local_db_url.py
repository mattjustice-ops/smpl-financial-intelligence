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


def validate_database_url(url: str) -> None:
    """Fail fast with a helpful message when DATABASE_URL is missing or still a placeholder."""
    stripped = url.strip()
    if not stripped:
        raise SystemExit(
            "DATABASE_URL is not set.\n"
            "In Railway: open your API service -> Variables -> copy DATABASE_URL.\n"
            'Then in PowerShell: $env:DATABASE_URL = "postgresql://USER:PASS@HOST/DB?sslmode=require"'
        )
    lowered = stripped.lower()
    placeholders = (
        "paste-your-railway-url-here",
        "your-railway-url",
        "your_password",
        "ep-xxxxx",
        "postgresql://...",
        "postgresql://user:pass@host",
        "neondb_owner:password@",
        "changeme",
        "example.com",
    )
    for token in placeholders:
        if token in lowered:
            raise SystemExit(
                "DATABASE_URL is still a placeholder, not your real Neon/Railway URL.\n"
                "Railway -> sfi-api-production service -> Variables -> DATABASE_URL -> copy value.\n"
                "It should look like: postgresql://neondb_owner:xxxxx@ep-xxxx.us-east-2.aws.neon.tech/neondb?sslmode=require\n"
                'Paste it: $env:DATABASE_URL = "postgresql://..."'
            )
    if "@" not in stripped or "://" not in stripped:
        raise SystemExit(
            f"DATABASE_URL does not look like a Postgres connection string: {stripped[:40]}...\n"
            "Copy the full value from Railway Variables (starts with postgresql://)."
        )


def database_url_host_hint(url: str) -> str:
    """Safe host preview for logs (no password)."""
    try:
        without_scheme = url.split("://", 1)[1]
        after_at = without_scheme.split("@", 1)[1]
        host = after_at.split("/", 1)[0]
        return host.split("?")[0]
    except Exception:
        return "(could not parse host)"


def prepare_local_database_env() -> str:
    """Set DATABASE_URL before importing app.db.session (must run first)."""
    raw = os.environ.get("DATABASE_URL", "").strip()
    validate_database_url(raw)
    normalized = normalize_database_url(raw)
    os.environ["DATABASE_URL"] = normalized
    return database_url_host_hint(normalized)
