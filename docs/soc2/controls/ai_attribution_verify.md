# Driver / attribution claim verify (live on primary AI paths)

> **Not SOC 2 certification.** Helper + path wiring — not a full ARR-bridge /
> GTM attribution engine. Copilot uses **structured** packages from the same
> freeze/live metric structures as the metrics blob (plus blob-label supplement).
> Citation verify + `_sources` warehouse tags: [ai_claim_verify.md](./ai_claim_verify.md).  
> Numeric claim-verify on **interactive** surfaces (regenerate / Copilot / commentary
> generate) is soft-warn only — board numbers are trusted; this helper is the
> primary gate for **what happened** and **forward-looking** story quality.  
> Linked from [README.md](./README.md) · Policy: [P15](../policies/P15_ai_llm_data_handling.md) §4.7 / §4.8
> · Production FE↔Board: [fe_board_single_source.md](./fe_board_single_source.md)

---

## Why numeric-only is not enough

Fail-closed numeric verify catches invented dollars and percents. It does **not** catch a correct number attributed to the wrong cause.

Example that passes numeric helper but fails attribution allowlist:

> "Net new ARR of **$2.7M** was driven by **three enterprise upsells**."

- `$2.7M` may match `arr_waterfall.net_new_arr` within **$1.00**.
- "three enterprise upsells" is not an engine allowlisted driver id/label → omit / don't-know
  (unless opportunity_attribution / customer_movement literally evidences that count + movement).

Board and MD&A risk is often **wrong story with right math** — not only phantom figures.

---

## Multi-driver AND/comma rule

When a causal phrase joins multiple drivers with `and` / commas, **every** named part must be on `allowed_drivers`.

| Phrase | Allowlist | Result |
|--------|-----------|--------|
| driven by expansion | expansion | pass |
| driven by expansion and churn | expansion, churn | pass |
| driven by expansion and three enterprise upsells | expansion only | **fail** (`partial_allowlist`) |
| driven by expansion, contraction, and churn | expansion, churn | **fail** (`partial_allowlist`) |

Previously any single allowlisted token inside the phrase was enough.

Code: `attribution_verify._split_driver_conjuncts`, `_match_claim`.

---

## What counts as a driver claim (v1)

Treat as an **attribution claim** when narrative asserts that a material metric moved **because of** a named operational cause. Patterns include:

| Pattern | Example |
|---------|---------|
| Cause → effect | "ARR grew **due to** expansion" |
| Counted events | "**three** enterprise upsells drove $420K" |
| Segment / channel | "S&M overspend driven by **paid search**" |
| Timing / one-time | "Cash dip from **annual prepay timing**" |
| Negation / exclusion | "Churn was **not** logo loss; it was contraction" |

Non-claims (out of scope for closed-period attribution): pure process advice without a stated causal link ("we should hire"), or restating a metric with no cause.

**Forward-looking / predictive** ("watch out", "will be driven by", next-quarter outlook that names a driver) must match the **forecast / pipeline** subset of `allowed_drivers` (source/id/label hints: forecast, pipeline, bookings, scenario, coverage, weighted, quota, outlook, opportunity). Invented future drivers → surgical strip / don't-know that clause.

---

## What shipped (v1 extended — 2026-07-30)

| Piece | Behavior | Code |
|-------|----------|------|
| Reusable helper | Detect causal language; match against `allowed_drivers`; fail-closed don't-know | `backend/app/services/commentary/attribution_verify.py` |
| Attribution package contract | `{ metric, period, value?, allowed_drivers[{id,label,amount?,source?,aliases}], policy }` | same module (`build_attribution_package*`) |
| `/commentary/generate` | Build allowlist from `CommentaryInputs` → embed ATTRIBUTION PACKAGE in prompt → post-LLM attribution verify after numeric verify → soft strip | `service.py`, `prompts.py` |
| MD&A Prompt 2 | Emit `attribution_package` on payload from ARR/cash bridge labels + variance metrics + sheet labels → nested string walk → soft strip; fully wiped variance sheet → hard block | `mda_package_payload.py`, `prompt2_mda_package.py` |
| Prompt 5 deck | Emit `attribution_package` on deck payload; embed in user message; post-LLM soft-strip off-allowlist causal claims in PPTX **string literals**; **export continues** even if every attribution check failed | `prompt5_deck.py` |
| Board slide regenerate | Allowlist from slide/deck fields (+ thin freeze-blob labels); per-bullet attribution strip → don't-know; all-wiped → don't-know narrative | `board_commentary_service.py`, `board_api_prompts.py` |
| Copilot | **Structured:** allowlist from comparison_waterfalls / cash_bridge / opportunity logos (+ frozen `attribution_package`); blob-label catalog as supplement | `board_platform_routes.py`, `build_attribution_package_from_copilot_structures` |
| **Deal-count / named-logo catalogs** | `customer_movement` counts → "N / word new customers"; notable customers + opportunity `customer_name` / `opportunity_name` / `account_name` as logos; movement-type deal counts | `attribution_verify.py` |
| **Magnitude dominance** | When one peer driver's \|amount\| ≥ 50% of family total, add aliases (`primarily X`, `largest bridge component`, …) so attribution does not over-strip | `apply_magnitude_dominance` |
| Tests | Unit helpers + deal-count / logo / dominance coverage | `backend/tests/test_attribution_verify.py` |

