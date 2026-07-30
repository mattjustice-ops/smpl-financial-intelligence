# P15 AI claim-verify — coverage checklist (founder review)

> **Not SOC 2 certification.** Product integrity gate for AI-stated numbers vs engine evidence.  
> **Branch note:** numeric claim-verify merged via PR #55 (`main`). Attribution via PR #56–#58; `_sources` + drivers + hydrate residue via PR #59. This branch: **DOM `data-source` overlay + partial client `runTieOut` publish gate** (Board/FE UI).  
> **Policy:** [P15 §4.7 / §4.8](../policies/P15_ai_llm_data_handling.md) · **Status snapshot:** [README.md](./README.md)  
> **Non-numeric drivers:** [ai_attribution_verify.md](./ai_attribution_verify.md)

Use this page to confirm what shipped, what is still open, and where to open the code.

---

## 1. What shipped (2026-07-30)

| Path | Behavior | Code |
|------|----------|------|
| `/api/v1/commentary/generate` | Evidence package in prompt → LLM → schema validate → **post-LLM numeric claim verify** → strip / don't-know bad sections | `backend/app/services/commentary/service.py`, `prompts.py`, `claim_verify.py` |
| MD&A Prompt 2 package | **Hard block** if variance display ≠ period_matrix; walk nested commentary strings; don't-know on fail; **block emit** if variance sheet is fully unverifiable | `backend/app/services/reporting/export/prompt2_mda_package.py`, `board_platform_metrics.py` |
| MD&A Prompt 5 deck | Evidence preview in user message; post-LLM verify of **$ / % / Nx in PPTX string literals** vs flattened deck payload; **hard block** (`CommentaryIntegrityError`) before Node render (adapt + fresh) | `backend/app/services/reporting/export/prompt5_deck.py` |
| Board slide regenerate | Flatten slide payload (+ freeze blob numbers) → per-bullet verify → don't-know on fail; all-bad → don't-know narrative | `backend/app/services/reporting/export/board_commentary_service.py` (`enrich_slide_with_ai`) |
| Board Copilot | **Structured packages:** evidence/attribution built from bundle / TS_DATA / cash bridge; freeze packs store packages in `sections`; post-LLM verify (+ blob supplement) | `board_platform_routes.py`, `claim_verify.build_evidence_package_from_copilot_structures` |
| **`_sources` on evidence packages** | Every evidence value key gets a citable source tag (WAREHOUSE table/column, COMPUTED formula_id, or ENGINE_PATH). Embedded in commentary / Copilot prompt packages via `evidence_package_for_prompt` | `claim_verify.attach_sources_to_values`, `_SOURCE_FIELD_CATALOG` |

Reusable helper: `backend/app/services/commentary/claim_verify.py`

**Attribution (non-numeric) on the same paths:** see [ai_attribution_verify.md](./ai_attribution_verify.md).

---

## 2. Algorithm (short)

1. **Build evidence** — flatten engine / freeze / display numbers into `evidence_package.values`; attach `_sources` per key.
2. **Prompt** — embed the same package (values + `_sources`) so the model is told to state only those values and cite paths.
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
| Copilot / chat paths | **Live (structured + blob supplement)** | Evidence/attribution from bundle/TS/cash (+ frozen packages); fail-closed don't-know |
| `_sources` on evidence packages | **Live (v1 contract)** | Catalog + ENGINE_PATH on primary package builders; freeze persists `_sources`. DOM overlay consumes when hydrate includes `_sources`; **not** full warehouse `loaded_at` / `org_id` / `is_final` on every row |
| Driver / attribution claim verify (non-numeric) | **Live (primary paths)** | Deal-count / logo / dominance enrichment — see [ai_attribution_verify.md](./ai_attribution_verify.md) |
| Production FE↔Board single-source | **Confirmed + hydrate residue fix** | Shared outlook API/builder; merge replace + prune closed Actuals — [fe_board_single_source.md](./fe_board_single_source.md) |
| DOM `data-source` + audit overlay | **Partial — live (UI)** | Board/FE KPIs via `smpl-provenance.js`; prefers hydrate `_sources` when present; catalog fallback; `Ctrl+Shift+A` — [fe_board_single_source.md](./fe_board_single_source.md) |
| Client `runTieOut()` publish gate | **Partial — live (Rule C/A)** | TS↔SRC Actuals + ARR identities; live FAIL blocks MD&A export + FINAL forecast promote; **not** full Rule Sets A–F |

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
| `backend/tests/test_claim_verify.py` | `TOL_ACTUALS=$1`; extract money/%/ratio; match pass; invented → don't-know; empty evidence → missing; tolerance cannot loosen; section-only rewrite; generate embeds evidence + strips invented; variance tie-out `fail_closed=True` raises; PPTX script string-literal verify; bullet list strip; blob evidence; **Copilot structured evidence + `_sources` tags**; commentary package `_sources` |
| `backend/tests/test_attribution_verify.py` | Causal extract; allowed driver pass; invented driver fail-closed; empty allowlist strips causal; numeric-only unaffected; commentary generate embeds attribution package + strips invented cause; deck allowlist; bullet attribution strip; PPTX soft-strip + hard-block-when-fully-wiped; Copilot blob allowlist; **Copilot structured waterfall/cash attribution**; **deal-count / logo / dominance** |
| `backend/tests/test_commentary_service.py` | Sparse inputs + invented dollars → don't-know; evidence package in prompt |
| `backend/tests/test_outlook_ts_src_actuals_alignment.py` | Production outlook `TS_DATA.Actual` ↔ `SRC.actuals` within $1; divergence / one-side-missing fail |
| `frontend/scripts/verify-outlook-hydrate.mjs` | Partial live hydrate replaces period rows + prunes closed demo Actual residue (no reseed) |
| `frontend/scripts/verify-provenance-tieout.mjs` | `data-source` attrs from catalog/`_sources`; annotateDom; runTieOut pass/fail; live gate blocks / demo warns |

