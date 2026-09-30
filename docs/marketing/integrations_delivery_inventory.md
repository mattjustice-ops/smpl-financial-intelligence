# Integrations delivery inventory (internal — not for publication)

**As of:** 2026-09-30
**Purpose:** What SMPL can already do per system, what has actually been tested, what work remains to deliver the implementation-led offer described on `/integrations`, and whether anything genuinely blocks it.
**Governing principle:** An unfinished packaged connector is not a reason we cannot serve a customer. Building or adapting the connection is part of SMPL-led implementation. Ordinary implementation work (credentials, mapping, a customer-specific extract) is listed as remaining work, not as a blocker.
**Sources:** `docs/INTEGRATIONS_SETUP.md`, `docs/GO_LIVE_POC_DIRECT_DATA_ACCESS.md`, `docs/partners/Maxio_Technical_Readiness_QA.md`, `docs/product/SMPL_Budget_Methodology.md`, `backend/scripts/*`, `backend/tmp/*` (gitignored probe output).

---

## 1. Capabilities shared by every system

These apply regardless of source and are the delivery path for any system below.

| Capability | Status | Evidence |
|---|---|---|
| Exact-header CSV ingest into typed warehouse marts (`gl_actuals`, `mrr_waterfall`, `subscriptions`, `opportunities`, `headcount_plan`, …) | Shipped | `POST /api/v1/ingest/csv`; demo-csv profiles; `backend/app/services/demo_csv/loader.py` |
| Programmatic batch ingest tagged by `source_system` | Shipped | `POST /api/v1/ingest/batches` |
| White-glove load ("Path A"): Snowflake secure share, cloud object storage, ERP exports to SFTP/shared drive, secure file drop → normalize → org-scoped warehouse load | Shipped (playbook + scripts; dry run and Customer Corp tie-out done) | `docs/GO_LIVE_POC_DIRECT_DATA_ACCESS.md`; `scripts/run-direct-access-poc.ps1`, `setup-prod-warehouse.ps1`, `provision-prod-customer.ps1`, `smoke-test-direct-access-poc.ps1` |
| Tenant isolation on load (org-scoped replace) | Shipped | `docs/soc2/evidence/tenant-isolation-2026-07-29.md` |
| Read-only posture (no GL/billing write-back) | Product constraint | `docs/INTEGRATIONS_SETUP.md` §Product constraints |
| Validation / tie-out after load ($1.00 closed-actuals bar, cross-source checks, freeze) | Shipped | `docs/SMPL_Reporting_Assurance_Context_for_ChatGPT.md` |
| Native OAuth / **scheduled** connector runtime | Not built (greenfield by design) | `docs/INTEGRATIONS_SETUP.md` "What already exists vs greenfield" |

**Implication for every deal:** first load and each refresh are delivered today by SMPL ops (Path A) from an API pull script or customer extracts. There is no automated scheduler. See §4.

---

## 2. Per-system inventory

Legend for "Tested": **API probe** = read-only script ran against a vendor sandbox/test org and produced output; **Export stub** = sample mapped to SMPL CSV headers (not loaded into a customer org); **None** = no system-specific testing.

### Maxio (billing / ARR / rev-rec)

- **Existing:** `backend/scripts/maxio_sandbox_probe.py` and `maxio_export_to_smpl.py` (Advanced Billing REST, Basic auth `api_key:x`, pagination; customers/subscriptions/invoices/products/`mrr_movements` → Stripe-compatible compact headers). Entity and field maps documented in `INTEGRATIONS_SETUP.md` §Maxio.
- **Tested:** None against live data. Scripts have never run with a real site + key (no `backend/tmp/maxio_sandbox_probe_summary.json`). learn.maxio catalog access only (`backend/tmp/learn_maxio_catalog_*.json`).
- **Remaining work:** Advanced Billing test site + read API key (self-serve sandbox signup is public: app.chargify.com/signup/maxio-billing-sandbox, so this does not depend on the partnership conversation); run probe; validate field map against live JSON; payments + fuller `mrr_waterfall`; Maxio Core (contracts, ASC 606 schedules, deferred revenue) access path.
- **Blocker?** No. Genuine limitation: Maxio Core API docs are inside Core Admin and partner/customer-gated. **Workable scope:** billing/ARR from Advanced Billing API or customer-run standard Maxio exports; deferred/recognized revenue from Core exports supplied by the customer or from the ERP.
- **Positioning guardrail:** Maxio is an exploratory partnership conversation. Never "partner", "certified", or "native".

### NetSuite (ERP / GL)

