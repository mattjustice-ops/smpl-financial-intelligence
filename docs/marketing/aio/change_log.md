# AIO / SEO content change log

Read the next scheduled AIO evaluation against these entries. No benchmark was rerun for these changes.

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
