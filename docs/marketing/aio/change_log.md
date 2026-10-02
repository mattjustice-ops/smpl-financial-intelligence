# AIO / SEO content change log

Read the next scheduled AIO evaluation against these entries. No benchmark was rerun for these changes.

---

## 2026-10-02 — Billing portal requires sign-in; server-side API calls send the internal key

This entry changes product behavior (billing and quote request handling), not marketing copy. No benchmark was run for it.

- **Gap:** `POST /api/billing/create-portal-session` had no sign-in check. Anyone could get a Stripe billing portal link (invoices, payment method, cancellation) for any organization by posting its `organization_id`, its billing email or a `stripe_customer_id`.
- **Fixed:** the route now requires a signed-in session and an `organization_id` the user belongs to (403 otherwise), and resolves the Stripe customer server-side. Email and client-supplied customer ids are no longer accepted. The billing page sends only the organization id.
- **Fixed:** the quote form (submit and HubSpot id update), the checkout rate-limit check and the portal account lookup now call the API through `callBillingBackend`, which sends the internal key. No behavior change today; this is required before the API refuses unkeyed requests.
- **Checks:** `tsc --noEmit` and `next lint` on changed files are clean.

---

## 2026-10-02 — Browser API calls go through the authenticated proxy

This entry changes product behavior (request routing), not marketing copy. No benchmark was run for it.

