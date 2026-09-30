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

**Implication for every deal:** SMPL delivers the first load during implementation (Path A) from an API pull script or customer extracts. After go-live, the customer initiates each refresh on its own close calendar (decided 2026-09-30, see §4). There is no automated scheduler, and public copy must not claim automated or scheduled sync.

---

## 2. Per-system inventory

Legend for "Tested": **API probe** = read-only script ran against a vendor sandbox/test org and produced output; **Export stub** = sample mapped to SMPL CSV headers (not loaded into a customer org); **None** = no system-specific testing.

### Maxio (billing / ARR / rev-rec)

- **Existing:** `backend/scripts/maxio_sandbox_probe.py` and `maxio_export_to_smpl.py` (Advanced Billing REST, Basic auth `api_key:x`, pagination; customers/subscriptions/invoices/products/`mrr_movements` → Stripe-compatible compact headers). Entity and field maps documented in `INTEGRATIONS_SETUP.md` §Maxio.
- **Tested:** None against live data. Scaffold scripts exist but have never run with a real site + key (no `backend/tmp/maxio_sandbox_probe_summary.json`); no live pull has been performed. learn.maxio catalog access only (`backend/tmp/learn_maxio_catalog_*.json`). The earlier blog line saying extract pipelines were "validated against ... Maxio developer environments" was inaccurate for Maxio and was removed from the buyer's guide in the 2026-09-29/30 release.
- **SMPL Maxio test account:** Deferred by Matt (2026-09-30). Not a blocker for the offer or for this release.
- **Remaining work:** When the test account is created: Advanced Billing test site + read API key (self-serve sandbox signup is public: app.chargify.com/signup/maxio-billing-sandbox, so this does not depend on the partnership conversation); run probe; validate field map against live JSON; payments + fuller `mrr_waterfall`; Maxio Core (contracts, ASC 606 schedules, deferred revenue) access path. For a first Maxio customer before then, the same work runs against the customer's read-only key or standard exports as part of implementation.
- **Blocker?** No. Genuine limitation: Maxio Core API docs are inside Core Admin and partner/customer-gated. **Workable scope:** billing/ARR from Advanced Billing API or customer-run standard Maxio exports; deferred/recognized revenue from Core exports supplied by the customer or from the ERP.
- **Positioning guardrail:** Maxio is an exploratory partnership conversation. Public copy describes the work SMPL commits to delivering for Maxio customers; it must never claim completed Maxio testing or validation, a partnership, certification, or a "native" connector. Re-checked 2026-09-30: `/integrations/maxio` and every other public Maxio mention comply.

### NetSuite (ERP / GL)

