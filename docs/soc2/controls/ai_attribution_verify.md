# Driver / attribution claim verify (design)

> **Not SOC 2 certification.** Design only — **not implemented** as a product gate yet.  
> Numeric claim-verify (`ai_claim_verify.md` / `claim_verify.py`) is a prerequisite but **not sufficient**.  
> Linked from [README.md](./README.md) · Policy: [P15](../policies/P15_ai_llm_data_handling.md) §4.7 / §4.8

---

## Why numeric-only is not enough

Fail-closed numeric verify catches invented dollars and percents. It does **not** catch a correct number attributed to the wrong cause.

Example that passes today's helper:

> "Net new ARR of **$2.7M** was driven by **three enterprise upsells**."

- `$2.7M` may match `arr_waterfall.net_new_arr` within **$1.00**.
- "three enterprise upsells" may be false, incomplete, or the wrong driver mix (e.g. new business + expansion, or a single logo).

Board and MD&A risk is often **wrong story with right math** — not only phantom figures.

---

## What counts as a driver claim

Treat as an **attribution claim** when narrative asserts that a material metric moved **because of** a named operational cause. Patterns include:

| Pattern | Example |
|---------|---------|
| Cause → effect | "ARR grew **due to** expansion" |
| Counted events | "**three** enterprise upsells drove $420K" |
| Segment / channel | "S&M overspend driven by **paid search**" |
| Timing / one-time | "Cash dip from **annual prepay timing**" |
| Negation / exclusion | "Churn was **not** logo loss; it was contraction" |

Non-claims (usually out of scope for v1): pure forward opinion ("we should hire"), process advice without a stated causal link to a closed-period figure, or restating a metric with no cause.

---

## Proposed verify approach

**Do not** ask a second LLM to "judge" free-text causes as the primary control.

Preferred: **structured allowlist of drivers from the engine**, then constrain or check narrative against that set.

1. **Engine produces driver evidence** (same freeze / close package as numbers), e.g.:
   - ARR bridge components: new business, expansion, reactivation, contraction, churn (amounts + optional deal counts).
   - Cash bridge / WC lines with labeled drivers.
   - GTM channel spend / pipeline / closed-won by channel.
   - Known one-time / timing flags from freeze pack prose **only when structured** (IDs or enums), not raw free text.
2. **Attribution package** shape (sketch):

```json
{
  "metric": "net_new_arr",
  "period": "2026-06",
  "value": 2655000,
  "allowed_drivers": [
    {"id": "expansion", "label": "Expansion ARR", "amount": 1800000, "source": "arr_waterfall.expansion_arr"},
    {"id": "new_business", "label": "New business ARR", "amount": 900000, "source": "arr_waterfall.new_business_arr"}
  ],
  "disallowed_without_evidence": ["three enterprise upsells", "paid search", "logo churn"]
}
```

3. **Model rules:** may only name drivers whose `id` / `label` appears in `allowed_drivers` for that metric/period; may cite driver amounts only if they appear in evidence (existing numeric verify).
4. **Post-check (fail-closed):**
   - Extract driver phrases (allowlist match / light NER against labels) from commentary.
   - Any asserted driver **not** in the allowlist → strip section / don't-know / hard-block on deck emit (same surface policy as numeric P15).
   - Optional later: magnitude check ("expansion drove the variance") when one component dominates within a band.

**Rejected as primary control:** free-text second-pass "does this sound right?" without engine-backed allowlist.

---

## Fail-closed behavior

| Surface | Proposed (aligned with numeric gates) |
|---------|----------------------------------------|
| `/commentary/generate` | Soft strip / don't-know on section with unverified driver |
| MD&A Prompt 2 / Prompt 5 deck | Hard block emit when material attribution fails (customer-visible package) |
| Board slide regenerate | Soft strip bullet → don't-know; all-bad → don't-know narrative |
| Copilot | Don't-know answer; log unverified attribution for review |

Never ship "correct number + invented cause" on customer-visible board/MD&A paths once this gate is live.

---

## Phased rollout

| Phase | Scope | Status |
|-------|--------|--------|
| **0** | Numeric claim-verify on commentary, Prompt 2, Prompt 5, board regenerate, Copilot thin wire | In progress / see `ai_claim_verify.md` |
| **1** | Design + schema for `allowed_drivers` on ARR waterfall + cash bridge (this doc) | **Design only** |
| **2** | Emit `attribution_package` from freeze / deck payload builders (no LLM change yet) | Not started |
| **3** | Prompt constraints: "only name drivers in attribution_package" | Not started |
| **4** | Structural post-verify (allowlist match) + tests; hard-block on Prompt 2/5 | Not started |
| **5** | Extend to GTM channels, headcount, one-time flags; Copilot | Not started |

Do **not** implement a full attribution engine in the same increment as numeric wiring unless a trivial allowlist already exists in payload builders.

---

## Relation to single-source / demo mismatch

Wrong drivers are worse when FE and Board are on **different seeds** for the same closed month (see [reconcile_financial_statements.md](./reconcile_financial_statements.md)). Attribution verify assumes one authoritative warehouse actuals source per customer. Confirm production single-source + automated regression separately; **do not** reseed demo to fake equality.

---

## Open questions for Matt

1. First metric surface: ARR waterfall only, or ARR + cash bridge together?
2. Are deal-count claims ("three upsells") in scope for phase 4, or amounts-only drivers first?
3. Hard-block vs soft strip on board regenerate when attribution fails but numbers pass?

---

_End of attribution claim-verify design_
