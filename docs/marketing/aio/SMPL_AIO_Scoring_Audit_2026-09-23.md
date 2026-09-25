# AIO Visibility Scoring Audit — Evidence Report
**Date:** 2026-09-23  
**Scope:** ChatGPT Search sacred baseline (2026-09-15) vs Full 46 (2026-09-23)  
**Evaluator under test:** `rules_v1` (`frontend/lib/aio/evaluate.ts`)  
**Constraint:** Original responses, stored scores, and frozen baseline preserved — no query re-runs, no production overwrites.

Companion canvas: [`canvases/aio-scoring-audit-2026-09-23.canvas.tsx`](../../canvases/aio-scoring-audit-2026-09-23.canvas.tsx)

---

## Direct answer

**Did SMPL appear in any additional queries that scoring missed?**  
**No.** Both runs contain exactly **one** named SMPL appearance: `use_case_03`. An independent case-insensitive scan of all 46+46 full answers (body + citation URLs) for `SMPL.ai`, `\bSMPL\b`, and `smpl-ai.com` found no other company references. A looser `/smpl/i` sweep produced no extra hits.

**Was recommendation strength misclassified?**  
**Yes — on that same single query, in both runs:**

| Run | Stored | Corrected (human rubric below) |
|---|---|---|
| 2026-09-15 baseline | `top_pick` | **`recommended`** (not top pick; Cube preferred in prose) |
| 2026-09-23 Full 46 | `mentioned` | **`shortlisted`** (explicit start-evaluation list including SMPL) |

The September 23 WoW report’s claim of “zero shortlist appearances” is therefore **wrong for the latest run**, and the baseline “top pick” claim is **inflated**.

---

## 1. Evidence inventory

| Run | Source | Rows | Unique seed query IDs | Empty / truncated (&lt;40 chars) |
|---|---|---:|---:|---:|
| Baseline 2026-09-15 | All `aio_manual_audits` **not** in batch `Full 46 - 2026-09-23` (many “Baseline bulk - 2026-09-15” batches) | 46 | 46 / 46 | 0 |
| Full 46 2026-09-23 | Batch `b5266ed4-b2a6-4adc-8ce2-a70a11bd2fd8` | 46 | 46 / 46 | 0 |

- Seed bank: `lib/aio/data/seed_queries.json` — 46 IDs; both runs cover all.
- No duplicate `query_id` within either reconstructed run.
- Re-running `evaluateManualAudit` on stored `raw_response` **reproduces** stored strengths → scores were persisted correctly; the bug is in **rules**, not import/stale eval.
- Frozen file `sacred_baseline.json` scorecard (`mention_count: 1`, `hit_query_id: use_case_03`) matches coverage. It does **not** store per-answer strength detail beyond that summary.

**Unknown (not treated as absence):** original ChatGPT UI session recordings beyond pasted `raw_response`; whether any answer was edited before paste (no evidence of that in DB).

---

## 2. Independent rubric (applied identically to both runs)

Ordinal; take the **maximum** tier supported by evidence:

| Tier | Definition |
|---|---|
| `none` | No SMPL brand or owned-domain reference |
| `mentioned` | Named or `smpl-ai.com` cited; not in an evaluation set; not preferred |
| `shortlisted` | Included in an explicit multi-vendor evaluation/consideration set, **or** framed as an option worth evaluating alongside others — without being the preferred pick |
| `recommended` | Prose recommends SMPL specifically (even with caveats) without naming it the single best |
| `top_pick` | Prose names SMPL as best / top / clearest / standout, or rank #1 for the ask |

Signals recorded separately (not collapsed into one boolean):

- Named in answer  
- In comparison table  
- Owned domain cited  
- In evaluation shortlist  
- Explicitly recommended / preferred  
- Discussed negatively / excluded  

**Rules of interpretation used here:** citation alone ≠ recommendation; table row alone ≠ top pick; being last in a shortlist still counts as shortlisted.

No replacement numerical `prominence_score` is proposed (that field is just `strengthWeight(strength)` today).

---

## 3. Independent review results

### Coverage scan (all 92 answers)

| Signal | Baseline | Full 46 |
|---|---:|---:|
| Named in answer | 1 (`use_case_03`) | 1 (`use_case_03`) |
| In comparison table | 1 | 1 |
| Owned-domain cited | 0 | 1 |
| Shortlisted (rubric) | 1 | 1 |
| Recommended (rubric) | 1 | 0 |
| Top pick (rubric) | 0 | 0 |
| Negative / excluded | 0 | 0 |
| **Mention misses vs stored** | **0** | **0** |
| **False-positive mentions** | **0** | **0** |

Only query with any SMPL signal in either run: **`use_case_03`** — *What FP&A software handles ARR, revenue, cash, and headcount together?*

### Occurrence map on `use_case_03`

**Baseline (3 body hits):** table row; “interesting newer option is SMPL.ai… I'd investigate it…”; trailing `SMPL.ai` citation label. No owned URL.

**Full 46 (4 body hits + owned cite):** table row; “newer option worth looking at is SMPL.ai…”; citation label; **“start the evaluation with Drivetrain, Cube, Pigment, and SMPL.ai”**. Owned URL: `https://www.smpl-ai.com/?utm_source=chatgpt.com`.

---

## 4. Discrepancy table

