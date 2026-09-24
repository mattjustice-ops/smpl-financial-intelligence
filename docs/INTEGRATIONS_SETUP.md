# Integrations setup — source connectors (kickoff)

**Status:** Living checklist for standing up **developer sandboxes + dummy data** as a first pass on Path B / native source connectors.  
**Not GA:** Product still loads customer data via **CSV + white-glove Path A**. Do not claim native ERP/CRM/billing connectors are live (see sales KB `connectors-today-vs-roadmap`).

| Related | Link |
|---------|------|
| Path A (white-glove today) | [GO_LIVE_POC_DIRECT_DATA_ACCESS.md](./GO_LIVE_POC_DIRECT_DATA_ACCESS.md) |
| Path B (self-serve CSV / map-schema) | [GO_LIVE_POC_ONBOARDING.md](./GO_LIVE_POC_ONBOARDING.md) |
| Progress tracker | `/progress` → `poc-0`…`poc-5` |
| Load domains (product labels) | `backend/app/services/workspace/load_domains.py` |
| Architecture (connectors = future) | [Architecture_Master.md](./Architecture_Master.md) |

**Last updated:** 2026-08-27

---

## Product constraints (do not violate)

1. **Read source systems only** — never post journals, invoices, or payroll back to ERP/GL/billing. Architecture: *not in scope: ERP/GL posting*. Sales: `no-gl-writeback`.
2. **Tenant isolation** — all pulls land in org-scoped warehouse rows (`organization_id`); no cross-tenant credentials or caches.
3. **Secrets in env / token files only** — never commit keys, OAuth client secrets, or sandbox passwords. Prefer `*_TOKEN_FILE` locally (same pattern as `STRIPE_TOKEN_FILE` / `HUBSPOT_TOKEN_FILE` in `frontend/.env.example`).
4. **Namespace connector credentials** — SMPL’s own SaaS billing already uses `STRIPE_*`; inbound sales uses `HUBSPOT_*`. Customer-source connector sandboxes must use a **`CONNECTOR_` prefix** (below) so they never collide.

---

## What already exists vs greenfield

| Capability | Status | Where |
|------------|--------|--------|
| Exact-header CSV ingest | **Shipped** | `POST /api/v1/ingest/csv`, demo-csv profiles, Data tab UI |
| API batch push (label only) | **Shipped** | `POST /api/v1/ingest/batches` + `source_system` string |
| Load domains (ERP/CRM/billing/cash/workforce) | **Shipped (labels)** | `load_domains.py` — `typical_systems` are product vocabulary, not live adapters |
| Path A white-glove | **Shipped** | Ops scripts + `GO_LIVE_POC_DIRECT_DATA_ACCESS.md`; `poc-0` / `poc-4` done |
| Path B upload + AI map-schema + `/app/onboarding` | **Open** | `poc-1`…`poc-3` |
| Native OAuth / scheduled connectors | **Greenfield** | Architecture “future”; impl specs under `backend/tmp/impl-docs/` are **not** runtime |
| SMPL Stripe / HubSpot | **Product ops only** | Our billing + inbound CRM — **not** customer FI connectors |

**Implication this week:** Stand up sandboxes and pull sample objects into notes / staging CSVs that map to existing entity types (`gl_actuals`, `mrr_waterfall`, `subscriptions`, `opportunities`, `headcount_plan`, etc.). Do **not** build a full connector framework yet.

---

## Priority model

1. **Self-serve + dummy data available** (start coding against real shapes this week)
2. **FP&A value** — Billing/ARR → GL → CRM pipeline → workforce
3. **Approval lead time** — start Intacct + Rillet outreach **now**, even if wave 2+

---

## Master status table

Update the **Status** column as Matt completes signups. Do not store secrets here.

