# SMPL Glossary Hub IA — Metric Literacy (not SaaSpedia clone)

**Status:** v1 build brief (Sep 2026)  
**Live URL:** https://www.smpl-ai.com/glossary  
**Related:** `SEO_Keyword_Strategy_Intent_Themes.md`, `SEO_Target_Keywords_2026-08.md`

---

## Positioning

Maxio’s SaaSpedia = billing / subscription encyclopedia.  
**SMPL glossary** = *SaaS finance metric literacy for board, close, and reconciliation* — how metrics are defined, calculated, where they break, and how they show up in the board pack.

Tagline for hub: **SaaS finance definitions finance leaders actually use in close and board.**

Do **not** race Maxio on thin “what is MRR” pages without a reporting / governance angle.

---

## Page model

| Surface | Role |
| --- | --- |
| `/glossary` | Themed hub (clusters) + A–Z index |
| `/glossary/[slug]` | Definition page (indexable only if body ≥ ~800 chars) |
| `/blog/...` pillars | Decision / comparison depth; glossary links in |
| `/book-demo` | Soft CTA on every term page |

**Term body template (required sections):**

1. **What it is** — quotable 2–3 sentence definition (AIO citation bait)  
2. **How it’s calculated** — formula / inputs / cohort rules  
3. **Where it breaks** — real SaaS failure modes (billing vs CRM, usage, multi-year, etc.)  
4. **In the board pack** — where it appears and what question it answers  
5. Related terms + related posts (internal links)

---

## Hub clusters (v1)

1. **ARR & recurring revenue** — ARR, MRR, waterfall, net new ARR, bookings, pipeline, billing ARR, CRM ARR  
2. **Retention & churn** — NRR, GRR, churn, logo churn, revenue churn, expansion, contraction  
3. **Board reporting & close** — board pack, close, MD&A, FP&A, variance analysis  
4. **Forecast & planning** — rolling forecast, cash forecast, scenario analysis, runway  
5. **Recognition & bridges** — GAAP revenue, deferred revenue  
6. **Efficiency** — CAC, LTV, burn multiple *(supporting; don’t over-invest)*

---

## Term inventory

### Expand now (indexable bodies) — existing slugs

| Slug | Priority | Pillar link |
| --- | --- | --- |
| `arr` | P0 | waterfall, board posts |
| `waterfall` | P0 | `/blog/arr-waterfall-vs-gaap-revenue` |
| `nrr` | P0 | `/blog/grr-vs-nrr` (when live) |
| `grr` | P0 | same |
| `gaap-revenue` | P0 | waterfall post |
| `deferred-revenue` | P0 | waterfall / board |
| `mrr` | P1 | ARR cluster |
| `churn` / `expansion` / `contraction` | P1 | retention cluster |
| `close` / `mda` / `fpa` / `rolling-forecast` | P1 | board cluster |
| `bookings` / `pipeline` | P1 | ARR cluster |
| `cac` / `ltv` / `burn-multiple` / `runway` | P2 | efficiency |

### New terms (v1 ship)

| Slug | Cluster | Why |
| --- | --- | --- |
| `board-pack` | board-close | P0 buyer language; pairs with board blog |
| `net-new-arr` | arr-recurring | Waterfall / growth literacy |
| `billing-arr` | arr-recurring | Feeds planned billing-vs-CRM pillar |
| `crm-arr` | arr-recurring | Same |
| `variance-analysis` | board-close | MD&A / AI commentary bridge |
| `scenario-analysis` | forecast | P1 SEO theme |
| `cash-forecast` | forecast | P1 SEO theme |
| `logo-churn` | retention | Long-tail + AIO |
| `revenue-churn` | retention | Long-tail + AIO |

### Keep if already in Studio (don’t delete)

`fisod`, `segregation-of-duties` — product trust language; leave as-is unless expanding later.

### Explicitly out of scope (Maxio-owned / wrong ICP)

Captive product pricing, billing cycles how-to, pure rev-rec textbook encyclopedia, QuickBooks setup, AP automation.

---

## SEO / AIO rules

- Short definition ≤ 320 chars (meta description).  
- Body plain text ≥ **800 chars** before indexing (`GLOSSARY_INDEXABLE_BODY_CHARS`).  
- One crisp quotable line early: “X is …” / “X is not …”  
- Internal links: glossary ↔ glossary ↔ live pillars.  
- Hub H1 stays “Glossary” (or “SaaS Finance Glossary”); clusters are H2s.  
- Do not rename URL to `/saaspedia` — keep `/glossary` equity.

---

## Ship sequence

1. IA + expanded content seed + publish script *(this doc + code)*  
2. Upsert Sanity terms (expand stubs → indexable)  
3. Hub UI: themed clusters above A–Z  
4. GSC: request indexing for `/glossary` + P0 slugs  
5. Next content: finish GRR vs NRR pillar; brief billing vs CRM ARR using new glossary terms  

---

## Success signals (30–60 days)

- Glossary term pages move from `noindex` → indexed  
- Impressions for `nrr`, `grr`, `arr waterfall`, `board pack`, `billing arr` / `crm arr`  
- Click paths glossary → pillar → `/book-demo` in analytics  
- LLM / AI Overview citations of short definitions (manual spot-checks)
