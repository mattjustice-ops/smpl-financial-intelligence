"""Read-only Campfire API client.

Auth is a Campfire API token (`Authorization: Token …`) for one company.
The trial company and a customer company use the same request shape.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_BASE = "https://api.meetcampfire.com"


class CampfireError(Exception):
    def __init__(self, status: int, path: str, body: str):
        self.status = status
        self.path = path
        self.body = body
        super().__init__(f"Campfire GET {path} failed ({status})")


class CampfireClient:
    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE, timeout: float = 60):
        key = (api_key or "").strip()
        if not key:
            raise ValueError("Campfire API key is empty")
        self._key = key
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        query = urllib.parse.urlencode(
            {k: v for k, v in (params or {}).items() if v is not None},
            doseq=True,
        )
        url = f"{self._base}{path}"
        if query:
            url = f"{url}?{query}"
        req = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Authorization": f"Token {self._key}",
                "Accept": "application/json",
            },
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                    raw = resp.read().decode("utf-8")
                    return json.loads(raw) if raw else None
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                if exc.code == 429 and attempt < 2:
                    wait = float(exc.headers.get("Retry-After") or "1")
                    time.sleep(min(wait, 5))
                    continue
                raise CampfireError(exc.code, path, detail[:2000]) from exc
        raise CampfireError(429, path, "rate limited")

    def list_all(self, path: str, params: dict[str, Any] | None = None, page_size: int = 100) -> list[dict[str, Any]]:
        """Follow Campfire's count/results/next pages. A bare JSON array is returned as-is."""
        first = self.get(path, {**(params or {}), "limit": page_size, "offset": 0})
        if isinstance(first, list):
            return [row for row in first if isinstance(row, dict)]
        if not isinstance(first, dict):
            return []
        rows = [row for row in (first.get("results") or []) if isinstance(row, dict)]
        offset = page_size
        while first.get("next"):
            page = self.get(path, {**(params or {}), "limit": page_size, "offset": offset})
            if not isinstance(page, dict):
                break
            batch = [row for row in (page.get("results") or []) if isinstance(row, dict)]
            if not batch:
                break
            rows.extend(batch)
            first = page
            offset += page_size
        return rows
