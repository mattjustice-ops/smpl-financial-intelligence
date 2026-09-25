"""One-shot Salesforce OAuth helper.

Loads CONNECTOR_SALESFORCE_* from backend/secrets.env (or .env), starts a tiny
callback server on localhost:8766, prints one authorize URL, exchanges the
code for tokens, and writes REFRESH_TOKEN + INSTANCE_URL back into secrets.env.

Uses login.salesforce.com by default (production / Developer Edition).
Pass --sandbox to use test.salesforce.com instead.

Usage (from repo root):
  python backend/scripts/salesforce_oauth_once.py

Or from backend/:
  python scripts/salesforce_oauth_once.py
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parent.parent
SECRETS_PATH = BACKEND / "secrets.env"
ENV_PATH = BACKEND / ".env"

SCOPE = "api refresh_token offline_access"
DEFAULT_REDIRECT = "http://localhost:8766/callback"


def _login_host(*, sandbox: bool) -> str:
    return "test.salesforce.com" if sandbox else "login.salesforce.com"


def _auth_url(*, sandbox: bool) -> str:
    return f"https://{_login_host(sandbox=sandbox)}/services/oauth2/authorize"


def _token_url(*, sandbox: bool) -> str:
    return f"https://{_login_host(sandbox=sandbox)}/services/oauth2/token"


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


def load_sf_config() -> dict[str, str]:
    merged: dict[str, str] = {}
    for path in (ENV_PATH, SECRETS_PATH):
        merged.update(_parse_env_file(path))
    import os

    for key in (
        "CONNECTOR_SALESFORCE_CLIENT_ID",
        "CONNECTOR_SALESFORCE_CLIENT_SECRET",
        "CONNECTOR_SALESFORCE_REDIRECT_URI",
    ):
        if os.environ.get(key):
            merged[key] = os.environ[key]
    return merged


def upsert_secrets(updates: dict[str, str], path: Path = SECRETS_PATH) -> None:
    """Set or uncomment CONNECTOR_SALESFORCE_* keys in secrets.env; preserve other lines."""
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
        if not any("Salesforce" in (l or "") for l in new_lines):
            new_lines.append("# Salesforce (connector sandbox / DE org)")
        for key, val in remaining.items():
            new_lines.append(f"{key}={val}")

    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8", newline="\n")


def _mask(value: str, keep: int = 4) -> str:
    if not value:
        return "(empty)"
    if len(value) <= keep * 2:
        return "***"
    return f"{value[:keep]}…{value[-keep:]} (len={len(value)})"


def _pkce_pair() -> tuple[str, str]:
    """Return (code_verifier, S256 code_challenge) per RFC 7636."""
    # 64 bytes → ~86 urlsafe chars (within 43–128); strip padding.
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def exchange_code(
    *,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code: str,
    code_verifier: str,
    sandbox: bool,
) -> dict[str, Any]:
    body = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
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
        raise SystemExit(f"Token exchange failed ({exc.code}): {detail[:400]}") from exc


def run_oauth(*, sandbox: bool = False) -> None:
    cfg = load_sf_config()
    client_id = (cfg.get("CONNECTOR_SALESFORCE_CLIENT_ID") or "").strip()
    client_secret = (cfg.get("CONNECTOR_SALESFORCE_CLIENT_SECRET") or "").strip()
    redirect_uri = (cfg.get("CONNECTOR_SALESFORCE_REDIRECT_URI") or DEFAULT_REDIRECT).strip()

    if not client_id or not client_secret:
        raise SystemExit(
            "Missing CONNECTOR_SALESFORCE_CLIENT_ID / CONNECTOR_SALESFORCE_CLIENT_SECRET in "
            f"{SECRETS_PATH.name} (or .env / process env)."
        )
    if redirect_uri != DEFAULT_REDIRECT:
        print(
            f"Note: redirect URI is {redirect_uri!r}; callback server expects "
            f"{DEFAULT_REDIRECT!r} unless you change the script."
        )

    parsed = urllib.parse.urlparse(redirect_uri)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8766
    path = parsed.path or "/callback"

    state = secrets.token_urlsafe(24)
    code_verifier, code_challenge = _pkce_pair()
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
            got_state = (qs.get("state") or [None])[0]
            # Ignore stray hits (browser prefetch / favicon-like probes) without
            # a code — keep listening for the real Salesforce redirect.
            if not code:
                print("Ignoring /callback without code (still waiting)…")
                body = b"<html><body><h1>Waiting for OAuth</h1><p>Use the authorize URL from the terminal.</p></body></html>"
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
            body = (
                b"<html><body><h1>Salesforce connected</h1>"
                b"<p>Return to the terminal. You can close this tab.</p></body></html>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    authorize = (
        f"{_auth_url(sandbox=sandbox)}?"
        + urllib.parse.urlencode(
            {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": SCOPE,
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
        )
    )

    login_host = _login_host(sandbox=sandbox)
    print("Salesforce OAuth (one-shot)")
    print(f"  secrets file: {SECRETS_PATH}")
    print(f"  client_id:    {_mask(client_id)}")
    print(f"  redirect:     {redirect_uri}")
    print(f"  login host:   {login_host}")
    print(f"  scope:        {SCOPE}")
    print(f"  PKCE:         S256")
    print()
    print("1) Ensure Callback URL on the Connected App is exactly:")
    print(f"   {DEFAULT_REDIRECT}")
    print("2) Open this URL, sign in, Allow:")
    print()
    print(authorize)
    print()

    server = HTTPServer((host, port), Handler)
    print(f"Listening on http://{host}:{port}{path} …")
    # Do not auto-open the browser: on Windows this often hits /callback
    # without a code and previously aborted the one-shot listener.
    print("Open the URL above in your browser (do not open localhost:8766 directly).")
    print()

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
        code_verifier=code_verifier,
        sandbox=sandbox,
    )
    refresh = (tokens.get("refresh_token") or "").strip()
    instance_url = (tokens.get("instance_url") or "").strip()
    if not refresh:
        raise SystemExit(f"Token response missing refresh_token. Keys: {list(tokens)}")
    if not instance_url:
        raise SystemExit(f"Token response missing instance_url. Keys: {list(tokens)}")

    upsert_secrets(
        {
            "CONNECTOR_SALESFORCE_REFRESH_TOKEN": refresh,
            "CONNECTOR_SALESFORCE_INSTANCE_URL": instance_url,
        }
    )

    print()
    print("SUCCESS — wrote tokens to secrets.env (gitignored)")
    print(f"  CONNECTOR_SALESFORCE_INSTANCE_URL:   {instance_url}")
    print(f"  CONNECTOR_SALESFORCE_REFRESH_TOKEN:  {_mask(refresh)}")
    if tokens.get("issued_at"):
        print(f"  issued_at:                           {tokens.get('issued_at')} (not stored)")
    print()
    print('Reply "OAuth done" in chat when you see this success line.')


if __name__ == "__main__":
    use_sandbox = "--sandbox" in sys.argv
    try:
        run_oauth(sandbox=use_sandbox)
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        sys.exit(130)
