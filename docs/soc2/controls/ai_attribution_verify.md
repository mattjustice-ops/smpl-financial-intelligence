# Driver / attribution claim verify (partially live)

> **Not SOC 2 certification.** v1 helper + primary-path wiring — **not** a full ARR-bridge /
> GTM / Copilot attribution engine.  
> Numeric claim-verify (`ai_claim_verify.md` / `claim_verify.py`) remains required and
> is **not sufficient** alone.  
> Linked from [README.md](./README.md) · Policy: [P15](../policies/P15_ai_llm_data_handling.md) §4.7 / §4.8

---

## Why numeric-only is not enough

Fail-closed numeric verify catches invented dollars and percents. It does **not** catch a correct number attributed to the wrong cause.

Example that passes numeric helper but fails attribution allowlist:

> "Net new ARR of **$2.7M** was driven by **three enterprise upsells**."

- `$2.7M` may match `arr_waterfall.net_new_arr` within **$1.00**.
- "three enterprise upsells" is not an engine allowlisted driver id/label → omit / don't-know.

Board and MD&A risk is often **wrong story with right math** — not only phantom figures.

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

Non-claims (out of scope for v1): pure forward opinion ("we should hire"), process advice without a stated causal link to a closed-period figure, or restating a metric with no cause.

---

## What shipped (v1 — 2026-07-30)

| Piece | Behavior | Code |
|-------|----------|------|
| Reusable helper | Detect causal language; match against `allowed_drivers`; fail-closed don't-know | `backend/app/services/commentary/attribution_verify.py` |
| Attribution package contract | `{ metric, period, value?, allowed_drivers[{id,label,amount?,source?,aliases}], policy }` | same module (`build_attribution_package*`) |
| `/commentary/generate` | Build allowlist from `CommentaryInputs` → embed ATTRIBUTION PACKAGE in prompt → post-LLM attribution verify after numeric verify → soft strip | `service.py`, `prompts.py` |
| MD&A Prompt 2 | Emit `attribution_package` on payload from ARR/cash bridge labels + variance metrics + sheet labels → nested string walk → soft strip; fully wiped variance sheet → hard block | `mda_package_payload.py`, `prompt2_mda_package.py` |
| Tests | Allowed driver passes; invented driver fails closed; numeric-only unaffected; generate strips invented cause | `backend/tests/test_attribution_verify.py` |

### Allowlist sources today (honest)

| Surface | Structured fields used |
|---------|------------------------|
| Commentary generate | MRR waterfall component names + aliases; `actuals_vs_forecast` metrics; `pipeline_changes` labels; `customer_movement` keys / notable customers; quota segments/reps; cash aging bucket keys |
| MD&A Prompt 2 | `arr_analysis.bridge_table` labels + ARR component keys; `cash_liquidity.bridge_table` labels; variance display metrics; sheet metric/category/channel labels; GTM channel names when present |

**Empty allowlist + causal claims → fail closed** (strip / don't-know). No causal claims → pass (numeric verify still applies).

### Fail-closed behavior (v1 live)

| Surface | v1 behavior |
|---------|-------------|
| `/commentary/generate` | Soft strip / don't-know on section with unverified driver |
| MD&A Prompt 2 | Soft strip nested strings; **hard block** if entire variance sheet is attribution don't-know |
| Prompt 5 / board regenerate / Copilot | **Not wired** — follow-up |

Never ship "correct number + invented cause" on the wired customer-visible paths above.

---

## Gaps / follow-ups

| Gap | Notes |
|-----|-------|
| Prompt 5 deck attribution | Numeric string-literal verify only today |
| Board slide regenerate | Numeric bullet strip only |
| Copilot | Thin numeric blob wire only |
| Deal-count / named-logo drivers | Not a first-class catalog; invented "three enterprise upsells" fails unless that phrase is literally in allowlist |
| Magnitude check ("expansion drove the variance") | Not in v1 |
| Full freeze `attribution_package` emit without LLM | Partial via MDA payload; dedicated freeze builder still open |
| Prompt constraints completeness | Commentary + Prompt 2 prompts updated; other surfaces not |

---

## Phased rollout (updated)

| Phase | Scope | Status |
|-------|--------|--------|
| **0** | Numeric claim-verify on commentary, Prompt 2, Prompt 5, board regenerate, Copilot thin wire | **Live** — see `ai_claim_verify.md` |
| **1** | Design + schema for `allowed_drivers` | **Done (design)** |
| **2** | Emit `attribution_package` from MDA payload builders | **Partial** — Prompt 2 payload |
| **3** | Prompt constraints on commentary + Prompt 2 | **Partial** |
| **4** | Structural post-verify + tests; soft strip commentary; hard-block Prompt 2 when fully wiped | **Partial — live on those two paths** |
| **5** | Extend to Prompt 5 / board regenerate / Copilot / richer GTM + deal counts | **Not started** |

---

## Relation to single-source / demo mismatch

Wrong drivers are worse when FE and Board are on **different seeds** for the same closed month (see [reconcile_financial_statements.md](./reconcile_financial_statements.md)). Attribution verify assumes one authoritative warehouse actuals source per customer. Confirm production single-source + automated regression separately; **do not** reseed demo to fake equality.

---

## Matt review checklist

- [ ] Confirm causal detector + allowlist match is the right v1 bar (no second LLM judge)
- [ ] Confirm empty-allowlist → strip causal claims is acceptable
- [ ] Confirm soft strip on commentary + Prompt 2 hard-block-when-fully-wiped matches product risk
- [ ] Accept Prompt 5 / board / Copilot attribution as follow-up
- [ ] Confirm **$1.00** numeric bar unchanged
- [ ] Merge when review OK — not SOC 2 certified

---

_End of attribution claim-verify_
