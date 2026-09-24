"""One-shot: login to learn.maxio (Skilljar) and dump course catalog titles.

Reads LEARN_MAXIO_EMAIL / LEARN_MAXIO_PASSWORD from backend/secrets.env.
Does not print the password. Writes HTML + title extract under backend/tmp/.
"""
from __future__ import annotations

import html as html_lib
import http.cookiejar
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
OUT_HTML = BACKEND / "tmp" / "learn_maxio_catalog_raw.html"
OUT_TXT = BACKEND / "tmp" / "learn_maxio_catalog_extract.txt"
OUT_JSON = BACKEND / "tmp" / "learn_maxio_catalog_courses.json"

TENANT = "y3s3o3yjlj7m"
DOMAIN = "d3el6ijd7c7n"


def _load_secrets() -> dict[str, str]:
    out: dict[str, str] = {}
    for path in (BACKEND / ".env", BACKEND / "secrets.env"):
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def main() -> None:
    secrets = _load_secrets()
    email = secrets.get("LEARN_MAXIO_EMAIL", "")
    password = secrets.get("LEARN_MAXIO_PASSWORD", "")
    if not email or not password:
        raise SystemExit("Missing LEARN_MAXIO_EMAIL / LEARN_MAXIO_PASSWORD in secrets.env")

    print(f"email={email}")
    print(f"password_set=True len={len(password)}")

    cj = http.cookiejar.CookieJar()

    class _NoRedir(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: N802
            return None

    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener_noredirect = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        _NoRedir,
    )
    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )
    opener.addheaders = [("User-Agent", ua)]
    opener_noredirect.addheaders = [("User-Agent", ua)]

    def fetch(url: str, data: bytes | None = None, headers: dict | None = None, *, noredirect: bool = False):
        o = opener_noredirect if noredirect else opener
        req = urllib.request.Request(
            url,
            data=data,
            headers=headers or {},
            method="POST" if data is not None else "GET",
        )
        try:
            with o.open(req, timeout=60) as resp:
                return resp.geturl(), resp.status, resp.read(), dict(resp.headers)
        except urllib.error.HTTPError as exc:
            return (
                getattr(exc, "url", url) or url,
                exc.code,
                exc.read(),
                dict(exc.headers),
            )

    def follow(url: str, max_hops: int = 12) -> tuple[str, int, bytes]:
        current = url
        body = b""
        status = 0
        for hop in range(max_hops):
            final, status, body, hdrs = fetch(current, noredirect=True)
            loc = hdrs.get("Location") or hdrs.get("location")
            print(f"  hop={hop} status={status} url={final[:120]}")
            if loc and status in (301, 302, 303, 307, 308):
                loc = html_lib.unescape(loc)
                current = urllib.parse.urljoin(final, loc)
                continue
            # Absolute success / non-redirect
            if status and status < 400:
                return final, status, body
            # Some Skilljar hops 404 with a useful Location-less body; try auto opener once
            final2, status2, body2, _ = fetch(current, noredirect=False)
            return final2, status2, body2
        return current, status, body

    next_path = "/auth/endpoint/login/result?next=%2Fpage%2Fcourse-catalog&d=" + DOMAIN
    login_url = (
        "https://accounts.skilljar.com/accounts/login/"
        f"?t={TENANT}&d={DOMAIN}&next={urllib.parse.quote(next_path, safe='')}"
    )
    final, status, body, _ = fetch(login_url)
    page = body.decode("utf-8", errors="replace")
    print(f"login_page status={status} final={final} len={len(page)}")

    m = re.search(
        r'name=["\']csrfmiddlewaretoken["\'][^>]*value=["\']([^"\']+)',
        page,
        re.I,
    ) or re.search(
        r'value=["\']([^"\']+)["\'][^>]*name=["\']csrfmiddlewaretoken["\']',
        page,
        re.I,
    )
    csrf = m.group(1) if m else ""
    print(f"csrf_found={bool(csrf)}")

    def hidden(name: str, default: str = "") -> str:
        mm = re.search(
            rf"name=['\"]{re.escape(name)}['\"][^>]*value=['\"]([^'\"]*)['\"]",
            page,
            re.I,
        ) or re.search(
            rf"name=['\"]{re.escape(name)}['\"]\s+value=['\"]([^'\"]*)['\"]",
            page,
            re.I,
        )
        return html_lib.unescape(mm.group(1)) if mm else default

    fields = {
        "csrfmiddlewaretoken": csrf,
        "t": hidden("t", TENANT),
        "d": hidden("d", DOMAIN),
        "login": email,
        "password": password,
        "remember": "on",
        "next": hidden("next", next_path),
    }
    post_url = final.split("?")[0]
    data = urllib.parse.urlencode(fields).encode("utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": final,
        "Origin": "https://accounts.skilljar.com",
    }
    final2, status2, body2, hdrs2 = fetch(post_url, data=data, headers=headers, noredirect=True)
    loc = hdrs2.get("Location") or hdrs2.get("location")
    print(f"post status={status2} location={loc}")
    if loc and status2 in (301, 302, 303, 307, 308):
        start = urllib.parse.urljoin(final2, html_lib.unescape(loc))
        final2, status2, body2 = follow(start)
    html2 = body2.decode("utf-8", errors="replace")
    print(f"after_login status={status2} final={final2[:160]} len={len(html2)}")
    print(f"cookies={[c.name for c in cj]}")

    # Catalog on learn.maxio — may bounce through Skilljar SSO
    final3, status3, body3 = follow("https://learn.maxio.com/page/course-catalog")
    html3 = body3.decode("utf-8", errors="replace")
    still_login = (
        "sign in with your existing account" in html3.lower()
        or "accounts/login" in final3
        or 'id="login_form"' in html3
    )
    print(f"catalog status={status3} final={final3[:160]} requires_login={still_login}")

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html3, encoding="utf-8")

    titles = [
        re.sub(r"\s+", " ", t).strip()
        for t in re.findall(r"<h[1-4][^>]*>([^<]{3,160})</h[1-4]>", html3, re.I)
    ]
    link_texts = re.findall(r'href=["\']([^"\']+)["\'][^>]*>([^<]{4,160})</a>', html3, re.I)
    courses: list[dict[str, str]] = []
    seen: set[str] = set()
    for href, text in link_texts:
        text = re.sub(r"\s+", " ", text).strip()
        low = text.lower()
        if low in seen or low in {"home", "all courses", "my training", "sign in", "help docs", "sign out"}:
            continue
        blob = f"{href} {text}".lower()
        if any(
            k in blob
            for k in (
                "course",
                "path",
                "series",
                "program",
                "training",
                "api",
                "billing",
                "core",
                "integrat",
                "report",
                "partner",
                "academy",
                "developer",
                "webhook",
                "mrr",
                "revenue",
            )
        ):
            seen.add(low)
            courses.append({"title": text, "href": href})

    # Also pull JSON-ish / data attributes if present
    data_titles = re.findall(
        r'data-(?:course-)?(?:title|name)=["\']([^"\']{4,160})["\']',
        html3,
        re.I,
    )
    for t in data_titles:
        t = re.sub(r"\s+", " ", html_lib.unescape(t)).strip()
        if t.lower() not in seen:
            seen.add(t.lower())
            courses.append({"title": t, "href": ""})

    OUT_TXT.write_text(
        "\n".join(
            [
                f"catalog_status={status3}",
                f"catalog_url={final3}",
                f"requires_login={still_login}",
                "",
                "H_TITLES:",
                *titles[:100],
                "",
                "COURSES:",
                *[f"{c['title']} | {c['href']}" for c in courses[:200]],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    OUT_JSON.write_text(
        json.dumps(
            {"requires_login": still_login, "final_url": final3, "courses": courses[:300]},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT_JSON} courses={len(courses)}")
    for c in courses[:50]:
        print(f"  - {c['title']}")


if __name__ == "__main__":
    main()