---

## 6. Matt review checklist

- [ ] Confirm live paths match product risk: commentary generate + MD&A Prompt 2 + Prompt 5 + board regenerate + Copilot structured packages for this increment
- [ ] Confirm DOM overlay + partial client tie-out gate match product risk for this increment
- [ ] Confirm remaining open items (full Rule Sets A–F, warehouse loaded_at/org_id on every tag) are acceptable follow-ups
- [ ] Confirm **$1.00** actuals bar stays non-negotiable
- [ ] Confirm fail-closed semantics: soft strip vs hard block (`CommentaryIntegrityError`) are correct per surface
- [x] Wire Prompt 5 deck generation and Board slide regenerate to claim_verify.py
- [x] Scope a design for non-numeric (driver/attribution) claim verification — [ai_attribution_verify.md](./ai_attribution_verify.md)
- [x] v1 attribution helper live on commentary generate + MD&A Prompt 2
- [x] Wire attribution through Prompt 5 + board regenerate + Copilot thin wire
- [x] Confirm production Forecast Engine and Board Platform read one shared warehouse source per customer; automated TS↔SRC regression — [fe_board_single_source.md](./fe_board_single_source.md)
- [x] Confirm data_integrity_framework.md's Guarantee 4 has been corrected to match README's machine-primary adaptation
- [x] Upgrade Copilot from thin blob wire to structured evidence/attribution packages
- [x] Attach `_sources` to primary evidence packages (commentary / Copilot / freeze)
- [x] FE hydrate merge residue fix (replace + prune; no demo reseed)
- [x] Merge `feat/p15-claim-verify-fail-closed` (PR #55)
- [x] Merge `feat/p15-attribution-verify` (PR #56)
- [x] Merge `feat/p15-attribution-wire-remaining` (PR #57)
- [x] Merge `feat/p15-copilot-evidence-fe-board-source` (PR #58)
- [x] Merge `feat/p15-sources-drivers-hydrate` (PR #59)
- [x] DOM `data-source` overlay + audit hotkey on Board/FE material KPIs
- [x] Partial client `runTieOut` publish gate (live export / FINAL promote)

---

### Honesty — DOM overlay + partial gate (this increment)

| Wired | Not wired |
|-------|-----------|
| `_sources` map on evidence packages + freeze | Full warehouse `loaded_at`, `org_id`, `is_final` on every tag |
| DOM `data-source` / title / aria on Board + FE material KPIs; audit overlay hotkey | Every chart datapoint / commentary number tagged |
| Client catalog fallback when hydrate omits `_sources` | Outlook API always emitting `_sources` for UI (consumes when present) |
| Partial `runTieOut` Rule C + ARR A2/A3; live FAIL blocks MD&A export + FINAL promote | Full Rule Sets A–F + HTML warehouse tie-out report as publish gate |
| ENGINE_PATH fallback so every value remains citable by dotted key | Automatic citation enforcement in post-LLM verify (verify still matches **values**, not source strings) |

---

_End of AI claim-verify coverage checklist_
