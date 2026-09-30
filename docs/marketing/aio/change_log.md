# AIO / SEO content change log

Read the next scheduled AIO evaluation against these entries. No benchmark was rerun for these changes.

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
