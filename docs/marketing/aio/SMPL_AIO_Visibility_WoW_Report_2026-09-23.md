# SMPL AIO Visibility — Week-over-Week Report
**Prepared:** 2026-09-23  
**Audience:** Paste into ChatGPT (or any analyst) as working context for AIO / GEO strategy  
**Owner:** SMPL Ops · Visibility

---

## 1. Executive answer to the key question

**Yes — on the one query where SMPL previously showed as a top pick, classification got worse.**

| Dimension | Sacred baseline (2026-09-15) | Full 46 re-run (2026-09-23) | Direction |
|---|---|---|---|
| Hit rate (SMPL mentioned / 46) | **1 / 46 (2.2%)** | **1 / 46 (2.2%)** | Flat |
| Sole hit query | `use_case_03` | `use_case_03` | Same query |
| Recommendation strength on that hit | **`top_pick`** | **`mentioned` only** | **Worse** |
| Prominence score (evaluator) | **1.0** | **0.2** | Worse |
| Owned-domain citation (`smpl-ai.com`) | No | **Yes** | Better |
| Any shortlist / recommend / top_pick anywhere in the 46 | Yes (1× top_pick) | **No** | Worse |
| Google Generative AI property impressions | 155 (sacred thru 9/14) | **249** (snapshot thru 9/21) | Better |

**One-line diagnosis:** ChatGPT Search still barely classifies SMPL (1/46). On the only commercial use-case that previously shortlisted SMPL hard, the model demoted SMPL from peer / top-pick framing to a lighter “newer option” mention — while Google generative retrieval kept improving.

---

## 2. Method (so ChatGPT does not over-interpret)

### ChatGPT Search audits (controlled)
- **Surface:** ChatGPT Search (consumer), web search on  
- **Session:** Temporary chat + unpersonalized  
- **Query bank:** Fixed 46 sacred queries (do not regenerate to improve score)  
- **Evaluator:** `rules_v1` (mention / recommendation strength / citations / positioning vs brand truth)  
- **Sacred baseline ID:** `chatgpt_search_baseline_2026-09-15` (frozen)  
- **Latest batch:** `Full 46 - 2026-09-23` (imported to Visibility DB)

### Google Generative AI (Search Console)
- **Report:** Performance on Search Generative AI Features  
- **Property:** `https://www.smpl-ai.com/`  
- **Metric:** Impressions only (no AI clicks, no underlying queries in this export)  
- **Sacred GenAI:** through 2026-09-14 (`google_genai_baseline_2026-09-14`)  
- **Latest GenAI:** export folder 2026-09-23; chart data through **2026-09-21** (Google lag / preliminary days)

**Do not mix engines.** Google = becoming retrievable as source material. ChatGPT Search = not yet reliably classifiable / shortlisted as a vendor answer.

---

## 3. ChatGPT Search — Full 46 scorecard (2026-09-23)

| Metric | Value |
|---|---|
| Queries scored | 46 |
| SMPL mentioned | **1** (2.2%) |
| Shortlisted / recommended / top_pick | **0** |
| Strong recommend (recommended + top_pick) | **0** |
| SMPL cited (any URL) | **1** |
| Owned-domain cited (`smpl-ai.com`) | **1** |
| Categories with ≥1 hit | **1 / 7** (use_case only) |

### Hits by category

| Category | Queries | SMPL mentions |
|---|---:|---:|
| authority | 8 | 0 |
| category | 7 | 0 |
| competitive | 5 | 0 |
| lean_finance | 6 | 0 |
| saas_icp | 5 | 0 |
| systems | 6 | 0 |
| **use_case** | **9** | **1** (`use_case_03`) |

### Competitor mention frequency across the Full 46 (SoV proxy)

| Competitor | Mentions in 46 answers |
|---:|---:|
| Pigment | 29 |
| Cube | 28 |
| Anaplan | 23 |
| Aleph | 21 |
| Abacum | 19 |
| Datarails | 18 |
| Workday Adaptive Planning | 15 |
| Runway | 14 |
| Drivetrain | 13 |
| Planful | 12 |
| Mosaic | 11 |
| Vena | 10 |
| **SMPL** | **1** |

---

## 4. Deep dive — the regression on `use_case_03`

**Query (unchanged):**  
> What FP&A software handles ARR, revenue, cash, and headcount together?

This is the **only** query that mentioned SMPL in both the sacred baseline and the 2026-09-23 Full 46.

