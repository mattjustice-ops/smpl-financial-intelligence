# POC customer onboarding (poc-1 … poc-5)

**Goal:** A prospect or paying customer can upload their CSVs, review AI-proposed column mappings, confirm, and land on `/app` with their data — without ops running warehouse scripts by hand.

**Tracked on:** `/progress` → milestone **POC customer onboarding**  
**Blocks:** gl-7 (first paying customer) until poc-1 … poc-3 are done.

**Ops-led path (today):** `provision-prod-customer.ps1` + `setup-prod-warehouse.ps1` — keep using this for demos on SMPL Demo Co until this milestone ships.

---

## Why this is go-live critical

| Path | Who loads data | Status |
|------|----------------|--------|
| **Ops-led** (gl-1) | SMPL team runs scripts against Neon | Works today |
| **Self-serve POC** (this doc) | Customer uploads CSVs in product | **Not built** |

Paying customers need the self-serve path. Without it, every onboarding is manual engineering work.

---

## What already exists (do not rebuild)

| Piece | Location | Gap vs POC |
|-------|----------|------------|
| Exact-header CSV upload | `POST /api/v1/demo-csv/upload` | Dev/demo format only; no auth on FastAPI; no arbitrary headers |
| Upload UI (basic) | `CsvUploadPanel` on `/app` | Hidden in workspace panel; expects SMPL seed CSV shapes |
| Ingest loader | `backend/app/services/demo_csv/` | No column mapping |
| Org scoping in DB | `organization_id` on warehouse tables | App-layer only; no Postgres RLS |
| Session + active org | Auth.js + `session-sync` | No workspace switcher |
| Next.js API proxy | `proxyToBackendAuthed` | Membership check on proxy; **not** on all FastAPI routes |

---

## Milestone checklist

### poc-1 — Secure CSV upload API

**Build:** `POST /api/v1/ingest/upload` (new router; keep `demo-csv` for internal seeds).

**Requirements:**

- Authenticated via Next.js proxy → FastAPI internal key or session-derived user context
- `organization_id` from session (not trusted from client alone)
- Multipart CSV upload; validate MIME/extension and max size (50MB)
- Store raw file in object storage (S3 / R2 / Supabase Storage) **or** stage in Postgres `ingest_jobs` with blob reference — pick one and document in `DEPLOYMENT.md`
- Return `{ job_id, status: "queued" | "processing" }` for async pipeline
- Scoped to org; reject cross-org access

**Definition of done:**

- [ ] Endpoint deployed on Railway staging + prod
- [ ] Smoke test: upload as Org A cannot write to Org B
- [ ] Document env vars for storage (if used)

---

### poc-2 — AI schema mapper API

**Build:** `POST /api/v1/ingest/map-schema`

**Input:** `organization_id`, list of uploaded files (headers + ~5 sample rows each).

**Output:** Structured JSON:

```json
{
  "mappings": [
    {
      "customer_column": "their_field",
      "smpl_field": "our_field",
      "confidence": 0.94,
      "transformation": "optional notes",
      "requires_review": false
    }
  ],
  "missing_fields": [],
  "ambiguous": []
}
```

**Implementation notes:**

- All LLM calls **server-side only** (never expose API keys to the browser)
- Repo already uses **OpenAI** for commentary (`OPENAI_API_KEY` in `backend/.env.example`); Claude (`ANTHROPIC_API_KEY`) is acceptable if product prefers it — one provider, documented in `DEPLOYMENT.md`
- Flag `requires_review: true` when `confidence < 0.85`
- Log token usage per `organization_id` for cost tracking (~$0.05–0.10 per onboarding)
- Target schema: see **SMPL target schema** section below (from reporting pipeline)

**Definition of done:**

- [ ] Endpoint returns valid mapping JSON for a sample customer CSV
- [ ] Unit test with mocked LLM response
- [ ] `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` set on Railway + documented

---

### poc-3 — `/app/onboarding` UI

**Route:** `frontend/app/app/onboarding/page.tsx` (auth-protected like `/app`).

**Three steps:**

1. **Upload** — drag/drop or file picker; calls `POST /api/v1/ingest/upload`; shows accepted types
2. **Review mapping** — table: [Their column] → [SMPL field] [confidence %] [Edit]; pre-check high confidence; flag low confidence
3. **Validate** — row counts, date ranges, sanity checks (“ARR for June 2026: $X — does this look right?”); **Confirm & import** triggers transform + load

On success → redirect to `/app` with session org data refreshed.

**Definition of done:**

