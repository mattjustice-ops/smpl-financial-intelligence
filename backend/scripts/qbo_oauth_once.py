"""One-shot QuickBooks Online (sandbox) OAuth helper.

Loads CONNECTOR_QBO_* from backend/secrets.env (or .env), starts a tiny
callback server on localhost:8765, prints one authorize URL, exchanges the
code for tokens, and writes REALM_ID + REFRESH_TOKEN back into secrets.env.

Usage (from repo root):
  python backend/scripts/qbo_oauth_once.py

Or from backend/:
  python scripts/qbo_oauth_once.py
"""
from __future__ import annotations

import base64
import json
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parent.parent
SECRETS_PATH = BACKEND / "secrets.env"
ENV_PATH = BACKEND / ".env"

AUTH_URL = "https://appcenter.intuit.com/connect/oauth2"
TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
SCOPE = "com.intuit.quickbooks.accounting"
DEFAULT_REDIRECT = "http://localhost:8765/callback"


def _parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key:
            out[key] = val
    return out


def load_qbo_config() -> dict[str, str]:
    merged: dict[str, str] = {}
    for path in (ENV_PATH, SECRETS_PATH):
        merged.update(_parse_env_file(path))
    # Process env wins over files if already set
    import os

    for key in (
        "CONNECTOR_QBO_CLIENT_ID",
        "CONNECTOR_QBO_CLIENT_SECRET",
        "CONNECTOR_QBO_REDIRECT_URI",
    ):
        if os.environ.get(key):
            merged[key] = os.environ[key]
    return merged


def upsert_secrets(updates: dict[str, str], path: Path = SECRETS_PATH) -> None:
    """Set or uncomment CONNECTOR_QBO_* keys in secrets.env; preserve other lines."""
    if path.is_file():
        lines = path.read_text(encoding="utf-8").splitlines()
    else:
        lines = [
            "# Local secrets — never commit.",
            "",
        ]

    remaining = dict(updates)
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        commented = stripped.startswith("#")
        body = stripped[1:].strip() if commented else stripped
        if "=" not in body:
            new_lines.append(line)
            continue
        key = body.split("=", 1)[0].strip()
        if key in remaining:
            new_lines.append(f"{key}={remaining.pop(key)}")
        else:
            new_lines.append(line)

    if remaining:
        if new_lines and new_lines[-1].strip():
            new_lines.append("")
        if not any("QuickBooks Online" in (l or "") for l in new_lines):
            new_lines.append("# QuickBooks Online (connector sandbox)")
        for key, val in remaining.items():
            new_lines.append(f"{key}={val}")

    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8", newline="\n")


def _mask(value: str, keep: int = 4) -> str:
    if not value:
        return "(empty)"
    if len(value) <= keep * 2:
        return "***"
    return f"{value[:keep]}…{value[-keep:]} (len={len(value)})"


def exchange_code(
    *,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code: str,
) -> dict[str, Any]:
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    body = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
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
        raise SystemExit(f"Token exchange failed ({exc.code}): {detail[:400]}") from exc


def run_oauth() -> None:
    cfg = load_qbo_config()
    client_id = (cfg.get("CONNECTOR_QBO_CLIENT_ID") or "").strip()
    client_secret = (cfg.get("CONNECTOR_QBO_CLIENT_SECRET") or "").strip()
    redirect_uri = (cfg.get("CONNECTOR_QBO_REDIRECT_URI") or DEFAULT_REDIRECT).strip()

    if not client_id or not client_secret:
        raise SystemExit(
            "Missing CONNECTOR_QBO_CLIENT_ID / CONNECTOR_QBO_CLIENT_SECRET in "
            f"{SECRETS_PATH.name} (or .env / process env)."
        )
    if redirect_uri != DEFAULT_REDIRECT:
        print(
            f"Note: redirect URI is {redirect_uri!r}; callback server expects "
            f"{DEFAULT_REDIRECT!r} unless you change the script."
        )

    parsed = urllib.parse.urlparse(redirect_uri)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8765
    path = parsed.path or "/callback"

    state = secrets.token_urlsafe(24)
    result: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return  # quiet

        def do_GET(self) -> None:  # noqa: N802
            u = urllib.parse.urlparse(self.path)
            if u.path != path:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not found")
                return
            qs = urllib.parse.parse_qs(u.query)
            err = (qs.get("error") or [None])[0]
            if err:
                desc = (qs.get("error_description") or [""])[0]
                result["error"] = f"{err}: {desc}"
                body = b"<html><body><h1>OAuth failed</h1><p>You can close this tab.</p></body></html>"
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            code = (qs.get("code") or [None])[0]
            realm = (qs.get("realmId") or [None])[0]
            got_state = (qs.get("state") or [None])[0]
            if not code or not realm:
                result["error"] = "Callback missing code or realmId"
                body = b"<html><body><h1>Missing code/realmId</h1></body></html>"
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if got_state != state:
                result["error"] = "State mismatch (possible CSRF); restart the script"
                body = b"<html><body><h1>State mismatch</h1></body></html>"
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            result["code"] = code
            result["realmId"] = realm
            body = (
                b"<html><body><h1>QuickBooks connected</h1>"
                b"<p>Return to the terminal. You can close this tab.</p></body></html>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    authorize = (
        f"{AUTH_URL}?"
        + urllib.parse.urlencode(
            {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": SCOPE,
                "state": state,
            }
        )
    )

    print("QBO sandbox OAuth (one-shot)")
    print(f"  secrets file: {SECRETS_PATH}")
    print(f"  client_id:    {_mask(client_id)}")
    print(f"  redirect:     {redirect_uri}")
    print(f"  scope:        {SCOPE}")
    print()
    print("1) Ensure this Redirect URI is saved on the Intuit app (Development → Keys).")
    print("2) Open this URL, pick a Sandbox company, Approve:")
    print()
    print(authorize)
    print()

    server = HTTPServer((host, port), Handler)
    print(f"Listening on http://{host}:{port}{path} …")
    try:
        webbrowser.open(authorize)
    except Exception:
        pass

    while "code" not in result and "error" not in result:
        server.handle_request()
    server.server_close()

    if result.get("error"):
        raise SystemExit(f"OAuth callback error: {result['error']}")

    tokens = exchange_code(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        code=result["code"],
    )
    refresh = (tokens.get("refresh_token") or "").strip()
    if not refresh:
        raise SystemExit(f"Token response missing refresh_token. Keys: {list(tokens)}")

    realm_id = result["realmId"]
    upsert_secrets(
        {
            "CONNECTOR_QBO_REALM_ID": realm_id,
            "CONNECTOR_QBO_REFRESH_TOKEN": refresh,
        }
    )

    print()
    print("SUCCESS — wrote tokens to secrets.env (gitignored)")
    print(f"  CONNECTOR_QBO_REALM_ID:       {_mask(realm_id, keep=3)}")
    print(f"  CONNECTOR_QBO_REFRESH_TOKEN:  {_mask(refresh)}")
    if tokens.get("expires_in"):
        print(f"  access_token expires_in:      {tokens.get('expires_in')}s (not stored)")
    print()
    print('Reply "OAuth done" in chat when you see this success line.')


if __name__ == "__main__":
    try:
        run_oauth()
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        sys.exit(130)