### Score comparison (same query, same method)

| Field | 2026-09-15 (sacred) | 2026-09-23 (Full 46) |
|---|---|---|
| `smpl_mentioned` | true | true |
| `recommendation_strength` | **top_pick** | **mentioned** |
| `prominence_score` | **1.0** | **0.2** |
| `answer_relevance` | 1.0 | 0.57 |
| `positioning_accuracy` | 0.91 | **1.0** |
| `smpl_cited` / owned domain | false / false | **true / true** (`https://www.smpl-ai.com/`) |
| Name variants found | SMPL.ai, SMPL | SMPL.ai, SMPL |
| Competitors named alongside | Cube, Mosaic, Pigment, Runway | Anaplan, Cube, Drivetrain, Pigment, Runway |

### What ChatGPT actually said (qualitative)

**2026-09-15 — stronger placement**
- Comparison table rated **SMPL.ai ★★★★★** across ARR / revenue / cash / headcount, with “Best fit: SaaS-specific operating model.”
- Peers in the same five-star band: Cube, Pigment.
- Prose called SMPL “an interesting newer option” and spelled the full chain:  
  `pipeline → bookings → ARR → GAAP revenue → EBITDA → cash → workforce`.
- Still preferred **Cube** as “probably the cleanest match,” with Pigment for sophistication — but SMPL was framed as a peer-tier product in the matrix (evaluator = `top_pick`).

**2026-09-23 — weaker placement**
- Table moved to qualitative “Strong” labels; SMPL is present but not differentiated with stars.
- New leaders in prose: **Drivetrain** first (“particularly purpose-built around SaaS”), then Cube, then Pigment.
- SMPL reduced to: “One newer option worth looking at…” + the same operating-model chain — then a shortlist of **Drivetrain, Cube, Pigment, and SMPL.ai** (SMPL last).
- **Positive:** ChatGPT Search **cited `smpl-ai.com`** (owned-domain citation). That is new vs sacred.

### Plain-English interpretation

SMPL did **not** fall off the answer entirely. It lost **rank / weight**:
1. From matrix peer / top-pick treatment → mild inclusion.  
2. From early consideration set energy → trailing “also look at.”  
3. Drivetrain entered as the SaaS-native default, crowding the slot SMPL was previously filling narratively.

Meanwhile, **citation improved** (owned URL present). That is consistent with Google-side retrieval gains (see §5): the web graph is noticing SMPL more, but ChatGPT’s **vendor shortlist behavior** for this use case got softer.

---

## 5. Google Generative AI — WoW (Search Console)

| Metric | Sacred thru 2026-09-14 | Snapshot export 2026-09-23 (chart thru 9/21) |
|---|---:|---:|
| Property impressions | 155 | **249** (+61%) |
| September to date in file | 110 (Sept 1–14) | **204** (Sept 1–21) |
| Last 7 days in file | 84 | **94** |
| Peak day | 2026-09-14 @ 38 | still 2026-09-14 @ 38 |
| Pages with impressions | 13 | **22** |
| US share | 48.4% | 48.2% |
| Desktop share | 93.5% | 94.4% |
| Top commercial article (`best-fpa-software-saas-companies`) | 50 | **101** (+102%) |

### Top pages (latest snapshot)

| URL | Impressions |
|---|---:|
| `/blog/best-fpa-software-saas-companies` | 101 |
| `/` (home) | 66 |
| `/blog/finance-os-vs-fpa-software` | 35 |
| `/blog/ai-operating-system-for-saas-finance` | 15 |
| `/blog/billing-vs-crm-arr` | 9 |
| `/pricing` | 4 |

**Interpretation:** Google generative features are increasingly retrieving SMPL as **source material**, especially the Best FP&A commercial article. That is the healthy retrieval half of AIO. It has **not** yet translated into ChatGPT Search shortlist classification beyond a soft mention on one use-case query.

---

## 6. Dual-engine diagnosis (keep these separate)

1. **Google GenAI:** Trajectory up. Best FP&A article is the commercial workhorse. Keep indexing / entity / comparison-page pressure here.  
2. **ChatGPT Search:** Still ~2% mention rate. Sole historical win (`use_case_03`) **demoted** from `top_pick` → `mentioned`. Zero shortlists in the latest Full 46.  
3. **Net:** Retrieval ≠ recommendation. Being in the generative citation graph helps citations; it does not yet make ChatGPT treat SMPL as a default shortlist vendor against Cube / Pigment / Drivetrain / Anaplan.

