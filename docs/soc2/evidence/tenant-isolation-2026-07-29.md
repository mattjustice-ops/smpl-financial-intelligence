# Tenant isolation evidence — 2026-07-29

> Filled after [../runbooks/tenant-isolation-test.md](../runbooks/tenant-isolation-test.md).  
> **Sanitized only** — no session cookies, API keys, connection strings, or raw customer dumps.  
> Completing a real Pass = Month 2 readiness evidence. **Not** SOC 2 certification.  
> **Agent limitation:** Cursor agent **cannot** run authenticated browser/API sessions as Matt’s Org-B-only user. Authenticated T1/T2 **Pass** via Matt chat attestation 2026-07-29 (same pattern as access-review Allow). **Do not invent fake API logs.**

## Status: PASS — 2026-07-29

| Field | Value |
|-------|--------|
| Date of test | 2026-07-29 |
| Operator | Agent (unit tests, read-only SQL, unauthenticated probes) + Matt Justice (Org-B-only user + authenticated T1/T2) |
| Environment | ☑ Production Neon (read-only SELECT) · ☑ Production web unauth probe · ☑ Authenticated Path A/B (Matt) |
| Destructive actions? | **No** — read-only assertions; Demo Co financials untouched |
| Overall result | ☑ **Pass** |
| Scoreboard | `[x]` |
| Attestation | Matt confirmed console checks + Org-B-only T1/T2 2026-07-29 via chat. |

---

## Tenants

| Role | Organization name | Organization ID |
|------|-------------------|-----------------|
| Org A | SMPL Demo Co | `8571e520-0687-4516-bdee-379f37c58c1f` |
| Org B | Customer Corp (existing prod org; prefer over new Path B) | `cfa7c116-3a89-4dd1-91df-80d4ece5c59d` |

| Actor | Email (ok to redact domain-local) | Member of |
|-------|-----------------------------------|-----------|
| User A | Dedicated Demo-only user (e.g. existing gmail admin on Demo Co) — **not** corporate dual-member | Org A only ☑ (Matt confirmed for T1/T2) |
| User B | Org-B-only user (provisioned by Matt for this exercise) | Org B only ☑ (Matt confirmed) |

### Membership sanity (T3 — production, SELECT only)

| Finding | Result |
|---------|--------|
| Org A and Org B both exist; distinct IDs/names | Pass |
| Active members Demo Co | 3 (at agent SQL check; may have changed after Org-B-only invite) |
| Active members Customer Corp | 1 at agent SQL check; Matt later provisioned Org-B-only actor for T1/T2 |
| Corporate `ma***@smpl-ai.com` active in **both** Org A and Org B | **Yes** at agent SQL check — **not** used for isolation assertions |
| Demo Co also has `ma***@gmail.com` admin | Candidate User A if not also on Org B (Matt confirmed Org-A-only session for T1/T2) |

Other orgs present at agent SQL check (0 active members each — optional Lab B): Enterprise Test Co, Path A Dry Run Co, Professional Test Co, several Starter Test Co rows.

---

## Results

| ID | Check | Result | Notes |
|----|-------|--------|-------|
| T1.1 | User A UI shows Org A only | ☑ **Pass** | Matt confirmed authenticated Org-A-only UI 2026-07-29 via chat. No agent browser session / no fabricated UI log. |
| T1.2 | User A cannot view Org B UI data | ☑ **Pass** | Matt confirmed cross-org UI blocked (Org B UUID) 2026-07-29 via chat. |
| T1.3 | User B UI shows Org B; not Demo Co numbers | ☑ **Pass** | Matt confirmed Org-B-only user UI 2026-07-29 via chat. |
| T2.1 | User A + `organization_id=A` → success | ☑ **Pass** | Matt confirmed authenticated Path A API 2026-07-29 via chat. **No fabricated HTTP status log from agent.** |
| T2.2 | User A + `organization_id=B` → **403** | ☑ **Pass** | Matt confirmed cross-org denial 2026-07-29 via chat. |
| T2.3 | User B + `organization_id=A` → **403** | ☑ **Pass** | Matt confirmed Org-B-only → Org A denial 2026-07-29 via chat. |
| T3 | Optional SQL — membership + row counts scoped | ☑ Pass (supporting) | Orgs + membership counts verified earlier; warehouse fact tables not present under probed names — N/A for row counts |
| T4 | Unauthenticated → 401 | ☑ Pass | `GET /api/workspace/summary?organization_id=…` on `www.smpl-ai.com` → **401** for Org A and Org B IDs |
| Lab | Backend unit membership gate | ☑ Pass | `backend/tests/test_org_membership.py` — allow member + cross-org **403** with detail `You do not have access to this organization.` (3/3 core tests). Dashboard TestClient case has pre-existing sqlite thread teardown flake — not used as Pass evidence. |

---

## API endpoints exercised (names only)

| Method + path (no tokens) | Org param | HTTP status / evidence |
|---------------------------|-----------|------------------------|
| `GET /api/workspace/summary` (www.smpl-ai.com) | Org A | **401** (unauthenticated — agent) |
| `GET /api/workspace/summary` (www.smpl-ai.com) | Org B | **401** (unauthenticated — agent) |
| Unit: `get_organization_or_404` cross-org | Org B as User A | **403** (in-process) |
| `GET …/health` (Railway prod) | n/a | **200** (reachability only) |
| Authenticated T2.1–T2.3 (`/api/workspace/summary` or equivalent org-scoped path) | A/B as single-org actors | **Pass per Matt** — chat attestation 2026-07-29; agent did **not** capture or invent status lines |

---

## Demo Co safety

| Check | Result |
|-------|--------|
| No Demo Co financial seed / Board / FE numbers rewritten | ☑ Confirmed — SELECT-only + unit tests; no seed scripts against Demo Co; Matt T1/T2 were access checks only |

---

## Findings / remediation

1. **Overall Pass 2026-07-29** — unit membership 403 + unauth 401 + SQL tenant distinctness (agent) + authenticated T1/T2 with Org-B-only actor (Matt chat attestation).
2. Corporate dual membership remains unsuitable for isolation assertions; Matt used Org-B-only + Org-A-only actors for T1/T2.
3. No fake authenticated API response bodies or status codes were invented for this file.

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Security owner | Matt Justice | 2026-07-29 | ☑ **Pass** — Matt confirmed console checks + Org-B-only T1/T2 2026-07-29 via chat. |

_Readiness evidence only — not SOC 2 certified._
