"""Read-only Salesforce (DE / sandbox) probe.

Loads CONNECTOR_SALESFORCE_* from backend/secrets.env, refreshes an access
token, runs SOQL COUNT() + small samples for Account / Contact / Opportunity /
Lead, and writes a summary JSON under backend/tmp/ (no PII dumps).

Usage (from repo root):
  python backend/scripts/salesforce_sandbox_probe.py

Or from backend/:
  python scripts/salesforce_sandbox_probe.py

Pass --sandbox to refresh via test.salesforce.com (default: login.salesforce.com).
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from salesforce_oauth_once import (  # noqa: E402
    _token_url,
    load_sf_config,
    upsert_secrets,
)

BACKEND = Path(__file__).resolve().parent.parent
OUT_PATH = BACKEND / "tmp" / "salesforce_sandbox_probe_summary.json"

OBJECTS = ("Account", "Contact", "Opportunity", "Lead")


def _mask(value: str, keep: int = 4) -> str:
    if not value:
        return "(empty)"
    if len(value) <= keep * 2:
        return "***"
    return f"{value[:keep]}…{value[-keep:]} (len={len(value)})"


def refresh_access_token(
    *,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    sandbox: bool,
) -> dict[str, Any]:
    body = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        _token_url(sandbox=sandbox),
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Token refresh failed ({exc.code}): {detail[:400]}") from exc


def sf_get(instance_url: str, access_token: str, path: str) -> Any:
    base = instance_url.rstrip("/")
    url = f"{base}{path}"
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"SF GET {path} failed ({exc.code}): {detail[:500]}") from exc


def soql(instance_url: str, access_token: str, query: str) -> dict[str, Any]:
    q = urllib.parse.quote(query, safe="")
    payload = sf_get(instance_url, access_token, f"/services/data/v59.0/query?q={q}")
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected SOQL response type: {type(payload)}")
    return payload


def _sample_fields(records: list[dict[str, Any]], n: int = 3) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for row in records[:n]:
        for k in row.keys():
            if k == "attributes":
                continue
            if k not in seen:
                seen.add(k)
                keys.append(k)
    return keys[:25]


def _probe_object(
    instance_url: str, access_token: str, sobject: str
) -> dict[str, Any]:
    count_payload = soql(
        instance_url, access_token, f"SELECT COUNT() FROM {sobject}"
    )
    total = int(count_payload.get("totalSize") or 0)

    # Id-only sample — avoids dumping names/emails into the summary file.
    sample_payload = soql(
        instance_url,
        access_token,
        f"SELECT Id, CreatedDate FROM {sobject} ORDER BY CreatedDate DESC NULLS LAST LIMIT 5",
    )
    records = [
        r for r in (sample_payload.get("records") or []) if isinstance(r, dict)
    ]
    return {
        "ok": True,
        "count": total,
        "sample_size": len(records),
        "field_names_sample": _sample_fields(records),
        "id_samples": [r.get("Id") for r in records if r.get("Id")],
    }


def main() -> None:
    use_sandbox = "--sandbox" in sys.argv
    cfg = load_sf_config()
    import os

    for key in (
        "CONNECTOR_SALESFORCE_CLIENT_ID",
        "CONNECTOR_SALESFORCE_CLIENT_SECRET",
        "CONNECTOR_SALESFORCE_REFRESH_TOKEN",
        "CONNECTOR_SALESFORCE_INSTANCE_URL",
    ):
        if os.environ.get(key):
            cfg[key] = os.environ[key]

    client_id = (cfg.get("CONNECTOR_SALESFORCE_CLIENT_ID") or "").strip()
    client_secret = (cfg.get("CONNECTOR_SALESFORCE_CLIENT_SECRET") or "").strip()
    refresh_token = (cfg.get("CONNECTOR_SALESFORCE_REFRESH_TOKEN") or "").strip()
    instance_url = (cfg.get("CONNECTOR_SALESFORCE_INSTANCE_URL") or "").strip()

    missing = [
        name
        for name, val in (
            ("CONNECTOR_SALESFORCE_CLIENT_ID", client_id),
            ("CONNECTOR_SALESFORCE_CLIENT_SECRET", client_secret),
            ("CONNECTOR_SALESFORCE_REFRESH_TOKEN", refresh_token),
            ("CONNECTOR_SALESFORCE_INSTANCE_URL", instance_url),
        )
        if not val
    ]
    if missing:
        raise SystemExit(f"Missing required secrets: {', '.join(missing)}")

    host = urllib.parse.urlparse(instance_url).netloc or "(unknown)"
    print("Salesforce probe (read-only)")
    print(f"  instance host: {_mask(host, keep=6)}")
    print(f"  client_id:     {_mask(client_id)}")
    print(f"  login host:    {'test' if use_sandbox else 'login'}.salesforce.com")
    print()

    tokens = refresh_access_token(
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
        sandbox=use_sandbox,
    )
    access = (tokens.get("access_token") or "").strip()
    if not access:
        raise SystemExit(f"Refresh response missing access_token. Keys: {list(tokens)}")
    print(f"  access_token: refreshed (expires_in={tokens.get('expires_in')}s)")

    # Prefer instance_url from refresh response when present
    refreshed_instance = (tokens.get("instance_url") or "").strip()
    if refreshed_instance and refreshed_instance != instance_url:
        upsert_secrets({"CONNECTOR_SALESFORCE_INSTANCE_URL": refreshed_instance})
        instance_url = refreshed_instance
        print("  instance_url: updated from token response and saved")

    entities: dict[str, Any] = {}
    errors: list[dict[str, str]] = []

    # Org identity (non-PII)
    try:
        org = soql(
            instance_url,
            access,
            "SELECT Id, Name, OrganizationType, IsSandbox, InstanceName FROM Organization LIMIT 1",
        )
        rows = [r for r in (org.get("records") or []) if isinstance(r, dict)]
        row = rows[0] if rows else {}
        entities["Organization"] = {
            "ok": True,
            "count": 1,
            "summary": {
                "Id": row.get("Id"),
                "Name": row.get("Name"),
                "OrganizationType": row.get("OrganizationType"),
                "IsSandbox": row.get("IsSandbox"),
                "InstanceName": row.get("InstanceName"),
            },
        }
        print(
            f"  Organization: {row.get('Name')!r} "
            f"type={row.get('OrganizationType')} sandbox={row.get('IsSandbox')}"
        )
    except Exception as exc:  # noqa: BLE001
        entities["Organization"] = {"ok": False, "count": 0}
        errors.append({"entity": "Organization", "error": str(exc)[:300]})
        print(f"  Organization: FAIL — {exc}")

    for sobject in OBJECTS:
        try:
            entities[sobject] = _probe_object(instance_url, access, sobject)
            print(f"  {sobject}: count={entities[sobject]['count']}")
        except Exception as exc:  # noqa: BLE001
            entities[sobject] = {"ok": False, "count": 0}
            errors.append({"entity": sobject, "error": str(exc)[:300]})
            print(f"  {sobject}: FAIL — {exc}")

    crm_counts = {name: entities.get(name, {}).get("count", 0) for name in OBJECTS}
    org_empty = all(int(crm_counts.get(name) or 0) == 0 for name in OBJECTS)

    summary = {
        "probed_at": datetime.now(timezone.utc).isoformat(),
        "environment": "sandbox_login" if use_sandbox else "production_login_or_de",
        "instance_host_masked": _mask(host, keep=6),
        "api_version": "v59.0",
        "read_only": True,
        "org_appears_empty": org_empty,
        "entities": entities,
        "crm_counts": crm_counts,
        "errors": errors,
        "success": all(e.get("ok") for e in entities.values()) and not errors,
        "notes": (
            (
                "Org appears empty (common for fresh DE); "
                if org_empty
                else "Org has CRM rows already; "
            )
            + "do not seed unless aligning Net/Quick demo CRM later. "
            "No ingest into SMPL Demo Co."
        ),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print()
    print(f"Wrote summary: {OUT_PATH}")
    print(f"org_appears_empty: {org_empty}")
    print(f"Overall success: {summary['success']}")
    if not summary["success"]:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        sys.exit(130)