| Run date | Query ID | Query text | Original classification | Corrected assessment | Exact supporting excerpt | Cause |
|---|---|---|---|---|---|---|
| 2026-09-15 | `use_case_03` | What FP&A software handles ARR, revenue, cash, and headcount together? | `top_pick` | **`recommended`** | “An interesting newer option is SMPL.ai… I'd investigate it if the primary goal is SaaS operating metrics… though it's a newer choice than Cube/Pigment.” Prose also: “Cube is probably the cleanest match…” | **Evaluator false positive.** `classifySmplStrength` uses only the ±180 char window around the **first** match (table row at idx 421). That window contains the column header **“Best fit”**, which matches `/\bbest\b/` and returns `top_pick` before later prose is considered. |
| 2026-09-23 | `use_case_03` | (same) | `mentioned` | **`shortlisted`** | “For a SaaS company, I'd probably start the evaluation with Drivetrain, Cube, Pigment, and SMPL.ai rather than generic budgeting tools.” | **Evaluator false negative.** First match is the table row at idx 533 (“Strong…”); window has no shortlist keywords → `mentioned`. The concluding evaluation-start list (~idx 1839) is never inspected. |

No other discrepancies on mention detection.

---

## 5. Confirmed code path

File: `frontend/lib/aio/evaluate.ts` — function `classifySmplStrength` (used by `evaluateManualAudit`).

```109:160:frontend/lib/aio/evaluate.ts
function classifySmplStrength(answer: string): {
  strength: RecommendationStrength;
  explicit_rank: number | null;
  variants: string[];
} {
  // ... finds FIRST regex match only ...
  const ctx = windowAround(answer, firstIdx).toLowerCase(); // ±180 chars

  if (
    /\b(best|top\s*pick|top\s*choice|standout|clearest|strongest)\b/.test(ctx) ||
    explicit_rank === 1
  ) {
    return { strength: "top_pick", explicit_rank, variants: unique(variants) };
  }
  // recommended patterns...
  // shortlisted: shortlist|alternatives?|options?|include[sd]?|also\s+look
  // else mentioned
}
```

**Confirmed causes (not hypotheses):**

1. **First-window-only scoring** → later shortlist sentences ignored (Full 46 under-score).  
2. **Bare `\bbest\b` in window** → table header “Best fit” promotes baseline to `top_pick` without SMPL being preferred in prose.  
3. **Missing shortlist cues** — patterns include `also look` / `options` but not `start the evaluation with` or `worth looking at` (would still miss Full 46 if only the first window is used).  
4. **Import/persistence OK** — re-eval of stored text matches stored JSON.  
5. **Report aggregation** — WoW report counted stored `recommendation_strength`, so it inherited both errors (“top pick lost” / “zero shortlists”).

**Hypothesis (not required to explain the two errors):** competitor strength uses the same windowing pattern and may mis-label peers; out of scope except as shared design risk.

---

## 6. Original vs corrected counts

| Metric | Baseline stored | Baseline corrected | Full 46 stored | Full 46 corrected |
|---|---:|---:|---:|---:|
| Mentions (named) | 1 | 1 | 1 | 1 |
| Owned-domain citations | 0 | 0 | 1 | 1 |
| Shortlist inclusion (≥ `shortlisted`) | 1* | 1 | **0** | **1** |
| Explicit recommendation (≥ `recommended`) | 1* | 1 | 0 | 0 |
| Top pick | 1 | **0** | 0 | 0 |

\*Baseline’s stored “≥ shortlisted / ≥ recommended” came only via the false `top_pick` label.

---

## 7. Visibility reassessment (corrected)

| Dimension | Verdict | Evidence |
|---|---|---|
| **Coverage** | **Flat** | 1/46 → 1/46; no missed mentions either side |
| **Recommendation strength** | **Soft decline** | Corrected `recommended` → `shortlisted` on the same query; qualitative lead shifted to Drivetrain/Cube/Pigment with SMPL last in the start-evaluation list — **not** the reported collapse `top_pick` → `mentioned` |
| **Owned citation** | **Improved** | 0 → 1 (`smpl-ai.com`) |

Separate coverage from strength: retrieval/citation improved; classification tier softened one step; absolute coverage unchanged.

---

## 8. Smallest supported evaluator / reporting correction

Keep historical `evaluation_json` and `sacred_baseline.json` frozen. Propose a **`rules_v2`** (or audit overlay) for new imports / parallel display:

1. Compute strength as the **max** over **all** SMPL match windows (and/or whole-answer multi-vendor list patterns).  
2. Do **not** treat table column headers like “Best fit” as `top_pick` unless the preference predicate binds to SMPL as subject.  
3. Add shortlist cues: `start the evaluation with`, `worth looking at`, `A, B, C, and SMPL` lists.  
4. Regression cases from this audit:  
   - Baseline `use_case_03` → must **not** be `top_pick`; expect `recommended` or `shortlisted`.  
   - Full 46 `use_case_03` → must be ≥ `shortlisted`.  
   - Both → `smpl_mentioned === true`.  
   - Absent-SMPL fixture → `none`.

Reporting: when publishing WoW, count shortlist from corrected/v2 labels or show “stored vs audited” side by side — do not silently rewrite sacred.

---

## 9. Evidence gaps

- Sacred baseline is a **summary file**, not a single batch foreign key; the 46 answers were reconstructed from dated baseline bulk batches (complete unique coverage verified).  
- No screenshot / HAR of the ChatGPT UI beyond pasted text.  
- Competitor mis-scores sharing the same window logic were not exhaustively re-audited.

---

*End of audit. Measurement corrected: no additional missed mentions; two strength errors on the sole hit query; visibility coverage flat, strength soft-decline, owned citation up.*
