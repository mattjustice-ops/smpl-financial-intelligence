# Tenant isolation evidence — 2026-07-29

> Filled after [../runbooks/tenant-isolation-test.md](../runbooks/tenant-isolation-test.md).  
> **Sanitized only** — no session cookies, API keys, connection strings, or raw customer dumps.  
> Completing a real Pass = Month 2 readiness evidence. **Not** SOC 2 certification.

## Status: PARTIAL / WIP — UNIT + SQL + UNAUTH DONE; UI/AUTH CROSS-ORG AWAITING MATT

| Field | Value |
|-------|--------|
| Date of test | 2026-07-29 |
| Operator | Agent (unit tests, read-only SQL, unauthenticated probes) + Matt Justice (authenticated UI/API still required) |
| Environment | ☑ Production Neon (read-only SELECT) · ☑ Production web unauth probe · ☐ Full authenticated Path A/B UI |
| Destructive actions? | **No** — read-only assertions; Demo Co financials untouched |
| Overall result | ☑ Partial (not Pass — cross-org authenticated sessions not run) |
| Scoreboard | `[~]` until T1/T2 Pass with single-org actors |

---

## Tenants

| Role | Organization name | Organization ID |
|------|-------------------|-----------------|
| Org A | SMPL Demo Co | `8571e520-0687-4516-bdee-379f37c58c1f` |
| Org B | Customer Corp (existing prod org; prefer over new Path B) | `cfa7c116-3a89-4dd1-91df-80d4ece5c59d` |

| Actor | Email (ok to redact domain-local) | Member of |
|-------|-----------------------------------|-----------|
| User A | Dedicated Demo-only user (e.g. existing gmail admin on Demo Co) — **not** corporate dual-member | Org A only ☐ (Matt must confirm session) |
| User B | **Need invite** — Customer Corp currently has only the dual-member corporate admin | Org B only ☐ (blocked until provisioned) |

### Membership sanity (T3 — production, SELECT only)

| Finding | Result |
|---------|--------|
| Org A and Org B both exist; distinct IDs/names | Pass |
| Active members Demo Co | 3 |
| Active members Customer Corp | 1 |
| Corporate `ma***@smpl-ai.com` active in **both** Org A and Org B | **Yes — cannot use for isolation assertions** |
| Demo Co also has `ma***@gmail.com` admin | Candidate User A if not also on Org B (confirm in UI) |

Other orgs present (0 active members each — optional Lab B): Enterprise Test Co, Path A Dry Run Co, Professional Test Co, several Starter Test Co rows.

---

## Results

| ID | Check | Result | Notes |
|----|-------|--------|-------|
| T1.1 | User A UI shows Org A only | ☑ Blocked | Needs browser session as Org-A-only user |
| T1.2 | User A cannot view Org B UI data | ☑ Blocked | Needs Org B UUID in URL + Org-A-only session |
| T1.3 | User B UI shows Org B; not Demo Co numbers | ☑ Blocked | No Org-B-only user yet — invite required |
| T2.1 | User A + `organization_id=A` → success | ☑ Blocked | Auth session required |
| T2.2 | User A + `organization_id=B` → **403** | ☑ Blocked | Auth session required |
| T2.3 | User B + `organization_id=A` → **403** | ☑ Blocked | Auth session required |
| T3 | Optional SQL — membership + row counts scoped | ☑ Pass (partial) | Orgs + membership counts verified; warehouse fact tables not present under probed names — N/A for row counts |
| T4 | Unauthenticated → 401 | ☑ Pass | `GET /api/workspace/summary?organization_id=…` on `www.smpl-ai.com` → **401** for Org A and Org B IDs |
| Lab | Backend unit membership gate | ☑ Pass | `backend/tests/test_org_membership.py` — allow member + cross-org **403** with detail `You do not have access to this organization.` (3/3 core tests). Dashboard TestClient case has pre-existing sqlite thread teardown flake — not used as Pass evidence. |

---

## API endpoints exercised (names only)

| Method + path (no tokens) | Org param | HTTP status |
|---------------------------|-----------|-------------|
| `GET /api/workspace/summary` (www.smpl-ai.com) | Org A | **401** |
| `GET /api/workspace/summary` (www.smpl-ai.com) | Org B | **401** |
| Unit: `get_organization_or_404` cross-org | Org B as User A | **403** (in-process) |
| `GET …/health` (Railway prod) | n/a | **200** (reachability only) |

---

## Demo Co safety

| Check | Result |
|-------|--------|
| No Demo Co financial seed / Board / FE numbers rewritten | ☑ Confirmed — SELECT-only + unit tests; no seed scripts against Demo Co |

---

## Findings / remediation

1. **Cannot close Pass with Matt’s corporate dual membership** — isolation assertions require User A ∉ Org B and User B ∉ Org A.
2. **Recommended Matt path (minimal):**
   1. Invite a throwaway email as **admin/member of Customer Corp only** (Org B) — e.g. `isolation-b+2026-07-29@…` — or run Path B provision for `Isolation Test Co 2026-07-29` if preferred.
   2. Sign in as **gmail Demo Co admin** (if Org-A-only) → T1.1–T1.2 + T2.1–T2.2 against `organization_id=cfa7c116-3a89-4dd1-91df-80d4ece5c59d` expecting **403** / no Org B financials.
   3. Sign in as Org-B-only user → T1.3 + T2.3 (Org A → **403**).
   4. Endpoint: `GET /api/workspace/summary?organization_id=<uuid>` (uses `requireOrganizationAccess`).
3. Unit-test Pass + unauth 401 + SQL tenant distinctness are **supporting** evidence only — do not claim full Org A ≠ Org B Pass until T1/T2 complete.

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Security owner | Matt Justice | | ☐ Pass ☐ Fail ☑ Partial / Blocked on authenticated Path A/B |

_Readiness evidence only — not SOC 2 certified._
