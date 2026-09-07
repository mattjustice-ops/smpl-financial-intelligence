"""Startup guard against serving a local API from a remote database.

Settings read DATABASE_URL from the OS environment before backend/.env, so a stray
export points a laptop at production without any visible signal. Many scripts under
scripts/ set that variable for prod tasks and leave it in the shell.

The check keys on backend/.env, which is gitignored and therefore absent in deployed
environments — so it can only ever fire on a developer machine.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_LOCAL_HOSTS = {"", "localhost", "127.0.0.1", "::1", "host.docker.internal"}
_TRUTHY = {"1", "true", "yes", "on"}


def _host_of(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def describe_target(url: str) -> str:
    """Render host/dbname for logs — never credentials."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return "unparseable-url"
    host = (parts.hostname or "?").lower()
    name = (parts.path or "").lstrip("/") or "?"
    return f"{host}/{name}"


def env_file_database_url(env_path: Path | None = None) -> str | None:
    path = env_path if env_path is not None else _BACKEND_ROOT / ".env"
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, sep, value = stripped.partition("=")
        if not sep or key.strip().upper() != "DATABASE_URL":
            continue
        cleaned = value.strip().strip('"').strip("'")
        if cleaned:
            return cleaned
    return None


def assert_local_database_target(
    effective_url: str,
    *,
    env_path: Path | None = None,
    allow_remote: bool | None = None,
) -> str:
    """Return a one-line description of the target, or raise if it looks like a mistake."""
    if _host_of(effective_url) in _LOCAL_HOSTS:
        return f"local {describe_target(effective_url)}"

    declared = env_file_database_url(env_path)
    # No local declaration to contradict: a deployed environment, or a machine
    # deliberately configured against a remote database.
    if declared is None or _host_of(declared) not in _LOCAL_HOSTS:
        return f"remote {describe_target(effective_url)}"

    if allow_remote is None:
        allow_remote = os.environ.get("SMPL_ALLOW_REMOTE_DB", "").strip().lower() in _TRUTHY
    if allow_remote:
        return f"remote {describe_target(effective_url)} (SMPL_ALLOW_REMOTE_DB)"

    raise RuntimeError(
        f"Refusing to start: backend/.env declares {describe_target(declared)} but "
        f"DATABASE_URL in the environment points at {describe_target(effective_url)}. "
        "A leftover export would run this API against production data. "
        "Clear it (PowerShell: Remove-Item Env:DATABASE_URL) and restart, or set "
        "SMPL_ALLOW_REMOTE_DB=1 if you meant to do this."
    )
