# P15 AI claim-verify — coverage checklist (founder review)

> **Not SOC 2 certification.** Product integrity gate for AI-stated numbers vs engine evidence.  
> **Branch note:** on main after prior PRs. This branch adds DOM overlay + runTieOut; citation/tags/AND already on main.  
> **Policy:** [P15 §4.7 / §4.8](../policies/P15_ai_llm_data_handling.md) · **Status snapshot:** [README.md](./README.md)  
> **Non-numeric drivers:** [ai_attribution_verify.md](./ai_attribution_verify.md)

Use this page to confirm what shipped, what is still open, and where to open the code.

---

## 1. What shipped (this increment)

| Path | Behavior | Code |
|------|----------|------|
| `/api/v1/commentary/generate` | Numeric verify → attribution verify → **citation verify** → soft strip / don't-know | `service.py`, `citation_verify.py`, `claim_verify.py` |
| MD&A Prompt 2 | Nested string numeric + attribution + **citation** walk; hard block if variance fully wiped | `prompt2_mda_package.py` |
| MD&A Prompt 5 deck | Evidence preview; post-LLM verify of **$ / % / Nx in PPTX string literals**; **hard block** before Node render (adapt + fresh). Citation gate not on PPTX literals this slice | `prompt5_deck.py` |
| Board slide regenerate | Flatten slide payload → per-bullet verify → don't-know on fail; all-bad → don't-know narrative | `board_commentary_service.py` |
| Board Copilot | Numeric + attribution + **citation** on answer; live packages carry org/loaded_at tags | `board_platform_routes.py` |
| **`_sources` warehouse tags** | Every source tag includes `org_id` / `loaded_at` / `is_final` (honest nulls when unknown) | `claim_verify.build_source_record` |
| **Post-LLM citation check** | Material money/%/Nx must cite `_sources` key, `table.column`, `formula_id`, or path | `citation_verify.py` |
| **DOM `data-source` overlay** | Board/FE material KPIs tagged; prefers hydrate `_sources`; catalog fallback; `Ctrl+Shift+A` audit | `smpl-provenance.js` |
| **Client `runTieOut` publish gate** | Partial Rule C/A; live FAIL blocks MD&A export + FINAL forecast promote | `smpl-provenance.js`, `board-hydrate.js` |

Reusable helpers: `claim_verify.py`, `citation_verify.py`, `attribution_verify.py`

**Attribution (non-numeric) on the same paths:** see [ai_attribution_verify.md](./ai_attribution_verify.md) (includes multi-driver AND rule).

---

## 2. Algorithm (short)

1. Build evidence values + `_sources` (with warehouse tags).
2. Prompt embeds the same package.
3. Extract numeric claims; match within **$1.00** / ratio tolerances.
4. Attribution allowlist check (multi-driver AND → all required).
5. Citation check: each material money/%/Nx cites a `_sources` token (inline or `citations[].label`).
6. Fail closed → don't-know / omit (Prompt 2 may hard-block).

### Agreed citation formats

| Form | Example |
|------|---------|
| Evidence key | `$110,000 (mrr_waterfall.ending_mrr)` |
| Key + period | `$86.1M (arr_waterfall.ending_arr, period 2026-06)` |
| table.column | `$7.4M (income_statement.revenue)` |
| Structured list | `citations[].label = "mrr_waterfall.ending_mrr"` |

### Tolerances (do not loosen)

| Kind | Constant | Value |
|------|----------|-------|
| Money / actuals | `TOL_ACTUALS` | **$1.00** |
| Ratios | `TOL_RATIO` | `0.0005` |
| Percent points | `TOL_PERCENT_POINTS` | `0.05` |

Callers cannot pass a looser `money_tolerance` — `verify_text_against_evidence` raises `ValueError` if not `TOL_ACTUALS`.

---

## 3. Coverage map — covered vs open