- **Existing:** Path A "ERP export" method (saved searches / scheduled CSV to SFTP) + `gl_actuals` schema, which already carries `subsidiary`, `department`, `cost_center` (class), `vendor_*`, `currency`, `statement_category`. QBO mapping rules (§Field maps) are the template for a NetSuite account→statement map.
- **Tested:** None.
- **Remaining work:** Customer-side integration record + read-only role (token-based auth) for SuiteTalk REST/SuiteQL, or scheduled saved-search exports; account/subsidiary/department/class mapping per customer; opening balances for Budget roll-forward.
- **Blocker?** No for single-entity or entity-level reporting. **Confirm before committing on multi-entity deals:** intercompany eliminations and multi-currency translation are not described as shipped anywhere in the docs. **Workable scope:** load subsidiary-level and consolidated results as NetSuite reports them (consolidation and eliminations performed in NetSuite), and report on them in SMPL.

### Salesforce (CRM)

- **Existing:** `salesforce_oauth_once.py` (OAuth web-server flow + PKCE, refresh token) and `salesforce_sandbox_probe.py` (read-only). Pipeline drilldown (waterfall cell → opportunity rows) is shipped in `/app`.
- **Tested:** API probe against Matt's Developer Edition org, 2026-07-26 — `backend/tmp/salesforce_sandbox_probe_summary.json` (13 Accounts plus Contacts/Opportunities starter rows; `org_appears_empty: false`). No customer-shaped opportunity history yet.
- **Remaining work:** Opportunity/OpportunityLineItem export → `opportunities` / `*_opportunity_movements`; stage/record-type/custom-field mapping per customer; account ↔ billing customer matching.
- **Blocker?** No. Genuine consideration: the pipeline waterfall's "slipped" and period movements need opportunity history. If the customer has no field-history tracking on Stage/CloseDate/Amount, **workable scope:** start period snapshots at go-live and build movement history forward; use current-state pipeline for coverage from day one.

### NetSuite + Salesforce (combined page)

- Same as the two rows above. The distinctive work is customer/product identity matching (Salesforce Account ↔ NetSuite Customer; CRM products ↔ NetSuite items). Pattern already exists: `backend/tmp/quick_demo_co/customer_master.csv` spine (`smpl_customer_id` ↔ source IDs). No blocker.

### Sage Intacct (ERP / GL)

