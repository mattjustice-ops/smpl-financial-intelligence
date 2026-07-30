# P15 AI claim-verify — coverage checklist (founder review)

> **Not SOC 2 certification.** Product integrity gate for AI-stated numbers vs engine evidence.  
> **Branch:** `feat/p15-claim-verify-fail-closed` (as of 2026-07-30 — **not merged to `main`** unless noted otherwise).  
> **Policy:** [P15 §4.7 / §4.8](../policies/P15_ai_llm_data_handling.md) · **Status snapshot:** [README.md](./README.md)

Use this page to confirm what shipped, what is still open, and where to open the code.

---

## 1. What shipped (2026-07-30)

| Path | Behavior | Code |
|------|----------|------|
| `/api/v1/commentary/generate` | Evidence package in prompt → LLM → schema validate → **post-LLM numeric claim verify** → strip / don't-know bad sections | `backend/app/services/commentary/service.py`, `prompts.py`, `claim_verify.py` |
| MD&A Prompt 2 package | **Hard block** if variance display ≠ period_matrix; walk nested commentary strings; don't-know on fail; **block emit** if variance sheet is fully unverifiable | `backend/app/services/reporting/export/prompt2_mda_package.py`, `board_platform_metrics.py` |

Reusable helper: `backend/app/services/commentary/claim_verify.py`

---

## 2. Algorithm (short)

1. **Build evidence** — flatten engine / freeze / display numbers into `evidence_package.values` (`build_evidence_package` / `flatten_evidence_values` / MD&A `evidence_values_from_mda_payload`).
2. **Prompt** — embed the same package so the model is told to state only those values.
3. **Extract claims** — `$` amounts (incl. K/M/B), `%`, multipliers (`Nx`), select ratios (`extract_numeric_claims`).
4. **Match** — each claim vs any evidence value within tolerance (`verify_text_against_evidence` / `_best_match`).
5. **Fail closed** — mismatch or missing evidence → replace text with don't-know / omit section content; never emit unsupported material claims. MD&A can **raise** `CommentaryIntegrityError` (matrix mismatch or all-unverifiable variance sheet).

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
| Board slide regenerate | **Open** | Same helper not wired |
| Prompt 5 deck generation | **Open** | Same helper not wired |
| Copilot / chat paths | **Open** | Framework Part 5 / Copilot runtime verify still roadmap |
| Full `_sources` provenance object on every LLM payload | **Open** | Framework Part 1; commentary ships flatter `evidence_package.values` |
| Driver / attribution claim verify (non-numeric) | **Open** | P15 requires structural verify of driver attributions; this helper is **numeric-only** |
| DOM `data-source` + full `runTieOut()` A–F publish gate | **Open** | See framework + tie-out prompt |

---

## 4. Docs to read

| Doc | Path |
|-----|------|
| Controls status table + changelog | `docs/soc2/controls/README.md` |
| This checklist | `docs/soc2/controls/ai_claim_verify.md` |
| Scoreboard note | `docs/soc2/PROGRESS.md` (§ “What we shipped 2026-07-30”) |
| Normative `_sources` / second-pass design | `docs/soc2/controls/data_integrity_framework.md` (Parts 1, 2, 5) |
| Approved policy | `docs/soc2/policies/P15_ai_llm_data_handling.md` |

---

## 5. Tests

| File | Covers |
|------|--------|
| `backend/tests/test_claim_verify.py` | `TOL_ACTUALS=$1`; extract money/%/ratio; match pass; invented → don't-know; empty evidence → missing; tolerance cannot loosen; section-only rewrite; generate embeds evidence + strips invented; variance tie-out `fail_closed=True` raises |
| `backend/tests/test_commentary_service.py` | Sparse inputs + invented dollars → don't-know; evidence package in prompt |

---

## 6. Matt review checklist

- [ ] Confirm live paths match product risk: commentary generate + MD&A Prompt 2 are enough for this increment
- [ ] Confirm open items (board slides, Prompt 5, Copilot, full `_sources`, non-numeric drivers) are acceptable follow-ups
- [ ] Confirm **$1.00** actuals bar stays non-negotiable
- [ ] Confirm fail-closed semantics: soft strip vs hard block (`CommentaryIntegrityError`) are correct per surface
- [ ] Merge `feat/p15-claim-verify-fail-closed` when review OK

---

_End of AI claim-verify coverage checklist_
