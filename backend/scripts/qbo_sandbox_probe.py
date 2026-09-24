"""Read-only QuickBooks Online sandbox probe.

Loads CONNECTOR_QBO_* from backend/secrets.env, refreshes an access token,
calls a few GET/query endpoints against the sandbox API, and writes a small
summary JSON under backend/tmp/ (no full entity dumps / PII).

Usage (from repo root):
  python backend/scripts/qbo_sandbox_probe.py
"""
from __future__ import annotations

import base64
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Reuse env helpers from the OAuth one-shot script
sys.path.insert(0, str(Path(__file__).resolve().parent))
from qbo_oauth_once import TOKEN_URL, load_qbo_config  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent
OUT_PATH = BACKEND / "tmp" / "qbo_sandbox_probe_summary.json"
SANDBOX_BASE = "https://sandbox-quickbooks.api.intuit.com"


def _mask(value: str, keep: int = 4) -> str:
    if not value:
        return "(empty)"
    if len(value) <= keep * 2:
        return "***"
    return f"{value[:keep]}…{value[-keep:]} (len={len(value)})"


def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> dict[str, Any]:
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    body = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Basic {basic}",
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


def qbo_get(access_token: str, path: str) -> dict[str, Any]:
    url = f"{SANDBOX_BASE}{path}"
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
        raise RuntimeError(f"QBO GET {path} failed ({exc.code}): {detail[:500]}") from exc


def _query_entities(payload: dict[str, Any], entity: str) -> list[dict[str, Any]]:
    qresp = payload.get("QueryResponse") or {}
    rows = qresp.get(entity) or []
    if isinstance(rows, dict):
        return [rows]
    if isinstance(rows, list):
        return [r for r in rows if isinstance(r, dict)]
    return []


def _sample_fields(rows: list[dict[str, Any]], n: int = 3) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows[:n]:
        for k in row.keys():
            if k not in seen:
                seen.add(k)
                keys.append(k)
    return keys[:20]


def _company_summary(payload: dict[str, Any]) -> dict[str, Any]:
    info = payload.get("CompanyInfo") or {}
    if isinstance(info, list):
        info = info[0] if info else {}
    return {
        "Id": info.get("Id"),
        "CompanyName": info.get("CompanyName"),
        "Country": info.get("Country"),
        "FiscalYearStartMonth": info.get("FiscalYearStartMonth"),
        "field_names_sample": sorted(list(info.keys()))[:25] if isinstance(info, dict) else [],
    }


