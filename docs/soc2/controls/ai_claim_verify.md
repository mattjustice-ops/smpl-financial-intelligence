# P15 AI claim-verify — coverage checklist (founder review)

> **Not SOC 2 certification.** Product integrity gate for AI-stated numbers vs engine evidence.  
> **Branch note:** numeric claim-verify merged via PR #55 (`main`). Attribution v1 (commentary + Prompt 2) via PR #56; remaining-path wire: `feat/p15-attribution-wire-remaining`.  
> **Policy:** [P15 §4.7 / §4.8](../policies/P15_ai_llm_data_handling.md) · **Status snapshot:** [README.md](./README.md)  
> **Non-numeric drivers:** [ai_attribution_verify.md](./ai_attribution_verify.md) (**live** on commentary, Prompt 2, Prompt 5, board regenerate, Copilot thin wire)

Use this page to confirm what shipped, what is still open, and where to open the code.

---

## 1. What shipped (2026-07-30)

| Path | Behavior | Code |
|------|----------|------|
| `/api/v1/commentary/generate` | Evidence package in prompt → LLM → schema validate → **post-LLM numeric claim verify** → strip / don't-know bad sections | `backend/app/services/commentary/service.py`, `prompts.py`, `claim_verify.py` |
| MD&A Prompt 2 package | **Hard block** if variance display ≠ period_matrix; walk nested commentary strings; don't-know on fail; **block emit** if variance sheet is fully unverifiable | `backend/app/services/reporting/export/prompt2_mda_package.py`, `board_platform_metrics.py` |
| MD&A Prompt 5 deck | Evidence preview in user message; post-LLM verify of **$ / % / Nx in PPTX string literals** vs flattened deck payload; **hard block** (`CommentaryIntegrityError`) before Node render (adapt + fresh) | `backend/app/services/reporting/export/prompt5_deck.py` |
| Board slide regenerate | Flatten slide payload (+ freeze blob numbers) → per-bullet verify → don't-know on fail; all-bad → don't-know narrative | `backend/app/services/reporting/export/board_commentary_service.py` (`enrich_slide_with_ai`) |
| Board Copilot | **Thin wire:** evidence = numbers parsed from metrics/freeze **text blob**; post-LLM verify → don't-know answer. Not full `_sources` | `backend/app/api/board_platform_routes.py` (`board_copilot`) |

Reusable helper: `backend/app/services/commentary/claim_verify.py`

**Attribution (non-numeric) on the same paths:** see [ai_attribution_verify.md](./ai_attribution_verify.md) — Prompt 5 soft-strip + hard-block-when-fully-wiped; board per-bullet strip; Copilot thin blob-label allowlist.

---

## 2. Algorithm (short)

1. **Build evidence** — flatten engine / freeze / display numbers into `evidence_package.values` (`build_evidence_package` / `flatten_evidence_values` / MD&A `evidence_values_from_mda_payload` / deck `evidence_values_from_deck_payload` / Copilot `evidence_values_from_text_blob`).
2. **Prompt** — embed the same package (or metrics blob) so the model is told to state only those values.
3. **Extract claims** — `$` amounts (incl. K/M/B), `%`, multipliers (`Nx`), select ratios (`extract_numeric_claims`). Prompt 5 scopes to string literals only.
4. **Match** — each claim vs any evidence value within tolerance (`verify_text_against_evidence` / `_best_match`).
5. **Fail closed** — mismatch or missing evidence → replace text with don't-know / omit section content; never emit unsupported material claims. MD&A Prompt 2 / Prompt 5 can **raise** `CommentaryIntegrityError`.

### Tolerances (do not loosen)

| Kind | Constant | Value |
|------|----------|-------|
| Money / actuals | `TOL_ACTUALS` | **$1.00** |
| Ratios | `TOL_RATIO` | `0.0005` (absolute on ratio form) |
| Percent points | `TOL_PERCENT_POINTS` | `0.05` (when evidence stores whole percents) |

Callers cannot pass a looser `money_tolerance` — `verify_text_against_evidence` raises `ValueError` if not `TOL_ACTUALS`.

---

## 3. Coverage map — covered vs open

