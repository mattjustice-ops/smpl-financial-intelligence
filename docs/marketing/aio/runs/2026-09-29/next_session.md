# Pick-up notes for next session (written 2026-09-29, evening)

We work one topic at a time: discuss it, decide, finish it, then move on.

## Where things stand

**Done today (local only, nothing committed or published):**
- Controlled ChatGPT rerun (46 prompts + 10 priority queries × 3 trials), corrected history for Sep 15/23/29, and the report in this folder (`comparison_report.md`, `conclusions.md`).
- `/app/ops/visibility` shows the new checkpoint data: current-state tiles, the visibility trend, and the priority-query panel.
- The dashboard not loading was fixed: its local build cache was corrupted and has been rebuilt, and the startup database deadlock is fixed in `frontend/lib/aio/schema.ts`.

**Not touched:** no website pages, blog articles, or Sanity content have been changed.

**Decisions already made:**
- Remove "We are early" wherever it appears (comparison article, FP&A platform article, lean-teams page).
- Integrations belong on one page, not a page per system.
- Plan Assurance stays off the public site unless we can show it genuinely differentiates us or strengthens our comparisons.

## Topics, in order (one per sitting)

### 1. Integrations: how we describe them
- **Why it matters:** ChatGPT's answers on NetSuite and Salesforce draw on integration listings, and we have no integrations page at all.
- **What's true today** (from `docs/INTEGRATIONS_SETUP.md`):
  - Working now: SMPL loads customers' exports for them, CSV upload, and the ingest API.
  - Read-only pulls work against test accounts for QuickBooks Online, Stripe, Chargebee and Salesforce.
  - Maxio: code written, waiting on keys from Maxio.
  - NetSuite, HubSpot, Xero, Sage Intacct, Gusto: not started.
  - No automatic, scheduled connectors yet.
- **Open point to settle together:** Matt wants native-connector wording. My recommendation is a single `/integrations` page that names every system under two labels, "Supported today, SMPL does the integration work" and "Native connector: early access," so we get the visibility without claiming a feature that doesn't exist yet.
- **One fact to confirm first:** after go-live, does SMPL refresh customer data every period, or does the customer upload it?

### 2. The comparison article (`/blog/best-fpa-software-saas-companies`)
- **The imbalance:** competitors get structured "Best fit / Core strength / Consideration" entries. SMPL gets a disclaimer-style section, and the FAQ answer to "What is the best FP&A software for SaaS?" names nine vendors but not SMPL.
- **Evidence:** ChatGPT visibly cited this article in all 3 trials of "What should I look for in an FP&A platform for SaaS?" and never named SMPL.
- **Proposed fix:** give SMPL an entry in the same format as the competitors. Add a small table using the columns buyers see on Google (core approach, best-fit stage, primary interface, who implements), with SMPL as one row.

### 3. SMPL-led implementation, stated plainly
- No public page says SMPL does the implementation. The implementation article only says SMPL is "being built around" the idea.
- Fix the article first. Then decide whether a separate page is needed.

### 4. Plan Assurance as a differentiator
- First check how Cube, Pigment, Datarails, Abacum, Runway and Jirav publicly describe plan testing, stress cases and simulation.
- Only then decide whether it goes public, and how.

### 5. Scorecard reorder (dashboard)
Lead with three counts: SMPL named as a relevant product, its capabilities described accurately, and SMPL shortlisted or recommended. Show visible and hidden citations separately, as diagnostics only. Keep Google results separate from ChatGPT answers.

## Guardrails
- No full benchmark rerun until the next scheduled evaluation.
- Log every content change with its date, so the next evaluation can be read against it.
- Don't commit the unrelated `docs/marketing/SEO_Target_Keywords_2026-08.md` edit.

---

## Update 2026-09-30: website work done, pending Matt's review

Items 1–4 above are implemented. The 2026-09-30 brief replaced two earlier decisions: integrations now get a hub plus one page per major system, and Plan Assurance is now on the public site. All of it is on local branch `seo/implementation-led-integrations`: committed, not pushed, not deployed, and not in Sanity.
- **Integrations (item 1):** superseded by the 2026-09-30 business correction. There are no "supported today / early access" labels. `/integrations` plus pages for Maxio, NetSuite, Salesforce, NetSuite + Salesforce, Sage Intacct, Xero, Rillet, and Campfire describe what SMPL delivers, with implementation led by SMPL. Refresh is worded as "on the cadence agreed during implementation". The open fact (who refreshes after go-live) is still open; see `docs/marketing/integrations_delivery_inventory.md` §4.
- **Comparison article (item 2):** SMPL entry in the same format as competitors, with a disclosure; a comparison table; the FAQ now names SMPL. This needs the Sanity publish script to go live, and that script has not been run.
- **Implementation article (item 3):** now states that SMPL leads implementation and links to `/integrations`.
- **Plan Assurance (item 4):** new `/budgeting-and-plan-assurance` page, with the simulation caveat. The competitor wording check was not done; the page makes no comparative claims.
- "We are early" has been removed everywhere. The footer "Platform" link now goes to a new public `/platform` page instead of `/app`.
- Full list of changes: `docs/marketing/aio/change_log.md`. Item 5 (scorecard reorder) has not been started.

## Update 2026-09-30 (later): approved and released

Matt answered the open points and approved publishing. Refresh after go-live is customer-initiated on the customer's own close calendar; NetSuite and Sage Intacct work from the ERP's consolidated results; the Maxio test account is deferred. The site changes were released to production and the four blog posts republished to Sanity. See the 2026-09-30 release entry in `docs/marketing/aio/change_log.md`.