- [ ] New customer completes flow on staging without ops scripts
- [ ] Empty/error states handled (bad file, mapping rejected, import failure)
- [ ] Middleware allows `/app/onboarding` for logged-in users only

---

### poc-4 — Backend membership enforcement

**Problem:** Today, FastAPI often checks `get_organization_or_404` (org exists) but not `organization_members`. Direct Railway calls could bypass Next.js proxy.

**Build:**

- FastAPI dependency: `require_org_member(user, organization_id)` on ingest + reporting routes
- Session sync or internal header carries authenticated email / user id from Next proxy
- Integration test: user in Org A cannot read Org B workforce/MRR data

**Definition of done:**

- [ ] Ingest routes require membership
- [ ] At least one reporting route tested for cross-org 403
- [ ] Document threat model in this file (proxy-only vs defense-in-depth)

---

### poc-5 — Workspace switcher (optional but tracked)

**Problem:** Users with multiple orgs (demo + customer pilot) always land on oldest `joined_at` org.

**Build:**

- Dropdown in `AppSessionBanner`: list `session.user.organizations`
- API to set active org (update session / re-sync) or persist `last_active_org` on member row
- Re-login not required after switch

**Definition of done:**

- [ ] User can switch between SMPL Demo Co and a customer test org without SQL

---

## Recommended build order

```
poc-4 (membership deps) ──┐
                          ├──► poc-1 (upload) ──► poc-2 (mapper) ──► poc-3 (UI)
poc-5 can parallel UI work after poc-1
```

Run **gl-5 staging** in parallel so poc work is tested on preview/staging before prod.

---

## SMPL target schema (for mapper prompt)

Pass this to the LLM as the canonical target. Keep aligned with `backend/app/services/demo_csv/` and reporting engines.

### Income statement (`income_statement`)

| Field | Description |
|-------|-------------|
| `period` | `YYYY-MM` |
| `revenue` | Total revenue (USD) |
| `subscription_revenue` | Recurring subscription revenue |
| `services_revenue` | Professional services / one-time |
| `cost_of_revenue` | Total COGS |
| `gross_profit` | Revenue minus COGS |
| `sales_and_marketing` | S&M opex |
| `research_and_development` | R&D opex |
| `general_and_administrative` | G&A opex |
| `ebitda` | EBITDA |
| `depreciation_and_amortization` | D&A add-back |
| `net_income` | Net income |

### ARR waterfall (`arr_waterfall`)

| Field | Notes |
|-------|-------|
| `period` | `YYYY-MM` |
| `beginning_arr` | Not additive across periods |
| `new_business_arr` | Additive |
| `expansion_arr` | Additive |
| `reactivation_arr` | Additive |
| `contraction_arr` | Additive (negative) |
| `churn_arr` | Additive (negative) |
| `net_new_arr` | Additive |
| `ending_arr` | Not additive across periods |
| `net_dollar_retention_rate` | Decimal (1.008 = 100.8%) |
| `gross_retention_rate` | Decimal |

### Cash flow (`cash_flow_statement`)

Key fields: `period`, `beginning_cash`, `net_income`, `depreciation_and_amortization`, working-capital changes, `net_cash_from_operating_activities`, investing/financing sections, `ending_cash`.

### Headcount plan (`headcount_plan`)

Key fields: `period`, `department`, `headcount_beginning`, `new_hires`, `attrition`, `headcount_ending`, `open_requisitions`, `monthly_cash_payroll_cost`.

Full JSON reference: see audit prompt in team docs or extend `backend/app/schemas/demo_csv/`.

---

## Smoke tests (when milestone complete)

```powershell
# After staging deploy
.\scripts\smoke-test-poc-onboarding.ps1   # TODO: add with poc-1
```

Manual:

1. Provision new org with `provision-prod-customer.ps1 -Plan professional`
2. Customer opens `/app/onboarding` on staging
3. Upload sample CSV with non-SMPL headers
4. Confirm mappings → import → `/app` shows their metrics

---

## Constraints

- Do **not** add backend dependencies to static `/board` HTML
- Do **not** expose LLM API keys to the frontend
- Local dev: keep Docker Postgres + `127.0.0.1:8001` working
- `/board` remains public demo; `/app/onboarding` is authenticated only

---

## Related docs

| Doc | Purpose |
|-----|---------|
| `GO_LIVE_GL1_CUSTOMER_PROVISIONING.md` | Ops-led invite + warehouse load |
| `GO_LIVE_GL3_PLAN_ENTITLEMENTS.md` | Plan gates after onboarding |
| `DEPLOYMENT.md` | Railway + Vercel env |
| `REPORTING_ARCHITECTURE.md` | Warehouse + reporting context |
