# SEO Target Keywords — August 2026

**Purpose:** Short working tracker for SMPL.ai buyer-intent SEO after the category SEO advisory.  
**Companion file:** `docs/marketing/SEO_Target_Keywords_2026-08.xlsx`  
**Strategy (themes + ads/SEO channel split):** `docs/marketing/SEO_Keyword_Strategy_Intent_Themes.md` (+ `.xlsx`) — use that for intent-theme review; keep this file for per-query → URL execution.  
**Related history:** `docs/marketing/SEO_Keywords_Before_After_2026-08.xlsx` (metadata before/after reconstruction — not this tracker)

## North-star rule

Rank for **buyer queries** finance leaders type when they have a metric, board, or reconciliation problem.  
Do **not** treat brand slogans as the SEO north star.

| Query | Status |
| --- | --- |
| AI operating system for SaaS finance | **Brand positioning, not SEO north star** — keep the thought-leadership post; do not optimize the site around this as the primary ranking wager |
| Finance OS / finance operating system | **Brand positioning, not SEO north star** — category language for narrative; secondary to concrete SaaS FP&A / board / ARR queries |

## Buyer-query tracker (8–10)

| Query | Intent | Target URL | Priority | Notes |
| --- | --- | --- | --- | --- |
| NRR vs GRR | Informational → board literacy | `/blog/grr-vs-nrr` *(draft — see `docs/marketing/drafts/grr-vs-nrr.md`)* | P0 | First pillar move. Support with `/glossary/nrr` and `/glossary/grr` |
| ARR waterfall | Informational / how-to | `/blog/arr-waterfall-vs-gaap-revenue` | P0 | Live. Pair with `/glossary/waterfall` |
| ARR waterfall vs GAAP revenue | Informational / comparison | `/blog/arr-waterfall-vs-gaap-revenue` | P0 | Live cornerstone. Strong internal-link hub |
| ARR methodology / ARR governance | Informational / policy | `/blog/arr-governance` | P0 | Live (Aug 3). Link from GRR/NRR + waterfall posts |
| SaaS board reporting / board pack | Problem / category | `/blog/saas-board-reporting-arr-cash-pl` | P0 | Live. Also supports homepage “board reporting” theme |
| Billing vs CRM ARR | Problem / reconciliation | `/blog/billing-vs-crm-arr` *(planned)* | P1 | High buyer pain; no dedicated post yet. Interim: link from waterfall + trust posts |
| ARR sources / where ARR comes from | Informational | `/blog/arr-waterfall-vs-gaap-revenue` *(interim)* → planned `/blog/arr-sources` | P1 | Often searched as “ARR from billing vs CRM.” Clarify source-of-truth in copy |
| SaaS cash forecast | Informational / how-to | `/blog/saas-cash-forecast` *(planned)* | P1 | Bridge from live board post (ARR–cash–P&L). Soft CTA to demo |
| SaaS board pack | Problem / template-adjacent | `/blog/saas-board-reporting-arr-cash-pl` | P1 | Close cousin of “board reporting”; watch GSC for pack vs reporting split |
| Net revenue retention / NRR SaaS | Informational | `/glossary/nrr` + `/blog/grr-vs-nrr` | P1 | Glossary for definition; pillar for board context |
| Gross revenue retention / GRR SaaS | Informational | `/glossary/grr` + `/blog/grr-vs-nrr` | P1 | Same pattern as NRR |

### Slogan / brand queries (tracked, deprioritized)

| Query | Intent | Target URL | Priority | Notes |
| --- | --- | --- | --- | --- |
| AI operating system for SaaS finance | Brand / category narrative | `/blog/ai-operating-system-for-saas-finance` | Brand only | **Brand positioning, not SEO north star** |
| Finance OS vs FP&A software | Brand / category narrative | `/blog/finance-os-vs-fpa-software` | Brand only | **Brand positioning, not SEO north star** |

## Google Search Console checklist

Use this after the GRR vs NRR post is published (and for the live URLs above).

1. **Confirm indexing**
   - [ ] `site:smpl-ai.com/blog/arr-waterfall-vs-gaap-revenue`
   - [ ] `site:smpl-ai.com/blog/saas-board-reporting-arr-cash-pl`
   - [ ] `site:smpl-ai.com/glossary/nrr` and `…/glossary/grr`
   - [ ] After publish: `site:smpl-ai.com/blog/grr-vs-nrr`
   - [ ] URL Inspection → “Request indexing” for new/updated URLs if not discovered within ~48h
2. **Track impressions for these terms**
   - [ ] Performance → New filter → Queries containing: `nrr`, `grr`, `arr waterfall`, `board reporting`, `board pack`, `cash forecast`, `billing` + `arr`, `crm` + `arr`
   - [ ] Save a monthly screenshot or export (Queries + Pages) for the rows in this tracker
   - [ ] Watch **page** performance for `/blog/grr-vs-nrr` separately from glossary pages (definition vs decision intent)
3. **Hygiene**
   - [ ] Canonicals unique per URL (no duplicate-without-canonical)
   - [ ] Sitemap includes blog + glossary slugs after publish
   - [ ] Noindex still on `/login` and sample/board surfaces that should not rank

## Next content moves (after this tracker)

1. Publish GRR vs NRR pillar when Matt approves the draft.  
2. Brief **billing vs CRM ARR** as the next P1 post.  
3. Brief **SaaS cash forecast** tied to the live ARR–cash–P&L board post.