- **Gap:** `next.config.js` rewrote `/api/v1/*` straight to Railway. Next applies rewrites before dynamic routes, so browser calls skipped the session and membership check in `app/api/v1/[...path]`. Board live data and exports also called Railway directly using `NEXT_PUBLIC_API_URL`.
- **Fixed (PR #203, 7f3a29b):** the rewrite is removed. Board live data and exports, billing and three unused dashboards use the same-origin proxy. The proxy passes binary bodies and `Content-Disposition` through, and allows 300s.
- **Verified on production (2026-10-02):** an anonymous `GET /api/v1/predictive-planning/constraints` on www.smpl-ai.com returned 401 from the website. Matt's click-through of the Board, Budget, Forecast, billing page, the MD&A deck export and the Excel package export all returned 200 in the Railway log, and both files downloaded.
- **Not changed:** the API on Railway still answers requests with no user header and no key (for example `reporting/outlook` and `billing/account` for a known organization id returned 200). Closing that is the next release.

---

## 2026-10-01 — API only trusts a claimed user when the internal key comes with it

This entry changes product behavior (API request handling) and production configuration, not marketing copy. No benchmark was run for it.

- **Gap:** `BILLING_INTERNAL_API_KEY` was set in neither Vercel production nor Railway `sfi-api`, so `require_internal_auth_key` allowed every caller. `/auth/session-sync` returned a user's id for any email, and the API trusted `X-SFI-User-Id` from any caller. Anyone who knew a customer's email could act as that customer.
- **Fixed (configuration, 2026-10-01 ~16:35 PT):** the same random 64-character key was set in Vercel production (Secret) and Railway `sfi-api` production, and both were redeployed. Before: an unkeyed `GET /api/v1/auth/organizations/{random}/seats` returned 404. After: 401, both directly on Railway and through www.smpl-ai.com. A real sign-in afterwards returned `session-sync 200`, confirming the two values match.
- **Fixed (code):** the request middleware now rejects any request that carries `X-SFI-User-Id` without a matching `X-Billing-Internal-Key` / `X-Smpl-Internal-Key`, with 401. The key comparison is now constant-time. Requests without a user header are unaffected. With the key unset (local dev, tests) behavior is unchanged.
- **Tests:** 8 new tests in `test_internal_key_user_header.py` cover a user header with no key, a wrong key or a malformed id (401), a valid key in either header (200), requests without a user header unaffected, key-guarded routes rejecting a wrong key, and the unset-key case. The full backend suite has the same 28 pre-existing failures as `main` and no new ones.
- **Not changed:** requests with no user header still reach routes that only check membership when a user is present (`get_organization_or_404`), both through the `/api/v1/:path*` rewrite and directly on Railway. Closing that requires routing browser calls through the authenticated proxy, then requiring the key on all non-public routes.

---

## 2026-10-01 — Plan Assurance API requires a signed-in member of the organization

This entry changes product behavior (predictive-planning API and its Next.js proxy), not marketing copy. No benchmark was run for it.

- **Gap:** every `/api/v1/predictive-planning/*` route accepted anonymous requests for any `organization_id`, including `/assess`, which persists assessments. The `/api/v1/:path*` rewrite in `next.config.js` sent these calls straight to the API, without the session check the authenticated proxy applies.
- **Fixed (API):** this uses the mechanism the rest of the API uses: the signed-in user forwarded by the Next.js proxy as `X-SFI-User-Id`, plus an active-membership check (`AuthService.get_member`). No user gives 401, and a user who isn't a member of the organization gives 403. `/assess`, `/simulate`, `/mc-inputs` and `GET /assessments` check the `organization_id` they act on. `GET /assessments/{id}` checks the record's organization. `/constraints` requires a signed-in user. The version checks are unchanged.
- **Fixed (proxy):** static route handlers for `assess`, `simulate`, `mc-inputs`, `constraints` and `assessments` take precedence over the rewrite. They require a session and forward the user to the API. The Budget and Forecast engines already call these paths same-origin with cookies, so signed-in users see no change. Board reads assessments directly from the database and is unaffected.
- **Tests:** 17 new auth tests in `test_plan_assurance_auth.py` cover anonymous rejection, another organization's id, an unknown user, nothing persisted on a rejected call, and success for a member on their own organization. Existing Plan Assurance tests run as a signed-in member. `verify:plan-assurance-mc` checks that the five handlers use the authenticated proxy.
- **Not changed:** the `/api/v1/:path*` rewrite still bypasses the session check for other API areas, and the API trusts `X-SFI-User-Id` from any caller that reaches it directly.

---

## 2026-10-01 — Plan Assurance: framework doc matches what shipped; marketing page rechecked (no copy change)

This entry changes an internal product doc only. No marketing copy changed and no benchmark was run.

- **Doc:** `docs/product/SMPL_Predictive_Planning_Intelligence_Framework.md` now describes the shipped state. Budget runs its full-plan Monte Carlo in the browser on server-issued seeded inputs, with the server packet model as a labeled fallback. Forecast uses the server packet model. Only the ARR growth volatility prior is fitted from history, and current data has too few pairs for correlations. Assessments persist against the saved version. Board AI commentary cites the active forecast version's assessment. Known gaps are listed: no per-user authorization on predictive-planning routes, no server-side rebuild of a packet from a stored version, no drift alerts, and no calibrated PoA, trajectory or accuracy store.
- **Page recheck:** each concrete claim on the live `/budgeting-and-plan-assurance` page was checked against the code. That covers the 15 constraints and their list, pass/warn/fail/advisory with skipped never counted as a pass, the What Has to Be True groups, the named stress cases, and 1,000 draws of four annual assumptions, each sampled once per draw and run through the full monthly model, with monthly P10–P90 cash bands, the cash low point and tightest month, and any-month versus December floor breaches. It also covers "stress frequency, not a calibrated probability of attainment", the assumption ranges shown on screen, and AI not computing figures. All are accurate, so the copy is unchanged. The page makes no claim about fitted priors, reproducibility or Board citation.

---

## 2026-10-01 — Plan Assurance: assessments persist against the saved version; Board cites the active forecast's assessment

This entry changes product behavior (Budget and Forecast engines, predictive-planning API, Board payload), not marketing copy. No benchmark was run for it.

- **Gap:** Forecast never persisted assessments, because the version id it sent was never set. Budget persisted against the last saved version id even after the plan was edited, so an assessment of an unsaved plan could be filed under a saved version. The server accepted any version id. Board AI commentary cited the latest assessment for the organization, whatever plan or version it described.
- **Fixed (persistence):** saving or promoting a Budget or Forecast version assesses that exact plan against the new version id, with a simulation of that plan. Budget reruns its scenario suite first if it is stale. Each engine fingerprints the plan as saved. Later assessments are filed under the version only while the plan still matches that fingerprint. Once the plan is edited, assessments are transient until it is saved again. Re-assessing the same version with the same simulation does not write a duplicate row. The save confirmation says when the assessment was saved against the version.
- **Fixed (server):** `/assess` persists only if the version exists and belongs to the organization. Otherwise it returns the assessment with a "Not persisted: …" note. The plan fingerprint is recorded with the assessment.
- **Fixed (Board):** Board figures come from the organization's active final forecast version. Board AI commentary (risks and board actions) now cites only the latest persisted assessment for that version, and records which version it describes. The Board platform payload exposes the same assessment as `plan_assurance`. If the active version has no persisted assessment, nothing is cited.
- **Tests:** 6 new backend tests in `test_plan_assurance_version_citation.py`. They cover Forecast and Budget assessments persisting against their versions, unknown or other-organization versions being rejected, Board citing the active version's latest assessment while ignoring older, draft and unversioned ones, and no citation without an assessment or a final forecast. The `verify:plan-assurance-mc` script now also checks the version binding, deduplication, and the Forecast canonical copy.
- **Not claimed:** Board does not fall back to a budget assessment. The deterministic Board commentary text does not cite Plan Assurance; only the AI-regenerated risks and board-actions slides do. Predictive-planning routes still have no per-user authorization check of their own.

---

## 2026-10-01 — Plan Assurance: server-issued inputs drive the Budget full-plan Monte Carlo

This entry changes product behavior (Budget and Forecast engines, predictive-planning API), not marketing copy. No benchmark was run for it.

- **Gap:** Budget's on-screen Monte Carlo always used hard-coded default priors and unseeded random draws. The method card showed the server's priors, which for a live customer could be the fitted ARR growth prior. The chart, the card and the saved assessment could disagree. The server packet model also ran on every scenario run, even though Budget displayed the browser result.
- **Fixed:** a new `POST /api/v1/predictive-planning/mc-inputs` issues the seed, lever priors (fitted from company history where possible) and lever correlations, with an inputs fingerprint. Budget runs its full-plan formula-graph Monte Carlo in the browser with exactly those inputs, using a shared seeded sampler (`/shared/smpl-plan-mc.js`). The same seed and inputs on the same plan give the same results.
- **Card, chart and saved record agree:** the summary sent to `/assess` records the priors, seed, correlations, engine, sampler and inputs fingerprint actually used. `/assess` checks them against what the server issues for that history. The method card shows the priors the simulation used. If they differ from the server's fit, the card says so and claims nothing as fitted. Persisted assessments store the same values and the actual seed.
- **Fallback:** the server packet model now runs only when the full-plan engine cannot run. The banner, narrative and method card label it as the fallback. If the server cannot issue inputs, the browser uses default priors and the card says the server was unavailable.
- **Forecast:** unchanged behavior. It still uses the server packet model as its primary engine. Its assessment summary now also records seed, correlations and engine.
- **Tests:** 10 new backend tests in `test_plan_assurance_mc_inputs.py` cover issued inputs, card/simulation prior agreement, mismatch labeling, fallback labeling, a tampered fingerprint, and the persisted record. A new `verify:plan-assurance-mc` script checks sampler reproducibility, correlation handling, and the Budget wiring.
- **Not claimed:** the full-plan Monte Carlo runs in the browser, not on the server. "Reproducible" means the same seed and recorded inputs on the same plan reproduce the same results. Breach rates are stress frequencies under stated priors, not a probability of attainment.

---

## 2026-10-01 — Plan Assurance: history priors activate; correlations applied in the server Monte Carlo

This entry changes product behavior (Budget and Forecast engines, predictive-planning API), not marketing copy. No benchmark was run for it. Marketing copy is reviewed after the remaining Plan Assurance fixes.

- **Gap:** Budget sent three year-end ARR values (two synthetic backcasts and the plan's own December ARR) as "history". The prior fit needs at least three growth rates, so it always fell back to defaults. Forecast sent no history. Correlations were accepted by the API but never used in the simulation.
- **Fixed (history):** Budget and Forecast now send closed-month ending ARR from the outlook (December 2025 through the close month; seven month-end values at the June 2026 close), tagged `warehouse` when the live outlook is loaded and `demo_seed` otherwise. The server fits the ARR growth volatility prior from monthly growth (sd of monthly growth × √12) when there are at least three growth rates from company data. Demo or backcast data is never fitted.
- **Not fitted:** cost per lead, sales attrition, and pipeline coverage keep their default priors. There is no real monthly history for them in the payload yet. The method card says which priors were fitted and which kept defaults (`history_partial`), with the observation count, month span, and source.
- **Fixed (correlations):** the server Monte Carlo draws the four levers jointly through a Cholesky factor when correlations are supplied, or fitted from at least 12 paired history observations. Inconsistent sets are shrunk until valid, and the method notes say so. With no correlations the draws are independent, and they match the previous results exactly. The method card says "Independent draws" when that applies, which is the case for all current customer and demo data.
- **Tests:** 11 new backend tests. They cover priors activating from monthly history, the minimum-data and demo fallbacks, correlation fitting and validation, and negative versus independent versus positive correlation changing the ARR spread and miss rate.
- **Not claimed:** company-specific behavior for any lever other than ARR growth volatility, or correlated draws on current data. Breach rates are stress frequencies under these priors, not a probability of attainment.

---

## 2026-10-01 — Blog index title lengthened (Bing SEO check)

This entry changes page metadata only, not visible page content. No benchmark was run for it.

- **Trigger:** Bing Webmaster Tools URL Inspection for `/blog` (2026-10-01) flagged "Title too short". Bing wants at least 15 characters; the title was `Blog | SMPL.ai` (14).
- **Fixed:** `/blog` title is now `SaaS FP&A & Board Reporting Blog | SMPL.ai` (42). og:title and twitter:title use the same constant. The H1, body copy, description, and canonical are unchanged.
- **Audit (production, all 93 sitemap URLs, entities decoded):** only `/blog` was under 15 characters. Only `/blog/saas-cash-forecasting` is over 70 (77); it is a Sanity title and is not changed here.
- No IndexNow submission for this change. Matt will request indexing in Bing URL Inspection.

---

## 2026-10-01 — Meta descriptions shortened to 155 characters or fewer (Bing SEO check)

This entry changes page metadata only, not visible page content. No benchmark was run for it.

- **Trigger:** Bing Webmaster Tools URL Inspection for the homepage (2026-10-01) flagged "Meta Description too long or too short". Bing wants 25–160 characters; the homepage had 169.
- **Audit (production, all 93 sitemap URLs, entities decoded):** no missing or duplicate descriptions. Code-managed pages over 160: homepage, `/fpa-software-for-saas`, `/fpa-software-for-lean-finance-teams`, `/saas-board-reporting`, `/arr-revenue-cash-headcount`, `/budgeting-and-plan-assurance`, `/glossary`, and the NetSuite, Salesforce, NetSuite + Salesforce, and Sage Intacct integration pages. At 156–160: `/integrations`, Maxio, Xero, Rillet, `/about`.
- **Fixed:** all 16 now 150–155 characters, with minimal wording changes. Homepage `SITE_DESCRIPTION` goes from 169 to 154; it keeps SaaS FP&A, ARR, pipeline, cash, financial statements, one governed model for close, and board-ready/traceable to source. The homepage title, H1, and body copy are unchanged. og:description and twitter:description use the same constants.
- **Not fixed here (Sanity):** 33 blog posts have descriptions over 160 characters, plus 4 more at 156–160. They need SEO description edits in Sanity and will be handled separately.
- After deploy, the changed URLs are resubmitted through IndexNow. The HTTP response is recorded in the release report.

---

## 2026-10-01 — Share image restored on marketing pages (Bing blank logo check)

This entry changes page metadata only, not visible page content. No benchmark was run for it.

- **Trigger:** Matt saw a blank logo next to SMPL.ai on Bing. Site-side check on production (2026-10-01, also fetched as Bingbot): `/favicon.ico` 200 `image/vnd.microsoft.icon`, multi-size 16/32/48, opaque teal brand mark; the 48/96/512 PNG icons, `/apple-touch-icon.png`, and the Organization JSON-LD `logo` (`/brand/icon-512.png`, 512×512) all return 200; apex redirects to www with a 308; robots.txt does not block icon paths. The favicon and logo were already correct. Bing's result for `smpl.ai` still showed the old homepage description, so Bing had not recrawled the current homepage or favicon. Bing Webmaster Tools was only set up on 2026-09-30.
- **Gap found and fixed:** no marketing page served `og:image` or `twitter:image`. The root layout sets the 1200×630 `/brand/og-image.png`, but each page that sets its own `openGraph` replaces the root object entirely in Next.js, which dropped the image. Bing (result thumbnails), LinkedIn, and other link previews use `og:image`. Added `DEFAULT_OG_IMAGE` in `frontend/lib/site.ts` and passed it from the homepage, the blog post fallback (used when a post has no main image), and 23 other marketing pages. Those pages also now use `twitter:card` `summary_large_image`, matching the root. `/progress` and the login pages are disallowed in robots.txt and left unchanged.
- After deploy, the homepage is resubmitted through IndexNow. The HTTP response is recorded in the release report.

---

## 2026-09-30 — IndexNow set up; 19 URLs submitted to Bing / IndexNow

This entry changes crawl notification only, not page content. No benchmark was run for it.

- Added an IndexNow key file at the site root (`frontend/public/<key>.txt`, content equals the filename) and `frontend/scripts/indexnow-submit.mjs`, which POSTs a URL list to `https://api.indexnow.org/indexnow`.
- After this release deploys, 19 URLs are submitted in one request (all checked 200 on production on 2026-09-30 before submission). The HTTP response is recorded in the release report.
  - **New (11):** `/integrations`, `/integrations/netsuite`, `/integrations/salesforce`, `/integrations/maxio`, `/integrations/netsuite-salesforce`, `/integrations/sage-intacct`, `/integrations/xero`, `/integrations/rillet`, `/integrations/campfire`, `/platform`, `/budgeting-and-plan-assurance`.
  - **Updated (8):** `/blog/best-fpa-software-saas-companies`, `/blog/fpa-software-implementation`, `/blog/fpa-platform-saas`, `/blog/billing-vs-crm-arr`, `/fpa-software-for-saas`, `/fpa-software-for-lean-finance-teams`, `/saas-board-reporting`, `/arr-revenue-cash-headcount`.
- IndexNow notifies Bing, Yandex, Seznam, Naver and others. It does not notify Google.

---

## 2026-09-30 — Release: AIO visibility dashboard (buyer-consideration scorecard)

This entry changes how visibility is measured and displayed, not the site. No new benchmark was run for it.

**Dashboard (PR [#188](https://github.com/mattjustice-ops/smpl-financial-intelligence/pull/188), merge `faea42a`, deployed to production):**

- `/app/ops/visibility` now leads with a buyer-consideration scorecard of three headline cards: **named as a product** (SMPL listed, shortlisted, recommended, or top pick as a vendor option), **capabilities accurately described** (shows "Not yet scored" until a manual capability checklist review is done; no number is guessed), and **shortlisted or better**. Counts come from the answer text only.
- Citations are reported separately as visible (SMPL source shown on screen) or hidden-only (SMPL appears only behind a "+N" sources button). Hidden-only citations are diagnostic and never raise a headline count.
- The old composite scores are removed.
- Checkpoint history and trend: every full 46-query run is re-scored with the current scorer so checkpoints compare like for like. The Sep 29 priority queries show 3 trials each.
- Capture v2 scripts (`frontend/scripts/aio/`) record the prose text, citation labels, and hidden "+N" sources, so citation visibility is known for new runs. Older checkpoints were captured without hidden sources, so their citation visibility is shown as unknown.

**Production data copy (read from the local store, written to production Neon, 2026-09-30):** production had no AIO answers before this (0 batches, 0 answers). After: 48 batches, 204 answers.

| Checkpoint | Batches | Answers |
|---|---|---|
| Baseline bulk, 2026-09-15 | 44 | 46 |
| Full 46, 2026-09-23 | 1 | 46 |
| Day-14 full 46, 2026-09-29 | 1 | 46 |
| Full 46, 2026-09-29 controlled rerun (v2) | 1 | 46 |
| Priority repeats, 2026-09-29 controlled rerun (v2) | 1 | 20 |

The `capture_json` column was added to `aio_manual_audits` in production (66 answers carry v2 capture data). Row ids and timestamps match the local store exactly.

**Headline counts under the new rules (ChatGPT, latest answer per query):**

| Checkpoint | Named as product | Shortlisted or better | SMPL citations |
|---|---|---|---|
| 2026-09-15 baseline | 1 | 1 | 1 (visibility unknown) |
| 2026-09-23 | 1 | 1 | 1 (visibility unknown) |
| 2026-09-29 day-14 | 0 | 0 | 1 (visibility unknown) |
| 2026-09-29 controlled rerun (v2) | 1 | 1 | 1 visible, plus 2 hidden-only (diagnostic) |

**Do not read the citation figure as a drop.** The Sep 29 v2 rerun has **1** visible SMPL citation under the new rules. The old rules reported **3** for the same answers because they counted the 2 hidden-only "+N" sources. The answers did not change; the counting rule did. Priority queries: 10 queries × 3 trials.

**Follow-up (ordering fix, PR [#189](https://github.com/mattjustice-ops/smpl-financial-intelligence/pull/189)):** the priority-query list and the 15 "recent gaps" could appear in a different order, or with different gaps listed, depending on the order the database returned rows (local and production differed). Audit rows now load in a fixed order (captured time, then id). The latest answer per query breaks ties on id. Priority queries follow the fixed list in `runs/2026-09-29/benchmark_design.json`. Recent gaps show the most recently captured first, with query id as the tie-breaker. Counts are unchanged, and local and production now render identical lists. `frontend/tsconfig.tsbuildinfo`, a TypeScript build cache, is no longer tracked in git.

---

## 2026-09-30 — Release: founder answers applied, site deployed, four posts republished

**What was published:** everything in the entry below (the integrations hub and 8 system pages, `/platform`, `/budgeting-and-plan-assurance`, the changed solution pages, header/footer, sitemap, robots.txt), plus the edits in this entry. Released from `seo/implementation-led-integrations` by pull request to `main`, which triggers the Vercel production deploy. The four blog posts were then republished to Sanity from seed with `frontend/scripts/publish-sep30-integrations-refresh.mjs`, which patches only title, excerpt, SEO title/description, and body on those four documents (slug, publishedAt, author, and categories unchanged; no other drafts or posts touched). Founder approved publishing on 2026-09-30.

**Edits applied from Matt's answers (2026-09-30):**

| Topic | Before → after | Where |
|---|---|---|
| Refresh ownership and cadence | "Reporting data is kept current on the refresh cadence/arrangement agreed during implementation" → "After go-live, your team initiates each refresh when your books close, on your own close calendar, and can load intra-month cash or pipeline data whenever you need a current view." Implementation step renamed "Run on your reporting cadence" → "Refresh on your close calendar". Hub "Who does what" now lists refresh under "Your team provides". No automated/scheduled sync claimed; possible future intra-month tracking reports recorded internally only. | `/integrations` (section, ownership, FAQ), all 8 system pages (step + FAQ; Salesforce page says pipeline data only), `/fpa-software-for-lean-finance-teams` FAQ, `best-fpa-software-saas-companies` SMPL entry |
| NetSuite / Sage Intacct consolidation | No statement (Sage Intacct: "entity structure is mapped" with "entity-level and total reporting") → SMPL uses the ERP's consolidated financial actuals, including its currency translation and intercompany elimination adjustments (consolidated USD results for USD reporters); the ERP remains the system of record for consolidation and SMPL builds reporting and planning on that foundation rather than recreating the consolidation engine. Implementation steps now confirm the extraction method delivers the consolidation context and reconcile imported results to the ERP's consolidated reports. Entity and currency information retained; subsidiary views "scoped during implementation" (a per-entity selector could not be confirmed in code, so it is not named). | `/integrations/netsuite` (new workflow item, steps, new FAQ), `/integrations/sage-intacct` (workflow item, steps, new FAQ, illustrative example now traces the variance through ledger lines), `/integrations/netsuite-salesforce` (steps, new FAQ), `/integrations` (section + new multi-entity FAQ), hub cards for NetSuite and Sage Intacct, `best-fpa-software-saas-companies` SMPL entry |
| Xero multiple organisations | "reporting structure for entity-level and combined views is agreed" (implied SMPL consolidates) → organisation-level views scoped; combined views come from consolidated results the customer already prepares, reconciled by SMPL; SMPL does not recreate the consolidation | `/integrations/xero` FAQ |
| Maxio | Re-checked: public copy describes committed delivery work only; no testing, validation, partnership, certification, or native-connector claim. The previously live buyer's guide line "Extract pipelines have been built and validated against … Maxio developer environments" is removed by this republish. SMPL Maxio test account deferred (not a blocker). | `/integrations/maxio`, all Maxio mentions; inventory §2 |

**Leftover-phrasing sweep (public pages + the four posts):** no remaining "agreed during implementation" (refresh), "refresh cadence", "We are early", "not generally available", "before you shortlist", "native connector", Maxio "partner"/"certified"/"validated", or any claim that SMPL performs consolidation. Nothing had to be isolated or removed.

**Internal:** `docs/marketing/integrations_delivery_inventory.md` §2 (Maxio, NetSuite, Sage Intacct), §3, §4, §5 updated with these decisions and the remaining open items.

---

## 2026-09-30 — Implementation-led integrations, capability underselling, comparison balance

**Branch:** `seo/implementation-led-integrations` (local; not pushed or deployed). Blog changes are in seed markdown only and are **not yet in Sanity**. They reach production only when the relevant publish script is run, which has not been done.

**Governing correction:** An unfinished packaged connector no longer reads as "SMPL can't serve you." Public copy now describes the outcomes SMPL delivers and states that SMPL leads implementation (data integration, mapping, configuration, and financial validation). The delivery arrangement is explained once per page: SMPL connects with read-only access or works from structured extracts, and data is kept current on the refresh cadence agreed during implementation. "We are early" is removed everywhere (founder decision).

### New pages

| Page | Target buyer intent | Before → after |
|---|---|---|
| `/integrations` | "FP&A software integrations", "does [tool] integrate with NetSuite/Salesforce/Maxio", "who does the implementation" | No page → hub covering how SMPL connects systems, 8 system pages, lighter systems (QuickBooks Online, HubSpot, Stripe, Chargebee, Recurly, HRIS/payroll, Snowflake/file delivery), who-does-what, trademark/no-endorsement note, FAQ + ItemList JSON-LD |
| `/integrations/maxio` | "FP&A for Maxio customers", "Maxio planning/forecasting software" | No page → billing/ARR actuals and rev-rec sub-ledger between CRM and ERP; ARR waterfall, deferred revenue, cash timing, budget vs billed actuals; SMPL-led implementation steps |
| `/integrations/netsuite` | "NetSuite FP&A software", "NetSuite reporting and planning for SaaS" | No page → GL, subsidiaries, departments, and classes for the three statements and management P&L; budget vs actual; cash bridge to GL |
| `/integrations/salesforce` | "Salesforce revenue forecasting", "pipeline to revenue forecast FP&A" | No page → opportunities → pipeline waterfall, bookings coverage, revenue forecast, GTM capacity; CRM vs billing ARR bridge |
| `/integrations/netsuite-salesforce` | "forecast revenue with NetSuite and Salesforce" | No page → customer/product matching across CRM and ledger; pipeline → bookings → ARR → revenue → cash chain |
| `/integrations/sage-intacct` | "Sage Intacct FP&A / planning software" | No page → dimensional ledger (department, location, class) and multi-entity structure; FAQ clarifies the page covers Sage Intacct, not all Sage products |
| `/integrations/xero` | "Xero FP&A / SaaS metrics / cash planning" | No page → tracking categories, bank-based cash position, ARR from billing next to Xero revenue |
| `/integrations/rillet` | "FP&A for Rillet customers" | No page → ledger plus revenue recognition → contract-based revenue forecast |
| `/integrations/campfire` | "FP&A for Campfire customers" | No page → close-to-board handoff, opening balances for the plan, Plan Assurance |
| `/budgeting-and-plan-assurance` | "SaaS budgeting software", "three-statement budget", "stress test operating plan", "Monte Carlo cash forecast" | Zero public mention → driver-based budget across IS/BS/CF, version lock, validation vs feasibility, 15 constraints, named stress cases, 1,000-draw cash-path simulation with the "stress frequency under stated priors, not calibrated probability" caveat, AI-explains-never-computes |
| `/platform` | "what is SMPL.ai", product overview; replaces auth-walled `/app` as the "Platform" destination | Footer "Platform" linked to `/app` (login redirect) → public overview of all capabilities, the trust model, and implementation |

### Changed pages

| Page | Target buyer intent | Before → after |
|---|---|---|
| `/fpa-software-for-saas` | "FP&A software for SaaS" (the query where ChatGPT recommends SMPL; connected operating-model positioning preserved) | "Who it is for" narrowed to 2–5-person teams → growing SaaS businesses with multi-system data and more demanding reporting and planning needs, covering smaller and established Finance teams; added Plan Assurance capability, three-statement budgeting, checked AI commentary, an "Implementation led by SMPL" section with links to integrations |
| `/fpa-software-for-lean-finance-teams` | "FP&A for small/lean finance teams" | "Managed, always-on connectors are in active development…", "ask us where that work stands before you shortlist. We are early" → implementation-led description; FAQ explains the connection method once; added budget + Plan Assurance; "two to five people" removed from meta and lead |
| `/saas-board-reporting` | "SaaS board reporting software", "AI variance commentary" | Commentary "grounded" only → describes claim verification (figures matched, causes checked against drivers, unsupported claims flagged or removed); close validation; new "Reporting validation and Plan Assurance answer different questions" and "Implementation led by SMPL" sections; new FAQ |
| `/arr-revenue-cash-headcount` | "ARR, revenue, cash and headcount in one model" | Added budget/Plan Assurance model item and SMPL-led implementation sentence; related links |
| Shared solution cards (`SolutionPage.tsx`) | Internal linking | Lean card "two to five people" → capacity-based wording; added Budgeting & Plan Assurance and Integrations cards |
| Header / footer | Crawl paths | Header "Platform" `/#modules` → `/platform`; Integrations added to Resources and mobile row; footer "Platform" `/app` → `/platform`, plus Budgeting & Plan Assurance and Integrations links |
| `robots.txt` | Crawl hygiene | Added `Disallow: /app$` (exact `/app`, which redirects to login) and `/budget-engine` (auth route) |
| `sitemap.ts` | Discovery | Added `/platform`, `/budgeting-and-plan-assurance`, `/integrations` and 8 system pages; bumped lastmod on edited pages |

### Blog seed markdown (not yet published to Sanity)

| Article | Target buyer intent | Before → after |
|---|---|---|
| `best-fpa-software-saas-companies` | "best FP&A software for SaaS" (ChatGPT cited it 3/3 times without naming SMPL) | "For transparency, since this is our site" + connectivity caveat + "We are early" → SMPL entry in the same Best fit / Core strength / Working model / Consideration format with a clear "this is our product" disclosure; new comparison table (Platform / Core approach / Best-fit stage / Primary interface / Implementation ownership) with SMPL as one row; FAQ now names SMPL in its category with disclosure |
| `fpa-software-implementation` | "FP&A implementation time", "who implements FP&A software" | "the principle SMPL.ai is being built around" → states plainly that SMPL leads implementation and what the customer supplies; "months to weeks" framed as a design objective only; links to `/integrations` |
| `fpa-platform-saas` | "FP&A platform" | "We are early…" removed → implementation-led description, budgeting and Plan Assurance, link to `/integrations` |
| `billing-vs-crm-arr` | "billing ARR vs CRM ARR" | Added one sentence on SMPL-led integration linking `/integrations/maxio` and `/integrations/salesforce` |

### What to watch in the next evaluation

- Whether ChatGPT and Google answers to "best FP&A software for SaaS" and "what to look for in an FP&A platform" start naming SMPL. The comparison article only changes once it is republished to Sanity.
- Whether system-specific prompts ("FP&A for Maxio / NetSuite / Salesforce users") surface the new integration pages.
- Whether "FP&A software for SaaS" still recommends SMPL. Connected operating-model wording on that page and the homepage was left intact.
- Whether answers describe Plan Assurance and SMPL-led implementation accurately, including the simulation caveat.
