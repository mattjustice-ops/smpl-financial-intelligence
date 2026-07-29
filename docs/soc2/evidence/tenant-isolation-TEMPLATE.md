# Tenant isolation evidence — YYYY-MM-DD

> Fill after [../runbooks/tenant-isolation-test.md](../runbooks/tenant-isolation-test.md).  
> **Sanitized only** — no session cookies, API keys, connection strings, or raw customer dumps.  
> Completing a real Pass = Month 2 readiness evidence. **Not** SOC 2 certification.

## Status: WIP — AWAITING RUN

| Field | Value |
|-------|--------|
| Date of test | YYYY-MM-DD |
| Operator | Matt Justice |
| Environment | ☐ Production (`www.smpl-ai.com` / Railway / Neon `smpl-auth-prod`) ☐ Staging (label clearly) |
| Destructive actions? | **No** — read-only assertions; Demo Co financials untouched |
| Overall result | ☐ Pass ☐ Fail ☐ Blocked |
| Scoreboard | Leave `[ ]` until Pass |

---

## Tenants

| Role | Organization name | Organization ID |
|------|-------------------|-----------------|
| Org A | SMPL Demo Co | `8571e520-0687-4516-bdee-379f37c58c1f` |
| Org B | | |

| Actor | Email (ok to redact domain-local) | Member of |
|-------|-----------------------------------|-----------|
| User A | | Org A only ☐ |
| User B | | Org B only ☐ |

---

## Results

| ID | Check | Result | Notes |
|----|-------|--------|-------|
| T1.1 | User A UI shows Org A only | ☐ Pass ☐ Fail ☐ Blocked | |
| T1.2 | User A cannot view Org B UI data | ☐ Pass ☐ Fail ☐ Blocked | |
| T1.3 | User B UI shows Org B; not Demo Co numbers | ☐ Pass ☐ Fail ☐ Blocked | |
| T2.1 | User A + `organization_id=A` → success | ☐ Pass ☐ Fail ☐ Blocked | |
| T2.2 | User A + `organization_id=B` → **403** | ☐ Pass ☐ Fail ☐ Blocked | |
| T2.3 | User B + `organization_id=A` → **403** | ☐ Pass ☐ Fail ☐ Blocked | |
| T3 | Optional SQL — membership + row counts scoped | ☐ Pass ☐ Fail ☐ N/A ☐ Blocked | Counts only |
| T4 | Unauthenticated → 401 | ☐ Pass ☐ Fail ☐ N/A ☐ Blocked | |

---

## API endpoints exercised (names only)

| Method + path (no tokens) | Org param | HTTP status |
|---------------------------|-----------|-------------|
| | | |

---

## Demo Co safety

| Check | Result |
|-------|--------|
| No Demo Co financial seed / Board / FE numbers rewritten | ☐ Confirmed |

---

## Findings / remediation

-

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Security owner | Matt Justice | | ☐ Pass ☐ Fail ☐ Blocked |

_Readiness evidence only — not SOC 2 certified._
