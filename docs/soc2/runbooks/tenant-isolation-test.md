# Tenant isolation test (Org A ≠ Org B) — Month 2

> **Readiness only — not SOC 2 certified.**  
> Prove a user in Org A cannot read Org B’s data via UI and authenticated API paths.  
> **Non-destructive:** do not delete Demo Co data, do not rewrite financials, do not change production env URLs.

| Field | Value |
|-------|--------|
| Related | [01_system_boundary.md](../01_system_boundary.md), [P03](../policies/P03_access_control_policy.md), [P07](../policies/P07_customer_data_confidentiality_procedures.md) |
| Scoreboard item | Tenant isolation evidence (Org A ≠ Org B) — Month 2 |
| Owner | Matt Justice |
| Evidence template | [../evidence/tenant-isolation-TEMPLATE.md](../evidence/tenant-isolation-TEMPLATE.md) |
| Enforcement refs | `frontend/lib/auth/server-org-access.ts` · `backend/app/api/deps/auth.py` |

---

## Known demo tenant (Org A)

| Field | Value |
|-------|--------|
| Name | **SMPL Demo Co** |
| Organization ID | `8571e520-0687-4516-bdee-379f37c58c1f` |
| Source | `frontend/lib/auth/constants.ts` (`DEMO_ORGANIZATION_ID`); go-live / restore evidence |
| Role in this test | **Org A** — control tenant with warehouse data |

**Do not** mutate Demo Co Board / Forecast Engine / seed actuals as part of this test.

---

## Org B (second tenant)

No fixed second production org UUID is checked into the repo. Choose **one**:

| Option | How | Notes |
|--------|-----|--------|
| **B1 — Prefer** | Reuse an existing second org if Matt already provisioned one (Path B customer / isolation lab) | Record UUID + name in evidence; no Demo Co changes |
| **B2 — Create throwaway** | [GO_LIVE_GL1](../../GO_LIVE_GL1_CUSTOMER_PROVISIONING.md) Path B | Name e.g. `Isolation Test Co YYYY-MM-DD`; plan `starter` |
| **B3 — Staging only** | Same procedure on staging Neon if prod seats/data risk is a concern | Label evidence **staging**; weaker than prod — note honesty |

Provision sketch (prod Path B):

```powershell
.\scripts\provision-prod-customer.ps1 `
  -Email isolation-b@smpl-ai.com `
  -OrganizationName "Isolation Test Co YYYY-MM-DD" `
  -Plan starter
```

Optional minimal warehouse for Org B (so charts are non-empty) — **do not** point scripts at Demo Co ID:

```powershell
.\scripts\setup-prod-warehouse.ps1 `
  -OrganizationId "<ORG_B_UUID>"
  # plus DatabaseUrl / local neon env as usual
```

Invite a **second user email** that is a member of Org B only (not a member of Demo Co), or use two browsers/profiles:

| Actor | Membership |
|-------|------------|
| User A | Active member of Org A (Demo Co) only |
| User B | Active member of Org B only |

Matt’s operator account may be in both orgs — that is fine for setup, but **isolation assertions must use a session that is not a member of the other org**.

---

## Test plan (read-only assertions)

### Prep

1. Confirm Org A ID = Demo Co UUID above.
2. Record Org B UUID + name.
3. Confirm User A ∉ Org B and User B ∉ Org A (`organization_members` or `/app` workspace list).
4. Open two clean browser profiles (or incognito + normal).

### T1 — UI workspace scope

| Step | Action | Expected |
|------|--------|----------|
| T1.1 | Sign in as User A → `/app` | Banner / workspace = Org A only |
| T1.2 | Attempt to open Org B board/summary URL with `organization_id=<ORG_B>` (if UI accepts query) | Denied, empty, or redirected — **not** Org B financials |
| T1.3 | Sign in as User B → `/app` | Workspace = Org B; **no** Demo Co charts/numbers |

### T2 — Authenticated Next.js proxy (membership gate)

With User A session cookie, call an org-scoped app API that uses `requireOrganizationAccess` (e.g. workspace summary / backend proxy with `organization_id` query):

| Step | Request | Expected |
|------|---------|----------|
| T2.1 | `organization_id=<ORG_A>` | **200** (or normal success) with Org A payload only |
| T2.2 | `organization_id=<ORG_B>` | **403** — `You do not have access to this organization.` |
| T2.3 | Repeat as User B swapped | Org B OK; Org A → **403** |

Do not paste session cookies or JWTs into evidence.

### T3 — Data layer sanity (optional SQL — prefer throwaway / read-only)

Against Neon (production or staging labeled). **SELECT only.**

```sql
-- Distinct tenants
SELECT id, name, plan, status
FROM organizations
WHERE id IN (
  '8571e520-0687-4516-bdee-379f37c58c1f',  -- Org A Demo Co
  '<ORG_B_UUID>'
);

-- Membership must not cross (replace user ids)
SELECT om.user_id, om.organization_id, om.status, o.name
FROM organization_members om
JOIN organizations o ON o.id = om.organization_id
WHERE om.user_id IN ('<USER_A_UUID>', '<USER_B_UUID>');

-- Warehouse rows scoped (example table — adjust if name differs)
SELECT organization_id, COUNT(*) AS n
FROM income_statement
WHERE organization_id IN (
  '8571e520-0687-4516-bdee-379f37c58c1f',
  '<ORG_B_UUID>'
)
GROUP BY organization_id;
```

Expected: counts/names differ; User A has no active membership on Org B.

### T4 — Negative controls (document only)

| Case | Expected |
|------|----------|
| Unauthenticated request to org-scoped API | **401** |
| Internal/billing key routes | Not usable as a substitute for customer org membership from the browser |

---

## Pass criteria

| # | Criterion |
|---|-----------|
| 1 | User A cannot obtain Org B financial/UI data |
| 2 | User B cannot obtain Org A (Demo Co) financial/UI data |
| 3 | Cross-org authenticated API call returns **403** (not silent Demo Co data) |
| 4 | Evidence filed sanitized — no cookies, keys, or customer PII dumps |
| 5 | Demo Co financial seed/dashboard **unchanged** |

---

## After the run

1. Copy template → `tenant-isolation-YYYY-MM-DD.md`.
2. Mark scoreboard `[x]` only on Pass.
3. Sync `frontend/lib/compliance/progress.ts`.
4. Optional cleanup: deactivate Isolation Test Co memberships or leave labeled for re-test — do not delete Demo Co.

---

_Document control: Month 2 prep 2026-07-29 — readiness pack only; item remains open until Matt executes._