| Platform | Category | Dev / signup | Dummy data | Status | Wave |
|----------|----------|--------------|------------|--------|------|
| QuickBooks Online | ERP / GL | [developer.intuit.com](https://developer.intuit.com) | Yes — sandbox company sample data | pull prototype | **1** |
| Xero | ERP / GL | [developer.xero.com](https://developer.xero.com) | Yes — Demo Company | not started | **1** |
| Stripe Billing | Billing / ARR | [dashboard.stripe.com](https://dashboard.stripe.com/register) (Test mode) | Yes — test cards; create customers/subs | pull prototype (Quick Demo Co seed+export) | **1** |
| Chargebee | Billing / ARR | [chargebee.com/trial-signup](https://www.chargebee.com/trial-signup) | Yes — sample data auto-configured | read-only probe (test site `smpl-ai-test`) | **1** |
| Maxio | Billing / ARR / rev-rec | Partnership (Kevin/Nick) — learn.maxio **open**; AB API still pending | TBD — need Advanced Billing sandbox (+ Core/MCP TBD) | **scaffold ready** + learn catalog mapped; **blocked on CONNECTOR_MAXIO_SITE + API_KEY** | **1** |
| Gusto | Payroll / workforce | [dev.gusto.com](https://dev.gusto.com) | Yes — demo companies + payrolls; sandbox instant | not started | **1** |
| Deel | HRIS | [developer.deel.com](https://developer.deel.com) | Yes — rich sandbox; reset anytime | not started | 1b / 2 |
| NetSuite | ERP / GL | [SuiteCloud / SDN](https://www.netsuite.com/portal/developers/sdn.shtml) | Sandbox; you build test records | not started | **2** |
| Salesforce | CRM | [developer.salesforce.com/signup](https://developer.salesforce.com/signup) | Empty org — populate yourself | OAuth connected; read-only probe (DE often empty) | **2** |
| HubSpot | CRM | [developers.hubspot.com](https://developers.hubspot.com) | Minimal (~2 records) — bulk import | not started | **2** |
| Zoho CRM | CRM | [developer.zoho.com](https://developer.zoho.com) | Option: ~10 sample records / object | not started | 2 |
| Pipedrive | CRM | [developers.pipedrive.com](https://developers.pipedrive.com) | Self-serve; create your own data | not started | 2 |
| Sage Intacct | ERP / GL | [developer.intacct.com](https://developer.intacct.com) | Request sandbox (lead time) | **blocked on sandbox** — outreach | **2** (outreach **today**) |
| Rillet | Accounting API | [docs.api.rillet.com](https://docs.api.rillet.com) / partner | Gated; `sandbox.api.rillet.com` exists; dummy data unconfirmed | **blocked on partner access** — outreach | **2** (outreach **today**) |
| BambooHR | HRIS | [documentation.bamboohr.com](https://documentation.bamboohr.com) | Self-serve; sample data unclear | not started | 2 |

---

## First wave (this week) — 5 systems

| # | System | Why |
|---|--------|-----|
| 1 | **Stripe Billing** | Instant test mode; ARR/MRR/subscriptions are core SaaS FP&A; maps to `billing_arr` entities; separate from SMPL’s own `STRIPE_*` product keys via `CONNECTOR_STRIPE_*` |
| 2 | **QuickBooks Online** | Self-serve sandbox + sample GL; US SMB ERP most common in early deals; maps to `erp_gl` / `gl_actuals` |
| 3 | **Xero** | Demo Company with sample data; second GL shape (intl) so adapters aren’t QBO-only |
| 4 | **Chargebee** | Trial + auto sample data; second billing shape (SaaS often Chargebee ≠ Stripe) |
| 5 | **Gusto** | Instant sandbox with employees + payrolls; workforce/opex bridge; Deel is the intl/contractor alternate (wave 1b if time) |

**Parallel billing priority:** **Maxio** — B2B SaaS billing/rev-rec sub-ledger (CRM → pipeline; Maxio → billing/ARR actuals; ERP → GL). Exploratory partnership (Kevin/Nick); ingest path (API / export / MCP) TBD — see [Maxio](#maxio-partnership-track--wave-1-billing).

**Deferred from wave 1:** Salesforce/HubSpot (empty/minimal data — more setup for less ARR signal this week); NetSuite (custom test records); Intacct/Rillet (gated — outreach only).

---

## Matt checklists — wave 1

Store secrets outside the repo (password manager or `*_TOKEN_FILE`). Suggested env names match `VENDOR_PURPOSE` / `CONNECTOR_` conventions.

### 1. Stripe Billing (customer-source sandbox)

- [x] Create or use a **separate** Stripe account (or Test mode only) for **connector R&D** — do not reuse prod live keys
- [x] Dashboard → **Test mode** on
- [x] Create test Customers, Products, Prices, Subscriptions; run a few invoices with [test cards](https://stripe.com/docs/testing) — via seed script (below)
- [x] Secret key stored locally as `CONNECTOR_STRIPE_SECRET_KEY` (+ optional publishable)
- [x] Local env (example):
  - `CONNECTOR_STRIPE_SECRET_KEY=`
  - `CONNECTOR_STRIPE_PUBLISHABLE_KEY=` (optional)
  - `CONNECTOR_STRIPE_TOKEN_FILE=` (optional local path)
- [x] **Do not** put these in `STRIPE_SECRET_KEY` (that’s SMPL SaaS billing)
- [x] Sample objects that matter for SMPL: Customer, Subscription, Invoice, InvoiceLineItem, Product/Price → `customers`, `subscriptions`, `invoices`, `mrr_waterfall`, `payments`

**Scripts (TEST write for seed; export is read-only from Stripe):**

Requires `stripe` in the backend venv (`pip install stripe` if missing).

| Script | Purpose |
|--------|---------|
| `backend/scripts/stripe_seed_quick_demo.py` | Idempotent seed (~24 customers) tagged `metadata.smpl_seed=quick_demo_co` |
| `backend/scripts/stripe_export_to_smpl.py` | Pull seed → compact demo CSV under `backend/tmp/stripe_export/` |
| `backend/scripts/stripe_quick_demo_common.py` | Shared customer master + header constants |

**Outputs (gitignored, export-only — do not ingest into SMPL Demo Co):**

| Path | Role |
|------|------|
| `backend/tmp/quick_demo_co/customer_master.csv` | **Shared spine** — SaaS names + `qbo_customer_ref_id` + planned MRR |
| `backend/tmp/stripe_export/*.csv` | Compact `customers` / `subscriptions` / `invoices` / `payments` / `mrr_waterfall` |

**Alignment to QBO:** Invoice-bearing QBO sandbox customer IDs (`invoices_staging.customer_ref_id`) are linked on the master. Intuit sample *display* names (retail/sandbox) are kept only as `qbo_sandbox_display_name` for traceability; Quick Demo Co uses coherent SaaS names for Stripe + warehouse CSVs. QBO `gl_actuals` remains thin (JE-only) — billing↔GL dollar match is **not** claimed in this pass.

### 2. QuickBooks Online

- [ ] Sign up at [developer.intuit.com](https://developer.intuit.com)
- [ ] Create an app → get **Client ID** / **Client Secret**
- [ ] Create / connect a **sandbox company** (sample data)
- [ ] Complete OAuth once; save **realmId** + refresh token (sandbox)
- [ ] Local env (example):
  - `CONNECTOR_QBO_CLIENT_ID=`
  - `CONNECTOR_QBO_CLIENT_SECRET=`
  - `CONNECTOR_QBO_REALM_ID=`
  - `CONNECTOR_QBO_REFRESH_TOKEN=`
  - `CONNECTOR_QBO_TOKEN_FILE=` (optional: JSON blob with the above)
- [x] Sample objects: Account (CoA), JournalEntry / Purchase / Invoice / Payment, Customer, Vendor → `gl_actuals`, chart mapping, cash tie-outs
- [x] Read-only probe: `python backend/scripts/qbo_sandbox_probe.py` → `backend/tmp/qbo_sandbox_probe_summary.json`
- [x] First-pass export → SMPL CSV: `python backend/scripts/qbo_export_to_smpl.py` → `backend/tmp/qbo_export/` (gitignored; export-only, not org ingest)

#### One-time OAuth (Playground)

Easiest path for a sandbox refresh token — no local callback server.

1. Portal: [developer.intuit.com](https://developer.intuit.com) → **My Hub** → **App dashboard** → open your app.
2. Keys: **Development** (not Production) → **Keys & OAuth** → copy **Client ID** / **Client Secret**.
3. Redirect URI (required): under Development **Redirect URIs**, add exactly  
   `https://developer.intuit.com/v2/OAuth2Playground/RedirectUrl` → **Save**.  
   (Playground may offer a small “set redirect URI” link that does this for you.)
4. Playground: open [OAuth 2.0 Playground](https://developer.intuit.com/app/developer/playground) (docs: [Practice authorization](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0-playground)).
5. Select your **app** / **sandbox company** → scope **Accounting** (`com.intuit.quickbooks.accounting`) → **Get authorization code** → authorize → **Get tokens**.
6. Copy into `backend/secrets.env` (do not commit; do not paste into chat):
   - Client ID / Secret → `CONNECTOR_QBO_CLIENT_ID` / `CONNECTOR_QBO_CLIENT_SECRET`
   - **realmId** / company ID → `CONNECTOR_QBO_REALM_ID`
   - **`refreshToken`** (not only `accessToken`) → `CONNECTOR_QBO_REFRESH_TOKEN`

**Alt if Playground unavailable:** add redirect `http://localhost:8765/callback` on Development keys, run a one-shot local OAuth callback, then store the same env vars.

**Pitfalls:** Development keys + sandbox company only; Production keys won’t talk to sandbox; authorizing the wrong company gives the wrong `realmId`; access tokens expire (~60 min) — you need the **refresh** token; skip Payments/OpenID scopes for read-only GL.

### 3. Xero

- [ ] Sign up at [developer.xero.com](https://developer.xero.com)
- [ ] Create app (OAuth 2.0); note Client ID / Secret
- [ ] Connect **Demo Company**
- [ ] Complete OAuth; save tenant id + tokens
- [ ] Local env (example):
  - `CONNECTOR_XERO_CLIENT_ID=`
  - `CONNECTOR_XERO_CLIENT_SECRET=`
  - `CONNECTOR_XERO_TENANT_ID=`
  - `CONNECTOR_XERO_REFRESH_TOKEN=`
  - `CONNECTOR_XERO_TOKEN_FILE=`
- [ ] Sample objects: Accounts, Invoices, BankTransactions, ManualJournals, Contacts → same `erp_gl` targets as QBO

### 4. Chargebee

**Auth:** API key (HTTP Basic Auth — key as username, empty password). **Not** OAuth like Salesforce / QBO.

- [x] Start trial at [chargebee.com/trial-signup](https://www.chargebee.com/trial-signup) — signup creates a **test site** automatically
- [x] Confirm sample / demo data is present (Customers, Subscriptions, Invoices) — via read-only probe on `smpl-ai-test`
- [x] Note **site name** from the browser URL (`https://{site}.chargebee.com` → `{site}`; test sites often end in `-test`) → `smpl-ai-test`
- [x] Settings → Configure Chargebee → **API Keys and Webhooks** → **API Keys** tab → create key (prefer **Read-Only: All**; **Full-Access** on TEST is OK for lab)
- [x] Local env (example):
  - `CONNECTOR_CHARGEBEE_SITE=smpl-ai-test` (hostname only, no `.chargebee.com`)
  - `CONNECTOR_CHARGEBEE_API_KEY=` (`test_…` only — never live)
  - `CONNECTOR_CHARGEBEE_TOKEN_FILE=` (optional local path)
- [x] Sample objects: Customer, Subscription, Invoice, Item/Plan → `billing_arr` entities
- [x] Read-only probe: `python backend/scripts/chargebee_sandbox_probe.py` → `backend/tmp/chargebee_sandbox_probe_summary.json`
- [x] Export stub (probe pass): `backend/tmp/chargebee_export/` (`subscriptions.csv`, `invoices.csv`, `export_manifest.json`) — gitignored; **not** org ingest
- [ ] Full export + Net Demo Co alignment (customers / payments / `mrr_waterfall` + shared `customer_master`) — next

**Status (2026-07):** TEST site `smpl-ai-test` configured; read-only probe + thin SMPL-shaped export stub. Do **not** use live keys; do **not** ingest into SMPL Demo Co. Next: align sample billing to Net Demo Co naming (same spine pattern as Stripe Quick Demo Co) and flesh out `chargebee_export_to_smpl.py`.

#### Beginner path (test site + API key)

1. Log into Chargebee (trial / developer account). You should land on a **test** site — check the URL bar: `https://{site}.chargebee.com`. The `{site}` part is `CONNECTOR_CHARGEBEE_SITE` (example: `acme-test`).
2. Confirm you are on the **test** site, not live (UI often shows a Test / Live site switcher; keys are **different** per site).
3. Glance at **Customers** / **Subscriptions** / **Invoices** — trial sites usually include sample data you can read for connector R&D.
4. Open **Settings** → **Configure Chargebee** → **API Keys and Webhooks** → **API Keys** tab ([docs](https://www.chargebee.com/docs/billing/2.0/site-configuration/api_keys)).
5. **+ Add API Key** (wording may be “Add an API Key”):
   - Prefer **Read-Only** → **All** (enough to list customers, subscriptions, invoices).
   - Or **Full-Access** on the **test** site if Read-Only is awkward in the UI — fine for lab; do not use a live full-access key for this work.
6. Name it e.g. `SMPL Connector Lab` → **Create** → copy the key once (often looks like `test_…`).
7. Put into `backend/secrets.env` (never commit; prefer **site name only** in chat — paste the key only if you want the same convenience as Stripe):

```
CONNECTOR_CHARGEBEE_SITE=smpl-ai-test
CONNECTOR_CHARGEBEE_API_KEY=
CONNECTOR_CHARGEBEE_TOKEN_FILE=
```

**Pitfalls:** Test vs live keys are not interchangeable; site value must be the subdomain only (`acme-test`, not the full URL); Publishable keys are for browser checkout — wrong type for server read of invoices/subscriptions; admin/owner role required to see API keys.

### Maxio (partnership track — wave 1 billing)

**Role in stack:** B2B SaaS billing and revenue-recognition sub-ledger between CRM and ERP. SMPL’s canonical split: **CRM** → pipeline; **Maxio** → billing/ARR actuals (+ rev-rec); **ERP** → GL. Common in mid-market SaaS where Stripe/Chargebee alone do not carry rev-rec.

**Status (2026-08-28):** Partnership track (Kevin 2026-08-21; Nick 2026-08-26). **`learn.maxio` login works** (Matt Skilljar seat; catalog scraped). **Connector scaffold landed** (`maxio_sandbox_probe.py`, `maxio_export_to_smpl.py`) — live Advanced Billing pull still **blocked on site + API key** (not in credential dump). Priority **alongside** Stripe + Chargebee; Maxio is the B2B/rev-rec shape those two do not cover. Remaining partnership steps: NDA if needed, use-case brief for Gong, technical SC (~Sep 8), **ask Nick for AB sandbox site+key**.

**Partnership fit (honest):** Maxio ends at billing/rev-rec actuals + ARR reporting; SMPL starts at unified close, forecast, board, and validation across CRM + billing + ERP. ~2,600-customer overlap with growth SaaS ICP ($10–100M, often post–first audit). VC/PE sometimes **require** Maxio — strong design-partner signal. Mosaic rolling into HiBob billing bundle cited as why some Maxio customers want an independent FP&A layer. **Abacum is Maxio's current FP&A/planning partner** (Matt / partner confirmation 2026-08-31). Partner ask: SMPL as **preferred / successor** FP&A partner — one governed FI platform (trust + board + planning/forecast + roadmap PPI) on Maxio actuals so customers aren't stacking Abacum + another trust layer; people want less software, not more. Do not invent Abacum feature matrices, win rates, or claim "we already replace Abacum in production."

**How Maxio fits (data model, short):**

| Layer | Product | Role | SMPL use |
|-------|---------|------|----------|
| Quote-to-cash billing engine | **Advanced Billing** (Chargify) | Customers → products/components → subscriptions → invoices/payments; Insights MRR movements | Day-1 Path A: REST → CSV → `billing_arr` |
| FinOps / rev-rec sub-ledger | **Maxio Core** (SaaSOptics) | Contracts, ASC 606 schedules, ARR/MRR reporting; AB syncs *into* Core | Day-2+: deferred revenue / board-grade ARR; API docs live *inside* Core Admin |
| Partner reporting | **Maxio MCP** | LLM/tooling over reporting (Kevin demo) | Eval / Gong demos only — **not** warehouse sync |

Canonical stack: **CRM** (pipeline) → **Maxio** (ARR actuals + rev-rec) → **ERP** (GL).

**Product surfaces (confirm with Nick/SC which Matt gets):**

| Surface | Heritage | What it gives SMPL | Auth (public docs) |
|---------|----------|--------------------|--------------------|
| **Advanced Billing** API | Chargify | Customers, subscriptions, products/components, invoices, Insights MRR movements | HTTP Basic — API key as username, literal `x` as password; base `https://{site}.chargify.com` |
| **Maxio Core** | SaaSOptics | Contracts, ARR/MRR reporting, ASC 606 rev-rec, SubMo-style metrics | Partner/docs gated (Admin → API Tokens; instance URL like `https://{tenant}.saasoptics.com/...`) — ask Nick |
| **Maxio MCP** | Newer | Reporting-oriented (Kevin demo: ARR by product via Claude) | Account-scoped MCP URL + token — great for demos / partner eval, **not** the Path A warehouse sync path |

**Day-1 connector target:** Advanced Billing REST only (same pattern as Chargebee: site + API key → probe → CSV stub → `billing_arr`). Core/MCP = Day-2+ once partner clarifies access.

**Public developer refs (no login):** [developers.maxio.com](https://developers.maxio.com/) (Advanced Billing portal), [Getting Started as a Developer](https://docs.maxio.com/hc/en-us/articles/24183843121677-Getting-Started-as-a-Developer), [Core Resources for Building an Integration](https://docs.maxio.com/hc/en-us/articles/24181468833037-Core-Resources-for-Building-an-Integration), [Developer One Sheet](https://docs.maxio.com/hc/en-us/articles/28271323360397-Developer-One-Sheet). Official SDKs: `maxio-com/ab-*-sdk` on GitHub. Self-serve sandbox signup: [app.chargify.com/signup/maxio-billing-sandbox](https://app.chargify.com/signup/maxio-billing-sandbox).

**Transcript notes (do not treat as API contracts):**

- Kevin (2026-08-21): Maxio = CRM↔ERP bridge; locked ARR/MRR formulas + per-item recurring flags; **MCP geared to reporting** (carve-outs on actuals, not forecast); Mosaic/Drivetrain owned prior FP&A integrations.
- Nick (2026-08-26): `learn.maxio` + NDA; tech-partner / co-sell path; follow-up ~Sept 8 (SC optional). No API keys handed on-call.
- Matt (2026-08-31): **Abacum confirmed** as current Maxio FP&A/planning partner. Corrected frame: SMPL as **preferred / successor** long-term FI partner — never “customers keep Abacum”; displace the stack (one platform), not coexist. Still no invented Abacum feature matrix / win rates / “already replace in production.”

**Do not claim:** Native Maxio connector is live (sales KB `connectors-today-vs-roadmap`).

#### Entity map → `billing_arr` (Advanced Billing)

| SMPL entity | Maxio Advanced Billing source | Notes |
|-------------|-------------------------------|-------|
| `customers` | `GET /customers.json` | Wrap: `{customer: {...}}`; use `id`, `organization` / name, `reference`, `created_at` |
| `subscriptions` | `GET /subscriptions.json` | `id`, nested `customer`, `product.handle`, `state`, `activated_at`, price/interval → MRR stub |
| `invoices` | `GET /invoices.json` | Relationship Invoicing: `uid`, `customer_id`, `issue_date`, `due_date`, `total_amount`, `status` |
| `payments` | Invoice payments / transactions (Day-2) | Not in Day-1 stub |
| `mrr_waterfall` | `GET /mrr_movements.json` (Insights; **deprecated** but still documented) | Categories: `new_business`, `expansion`, `contraction`, `churn`, … → waterfall columns |
| Rev-rec / deferred | **Maxio Core** (later) | Not on Advanced Billing list endpoints |

Pagination: `page` + `per_page` (max **200** for most lists; **50** for `mrr_movements`). Auth differs from Chargebee (`api_key:` empty password) — Maxio uses **`api_key:x`**.

#### Field map (Day-1 stub → compact Stripe/Chargebee headers)

| SMPL header | Maxio field (Advanced Billing) |
|-------------|--------------------------------|
| `subscription_id` | `subscription.id` |
| `customer_id` | `subscription.customer.id` or `customer_id` |
| `product` | `subscription.product.handle` (fallback `name`) |
| `billing_cadence` | `product.interval` + `interval_unit` → monthly/quarterly/annual |
| `start_date` / `end_date` | `activated_at` / `canceled_at` (ISO date prefix) |
| `current_mrr` / `current_arr` | Approx from `product.price_in_cents` + interval (**stub**); prefer Insights/Core for production ARR |
| `status` | `subscription.state` |
| `invoice_id` | `invoice.uid` |
| `invoice_amount` | `invoice.total_amount` (decimal string, not cents) |
| `payment_status` | `invoice.status` |
| waterfall `movement_type` / buckets | `mrr_movements[].category` + `amount_in_cents` |

#### Matt request list (when network access opens)

Ask Nick / SC explicitly:

1. **Advanced Billing test site** — subdomain + ability to create API keys (`Config → Integrations → API Keys`), preferably with sample subscriptions/invoices  
   - Self-serve fallback to try today: [Maxio Billing sandbox signup](https://app.chargify.com/signup/maxio-billing-sandbox) (public docs) — still ask partner which site/env they want SMPL on
2. Confirm **API key vs OAuth** for partner apps (public Advanced Billing docs = **API key Basic Auth only**; no OAuth for this surface)
3. Whether **Maxio Core** (rev-rec / ARR reports / contracts) API or export is in scope for partners, and sample data availability
4. Whether **MCP** credentials are available for partner sandbox (demo / eval only)
5. Preferred **sandbox vs production** separation and any partner-app registration / NDA gates beyond `learn.maxio`
6. **`learn.maxio` login** — confirm Matt's Skilljar seats + which partner tracks (API / integrations / Core / reporting) to prioritize

Local env (never commit; `backend/secrets.env` + `backend/.credentials/` are gitignored):

```
# learn.maxio (Skilljar) — present locally as of 2026-08-28
LEARN_MAXIO_EMAIL=
LEARN_MAXIO_PASSWORD=
LEARN_MAXIO_URL=https://learn.maxio.com
# Advanced Billing API — still empty until Nick/sandbox
CONNECTOR_MAXIO_SITE=                 # Advanced Billing subdomain only (no .chargify.com)
CONNECTOR_MAXIO_API_KEY=              # site API key (Basic Auth username; password = x)
CONNECTOR_MAXIO_TOKEN_FILE=           # optional local path
# Later / if Core or MCP granted:
# CONNECTOR_MAXIO_CORE_URL=           # e.g. https://xxx.saasoptics.com/yyy
# CONNECTOR_MAXIO_CORE_API_TOKEN=
# CONNECTOR_MAXIO_MCP_URL=
# CONNECTOR_MAXIO_MCP_TOKEN=
```

Credential dump path (gitignored): `backend/.credentials/Maxio Credentials.txt` — currently **learn portal only** (URL + email + password). No AB site/API key there yet.

#### Checklist — network access imminent → first pull

- [x] `learn.maxio` login (Matt seat; Partner signup field) — catalog accessible
- [ ] NDA from Nick if still required beyond Skilljar access
- [ ] Confirm which product(s): Advanced Billing only vs + Core vs + MCP
- [ ] Sandbox/test site subdomain + **read** API key in password manager / `secrets.env`
- [ ] Smoke: `curl -u APIKEY:x https://{site}.chargify.com/subscriptions.json`
- [x] Thin read-only probe: `backend/scripts/maxio_sandbox_probe.py`
  - Base `https://{site}.chargify.com/…`; auth Basic `api_key:x`
  - Paginate `page` / `per_page`; lists customers / subscriptions / invoices / products; optional `stats.json` + `mrr_movements.json`
  - Writes `backend/tmp/maxio_sandbox_probe_summary.json` + stub CSVs under `backend/tmp/maxio_export/`
- [x] Thin export entrypoint: `backend/scripts/maxio_export_to_smpl.py` (same headers as Stripe compact spine)
- [ ] Live probe with real site+key → non-zero sample (or document empty sandbox)
- [ ] Map sample objects → `billing_arr` ingest path (still **export-only**; no Demo Co ingest)
- [ ] **Do not** ingest into SMPL Demo Co until demo spine alignment (same rule as Chargebee/Stripe)

#### Suggested Day-1 / Day-2 sequence

| Day | Goal | Done when |
|-----|------|-----------|
| **1** | Credentials + probe | Site + key work; summary JSON shows non-zero customers/subs/invoices (or documents empty sandbox); stub CSVs under `tmp/maxio_export/` |
| **1–2** | Field map | Table above validated against live JSON samples |
| **2** | Expand export | `maxio_export_to_smpl.py` — customers + payments + fuller `mrr_waterfall` from Insights (or Core) |
| **Later** | Core rev-rec, CRM closed-won ↔ new ARR tie-out, scheduled connector runtime, MCP-assisted reporting demos | Needs Core access + CRM spine; not a 1–2 day claim |

#### Matt learning path (`learn.maxio` + public docs)

Catalog accessed 2026-08-28 as **Matt Justice** (`mattjustice@smpl-ai.com`, Skilljar signup field **Partner**). ~59 catalog tiles (3 paths + courses/webinars). Snapshot: `backend/tmp/learn_maxio_catalog_courses.json` (gitignored tmp).

**Take in this order (integration / ARR focus):**

| Pri | Item | Why for SMPL |
|-----|------|----------------|
| **P0** | **PATH:** [Advanced Billing Essentials](https://learn.maxio.com/path/advanced-billing-essentials) | Day-1 connector surface — customers/subs/invoices/MRR |
| **P0** | [Maxio Onboarding Essentials](https://learn.maxio.com/maxio-onboarding-essentials) | Platform mental model |
| **P0** | [Getting Started with Maxio Implementation](https://learn.maxio.com/path/maxio-core-implementation-essentials/getting-started-with-maxio-implementation) + **Core Objects** | Object model language shared with Core |
| **P0** | **PATH:** [Maxio Core Essentials Certifications for Partners](https://learn.maxio.com/path/maxio-essentials-for-partners) | Partner track Nick pointed at |
| **P1** | **PATH:** [Maxio Core Implementation Essentials](https://learn.maxio.com/path/maxio-core-implementation-essentials) — prioritize **Finance Reporting**, **Analytics Reporting and Dashboards**, **Items**, **Full Workflow** | ARR/rev-rec + reporting → `billing_arr` / board metrics |
| **P1** | Webinar: [Self-Service Billing in Advanced Billing](https://learn.maxio.com/webinar-self-service-billing-in-advanced-billing) | AB product behavior |
| **P1** | Webinars: [Revenue Recognition 101](https://learn.maxio.com/revenue-recognition-101-in-maxio), [Audit Ready Rev Rec](https://learn.maxio.com/audit-ready-revenue-recognition-with-maxio-webinar), [Month-End Close — Core Workflows](https://learn.maxio.com/month-end-close-in-maxio-core-workflows) | Close / ASC 606 narrative for Gong + product |
| **P1** | [Maxio MCP how-to](https://learn.maxio.com/how-to-video-series-maxio-mcp-cpos-working-with-mcp) + MCP C-suite webinars | Demo/eval only — **not** Path A warehouse sync |
| **P2** | Core Implementation: Salesforce / QuickBooks / Importer / Data Migration | CRM↔billing↔ERP adjacency later |
| **Skip now** | Advocacy, Blog, SaaSPedia deep-dives, most roadmap/AI webinars | Low ROI vs connector unblock |

**API coding** is thin on Skilljar — pair AB Essentials with public [Developer Portal](https://developers.maxio.com/) + [Building Workflows with APIs and Webhooks](https://docs.maxio.com/hc/en-us/articles/24181509386381-Building-Workflows-with-APIs-and-Webhooks) + [Core Resources for Building an Integration](https://docs.maxio.com/hc/en-us/articles/24181468833037-Core-Resources-for-Building-an-Integration).

**Ask Nick for (next):** (a) Advanced Billing **sandbox site + read API key** — only remaining Day-1 blocker, (b) whether Core API token is in partner scope, (c) MCP URL+token if we want a reporting demo, (d) confirm partner path vs customer onboarding path on Skilljar.

**Clone from Chargebee (closest twin):** `chargebee_sandbox_probe.py` (auth/env/summary/export stub). **Also reuse:** `stripe_export_to_smpl.py` + `stripe_quick_demo_common.py` headers for full CSV spine when ready. **Do not** build a connector framework package yet (same engineering sequence as rest of this doc).

### 5. Gusto

- [ ] Sign up at [dev.gusto.com](https://dev.gusto.com)
- [ ] Create app; use **sandbox** (demo companies with employees + payrolls)
- [ ] Note: production keys may need Gusto QA — stay in sandbox for wave 1
- [ ] Local env (example):
  - `CONNECTOR_GUSTO_CLIENT_ID=`
  - `CONNECTOR_GUSTO_CLIENT_SECRET=`
  - `CONNECTOR_GUSTO_ACCESS_TOKEN=` / refresh as docs require
  - `CONNECTOR_GUSTO_TOKEN_FILE=`
- [ ] Sample objects: Company, Employee, Payroll, Compensations → `workforce_employees`, `headcount_plan`, opex drivers

### Optional wave 1b — Deel

- [ ] [developer.deel.com](https://developer.deel.com) → sandbox (reset anytime)
- [ ] `CONNECTOR_DEEL_API_TOKEN=` / `CONNECTOR_DEEL_TOKEN_FILE=`
- [ ] Sample: contractors, contracts, payments → workforce / opex international view

---

## Wave 2 prep — Salesforce (connect now)

**Why now:** Matt’s DE/scratch-style org is ready. HubSpot is the Quick Demo Co CRM in the wave-1 spine; Salesforce is fine as a **second CRM lab** (Net Demo Co in the longer vision). Do **not** block on sample data — DE orgs often start empty; we will seed or import Accounts / Opportunities / Contacts later for demo alignment.

**Auth preference:** OAuth web server flow + **refresh token** (same pattern as QBO). Avoid username + password + security token.

**UI note (2025–2026):** Prefer **External Client App** (Setup → **External Client App Manager** → **New External Client App**). Older orgs may still show **App Manager** → **New Connected App**. Same OAuth ideas apply; labels below match External Client App first.

### Checklist

- [x] Developer Edition (or scratch) org active — [developer.salesforce.com/signup](https://developer.salesforce.com/signup)
- [x] Create External Client App (or Connected App) with OAuth enabled
- [x] Callback URL: `http://localhost:8766/callback` (do **not** reuse QBO’s `8765`)
- [x] Scopes: **Manage user data via APIs (`api`)** + **Perform requests at any time (`refresh_token`, `offline_access`)**  
  (UI often shows one combined checkbox: “Perform requests at any time (refresh_token, offline_access)”.)
- [x] Copy Consumer Key / Consumer Secret + My Domain / instance URL into `backend/secrets.env`
- [x] OAuth one-shot: `python backend/scripts/salesforce_oauth_once.py` → wrote `CONNECTOR_SALESFORCE_REFRESH_TOKEN` + `INSTANCE_URL`
- [x] Read-only probe: `python backend/scripts/salesforce_sandbox_probe.py` → `backend/tmp/salesforce_sandbox_probe_summary.json` (no SMPL Demo Co ingest)
- [ ] Sample CRM later (Net/Quick demo alignment): Account, Contact, Opportunity, OpportunityLineItem → `opportunities` / pipeline entities (seed/import TBD; DE often empty until then)

### Create External Client App (beginner path)

1. Log into the Salesforce org → gear → **Setup**.
2. Quick Find: **External Client App Manager** (or **App Manager**).
3. **New External Client App** (or **New Connected App** if that’s what you see).
4. **Basic Information:** name e.g. `SMPL Connector Lab`, contact email, distribution **Local** (org-only).
5. Expand **API (Enable OAuth Settings)** → check **Enable OAuth**.
6. **Callback URL** (exact):  
   `http://localhost:8766/callback`
7. **OAuth Scopes** — select at least:
   - Manage user data via APIs (`api`)
   - Perform requests at any time (`refresh_token`, `offline_access`)
8. Flow / security (typical for a local helper that can keep a secret):
   - Enable **Authorization Code** / web server flow (wording varies)
   - **Require Secret for Web Server Flow** = on
   - **Require Secret for Refresh Token Flow** = on
   - Keep **Require Proof Key for Code Exchange (PKCE)** enabled — `salesforce_oauth_once.py` sends S256 `code_challenge` / `code_verifier`
9. **Save**. Open the app → **Settings** → OAuth → **Consumer Key and Secret** (email verification code is often required). Copy both.
10. Note **My Domain** / instance URL from Setup → **My Domain**, or from the browser address bar after login — form `https://<your-domain>.my.salesforce.com` (not the lightning `*.lightning.force.com` UI host for API base).

### Local env (`backend/secrets.env` — never commit)

```
CONNECTOR_SALESFORCE_CLIENT_ID=          # Consumer Key
CONNECTOR_SALESFORCE_CLIENT_SECRET=      # Consumer Secret
CONNECTOR_SALESFORCE_REDIRECT_URI=http://localhost:8766/callback
CONNECTOR_SALESFORCE_INSTANCE_URL=       # https://<mydomain>.my.salesforce.com
CONNECTOR_SALESFORCE_REFRESH_TOKEN=      # after OAuth one-shot
CONNECTOR_SALESFORCE_TOKEN_FILE=         # optional JSON blob path
```

**Status (2026-07):** OAuth connected for Matt’s DE org (`SMPL.ai`). Read-only probe OK — org has starter CRM rows (not empty). Do **not** ingest into SMPL Demo Co. Optional later: seed/align CRM for Net/Quick demo. Chargebee TEST probe is done (`smpl-ai-test`); Net Demo Co billing alignment is the next Chargebee step.

**Do not** paste Consumer Secret or refresh token into chat.

**Pitfalls:** DE orgs may be empty or lightly populated; login host vs API instance URL mix-ups; using `full` scope when `api` is enough; colliding with QBO callback port `8765`; password+security-token flow (skip — prefer OAuth like QBO).

---

## Immediate actions today (Matt)

**Sign up / configure (self-serve):**

1. Stripe Test mode + sample customers/subs  
2. Intuit developer + QBO sandbox  
3. Xero developer + Demo Company  
4. Chargebee trial  
5. Gusto developer sandbox  

**Outreach (lead time — do not wait for wave 1 code):**

6. **Sage Intacct** — request developer sandbox at [developer.intacct.com](https://developer.intacct.com); note expected wait  
7. **Rillet** — contact partner / API access; ask about `sandbox.api.rillet.com` + sample data  

**Optional same day (wave 2 prep):** Salesforce Developer Edition + HubSpot developer account (expect empty/minimal data). Salesforce Connected App / External Client App steps → [Wave 2 prep — Salesforce](#wave-2-prep--salesforce-connect-now).

**Do not:** commit secrets; apply for partner apps that need legal entity docs unless ready; write anything back to ERP; wire sandboxes into prod Railway/Vercel yet.

---

## Suggested engineering sequence (after accounts exist)

```
1. Export / API-pull sample JSON → hand-map to load_domains entity types
2. Normalize to CSV matching existing demo-csv / warehouse loaders (Path A path)
3. Document field maps per vendor in this file (or a short subsection below)
4. Only then: thin read-only sync scripts under backend/scripts/ (optional)
5. Path B (poc-1…3) stays the self-serve product track — connectors feed the same warehouse schema later
```

No connector runtime package is scaffolded yet on purpose — avoid an unfinished framework. When the first pull script lands, link it from the Status table row.

---

## Field maps (sandbox → warehouse)

### Stripe Billing → SMPL `billing_arr` CSVs (Quick Demo Co)

**Namespace:** `CONNECTOR_STRIPE_*` only. Never `STRIPE_*` (SMPL product billing).

**Spine:** `backend/tmp/quick_demo_co/customer_master.csv` is the shared identity layer for Quick Demo Co. Future QBO enrichment and Stripe seed/export both key off `smpl_customer_id` (`QDC-###`). QBO joins use `qbo_customer_ref_id` ↔ `invoices_staging.customer_ref_id`.

| Stripe object | SMPL CSV | Notes |
|---------------|----------|--------|
| Customer (`metadata.smpl_customer_id`) | `customers.csv` | Compact headers; `stripe_customer_id` filled from Stripe |
| Subscription (+ line prices) | `subscriptions.csv` | MRR from monthly `unit_amount`; cancelled when status not active |
| Invoice | `invoices.csv` | `invoice_period` = `YYYY-MM` from created |
| paid Invoice | `payments.csv` | `payment_id` = charge id when present |
| (derived) | `mrr_waterfall.csv` | Jan–May 2026 customer-level bridge synthesized from master start dates + current Stripe MRR (not full billing history) |

**Idempotency:** seed objects carry `metadata.smpl_seed=quick_demo_co`. Re-runs reuse matching products/customers/subscriptions.

**Ingest status:** Export + header shapes only. Do **not** load into SMPL Demo Co unless explicitly requested.

### QuickBooks Online → SMPL `gl_actuals` / CoA

**Scripts (read-only):**

| Script | Purpose |
|--------|---------|
| `backend/scripts/qbo_sandbox_probe.py` | Auth smoke + entity counts / field samples |
| `backend/scripts/qbo_export_to_smpl.py` | Pull Account + JournalEntry (+ Invoice staging) → CSV under `backend/tmp/qbo_export/` |

**Target profiles:**

| Output file | SMPL target | Header source |
|-------------|-------------|-----------------|
| `gl_actuals.csv` | Typed mart `gl_actuals` (`erp_gl` domain) | Exact expanded headers in `detector.py` / `templates/csv/02-operational-marts/gl_actuals.csv` |
| `chart_of_accounts.csv` | Staging CoA (not a typed mart yet) | `templates/csv/01-source-inputs/erp/ERP_Chart_of_Accounts_Export.csv` |
| `invoices_staging.csv` | Staging only (not exact `invoices` mart) | Slim QBO fields for later `billing_arr` mapping |

**JournalEntry line → `gl_actuals` columns:**

| QBO field | SMPL column | Notes |
|-----------|-------------|--------|
| `JournalEntry.TxnDate` (month start) | `period` | `YYYY-MM-01` |
| *(literal)* `Actual` | `version` | Actuals only in this pass |
| `Account.AcctNum` or `QBO-{Account.Id}` | `account_number` | Sandbox often omits `AcctNum` |
| `Account.Name` / `AccountRef.name` | `account_name` | |
| `Account.Classification` + `AccountType` / `AccountSubType` | `statement`, `statement_category` | See mapping rules below; loader also accepts `category` ← `statement_category` |
| `Account.AccountType` | `account_group` | Pass-through label |
| `Account.AccountSubType` | `expense_type` | Pass-through label |
| `JournalEntryLineDetail.DepartmentRef` | `department` | name or id |
| `JournalEntryLineDetail.ClassRef` | `cost_center` | QBO Class → cost center slot |
| *(empty)* | `sub_department` | Not sourced yet |
| `JournalEntryLineDetail.Entity.EntityRef` | `vendor_id`, `vendor_name` | When EntityType is Vendor (ids/names as returned) |
| *(literal)* `qbo_journal_entry` | `source_file` | Stable PK component |
| `{JournalEntry.Id}:{Line.Id}` | `source_record_id` | Line-level grain |
| `Line.Amount` + `PostingType` | `amount` | Signed natural balance (see below) |
| `JournalEntry.CurrencyRef` | `currency` | Default `USD` |
| *(empty)* | `subsidiary` | Single-company sandbox |
| *(literal)* `quickbooks` | `source_system` | |
| `PrivateNote` / line `Description` / posting | `notes` | Truncated |

**Account → staging CoA columns:**

| QBO field | SMPL / staging column |
|-----------|------------------------|
| `AcctNum` or `QBO-{Id}` | `account_code` |
| `Name` | `account_name` |
| `AccountType` | `account_type` |
| parent `AcctNum` / `QBO-{ParentRef}` | `parent_account_code` |
| Classification / type rules | `statement`, `category` |

**Statement / category rules (first pass):**

| QBO Classification / AccountType | `statement` | `statement_category` / `category` |
|----------------------------------|-------------|-------------------------------------|
| Revenue / Income / Other Income | `income` | `revenue` (discounts → `contra_revenue`) |
| Cost of Goods Sold | `income` | `cogs` |
| Expense / Other Expense | `income` | `opex` (payroll/depr heuristics when subtype matches) |
| Asset / Bank / A/R / … | `balance_sheet` | `asset` |
| Liability / A/P / … | `balance_sheet` | `liability` |
| Equity | `balance_sheet` | `equity` |

**Amount sign convention:** Income revenue credits and expense/COGS debits are positive; BS liability/equity credits and asset debits are positive. Opposite posting flips the sign.

**Invoice staging (not mart-ready):** `Id` → `invoice_id`, `DocNumber`, `TxnDate`, `TotalAmt`, `Balance`, `CurrencyRef`, `CustomerRef.value` only (no customer display names in the export artifact). Full map to `invoices` mart headers is a follow-up.

**Ingest status:** Export + header dry-run only (`detect_csv_kind == gl_actuals`). Do **not** load into Demo Co from this script unless explicitly requested — avoids mixing sandbox GL into the seeded demo warehouse.

---

## Wave 2 order (after first-wave sandboxes are usable)

| Order | System | Notes |
|-------|--------|--------|
| 1 | **NetSuite** | Highest enterprise GL ask; expect SuiteScript + DIY test records |
| 2 | **Salesforce** | Pipeline; empty DE org — import sample opportunities early |
| 3 | **Sage Intacct** | Mid-market GL; depends on sandbox approval from today’s outreach |
| 4 | **Rillet** | Modern accounting API; gated — unblock via partner |
| 5 | **HubSpot** | Common SMB CRM; plan a bulk import of deals/companies |
| 6 | **Deel** (if skipped in 1b) | Global workforce |
| 7 | Zoho / Pipedrive / BambooHR | Lower ICP frequency or unclear sample data |

---

## Env naming cheat sheet

| Kind | Pattern | Example |
|------|---------|---------|
| Connector secret | `CONNECTOR_<VENDOR>_<THING>` | `CONNECTOR_QBO_CLIENT_SECRET` |
| Local file pointer | `CONNECTOR_<VENDOR>_TOKEN_FILE` | path outside repo |
| SMPL product Stripe | `STRIPE_*` | unchanged — SaaS billing only |
| SMPL product HubSpot | `HUBSPOT_*` | unchanged — inbound sales only |

Never use `NEXT_PUBLIC_*` for connector credentials.

---

## Status legend

| Status | Meaning |
|--------|---------|
| not started | No account / no keys yet |
| sandbox ready | Account + dummy data + credentials in local env/token file |
| pull prototype | Script or notebook can read sample objects |
| mapped to warehouse | Sample → CSV/API batch into a test org |
| blocked on sandbox | Waiting on vendor approval (Intacct, Rillet, …) |
| blocked on partner | Legal / partnership gate |