---

## 7. Implications for content / GTM (actionable)

1. **Defend `use_case_03` language** — “ARR + revenue + cash + headcount in one connected model” was the only hit. Publish and reinforce that exact chain on owned pages and third-party surfaces ChatGPT cites.  
2. **Counter Drivetrain / Cube framing** — Latest answer leads with Drivetrain as “purpose-built around SaaS.” Need clearer public differentiation vs Drivetrain + Cube on the same connected-model claim (demo script: churn + hiring + bookings → ARR / GAAP / cash in one scenario).  
3. **Do not celebrate owned citation alone** — Citation without shortlist is progress on retrieval, not on recommendation. Track both.  
4. **Double down on Best FP&A** — GenAI impressions doubled on that URL; it is the strongest Google lever.  
5. **Keep the sacred 46 frozen** — Compare future runs to 2026-09-15 and 2026-09-23; never edit queries to chase a better score.

---

## 8. Verbatim excerpts (for ChatGPT analysis)

### Query
`What FP&A software handles ARR, revenue, cash, and headcount together?`

### 2026-09-15 excerpt (stronger)
> An interesting newer option is SMPL.ai, which is unusually explicit about the exact SaaS chain you're asking for: pipeline → bookings → ARR → GAAP revenue → EBITDA → cash → workforce. … I'd investigate it if the primary goal is SaaS operating metrics rather than generic enterprise planning, though it's a newer choice than Cube/Pigment.

Evaluator: **`top_pick`**, prominence **1.0**, no owned citation.

### 2026-09-23 excerpt (weaker)
> One newer option worth looking at is SMPL.ai, which explicitly models the chain pipeline → bookings → ARR → GAAP revenue → EBITDA → cash → workforce and ingests CRM, ERP, billing and HRIS data.  
> … For a SaaS company, I'd probably start the evaluation with Drivetrain, Cube, Pigment, and SMPL.ai …

Evaluator: **`mentioned`**, prominence **0.2**, owned citation **yes** (`https://www.smpl-ai.com/`).

---

## 9. Suggested prompt if pasting this into ChatGPT

> You are advising SMPL.ai on AIO / generative-engine optimization. Using ONLY the report below, (1) summarize the ChatGPT Search regression on use_case_03, (2) separate Google GenAI gains from ChatGPT recommendation weakness, (3) propose a 30-day content + entity plan that defends the ARR/revenue/cash/headcount use case without inventing metrics not in the report, and (4) list what evidence we still lack.

Then paste this entire document.

---

## 10. Source artifacts (internal)

| Artifact | Location / ID |
|---|---|
| Sacred ChatGPT baseline | `frontend/lib/aio/data/sacred_baseline.json` · `chatgpt_search_baseline_2026-09-15` |
| Latest Full 46 batch | Postgres `aio_batches` · name `Full 46 - 2026-09-23` · 46 audits |
| Sacred GenAI baseline | `frontend/lib/aio/data/google_genai_baseline_2026-09-14.json` |
| Current GenAI snapshot | `frontend/lib/aio/data/google_genai_baseline.json` · `google_genai_baseline_2026-09-23` |
| GSC export folder | `smpl-ai.com-Performance-on-Search-Generative-AI-Features-2026-09-23` |

---

*End of report. Numbers are from controlled manual audits + Search Console Generative AI impressions only — not an OpenAI ranking score.*

---

## Addendum — Scoring audit (2026-09-23)

An independent review of all 92 saved answers found **no additional missed SMPL mentions** (still 1/46 both runs). Recommendation strength on `use_case_03` was misclassified in both directions:

| Run | Report / stored | Audited |
|---|---|---|
| Baseline | `top_pick` | **`recommended`** (Cube preferred in prose; `top_pick` was a “Best fit” table-header false positive) |
| Full 46 | `mentioned` / “zero shortlists” | **`shortlisted`** (“start the evaluation with Drivetrain, Cube, Pigment, and SMPL.ai”) |

Corrected WoW: **coverage flat**, **strength soft-decline** (recommended → shortlisted), **owned citation improved** (0 → 1). Full evidence: [SMPL_AIO_Scoring_Audit_2026-09-23.md](./SMPL_AIO_Scoring_Audit_2026-09-23.md).
