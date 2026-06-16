# POC customer onboarding — overview

**Goal:** Get a customer's financial data into the SMPL warehouse so `/app` shows **their** metrics.

**Tracked on:** `/progress` → milestone **POC customer onboarding** (`poc-0` … `poc-5`)

There are **two paths**. Both should be supported for go-live; they serve different customers.

| Path | Doc | Checklist | Best for |
|------|-----|-----------|----------|
| **A. Direct data access** | `GO_LIVE_POC_DIRECT_DATA_ACCESS.md` | **poc-0** | Enterprise POC — customer grants read access; SMPL ops loads data |
| **B. Self-serve CSV** | This file (sections below) | **poc-1 … poc-3** | Scale, Starter motion, IT won't open systems |

**Shared foundation:** **poc-4** (backend membership enforcement), **poc-5** (workspace switcher)

---

## What unblocks gl-7 (first paying customer)?

| Requirement | Path A | Path B |
|-------------|--------|--------|
| Customer org + login | Yes (`gl-1`) | Yes |
| Their data in warehouse | Ops load via direct access | Self-serve onboarding |
| **Can close gl-7 without path B?** | **Yes** — white-glove is valid for first revenue | Path B needed to scale without ops per deal |

---

## Recommended parallel work

```
poc-0 (playbook + first white-glove POC)     ──► gl-7 eligible (with gl-5/gl-6)
        │
poc-4 (membership) ──► poc-1 ──► poc-2 ──► poc-3 (self-serve)  ──► scale
        │
poc-5 (workspace switcher) — after first multi-org pain
```

Run **gl-5 staging** in parallel so ingest work is tested before prod.

---

## Path B — Self-serve CSV (poc-1 … poc-3)

**Goal:** Customer uploads CSVs in `/app/onboarding`, reviews AI column mappings, confirms, lands on dashboard — no ops scripts.

**Ops-led fallback (today):** `provision-prod-customer.ps1` + `setup-prod-warehouse.ps1` — see path A.

---

## What already exists (do not rebuild)

| Piece | Location | Gap vs self-serve POC |
|-------|----------|------------------------|
| Exact-header CSV upload | `POST /api/v1/demo-csv/upload` | Dev/demo format; weak auth on direct API |
| Upload UI (basic) | `CsvUploadPanel` on `/app` | Expects SMPL seed CSV shapes |
| Ingest loader | `backend/app/services/demo_csv/` | No column mapping |
| Ops warehouse load | `setup-prod-warehouse.ps1` | **Path A** — works today |

---

### poc-1 — Secure CSV upload API

**Build:** `POST /api/v1/ingest/upload` (new router; keep `demo-csv` for internal seeds).

**Requirements:**

- Authenticated via Next.js proxy → FastAPI internal key or session-derived user context
- `organization_id` from session (not trusted from client alone)
- Multipart CSV upload; validate MIME/extension and max size (50MB)
- Store raw file in object storage (S3 / R2 / Supabase Storage) **or** stage in Postgres `ingest_jobs` — document in `DEPLOYMENT.md`
- Return `{ job_id, status: "queued" | "processing" }` for async pipeline

**Definition of done:**

- [ ] Endpoint on Railway staging + prod
- [ ] Smoke test: Org A cannot write to Org B
- [ ] Storage env vars documented

---

### poc-2 — AI schema mapper API

**Build:** `POST /api/v1/ingest/map-schema`

**Input:** uploaded files (headers + ~5 sample rows each).

**Output:** mapping JSON with confidence scores; `requires_review` when `confidence < 0.85`.

**Notes:**

- LLM calls server-side only (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`)
- Reuse mapping logic later for **path A** ops (normalize customer exports before load)
- Target schema: below

**Definition of done:**

- [ ] Valid mapping JSON for sample non-SMPL CSV
- [ ] Unit test with mocked LLM
- [ ] API key on Railway + documented

---

### poc-3 — `/app/onboarding` UI

**Route:** `frontend/app/app/onboarding/page.tsx`

1. **Upload** → `POST /api/v1/ingest/upload`
2. **Review mapping** → edit / confirm proposals from poc-2
3. **Validate** → sanity metrics → **Confirm & import** → `/app`

**Definition of done:**

- [ ] Staging: new customer completes flow without ops scripts
- [ ] Auth middleware protects route

---

### poc-4 — Backend membership enforcement

FastAPI must validate `organization_members`, not only org existence — for ingest **and** reporting. See path A security model.

**Definition of done:**

- [ ] Ingest routes require membership
- [ ] Cross-org integration test returns 403

---

### poc-5 — Workspace switcher

Dropdown in `AppSessionBanner` to change `activeOrganizationId` without Neon SQL.

---

## SMPL target schema (for mapper prompt)

Keep aligned with `backend/app/services/demo_csv/` and `REPORTING_ARCHITECTURE.md`.

### Income statement (`income_statement`)

`period`, `revenue`, `subscription_revenue`, `services_revenue`, `cost_of_revenue`, `gross_profit`, `sales_and_marketing`, `research_and_development`, `general_and_administrative`, `ebitda`, `depreciation_and_amortization`, `net_income`

### ARR waterfall (`arr_waterfall`)

`period`, `beginning_arr`, `new_business_arr`, `expansion_arr`, `reactivation_arr`, `contraction_arr`, `churn_arr`, `net_new_arr`, `ending_arr`, `net_dollar_retention_rate`, `gross_retention_rate`

### Cash flow / headcount

See full field lists in team audit doc or extend `backend/app/schemas/demo_csv/`.

---

## Smoke tests

**Path A (ops):**

```powershell
.\scripts\provision-prod-customer.ps1 -Email ... -OrganizationName "..." -Plan enterprise
.\scripts\setup-prod-warehouse.ps1 -DatabaseUrl "..." -OrganizationId "<uuid>"
```

**Path B (when built):**

```powershell
.\scripts\smoke-test-poc-onboarding.ps1   # TODO
```

---

## Related docs

| Doc | Purpose |
|-----|---------|
| `GO_LIVE_POC_DIRECT_DATA_ACCESS.md` | **Path A** — Snowflake, S3, ERP export |
| `GO_LIVE_GL1_CUSTOMER_PROVISIONING.md` | Invites + org provisioning |
| `GO_LIVE_GL3_PLAN_ENTITLEMENTS.md` | Plan gates |
| `DEPLOYMENT.md` | Railway + Vercel |