| Surface | Status | Notes |
|---------|--------|-------|
| Commentary generate API | **Live** | Section-level strip; soft log warning; still returns package with don't-know sections |
| MD&A Prompt 2 | **Live (harder)** | Matrix mismatch → hard block; post-LLM strip; fully unverifiable variance sheet → hard block |
| Prompt 5 deck generation | **Live (hard block)** | String-literal $/%/Nx vs deck payload; invent → block emit. Chart array / layout coords not scanned |
| Board slide regenerate | **Live (soft strip)** | Per-bullet don't-know; all-unverifiable → don't-know narrative |
| Copilot / chat paths | **Partial (thin wire)** | Blob-derived evidence allowlist; fail-closed don't-know. **Gap:** freeze/live prose is not structured `_sources`; bare integers in answers may be under-constrained if absent from blob parse |
| Full `_sources` provenance object on every LLM payload | **Open** | Framework Part 1; commentary ships flatter `evidence_package.values` |
| Driver / attribution claim verify (non-numeric) | **Live (primary paths)** | Helper + commentary, Prompt 2, Prompt 5, board regenerate, Copilot thin wire — see [ai_attribution_verify.md](./ai_attribution_verify.md). Remaining: stronger Copilot structured evidence + FE↔Board single-source |
| Production FE↔Board single-source | **Open (confirm + test)** | Demo dual-seed `data_mismatch` documented; do not reseed demos; confirm production warehouse share |
| DOM `data-source` + full `runTieOut()` A–F publish gate | **Open** | See framework + tie-out prompt |

---

## 4. Docs to read

| Doc | Path |
|-----|------|
| Controls status table + changelog | `docs/soc2/controls/README.md` |
| This checklist | `docs/soc2/controls/ai_claim_verify.md` |
| Attribution / driver design | `docs/soc2/controls/ai_attribution_verify.md` |
| Scoreboard note | `docs/soc2/PROGRESS.md` (§ “What we shipped 2026-07-30”) |
| Normative `_sources` / second-pass design | `docs/soc2/controls/data_integrity_framework.md` (Parts 1, 2, 5) — Guarantee 4 = machine-primary |
| Approved policy | `docs/soc2/policies/P15_ai_llm_data_handling.md` |

---

## 5. Tests

| File | Covers |
|------|--------|
| `backend/tests/test_claim_verify.py` | `TOL_ACTUALS=$1`; extract money/%/ratio; match pass; invented → don't-know; empty evidence → missing; tolerance cannot loosen; section-only rewrite; generate embeds evidence + strips invented; variance tie-out `fail_closed=True` raises; PPTX script string-literal verify; bullet list strip; blob evidence |
| `backend/tests/test_attribution_verify.py` | Causal extract; allowed driver pass; invented driver fail-closed; empty allowlist strips causal; numeric-only unaffected; commentary generate embeds attribution package + strips invented cause; deck allowlist; bullet attribution strip; PPTX soft-strip + hard-block-when-fully-wiped; Copilot blob allowlist thin wire |
| `backend/tests/test_commentary_service.py` | Sparse inputs + invented dollars → don't-know; evidence package in prompt |

---

## 6. Matt review checklist

- [ ] Confirm live paths match product risk: commentary generate + MD&A Prompt 2 + Prompt 5 + board regenerate (+ Copilot thin wire) for this increment
- [ ] Confirm remaining open items (full `_sources`, stronger Copilot attribution evidence, production single-source test) are acceptable follow-ups
- [ ] Confirm **$1.00** actuals bar stays non-negotiable
- [ ] Confirm fail-closed semantics: soft strip vs hard block (`CommentaryIntegrityError`) are correct per surface
- [x] Wire Prompt 5 deck generation and Board slide regenerate to claim_verify.py
- [x] Scope a design for non-numeric (driver/attribution) claim verification — [ai_attribution_verify.md](./ai_attribution_verify.md)
- [x] v1 attribution helper live on commentary generate + MD&A Prompt 2
- [x] Wire attribution through Prompt 5 + board regenerate + Copilot thin wire
- [ ] Confirm production Forecast Engine and Board Platform read one shared warehouse source per customer (not independently-loaded datasets, per the demo-environment finding in reconcile_financial_statements.md); add an automated test for this specifically
- [x] Confirm data_integrity_framework.md's Guarantee 4 has been corrected to match README's machine-primary adaptation
- [ ] Accept Copilot as **thin wire** (blob evidence + thin attribution labels) until structured `_sources` lands — do not claim full Copilot coverage
- [x] Merge `feat/p15-claim-verify-fail-closed` (PR #55)
- [x] Merge `feat/p15-attribution-verify` (PR #56)

---

_End of AI claim-verify coverage checklist_
