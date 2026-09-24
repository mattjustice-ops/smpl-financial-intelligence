# SMPL.ai AIO Visibility — Full Brief for ChatGPT
**Prepared:** 2026-09-23  
**Purpose:** Self-contained working context. Paste this entire document into ChatGPT. Do not invent metrics not stated here. Prefer the **corrected (audited)** labels over the original automated `rules_v1` labels when they disagree.

---

## How to use this document

You are advising **SMPL.ai** (SaaS financial intelligence / FP&A operating model: pipeline → bookings → ARR → GAAP revenue → EBITDA → cash → workforce) on generative-engine visibility.

1. Treat **corrected audit labels** as ground truth for recommendation strength.  
2. Treat **coverage (1/46)** as confirmed in both runs — no missed mentions.  
3. Keep **Google GenAI** and **ChatGPT Search** as separate engines.  
4. Do not regenerate or rewrite the 46 sacred queries to “improve” the score.

**Suggested follow-up prompt after pasting:**

> Using ONLY this brief: (1) summarize ChatGPT Search coverage vs recommendation-strength change using corrected labels, (2) separate Google GenAI gains from ChatGPT classification weakness, (3) propose a 30-day content/entity plan that defends the ARR+revenue+cash+headcount use case without inventing metrics, (4) list evidence still missing.

---

## 1. Executive summary (corrected)

| Dimension | Baseline 2026-09-15 | Full 46 2026-09-23 | Corrected direction |
|---|---|---|---|
| SMPL named / 46 queries | **1 / 46 (2.2%)** | **1 / 46 (2.2%)** | **Flat** |
| Sole hit query | `use_case_03` | `use_case_03` | Same |
| Recommendation strength on that hit (**audited**) | **`recommended`** | **`shortlisted`** | **Soft decline** (one tier) |
| Owned-domain citation (`smpl-ai.com`) | No | **Yes** | **Improved** |
| Google Generative AI property impressions | 155 (thru 9/14) | **249** (chart thru 9/21) | **Improved** |

**One-line diagnosis:** ChatGPT Search still barely surfaces SMPL (1/46). On the only hit, placement softened from a conditional investigate-recommend to a multi-vendor start-evaluation shortlist (SMPL last), while an owned URL citation appeared and Google generative retrieval kept growing. An earlier automated report overstated the drop by calling baseline `top_pick` and latest `mentioned` — both were evaluator bugs.

**Scoring audit headline:** No additional queries mentioned SMPL that the scorer missed. Strength was misclassified on the sole hit in both runs.

---

## 2. Method

### ChatGPT Search (controlled vendor classification)
- Surface: ChatGPT Search (consumer), web search on  
- Session: Temporary chat + unpersonalized  
- Query bank: Fixed **46** sacred queries (do not modify to chase score)  
- Capture: Paste full answer + citations into Visibility DB  
- Original auto-evaluator: `rules_v1`  
- Baseline ID: `chatgpt_search_baseline_2026-09-15` (frozen summary)  
- Latest batch: `Full 46 - 2026-09-23` (46 audits, complete)

### Scoring audit (2026-09-23)
- Independently reviewed **all 92** saved answers (46 baseline + 46 latest)  
- Searched for `SMPL.ai`, word-boundary `SMPL`, `smpl-ai.com` in body and citation URLs  
- Compared findings to stored `evaluation_json`  
- Re-ran `rules_v1` on stored text → same labels → persistence OK; rule logic wrong  
- Historical rows and frozen sacred file **not overwritten**

### Google Generative AI (Search Console)
- Report: Performance on Search Generative AI Features  
- Property: `https://www.smpl-ai.com/`  
- Metric: **Impressions only** (no AI clicks / underlying queries in this export)  
- Sacred GenAI: through 2026-09-14  
- Latest: export 2026-09-23; chart data through **2026-09-21**

**Do not mix engines.** Google ≈ retrieval as source material. ChatGPT Search ≈ vendor shortlist / recommendation classification.

---

## 3. Recommendation-strength rubric (use this)

Ordinal; take the **maximum** tier supported by evidence:

