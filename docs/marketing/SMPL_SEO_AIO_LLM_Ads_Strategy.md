# SMPL.ai — SEO · AIO · LLM (MLO) · Google Ads Strategy

**Audience:** Matt (founder working doc)  
**As of:** 2026-08-12  
**Tone:** Board-light / MD&A preference — buyer problems, not slogans  
**Honesty rules:** No invented search volumes. No SOC 2 *certified* claims (Type I readiness only). Ads conversion numbers are noisy until form tracking is real.

---

## 1. Purpose / how to use

This is the **one place** to see SEO, AIO/LLM optimization (MLO), and paid search together — plus where the messy source files live.

| Use this for… | Don’t use this for… |
| --- | --- |
| Theme + priority decisions (P0/P1) | Inventing Keyword Planner volumes |
| Ads keep / negative / watch lists from real search terms | Treating Ads “conversions” as demo proof |
| AIO/MLO framing Anh meant (long-tail → LLM citations) | Ranking on “AI OS / Finance OS” as north star |
| Next actions that actually move outcomes | Replacing per-URL content trackers |

**Working order:** themes → short intent phrases → content/ads → GSC/Ads feedback.  
**Per-query → URL execution** still lives in `SEO_Target_Keywords_2026-08.*`.

---

## 2. Index of source files

### Repo (`docs/marketing/`)

| File | Role |
| --- | --- |
| `docs/marketing/SEO_Keyword_Strategy_Intent_Themes.md` | **Strategy brief** — themes, channel split, avoid list |
| `docs/marketing/SEO_Keyword_Strategy_Intent_Themes.xlsx` | Same + Review sheets |
| `docs/marketing/SEO_Target_Keywords_2026-08.md` | Buyer-query → URL tracker (Aug 2026) |
| `docs/marketing/SEO_Target_Keywords_2026-08.xlsx` | Companion spreadsheet |
| `docs/marketing/SEO_Keywords_Before_After_2026-08.xlsx` | Historical metadata before/after only — **not** strategy |
| `docs/marketing/SEO_Keyword_Founder_Brainstorm.xlsx` | Founder vote workbook (Themes / Keywords / Negatives). **In git** (`9585639`); restore if missing from disk: `git checkout HEAD -- docs/marketing/SEO_Keyword_Founder_Brainstorm.xlsx` |
| `docs/marketing/drafts/grr-vs-nrr.md` | GRR vs NRR pillar draft / source |
| `docs/marketing/PERF_NOTES.md` | Perf notes (adjacent, not keyword strategy) |
| `docs/marketing/SMPL_SEO_AIO_LLM_Ads_Strategy.md` | **This master doc** (repo copy) |

### Downloads (Matt’s working copies)

| File | Role |
| --- | --- |
| `C:\Users\mattj\Downloads\SMPL_SEO_AIO_LLM_Ads_Strategy.md` | **This master doc** (primary for Matt) |
| `C:\Users\mattj\Downloads\SEO_Keyword_Strategy_Intent_Themes.xlsx` | Strategy sheet copy |
| `C:\Users\mattj\Downloads\SMPL_Keyword_Planning_Review_Anh_David.docx` | Shareable Anh/David review brief |
| `C:\Users\mattj\Downloads\SMPL_Keyword_Planning_Review_Table.csv` | Theme table for Sheets import |
| `C:\Users\mattj\Downloads\Keyword Stats 2026-08-06 at 12_14_35.csv` | Keyword Planner export (~725 rows) — noisy |
| `C:\Users\mattj\Downloads\Search terms report.csv` | Google Ads search terms (Aug 6–10, 2026) |
| `C:\Users\mattj\Downloads\SMPL.ai Feedback Part Deux - 2026_08_05 10_01 PDT - Notes by Gemini.docx` | Aug 5 call transcript/notes (AIO + Planner asks) |
| `C:\Users\mattj\Downloads\SMPL_Competitor_Brief_Aleph_Sapien_Fresh.md` | Competitor context (Aleph / Sapien / Fresh) — not keyword volume |
| `C:\Users\mattj\Downloads\SMPL_SEO_Tag_Comparison_Rev1.0.pdf` | Older SEO tag comparison |
| `C:\Users\mattj\Downloads\SMPL_SEO_Tag_Comparison_SecondaryPages_Rev1.0.pdf` | Secondary-pages tag comparison |