def main() -> None:
    cfg = load_qbo_config()
    # Also allow realm/refresh from files / env
    import os

    for key in ("CONNECTOR_QBO_REALM_ID", "CONNECTOR_QBO_REFRESH_TOKEN"):
        if os.environ.get(key):
            cfg[key] = os.environ[key]
        else:
            # reload may have missed if only in secrets — load_qbo_config already merges
            pass

    client_id = (cfg.get("CONNECTOR_QBO_CLIENT_ID") or "").strip()
    client_secret = (cfg.get("CONNECTOR_QBO_CLIENT_SECRET") or "").strip()
    realm_id = (cfg.get("CONNECTOR_QBO_REALM_ID") or "").strip()
    refresh_token = (cfg.get("CONNECTOR_QBO_REFRESH_TOKEN") or "").strip()

    missing = [
        name
        for name, val in (
            ("CONNECTOR_QBO_CLIENT_ID", client_id),
            ("CONNECTOR_QBO_CLIENT_SECRET", client_secret),
            ("CONNECTOR_QBO_REALM_ID", realm_id),
            ("CONNECTOR_QBO_REFRESH_TOKEN", refresh_token),
        )
        if not val
    ]
    if missing:
        raise SystemExit(f"Missing required secrets: {', '.join(missing)}")

    print("QBO sandbox probe (read-only)")
    print(f"  realm_id:   {_mask(realm_id, keep=3)}")
    print(f"  client_id:  {_mask(client_id)}")
    print(f"  base:       {SANDBOX_BASE}")
    print()

    tokens = refresh_access_token(client_id, client_secret, refresh_token)
    access = (tokens.get("access_token") or "").strip()
    if not access:
        raise SystemExit(f"Refresh response missing access_token. Keys: {list(tokens)}")
    print(f"  access_token: refreshed (expires_in={tokens.get('expires_in')}s)")

    # If Intuit rotates refresh_token, persist the new one without printing it
    new_refresh = (tokens.get("refresh_token") or "").strip()
    if new_refresh and new_refresh != refresh_token:
        from qbo_oauth_once import upsert_secrets

        upsert_secrets({"CONNECTOR_QBO_REFRESH_TOKEN": new_refresh})
        print("  refresh_token: rotated and saved to secrets.env")

    entities: dict[str, Any] = {}
    errors: list[dict[str, str]] = []

    # CompanyInfo
    try:
        company = qbo_get(access, f"/v3/company/{realm_id}/companyinfo/{realm_id}?minorversion=65")
        entities["CompanyInfo"] = {
            "ok": True,
            "count": 1,
            "summary": _company_summary(company),
        }
        print("  CompanyInfo: ok")
    except Exception as exc:  # noqa: BLE001
        entities["CompanyInfo"] = {"ok": False, "count": 0}
        errors.append({"entity": "CompanyInfo", "error": str(exc)[:300]})
        print(f"  CompanyInfo: FAIL — {exc}")

    # Chart of accounts (sample)
    try:
        q = urllib.parse.quote("select * from Account maxresults 10")
        accounts = qbo_get(access, f"/v3/company/{realm_id}/query?query={q}&minorversion=65")
        rows = _query_entities(accounts, "Account")
        entities["Account"] = {
            "ok": True,
            "count": len(rows),
            "maxresults_requested": 10,
            "field_names_sample": _sample_fields(rows),
            "name_samples": [r.get("Name") for r in rows[:5] if r.get("Name")],
            "types_sample": sorted(
                {str(r.get("AccountType")) for r in rows if r.get("AccountType")}
            )[:10],
        }
        print(f"  Account: {len(rows)} row(s)")
    except Exception as exc:  # noqa: BLE001
        entities["Account"] = {"ok": False, "count": 0}
        errors.append({"entity": "Account", "error": str(exc)[:300]})
        print(f"  Account: FAIL — {exc}")

    # Invoice sample
    try:
        q = urllib.parse.quote("select * from Invoice maxresults 5")
        invoices = qbo_get(access, f"/v3/company/{realm_id}/query?query={q}&minorversion=65")
        rows = _query_entities(invoices, "Invoice")
        entities["Invoice"] = {
            "ok": True,
            "count": len(rows),
            "maxresults_requested": 5,
            "field_names_sample": _sample_fields(rows),
            # Avoid customer display names / PII — ids and totals only
            "id_samples": [r.get("Id") for r in rows[:5] if r.get("Id")],
            "total_amt_present": sum(1 for r in rows if "TotalAmt" in r),
        }
        print(f"  Invoice: {len(rows)} row(s)")
    except Exception as exc:  # noqa: BLE001
        entities["Invoice"] = {"ok": False, "count": 0}
        errors.append({"entity": "Invoice", "error": str(exc)[:300]})
        print(f"  Invoice: FAIL — {exc}")

    # JournalEntry sample
    try:
        q = urllib.parse.quote("select * from JournalEntry maxresults 5")
        jes = qbo_get(access, f"/v3/company/{realm_id}/query?query={q}&minorversion=65")
        rows = _query_entities(jes, "JournalEntry")
        entities["JournalEntry"] = {
            "ok": True,
            "count": len(rows),
            "maxresults_requested": 5,
            "field_names_sample": _sample_fields(rows),
            "id_samples": [r.get("Id") for r in rows[:5] if r.get("Id")],
        }
        print(f"  JournalEntry: {len(rows)} row(s)")
    except Exception as exc:  # noqa: BLE001
        entities["JournalEntry"] = {"ok": False, "count": 0}
        errors.append({"entity": "JournalEntry", "error": str(exc)[:300]})
        print(f"  JournalEntry: FAIL — {exc}")

    summary = {
        "probed_at": datetime.now(timezone.utc).isoformat(),
        "environment": "sandbox",
        "api_base": SANDBOX_BASE,
        "realm_id_masked": _mask(realm_id, keep=3),
        "read_only": True,
        "entities": entities,
        "errors": errors,
        "success": all(e.get("ok") for e in entities.values()) and not errors,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print()
    print(f"Wrote summary: {OUT_PATH}")
    print(f"Overall success: {summary['success']}")
    if not summary["success"]:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        sys.exit(130)