### Allowlist sources today (honest)

| Surface | Structured fields used |
|---------|------------------------|
| Commentary generate | MRR waterfall component names + aliases; `actuals_vs_forecast` metrics; `pipeline_changes` labels; `customer_movement` keys / **deal-count phrases** / notable customers; quota segments/reps; cash aging bucket keys; **dominance** on amount-bearing peers |
| MD&A Prompt 2 | `arr_analysis.bridge_table` labels + amounts + ARR component keys; `cash_liquidity.bridge_table` labels + amounts; variance display metrics; sheet metric/category/channel labels; GTM channel names; **dominance** |
| Prompt 5 deck | Same MDA-style bridge fields on deck payload + `period_matrix` metrics + `gtm_performance.channels` |
| Board regenerate | Slide/deck structured fields via `build_attribution_package_from_deck_payload`; freeze prose only adds **canonical** labels that appear in the blob |
| Copilot | Waterfall component types + amounts; cash_bridge field labels; **opportunity logos + deal counts**; marketing channels; blob-label catalog as supplement; freeze packs store `attribution_package` in sections; **dominance** |

**Empty allowlist + causal claims → fail closed** (strip / don't-know). No causal claims → pass (numeric verify still applies).

### Fail-closed behavior (v1 live)

| Surface | v1 behavior |
|---------|-------------|
| `/commentary/generate` | **Interactive:** surgical strip of bad causal / ungrounded forward sentences (prefer keep good clauses) |
| MD&A Prompt 2 | Soft strip nested strings; **hard block** if entire variance sheet is attribution don't-know (**strict** deck) |
| Prompt 5 deck | Soft strip bad string literals; prefer **export with stripped text** (no hard-block on full wipe) |
| Board slide regenerate | **Interactive:** per-bullet surgical strip; all-story-wiped → don't-know narrative |
| Copilot | **Interactive:** surgical strip of bad causal / forward clauses; full don't-know only if nothing remains |

Never ship "correct number + invented cause" or invented forward drivers on the wired customer-visible paths above. Interactive surfaces no longer nuke whole answers for unmatched $/% alone — see [ai_claim_verify.md](./ai_claim_verify.md).

---

## Gaps / follow-ups

| Gap | Notes |
|-----|-------|
| Warehouse `_sources` null honesty | Tags now include `org_id` / `loaded_at` / `is_final` with honest nulls when unknown — [ai_claim_verify.md](./ai_claim_verify.md) |
| Older freeze packs | Freezes built before structured packages lack `sections.attribution_package` → blob-label fallback |
| Invented deal stories | Still fail unless count + movement literally evidenced (e.g. expansion movement_type × N) |
| DOM overlay / runTieOut | Shipped on DOM branch — see [ai_claim_verify.md](./ai_claim_verify.md) / [fe_board_single_source.md](./fe_board_single_source.md) |

---

## Phased rollout (updated)

| Phase | Scope | Status |
|-------|--------|--------|
| **0** | Numeric claim-verify on commentary, Prompt 2, Prompt 5, board regenerate, Copilot | **Live** — see `ai_claim_verify.md` |
| **1** | Design + schema for `allowed_drivers` | **Done (design)** |
| **2** | Emit `attribution_package` from MDA / deck payload builders | **Live** — Prompt 2 + Prompt 5 |
| **3** | Prompt constraints on commentary + Prompt 2 + Prompt 5 + board + Copilot | **Live** |
| **4** | Structural post-verify + tests; soft strip / hard-block-when-fully-wiped | **Live on wired paths** |
| **5** | Stronger Copilot structured evidence + FE↔Board single-source confirm | **Live** (prior PR) |
| **6** | Deal-count / logo catalogs + magnitude dominance + evidence `_sources` + FE hydrate residue | **Live** |
| **7** | Multi-driver AND/comma require-all | **Live** |

---

## Relation to single-source / demo mismatch

Wrong drivers are worse when FE and Board are on **different seeds** for the same closed month (see [reconcile_financial_statements.md](./reconcile_financial_statements.md)). Attribution verify assumes one authoritative warehouse actuals source per customer. **Production path confirmed:** both UIs hydrate via `build_unified_outlook_payload` — [fe_board_single_source.md](./fe_board_single_source.md). Demo dual-seed left alone; hydrate merge now replaces/prunes closed Actual residue instead of field-merging demo cells.

---

## Matt review checklist

- [ ] Confirm causal detector + allowlist match is the right v1 bar (no second LLM judge)
- [ ] Confirm empty-allowlist → strip causal claims is acceptable
- [ ] Confirm soft strip + hard-block-when-fully-wiped on Prompt 2 matches product risk; Prompt 5 soft-strip + export
- [ ] Accept deal-count / logo / dominance enrichment (still invent → fail)
- [ ] Confirm multi-driver require-all is the right bar
- [ ] Confirm **$1.00** numeric bar unchanged
- [ ] Merge when review OK — not SOC 2 certified

---

_End of attribution claim-verify_