### Related (not SEO strategy, but nearby)

| File | Role |
| --- | --- |
| `frontend/sanity/seed/*.mjs` + `frontend/scripts/publish-*.mjs` | Blog/glossary publish sources |
| `scripts/_build_seo_founder_brainstorm_xlsx.py` | Rebuild founder brainstorm xlsx |

---

## 3. SEO strategy

### North-star rule

Rank and advertise for **buyer queries** finance leaders type when they have an FP&A, board, ARR, forecast, or reconciliation problem.

| Phrase | Treatment |
| --- | --- |
| AI operating system for SaaS finance / AI OS | Brand / positioning only — thought-leadership OK; **not** organic/ads north star |
| Finance OS / finance operating system | Category narrative — secondary to concrete SaaS FP&A / board / ARR queries |
| SaaS FP&A, board reporting, ARR reporting, AI CFO Copilot, financial intelligence | **Primary** ranking + ads themes |

### Themes (P0 / P1) — qualitative priorities only

| Theme | Intent | Priority | Channel bias |
| --- | --- | --- | --- |
| SaaS FP&A Software | Transactional / commercial | **P0** | Both |
| Board Reporting / board pack | Commercial / problem | **P0** | Both |
| ARR Reporting / waterfall | Commercial / informational | **P0** | Both (ads prefer “software/tool”) |
| NRR / GRR literacy | Informational → board | **P0** | SEO then soft CTA |
| SaaS Financial Intelligence | Commercial | **P0** | Both |
| AI CFO Copilot | Commercial / branded-category | **P0 ads / P1 SEO** | Ads-leaning until clearer landing |
| Cash Forecasting | Informational → commercial | **P1** | SEO then Ads |
| Billing vs CRM ARR | Problem / reconciliation | **P1** | Content gap |
| Scenario / revenue forecasting | Commercial | **P1** | Supporting |
| Executive reporting / board deck automation | Commercial / transactional | **P1** | Ads-leaning |
| Variance / MD&A | Informational / commercial | **P1–P2** | SEO literacy |
| AI OS / Finance OS | Brand only | Brand | Not north star |

### Organic priorities (what to win)

1. **ARR methodology cluster** — waterfall, ARR vs GAAP, governance, billing vs CRM ARR (gap), NRR vs GRR  
2. **Board reporting / board pack** — live post + homepage theme; internal links  
3. **SaaS FP&A / financial intelligence** — homepage, pricing, demo, glossary hub  
4. **Cash forecast + scenario / variance** — bridge from board ARR–cash–P&L  
5. **Glossary definitions** — NRR, GRR, waterfall, ARR (definition → pillar)

### Avoid list (wrong intent — esp. Ads negatives)

Do **not** bid or optimize as if we sell:

- Bookkeeping / bookkeeper  
- Payroll / payroll software  
- Tax software / tax filing  
- AP automation / invoice OCR  
- QuickBooks setup / “accounting software” as primary (GL replacement)  
- Generic ChatGPT / “ChatGPT for finance” wrappers  
- NetSuite / Sage Intacct / Salesforce **replacement** (we connect; we do not replace SoR)  
- SOC 2 **certified** claims  
- **AI OS / Finance OS** as the primary organic or ads wager  

### Content gaps still open

| Gap | Why | Next move |
| --- | --- | --- |
| Billing vs CRM ARR | High reconciliation pain; no dedicated URL | Brief + publish P1 pillar |
| Clearer AI CFO Copilot landing | Ads theme; homepage/blog only | Thin feature URL or `/` section for message match |
| Scenario / variance landing | Under-served supporting theme | After cash forecast solidifies |
| GSC validation | Priorities are qualitative until data | Track queries after indexing |

---

## 4. AIO / LLM optimization (MLO)

### What Anh meant (Aug 5 call)

From Gemini notes + the Anh/David review brief:

- Go **long-tail / intent themes**, not only classic head SEO.  
- Long-tail is **short-term relevance** *and* more effective for **AIO / LLMs** — content that answers a clear question is more likely to be cited or summarized by answer engines and chat tools.  
- Structure work as **intent themes → 2–3 word phrases** people would actually type (or ask an LLM).  
- David’s complement: plant broad head terms for a ~5-year horizon; win near-term with achievable 2–3 word phrases; consolidate pages/tags around Keep themes later.

### How long-tail + FAQ / glossary + quotable definitions help citations

| Asset | Why it helps AIO/MLO |
| --- | --- |
| **Long-tail pillars** (e.g. ARR waterfall vs GAAP, GRR vs NRR, board pack) | Specific question → specific answer LLMs can quote |
| **Glossary terms** (NRR, GRR, waterfall, ARR, …) | Short, stable definitions = citation-friendly snippets |
| **Quotable one-liners** in posts (what it is / isn’t; how metric is calculated) | Models prefer crisp, attributable statements over vague marketing |
| **Internal links** glossary ↔ pillar ↔ product | Reinforces entity/theme consistency across the site |
| **FAQ-style sections** on pillars | Match “how do I… / what’s the difference…” query shapes |

### What we are NOT doing yet (honest)

- No dedicated **AIO citation program** (schema FAQ markup audit, “quotable definition” style guide, answer-engine tracking).  
- No systematic **LLM mention / citation monitoring** (ChatGPT, Perplexity, Google AI Overviews).  
- Keyword Planner export is **not** an AIO Keep list — it’s a broad, noisy seed.  
- We have **not** finished Anh/David Keep/Cut votes on the review table.  
- Ads PMax is **not** AIO — it’s paid inventory that drifted into generic AI queries.

**Practical MLO for now:** keep shipping definition-grade glossary + problem-shaped pillars with clear H2 answers; don’t wait for a separate “AIO project.”

---

## 5. Paid search / Google Ads

### Window reviewed

`Search terms report.csv` — **Aug 6–10, 2026**, almost entirely **Performance Max**.

| Slice | Clicks | Impr. | Cost | “Conversions” (Ads UI) |
| --- | --- | --- | --- | --- |
| Listed search terms | 18 | 97 | $24.17 | 3 |
| Campaign total (incl. other) | 131 | 1,130 | $92.43 | **37** |

### Conversion wiring reality (critical)

- Intended primary goal: **Submit lead form** / schedule demo (`/book-demo`, `/request-quote`).  
- **Form conversion is not cleanly wired** from successful form submit → Google Ads conversion event.  
- Site has Ads base tag; without a real submit event, Ads “conversions” are **noisy** (auto-detection, page views, enhanced guesses, etc.).  
- **Do not** use the campaign’s 37 “conversions” to decide winners. Use search terms for **scope + negatives**, not ROI proof.

### What we learned from search terms

**Keep / lean in (on-brand finance software intent)**

| Search term | Why |
| --- | --- |
| `cash flow forecasting software` | Clearest SaaS-finance / forecasting intent in the export (1 click, $4.88) |

**Watch (maybe related, weak or ambiguous)**

| Search term | Note |
| --- | --- |
| `finance tools` | Too broad — watch, don’t scale |
| `data insights tools` | Soft BI intent; spent ~$6; “conversion” untrustworthy |
| `business information software` | Vague; same caveat |
| Competitor BI names (`klipfolio…`, `sisense…`) | Wrong product class — negative |

**Negative / cut hard (PMax drift into generic AI + junk)**

| Pattern / term | Why |
| --- | --- |
| `ai agencies`, `ai business`, `best business ai`, `business ai`, `ai tools for business`, `ai powered tools`, `best ai solutions` | Generic AI curiosity — not SaaS FP&A |
| `ai for sme`, `ai applications`, `ai vendor`, `ai providers`, `ai solutions`, `enterprise ai` | Platform shopping, not finance buyer |
| `artificial intelligence services…`, French IA phrases (`entreprise intelligence artificielle`, etc.) | Services / non-ICP / language bleed |
| `enterprise it infrastructure services`, `enterprise it automation` | IT services, not finance OS |
| `level ai`, `cloud data platforms`, `big data ai` | Off-category |
| `ai financial planner` | Personal-finance / planner intent risk |