- **Existing:** Path A "ERP export" method (saved searches / scheduled CSV to SFTP) + `gl_actuals` schema, which already carries `subsidiary`, `department`, `cost_center` (class), `vendor_*`, `currency`, `statement_category`. QBO mapping rules (§Field maps) are the template for a NetSuite account→statement map.
- **Tested:** None.
- **Remaining work:** Customer-side integration record + read-only role (token-based auth) for SuiteTalk REST/SuiteQL, or scheduled saved-search exports; account/subsidiary/department/class mapping per customer; opening balances for Budget roll-forward.
- **Blocker?** No.
- **Consolidation approach (decided by Matt, 2026-09-30):** SMPL consumes NetSuite's consolidated financial actuals, including NetSuite's currency translation and intercompany elimination adjustments; for USD-reporting customers, SMPL uses the consolidated USD results. SMPL supports reporting and planning on that ERP-consolidated foundation and does **not** recreate NetSuite's consolidation engine; NetSuite remains the system of record for consolidation. Implementation steps: (1) confirm the extraction method (SuiteQL/saved search/report export) delivers the required consolidation context (consolidated results plus entity and currency detail); (2) reconcile imported results to NetSuite's consolidated reports before sign-off. Where subsidiary reporting is needed, SMPL retains entity and currency information and scopes subsidiary selection accordingly.
- **Entity views:** Matt confirms key reports can be viewed by selected entity. The 2026-09-30 code check confirmed `gl_actuals` carries `subsidiary` and `currency`, but did not locate an entity selector in the report UI, so public copy says "subsidiary views are scoped during implementation" rather than naming a selector. Upgrade the wording once the selector is confirmed in the product.
- **Still to finalize:** multi-currency and multi-subsidiary specifics (translation source, elimination entities, entity-level vs consolidated view set) will be finalized with the first such customer.

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
- **Blocker?** No — the sandbox wait blocks SMPL's own lab work, not a customer implementation, which can run from the customer's exports.
- **Consolidation approach (decided 2026-09-30):** same as NetSuite. SMPL consumes Sage Intacct's consolidated financial actuals (including its currency translation and intercompany elimination adjustments; consolidated USD results for USD reporters), does not recreate the consolidation engine, confirms the extraction method delivers the consolidation context, and reconciles imported results to Sage Intacct's consolidated reports. Entity and currency information is retained; entity-level views are scoped during implementation. Multi-currency/multi-entity specifics finalized with the first such customer.

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
| Maxio | `/integrations/maxio` | AB API scaffold + exports | None live (no pull yet; test account deferred) | No (Core via exports) |
| NetSuite | `/integrations/netsuite` | Exports (Path A) | None | No (ERP-consolidated results; decided 2026-09-30) |
| Salesforce | `/integrations/salesforce` | OAuth + probe | DE org probe 2026-07-26 | No (history forward if absent) |
| Sage Intacct | `/integrations/sage-intacct` | Exports (Path A) | None | No (ERP-consolidated results; decided 2026-09-30) |
| Xero | `/integrations/xero` | Exports (Path A) | None | No |
| Rillet | `/integrations/rillet` | Exports (Path A) | None | No |
| Campfire | `/integrations/campfire` | Exports (Path A) | None | No |
| QuickBooks Online | hub | OAuth + probe + export | Sandbox probe + export 2026-07-24/25 | No |
| Stripe | hub | Seed + export | Test-mode export 2026-07-25 | No |
| Chargebee | hub | Probe + stub | Test-site probe 2026-07-26 | No |
| HubSpot, Recurly, HRIS/payroll | hub | Exports (Path A) | None | No |

Nothing on the public pages says a system has been tested or validated.

---

## 4. Refresh after go-live (decided 2026-09-30)

**Decision (Matt):** after go-live, the **customer initiates each data refresh**, on its own close calendar. SMPL does not know when a customer's books are closed, and close cadences differ by company. Companies that load data intra-month (for example cash reporting or deal/pipeline tracking) push that data through whenever they are ready.

There is no scheduled connector runtime, and public copy must not claim automated or scheduled sync. Loads run through the existing paths (CSV ingest, ingest API, or a Path A extract → normalize → load → tie-out). Concurrent loads for the same org are last-write-wins (no load mutex; `Maxio_Technical_Readiness_QA.md` Q5).

- **Public wording (2026-09-30):** "After go-live, your team initiates each refresh when your books close, on your own close calendar, and can load intra-month cash or pipeline data whenever you need a current view." (Salesforce page: pipeline data only.) Replaces the earlier "kept current on the refresh cadence agreed during implementation".
- **Pricing check:** `/pricing` and `lib/billing/plans.ts` mention only "N integrations included" and "CSV uploads"; nothing there conflicts with customer-initiated refresh.
- **Future item (not publicly promised):** intra-month / intra-quarter tracking reports may come later (Matt, 2026-09-30). Do not mention them in public copy until they ship.

---

## 5. Open items (short)

Resolved 2026-09-30: refresh ownership and cadence (§4); NetSuite / Sage Intacct consolidation approach (ERP-consolidated results, §2); Maxio test account (deferred, not a blocker, §2).

Still open:

1. Multi-currency and multi-subsidiary specifics for NetSuite / Sage Intacct, to be finalized with the first such customer.
2. Confirm the per-entity report selector in the product so public copy can move from "subsidiary views are scoped during implementation" to naming it.
3. Create the SMPL Maxio Advanced Billing test account when Matt un-defers it, then run the probe and record results here.
4. Intra-month / intra-quarter tracking reports (possible future product item; internal only).