- **Existing:** Path A ERP export; `gl_actuals` dimension columns.
- **Tested:** None. Developer sandbox request outstanding ("blocked on sandbox").
- **Remaining work:** Customer-scheduled custom report exports, or Web Services API access (Intacct Web Services uses a sender ID plus company user credentials; confirm whether SMPL needs its own sender ID or can use the customer's authorization). Dimension mapping (department, location, class, project) per customer.
- **Blocker?** No — the sandbox wait blocks SMPL's own lab work, not a customer implementation, which can run from the customer's exports. Same multi-entity consolidation caveat as NetSuite.

### Xero (accounting)

- **Existing:** Path A exports; QBO mapping as template (same `erp_gl` targets).
- **Tested:** None (not started).
- **Remaining work:** Xero OAuth app (Demo Company for lab); Accounts/Invoices/BankTransactions/ManualJournals/tracking categories → `gl_actuals`. Note: Xero caps the number of organisations an uncertified app can connect; check the current limit before relying on API pulls at scale.
- **Blocker?** No. Exports work from day one.

### Rillet (accounting / ERP)

- **Existing:** Path A exports.
- **Tested:** None. API is partner-gated ("blocked on partner access"; `sandbox.api.rillet.com` exists).
- **Remaining work:** Customer exports (GL, revenue schedules) or customer-authorized API access; map revenue schedules to the ARR→revenue bridge.
- **Blocker?** No. **Workable scope:** customer-provided exports until partner/API access is granted.

### Campfire (accounting / ERP)

- **Existing:** Path A exports only. Only internal mention is a Campfire sales call transcript (`tmp/2026-09-22_08-59-48.srt`); no technical docs.
- **Tested:** None.
- **Remaining work:** Confirm Campfire's export formats and whether read-only API access is available to customers; map GL and any revenue data.
- **Blocker?** No. **Workable scope:** structured exports.

### QuickBooks Online (accounting) — hub only

- **Existing:** `qbo_oauth_once.py`, `qbo_sandbox_probe.py`, `qbo_export_to_smpl.py`; full field map in `INTEGRATIONS_SETUP.md` §QuickBooks Online.
- **Tested:** API probe (sandbox, 2026-07-24, `backend/tmp/qbo_sandbox_probe_summary.json`) + export stub (`backend/tmp/qbo_export/`: chart_of_accounts, gl_actuals, invoices_staging, customers_staging) with `detect_csv_kind == gl_actuals` header dry-run.
- **Remaining work:** Intuit production app keys (production access requires Intuit's app review); sandbox GL is JE-only and thin, so billing↔GL dollar tie is not yet exercised.
- **Blocker?** No.

### Stripe Billing — hub only

- **Existing:** `stripe_seed_quick_demo.py`, `stripe_export_to_smpl.py`, `stripe_quick_demo_common.py`.
- **Tested:** Test-mode seed (~24 customers) + export to compact CSVs (`backend/tmp/stripe_export/`: customers, subscriptions, invoices, payments, mrr_waterfall, customer_master). Waterfall Jan–May 2026 is synthesized from seed dates, not billing history.
- **Remaining work:** Customer restricted read-only key; real subscription history for the waterfall.
- **Blocker?** No.

### Chargebee — hub only

- **Existing:** `chargebee_sandbox_probe.py`.
- **Tested:** API probe on test site `smpl-ai-test`, 2026-07-26 (`backend/tmp/chargebee_sandbox_probe_summary.json`: 5 customers, 5 subscriptions, 2 invoices, 9 items) + thin export stub (`backend/tmp/chargebee_export/`).
- **Remaining work:** Full export (customers, payments, `mrr_waterfall`) — `chargebee_export_to_smpl.py` not yet fleshed out.
- **Blocker?** No.

### HubSpot — hub only

- **Existing / Tested:** None for customer-source data (SMPL's own HubSpot is inbound-sales ops only, `HUBSPOT_*`).
- **Remaining work:** Customer private-app token (read scopes) or deal exports → `opportunities`.
- **Blocker?** No.

### Recurly — hub only

- **Existing / Tested:** None.
- **Remaining work:** Read-only API key or exports → `billing_arr` entities.
- **Blocker?** No.

### HRIS / payroll (Rippling, Gusto, BambooHR, Workday, HiBob, Deel) — hub only

- **Existing:** `workforce_employees` / `headcount_plan` marts; Path A exports.
- **Tested:** None (Gusto and Deel sandboxes not started).
- **Remaining work:** Census/compensation report exports per customer; Gusto production API requires Gusto's partner review, so start from exports.
- **Blocker?** No. Compensation data is sensitive — confirm access scoping with the customer during implementation.

### Snowflake / cloud storage / SFTP — hub only

- **Existing:** Path A preferred method when the customer is on Snowflake (secure share or read-only service user); object storage and SFTP documented.
- **Tested:** Playbook dry run with bundled demo data (poc-0 done); no real customer share yet.
- **Blocker?** No.

---

## 3. Summary table

| System | Page | Existing extraction | System-specific testing | Blocker to the offer |
|---|---|---|---|---|
| Maxio | `/integrations/maxio` | AB API scaffold + exports | None live | No (Core via exports) |
| NetSuite | `/integrations/netsuite` | Exports (Path A) | None | No (confirm consolidation scope) |
| Salesforce | `/integrations/salesforce` | OAuth + probe | DE org probe 2026-07-26 | No (history forward if absent) |
| Sage Intacct | `/integrations/sage-intacct` | Exports (Path A) | None | No (confirm consolidation scope) |
| Xero | `/integrations/xero` | Exports (Path A) | None | No |
| Rillet | `/integrations/rillet` | Exports (Path A) | None | No |
| Campfire | `/integrations/campfire` | Exports (Path A) | None | No |
| QuickBooks Online | hub | OAuth + probe + export | Sandbox probe + export 2026-07-24/25 | No |
| Stripe | hub | Seed + export | Test-mode export 2026-07-25 | No |
| Chargebee | hub | Probe + stub | Test-site probe 2026-07-26 | No |
| HubSpot, Recurly, HRIS/payroll | hub | Exports (Path A) | None | No |

Nothing on the public pages says a system has been tested or validated.

---

## 4. The one genuine delivery limitation: refresh after go-live

There is no scheduled connector runtime. Keeping data current after go-live means SMPL ops re-running the Path A load (API pull script or customer extract → normalize → load → tie-out) each period. Concurrent loads for the same org are last-write-wins (no load mutex; `Maxio_Technical_Readiness_QA.md` Q5).

- **Public wording used:** "the reporting data is kept current on the refresh cadence agreed during implementation" — deliberately does not promise a frequency or say who runs it.
- **Proposed workable scope:** close-aligned monthly refresh operated by SMPL for each customer, with an extra mid-month refresh for forecast/board cycles when agreed. Daily or weekly refresh is scoped per customer and needs engineering (scheduler + credentials vault) before it is offered broadly.
- **Decision needed (Matt):** confirm SMPL operates the refresh (vs customer uploads) and the default cadence included in each pricing tier.

---

## 5. Open items to confirm (short)

1. Who runs ongoing refresh, at what default cadence, and whether it is included in the tier price (see §4; `lib/billing/plans.ts` lists 1/3/5 "integrations included").
2. Multi-entity scope for NetSuite / Sage Intacct: load ERP-consolidated results only, or perform eliminations and currency translation in SMPL?
3. Whether SMPL obtains its own Maxio Advanced Billing sandbox via public signup now, independent of the partnership conversation.