**PMax drift summary:** Inventory spent on **generic AI / BI / IT** queries. Buyer themes we care about (SaaS FP&A, ARR reporting, board reporting) barely appear — that is usually **theme/asset/setup**, not “nobody searches that.”

### Ads operating rules (until tracking is fixed)

1. Add **negatives** from avoid list + PMax junk above before scaling spend.  
2. Prefer **Search** (or tightly themed campaigns) on P0 phrases once ready — don’t rely on PMax to discover ICP.  
3. Fix **demo/lead form conversion** firing before optimizing to Maximize Conversions seriously.  
4. Bid/copy to **SaaS-qualified** language (SaaS FP&A, board reporting, ARR) — not “AI platform.”

---

## 6. Keyword Planner / messy stats

**Source:** `C:\Users\mattj\Downloads\Keyword Stats 2026-08-06 at 12_14_35.csv`  
**Period label in file:** July 1, 2025 – June 30, 2026  
**Rows:** ~725 keywords (after header junk)

### How to treat this file

- **Directional only.** Broad seed from a noisy Planner pass — includes nonsense (`saa s`, `fp &a`), mega-heads (`intelligent ai` ~500k), and off-ICP.  
- **Do not** dump all 725 into ads or metadata.  
- Volumes shown below are **from Google’s export as-is** (often bucketed: 50 / 500 / 5000…) — not invented by us, also not precise.

### On-brand cluster (examples worth keeping in research)

Planner rows that match FP&A / ARR / board / forecast / financial intelligence themes (subset):

| Keyword (Planner) | Avg. monthly searches (export) | Competition |
| --- | --- | --- |
| cash forecasting software | 5000 | Low |
| new arr | 5000 | High |
| fp&a software | 500 | Medium |
| software fp&a | 500 | Medium |
| financial forecasting software | 500 | Medium |
| financial intelligence software | 500 | Low |
| forecasting software | 500 | Medium |
| scenario planning software | 500 | Low |
| arr waterfall | 500 | Low |
| arr saas / arr metric / arr revenue… | 500 | Low |
| ai for fp&a | 500 | Medium |
| saas finance | 500 | Low |
| finance os | 50 | Medium |
| arr reporting | 50 | Low |
| board fp&a | 50 | Medium |
| ai in fp&a | 50 | Medium |

~80 rows matched a simple on-brand pattern pass; many ARR variants are literacy/how-to (good for SEO, careful for ads without “software/tool”).

### Junk / wrong-intent heads (do not chase)

High-volume ambiguous or off-ICP examples from the same export:

| Keyword (Planner) | Avg. monthly searches (export) | Why junk for SMPL |
| --- | --- | --- |
| intelligent ai | 500000 | Mega-head nonsense |
| ai company / ai and co / company software | 50000 | Generic |
| ai for business / ai in finance / enterprise ai | 5000 | Too broad / wrong funnel |
| ai operating system / ai os | 5000 | Brand-adjacent but **not** north star for spend |
| finance software / business software / saas platform | 5000 | GL / generic SaaS |
| financial reporting software | 5000 | Often GL/close tools — qualify heavily |
| salesforce saas / hr saas | 5000 | Wrong product |
| samples of financial statement | 5000 | Student / template intent |

### Breakout rule

| Bucket | Action |
| --- | --- |
| On-brand + problem-shaped | Feed SEO pillars + future Search ads (with SaaS qualifiers) |
| Brand-only (AI OS / Finance OS) | Thought-leadership only |
| Junk / mega-head / SoR replacement | Negatives + ignore in Planner follow-ups |
| Everything else in the 725 | Leave in CSV; don’t promote until Keep/Cut with Anh/David |

**Next Planner pass:** fake Ads campaign on **Keep list only** (David’s method) — drop the broad dump.

---

## 7. Content already shipped (SEO / AIO proof points)

Base: `https://www.smpl-ai.com`  
Live / known cluster (from strategy trackers + Sanity seed / publish scripts). Confirm indexing in GSC.

### Pillars (buyer / literacy)