| Tier | Definition |
|---|---|
| `none` | No SMPL brand or owned-domain reference |
| `mentioned` | Named or `smpl-ai.com` cited; not in an evaluation set; not preferred |
| `shortlisted` | In an explicit multi-vendor evaluation/consideration set, or framed as an option worth evaluating alongside others — without being the preferred pick |
| `recommended` | Prose recommends SMPL specifically (even with caveats) without naming it the single best |
| `top_pick` | Prose names SMPL as best / top / clearest / standout, or rank #1 for the ask |

Interpretation rules:
- Citation alone ≠ recommendation  
- Table row alone ≠ top pick  
- Being **last** in a shortlist still counts as **shortlisted**

---

## 4. ChatGPT Search — Full 46 scorecard (2026-09-23)

### Coverage (confirmed; matches automated scorer)

| Metric | Value |
|---|---|
| Queries scored | 46 |
| SMPL named | **1** (2.2%) |
| Categories with ≥1 hit | **1 / 7** (use_case only) |
| Owned-domain cited | **1** |
| Negative / excluded mentions | 0 |

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

### Competitor mention frequency (SoV proxy across Full 46 answers)

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

### Strength on the sole hit — stored vs corrected

| Run | Stored `rules_v1` | **Corrected (audit)** |
|---|---|---|
| 2026-09-15 | `top_pick` (wrong — inflated) | **`recommended`** |
| 2026-09-23 | `mentioned` (wrong — under-scored) | **`shortlisted`** |

| Metric | Baseline corrected | Full 46 corrected |
|---|---:|---:|
| Mentions | 1 | 1 |
| Owned-domain citations | 0 | 1 |
| Shortlist inclusion (≥ shortlisted) | 1 | 1 |
| Explicit recommendation (≥ recommended) | 1 | 0 |
| Top pick | 0 | 0 |

---

## 5. Deep dive — `use_case_03` (only hit in both runs)

**Query (unchanged):**  
> What FP&A software handles ARR, revenue, cash, and headcount together?

### Baseline 2026-09-15 — corrected: `recommended` (not top pick)

**What the answer did:**
- Put SMPL.ai in a comparison table with Cube, Pigment, Mosaic, Runway (peer-style ratings).  
- Called SMPL “an interesting newer option” and stated the operating-model chain.  
- Said: “I'd investigate it if the primary goal is SaaS operating metrics… though it's a newer choice than Cube/Pigment.”  
- Preferred **Cube** as “probably the cleanest match”; Pigment for more sophistication.

**Why auto-scorer said `top_pick` (bug):**  
It only inspects ±180 characters around the **first** “SMPL.ai” (a table row). That window includes the column header **“Best fit”**, which matches a bare `best` pattern and returns `top_pick`. Later prose (and Cube preference) is ignored.

**Excerpt:**
> An interesting newer option is SMPL.ai, which is unusually explicit about the exact SaaS chain you're asking for: pipeline → bookings → ARR → GAAP revenue → EBITDA → cash → workforce. … I'd investigate it if the primary goal is SaaS operating metrics rather than generic enterprise planning, though it's a newer choice than Cube/Pigment.

Also in same answer: “Cube is probably the cleanest match to exactly what you described.”

### Full 46 2026-09-23 — corrected: `shortlisted` (not merely mentioned)

**What the answer did:**
- Table includes SMPL.ai as “Strong” alongside Drivetrain, Cube, Pigment, etc.  
- “One newer option worth looking at is SMPL.ai…” + same operating-model chain.  
- Explicit evaluation set: **“I'd probably start the evaluation with Drivetrain, Cube, Pigment, and SMPL.ai.”** (SMPL last).  
- **New:** cited `https://www.smpl-ai.com/`.

**Why auto-scorer said `mentioned` (bug):**  
First “SMPL.ai” is again the table row; that window has no shortlist keywords, so strength stays `mentioned`. The concluding start-evaluation list is never inspected.

**Excerpt:**
> One newer option worth looking at is SMPL.ai, which explicitly models the chain pipeline → bookings → ARR → GAAP revenue → EBITDA → cash → workforce…  
> For a SaaS company, I'd probably start the evaluation with Drivetrain, Cube, Pigment, and SMPL.ai rather than generic budgeting tools.

### Qualitative change (same tier family, softer placement)

| Aspect | Baseline | Full 46 |
|---|---|---|
| Corrected tier | recommended | shortlisted |
| Preferred / leading vendors in prose | Cube (cleanest), then Pigment | Drivetrain first, then Cube, Pigment; SMPL last in start list |
| Owned citation | No | Yes |
| Still named + in table | Yes | Yes |