| Surface | Status | Notes |
|---------|--------|-------|
| Commentary generate API | **Live** | Numeric → attribution → citation; section-level strip; soft log warning; still returns package with don't-know sections |
| MD&A Prompt 2 | **Live (harder)** | Matrix mismatch → hard block; post-LLM strip + citation; fully unverifiable variance sheet → hard block |
| Prompt 5 deck generation | **Live (hard block)** | String-literal $/%/Nx vs deck payload; invent → block emit. Chart array / layout coords not scanned. Citation gate not on PPTX literals this slice |
| Board slide regenerate | **Live (soft strip)** | Per-bullet don't-know; all-unverifiable → don't-know narrative (prior numeric/attribution; citation not on this path this slice) |
| Copilot / chat paths | **Live (structured + blob supplement)** | Evidence/attribution/citation from bundle/TS/cash (+ frozen packages); fail-closed don't-know |
| `_sources` + warehouse tags | **Live (v1 + honest nulls)** | Catalog + ENGINE_PATH on primary builders; freeze: org + loaded_at + is_final=true; live Copilot: org + loaded_at + is_final=false (nulls when unknown). DOM overlay consumes when hydrate includes `_sources` |
| Driver / attribution claim verify (non-numeric) | **Live (primary paths)** | Deal-count / logo / dominance + multi-driver AND — see [ai_attribution_verify.md](./ai_attribution_verify.md) |
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
| `backend/tests/test_claim_verify.py` | `TOL_ACTUALS=$1`; extract money/%/ratio; match pass; invented → don't-know; empty evidence → missing; tolerance cannot loosen; section-only rewrite; generate embeds evidence + strips invented; variance tie-out `fail_closed=True` raises; PPTX script string-literal verify; bullet list strip; blob evidence; **Copilot structured evidence + `_sources` / warehouse tags**; commentary package `_sources` |
| `backend/tests/test_citation_verify.py` | Inline/structured citation; warehouse tags; material money/%/Nx must cite `_sources` token |
| `backend/tests/test_attribution_verify.py` | Causal extract; allowed driver pass; invented driver fail-closed; empty allowlist strips causal; numeric-only unaffected; commentary generate embeds attribution package + strips invented cause; deck allowlist; bullet attribution strip; PPTX soft-strip + hard-block-when-fully-wiped; Copilot blob allowlist; **Copilot structured waterfall/cash attribution**; **deal-count / logo / dominance**; **multi-driver AND/comma require-all** |
| `backend/tests/test_commentary_service.py` | Sparse inputs + invented dollars → don't-know; evidence package in prompt; happy path with `_sources` cites |
| `backend/tests/test_outlook_ts_src_actuals_alignment.py` | Production outlook `TS_DATA.Actual` ↔ `SRC.actuals` within $1; divergence / one-side-missing fail |
| `frontend/scripts/verify-outlook-hydrate.mjs` | Partial live hydrate replaces period rows + prunes closed demo Actual residue (no reseed) |
| `frontend/scripts/verify-provenance-tieout.mjs` | `data-source` attrs from catalog/`_sources`; annotateDom; runTieOut pass/fail; live gate blocks / demo warns |

---

## 6. Matt review checklist

- [ ] Confirm live paths match product risk: commentary generate + MD&A Prompt 2 + Prompt 5 + board regenerate + Copilot structured packages for this increment
- [ ] Confirm citation formats are the right bar
- [ ] Confirm warehouse tags with honest nulls are acceptable
- [ ] Confirm DOM overlay + partial client tie-out gate match product risk for this increment
- [ ] Confirm remaining open items (full Rule Sets A–F, citation on Prompt 5 PPTX literals) are acceptable follow-ups
- [ ] Confirm **$1.00** actuals bar stays non-negotiable
- [ ] Confirm fail-closed semantics: soft strip vs hard block (`CommentaryIntegrityError`) are correct per surface
- [ ] Merge when review OK — not SOC 2 certified
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
- [x] Post-LLM citation verify + warehouse tags (`org_id` / `loaded_at` / `is_final`) + multi-driver AND (on main via citation PR)
- [x] DOM `data-source` overlay + audit hotkey on Board/FE material KPIs
- [x] Partial client `runTieOut` publish gate (live export / FINAL promote)

---

### Honesty — citation + warehouse tags (on main)

| Wired | Not wired |
|-------|-----------|
| Post-LLM citation check on commentary generate, MD&A Prompt 2, Copilot | Citation gate on Prompt 5 PPTX string literals / board regenerate bullets |
| `_sources` tags include `org_id` / `loaded_at` / `is_final` (honest nulls when unknown) | Every chart datapoint / commentary number forced to cite at render time |
| Freeze packs: org + loaded_at + is_final=true | Older freeze packs without tagged `_sources` |
| Live Copilot: org + loaded_at + is_final=false | — |

### Honesty — DOM overlay + partial gate (this branch)

| Wired | Not wired |
|-------|-----------|
| DOM `data-source` / title / aria on Board + FE material KPIs; audit overlay hotkey | Every chart datapoint / commentary number tagged |
| Client catalog fallback when hydrate omits `_sources` | Outlook API always emitting `_sources` for UI (consumes when present) |
| Partial `runTieOut` Rule C + ARR A2/A3; live FAIL blocks MD&A export + FINAL promote | Full Rule Sets A–F + HTML warehouse tie-out report as publish gate |
| Prefers hydrate `_sources` when present for overlay labels | — |

---

_End of AI claim-verify coverage checklist_