| Topic | URL |
| --- | --- |
| ARR waterfall vs GAAP revenue | https://www.smpl-ai.com/blog/arr-waterfall-vs-gaap-revenue |
| ARR governance | https://www.smpl-ai.com/blog/arr-governance |
| SaaS board reporting (ARR–cash–P&L) | https://www.smpl-ai.com/blog/saas-board-reporting-arr-cash-pl |
| GRR vs NRR | https://www.smpl-ai.com/blog/grr-vs-nrr |
| No standard ARR calculation | https://www.smpl-ai.com/blog/no-standard-arr-calculation |
| SaaS revenue model shapes finance | https://www.smpl-ai.com/blog/saas-revenue-model-shapes-finance |
| Finance uncertainty problem | https://www.smpl-ai.com/blog/finance-uncertainty-problem |

### Brand / category narrative (not SEO north star)

| Topic | URL |
| --- | --- |
| AI operating system for SaaS finance | https://www.smpl-ai.com/blog/ai-operating-system-for-saas-finance |
| Finance OS vs FP&A software | https://www.smpl-ai.com/blog/finance-os-vs-fpa-software |

### Newer cluster (publish scripts exist — treat as shipped if live in Sanity/prod)

Expected slugs from Aug content push (verify live):

| Topic | Expected URL |
| --- | --- |
| SaaS cash forecasting | https://www.smpl-ai.com/blog/saas-cash-forecasting |
| SaaS revenue forecasting (ARR / bookings / GAAP) | https://www.smpl-ai.com/blog/saas-revenue-forecasting-arr-bookings-gaap |
| Finance integration layer | https://www.smpl-ai.com/blog/finance-integration-layer |
| Rethinking how finance scales | https://www.smpl-ai.com/blog/rethinking-how-finance-scales |
| Single source of truth not enough | https://www.smpl-ai.com/blog/single-source-of-truth-not-enough |
| What should a finance operating system be | https://www.smpl-ai.com/blog/what-should-a-finance-operating-system-be |

### Glossary (definition → pillar)

Examples:  
https://www.smpl-ai.com/glossary/nrr · `/glossary/grr` · `/glossary/waterfall` · `/glossary/arr` · related SaaS metric terms (`mrr`, `churn`, `bookings`, …)

### Conversion pages (ads message match)

- https://www.smpl-ai.com/book-demo  
- https://www.smpl-ai.com/request-quote  
- Homepage / pricing — SaaS FP&A + financial intelligence language  

---

## 8. Next actions checklist (narrow)

### This week (outcomes > theater)

- [ ] **Anh/David Keep/Cut** on `SMPL_Keyword_Planning_Review_*` (or founder brainstorm sheet) — lock P0 themes  
- [ ] **Ads negatives:** paste avoid list + PMax junk (`ai agencies`, `ai tools`, `sisense`, `klipfolio`, IT automation, non-English IA, etc.)  
- [ ] **Pause or constrain PMax** until Search/themes are clean — stop paying for generic AI curiosity  
- [ ] **GSC:** confirm indexing for live pillars + glossary; request indexing where missing  
- [ ] Spot-check newer blog URLs above are actually live (200 + in sitemap)

### Before scaling paid

- [ ] Wire **real** lead-form / demo submit → Ads conversion (ignore UI “conversions” until then)  
- [ ] Focused Keyword Planner pass on **Keep phrases only** (fake campaign, no spend)  
- [ ] Optional: thin **AI CFO Copilot** landing for ads message match  

### Content (P1, after Keep votes)

- [ ] Brief **billing vs CRM ARR**  
- [ ] Confirm cash / revenue forecasting posts are live and internally linked from board + ARR pillars  
- [ ] Add 1–2 **quotable definition** boxes per pillar (AIO/MLO without a new workstream)

### Explicitly defer

- [ ] Full AIO citation monitoring program  
- [ ] Re-litigating AI OS / Finance OS as ranking north star  
- [ ] Treating Keyword Stats 725-row dump as the keyword list  

---

## One-line strategy

**Win SaaS FP&A / board / ARR buyer queries in organic + Search; use long-tail definitions for LLMs; treat PMax generic-AI traffic and Ads “conversions” as noise until form tracking and negatives are fixed.**

---

*Internal marketing working doc · Aug 2026 · Not SOC 2 certified · No fabricated keyword volumes.*