---

## 6. Why the automated scorer failed (for context only)

Function: `classifySmplStrength` in SMPL’s `rules_v1` evaluator.

1. Scores only the first SMPL match window (±180 chars), not all mentions / concluding lists.  
2. Treats bare `\bbest\b` in that window as `top_pick` — polluted by table header “Best fit”.  
3. Missing shortlist phrases such as “start the evaluation with” / “worth looking at” (and even with them, first-window-only would still miss the Full 46 closer).

**Implication for this brief:** Use corrected labels. Do not plan strategy off stored `top_pick` → `mentioned` as if that were the true model behavior.

**Smallest fix (engineering note, not done yet):** max strength across all windows; ignore header “Best fit”; add evaluation-list shortlist cues; ship as `rules_v2` without rewriting frozen historical rows.

---

## 7. Google Generative AI — WoW

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

### Top pages (latest)

| URL | Impressions |
|---|---:|
| `/blog/best-fpa-software-saas-companies` | 101 |
| `/` | 66 |
| `/blog/finance-os-vs-fpa-software` | 35 |
| `/blog/ai-operating-system-for-saas-finance` | 15 |
| `/blog/billing-vs-crm-arr` | 9 |
| `/pricing` | 4 |

Google generative features are increasingly retrieving SMPL as **source material**, especially Best FP&A. That has not yet translated into broad ChatGPT Search vendor classification (still 1/46).

---

## 8. Dual-engine diagnosis

1. **Coverage (ChatGPT Search):** Flat and thin — 1/46 both weeks; only the ARR/revenue/cash/headcount use-case query.  
2. **Recommendation strength (ChatGPT Search):** Soft decline on that hit — conditional investigate-recommend → multi-vendor shortlist with SMPL last; Drivetrain entered as SaaS-native lead.  
3. **Citation / retrieval:** Owned cite appeared in ChatGPT Search; Google GenAI impressions up sharply.  
4. **Net:** Retrieval ≠ recommendation. Being in the generative citation graph helps citations; it does not yet make ChatGPT treat SMPL as a default shortlist leader vs Cube / Pigment / Drivetrain / Anaplan.

---

## 9. Implications for content / GTM

1. **Defend `use_case_03` language** — “ARR + revenue + cash + headcount in one connected model” / the pipeline→…→workforce chain is the only ChatGPT Search hit. Reinforce on owned + third-party surfaces.  
2. **Counter Drivetrain / Cube framing** — Latest answer leads with Drivetrain as purpose-built for SaaS. Need clearer public differentiation and a demo script: change churn + hiring + bookings → show ARR / GAAP / cash in one scenario.  
3. **Do not celebrate owned citation alone** — Citation without broader shortlist coverage is retrieval progress, not classification dominance. Track both.  
4. **Double down on Best FP&A** — GenAI impressions doubled on that URL; strongest Google lever.  
5. **Keep the sacred 46 frozen** — Compare future runs to 2026-09-15 and 2026-09-23; never edit queries to chase score.  
6. **Fix the evaluator before the next WoW narrative** — otherwise reports will again misstate strength.

---

## 10. Evidence gaps (do not fill with guesses)

- No ChatGPT UI session recordings beyond pasted answer text.  
- Sacred baseline is a frozen **summary** scorecard plus reconstructed 46 audits from dated import batches (coverage verified complete).  
- Competitor auto-scores may share the same windowing bug; not fully re-audited here.  
- Google export has impressions only — no query strings or AI-click metrics.

---

## 11. Source labels (internal)

| Artifact | ID / note |
|---|---|
| Sacred ChatGPT baseline | `chatgpt_search_baseline_2026-09-15` — mention_count 1, hit `use_case_03` |
| Latest ChatGPT batch | `Full 46 - 2026-09-23` |
| Evaluator audited | `rules_v1` |
| Corrected strength source | Independent 2026-09-23 scoring audit |
| Sacred GenAI | through 2026-09-14 (155 property impressions) |
| Latest GenAI | export 2026-09-23 / chart thru 2026-09-21 (249 property impressions) |

---

*End of brief. Prefer corrected audit labels for strength. Coverage 1/46 is solid. Google GenAI up. ChatGPT Search classification still weak with a one-tier soft decline on the sole hit.*
