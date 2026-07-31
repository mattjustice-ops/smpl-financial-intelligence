# P15 AI claim-verify — coverage checklist (founder review)

> **Not SOC 2 certification.** Product integrity gate for AI-stated numbers vs engine evidence.  
> **Branch note:** `feat/p15-integrity-finish` completes client A–F + Prompt 5/board citation.  
> **Policy:** [P15 §4.7 / §4.8](../policies/P15_ai_llm_data_handling.md) · **Status snapshot:** [README.md](./README.md)  
> **Non-numeric drivers:** [ai_attribution_verify.md](./ai_attribution_verify.md)

Use this page to confirm what shipped, what is still open, and where to open the code.

---

## 1. What shipped (this increment)

| Path | Behavior | Code |
|------|----------|------|
| `/api/v1/commentary/generate` | **Interactive policy:** numeric + citation **soft-warn** (board numbers trusted); attribution + forward-looking **surgical strip** | `service.py`, `citation_verify.py`, `claim_verify.py`, `attribution_verify.py` |
| MD&A Prompt 2 | Nested string numeric + attribution + **citation** walk; hard block if variance fully wiped (**strict** — deck publish) | `prompt2_mda_package.py` |
| MD&A Prompt 5 deck | **Widened evidence package** (actuals ≤ close, forecast after close, pipeline/deals, cash/ARR bridges, variance drivers) + `_sources` (`series_kind` where tagged) + attribution (incl. forecast/pipeline forward keys) in prompt; post-LLM verify of **$ / % / Nx in PPTX string literals**; numeric **soft-strip** (short KPI/table cells → `—`, narrative → don't-know); citation **warn-only** (do not wipe uncited board cells); attribution soft-strip; prefer export even when fully wiped. Prompt: cite in takeaways, not inside KPI/table cells | `prompt5_deck.py`, `board_platform_metrics.build_evidence_package_from_deck_payload` |
| Board slide regenerate | **Interactive:** numeric + citation soft-warn; attribution / forward surgical strip; all-story-wiped → don't-know | `board_commentary_service.py` |
| Board Copilot | **Interactive:** numeric + citation soft-warn; attribution + forward surgical strip | `board_platform_routes.py` |
| **`_sources` warehouse tags** | Every source tag includes `org_id` / `loaded_at` / `is_final` (honest nulls when unknown) | `claim_verify.build_source_record` |
| **Post-LLM citation check** | Material money/%/Nx should cite `_sources`; **strict** on Prompt 2 (hard-block when fully wiped); Prompt 5 **warn-only** (board KPI/table cells trusted from payload); **interactive** warn only | `citation_verify.py` |
| **DOM `data-source` overlay** | Board/FE material KPIs tagged; prefers hydrate `_sources`; catalog fallback; `Ctrl+Shift+A` audit | `smpl-provenance.js` |
| **Client `runTieOut` advisory export** | Client Rule Sets A–F when local data exists; FAIL → **WARN** + HTML companion; MD&A export + FINAL promote **proceed** (hard actuals ID at import/close). Forecast C5/F4 soft after close | `smpl-provenance.js`, `board-hydrate.js` |

Reusable helpers: `claim_verify.py`, `citation_verify.py`, `attribution_verify.py` (`VerifyPolicy`: `strict` \| `interactive`)

**Attribution (non-numeric) on the same paths:** see [ai_attribution_verify.md](./ai_attribution_verify.md) (includes multi-driver AND + forward/pipeline grounding).

### Product split (honest)

| Surface | Numbers ($ / % / cites) | Story (what happened + outlook) |
|---------|-------------------------|----------------------------------|
| Commentary generate, board regenerate, Copilot | Trusted — verify + **warn/log**; do **not** replace the whole answer for unmatched $/% or missing cites alone (demo / incomplete evidence packages) | Attribution fail-closed via **surgical clause strip**; forward-looking must ground in **forecast / pipeline** allowlist |
| Prompt 5 deck | Soft-strip unmatched $/% in PPTX strings (cells → `—`); citation **warn-only**; **export continues** (board/warehouse numbers trusted; demo evidence gaps must not block the deck) | Attribution soft-strip; prefer export with stripped text over hard-block |
| Prompt 2 MD&A package | Keep **strict** fail-closed / hard-block when variance sheet fully wiped | Soft strip; hard-block when fully wiped |
| Tie-out identification | Hard gate remains an **import/close** concern — not regenerate/Copilot / Prompt 5 export | — |

---

## 2. Algorithm (short)

1. Build evidence values + `_sources` (with warehouse tags).
2. Prompt embeds the same package.
3. Extract numeric claims; match within **$1.00** / ratio tolerances.
4. Attribution allowlist check (multi-driver AND → all required); forward-looking → forecast/pipeline subset.
5. Citation check: each material money/%/Nx cites a `_sources` token (inline or `citations[].label`).
6. Apply policy: **interactive** soft-warns numeric/citation and surgically strips bad story clauses; Prompt 5 soft-strips invented PPTX numbers (cells → `—`), citation warn-only, and exports; **strict** don't-know / hard-block remains on Prompt 2 when fully wiped.

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
| Commentary generate API | **Live (interactive)** | Numeric + citation soft-warn; attribution / forward surgical strip |
| MD&A Prompt 2 | **Live (harder / strict)** | Matrix mismatch → hard block; post-LLM strip + citation; fully unverifiable variance sheet → hard block |
| Prompt 5 deck generation | **Live (soft-strip + export)** | Widened evidence (actual/forecast/pipeline/bridges) so rich board story can use package context without false shutdowns; invent still soft-strips (KPI/table cells → `—`, not don't-know essays); citation **warn-only** (uncited board cells kept); attribution soft-strip; **export continues**. Chart array / layout coords not scanned. Export-time warehouse / client A–F validation unchanged (advisory). |
| Board slide regenerate | **Live (interactive)** | Numeric + citation soft-warn; attribution / forward surgical strip; all-story-wiped → don't-know |
| Copilot / chat paths | **Live (interactive)** | Structured packages + blob supplement; numeric/citation soft-warn; story strip |
| `_sources` + warehouse tags | **Live (v1 + honest nulls)** | Catalog + ENGINE_PATH on primary builders; freeze: org + loaded_at + is_final=true; live Copilot: org + loaded_at + is_final=false (nulls when unknown). DOM overlay consumes when hydrate includes `_sources` |
| Driver / attribution claim verify (non-numeric) | **Live (primary paths)** | Deal-count / logo / dominance + multi-driver AND — see [ai_attribution_verify.md](./ai_attribution_verify.md) |
| Production FE↔Board single-source | **Confirmed + hydrate residue fix** | Shared outlook API/builder; merge replace + prune closed Actuals — [fe_board_single_source.md](./fe_board_single_source.md) |
| DOM `data-source` + audit overlay | **Partial — live (UI)** | Board/FE KPIs via `smpl-provenance.js`; prefers hydrate `_sources` when present; catalog fallback; `Ctrl+Shift+A` — [fe_board_single_source.md](./fe_board_single_source.md) |
| Client `runTieOut()` at export | **Partial — advisory (client A–F)** | A–F when SRC/TS/WF/engine/display present; skips D2–D4 / E / B2 / F5 without data; FAIL → WARN + HTML companion (does **not** block export/promote); C5/F4 forecast soft; hard production-actuals ID at import/close (roadmap) |

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
| `backend/tests/test_claim_verify.py` | `TOL_ACTUALS=$1`; extract money/%/ratio; match pass; invented → don't-know (**strict**); **interactive keeps unmatched $**; empty evidence → missing; tolerance cannot loosen; section-only rewrite; generate embeds evidence + keeps numbers interactive; variance tie-out `fail_closed=True` raises; PPTX string-literal verify; **PPTX soft-strip + Prompt 5 export-continues**; **Prompt 5 widened evidence: forecast/pipeline in package verify, invent still strips**; error summaries include failed claim samples; bullet list strip; blob evidence; **Copilot structured evidence + `_sources` / warehouse tags**; commentary package `_sources` |
| `backend/tests/test_citation_verify.py` | Inline/structured citation; warehouse tags; material money/%/Nx must cite `_sources` token (**strict**); **interactive keeps uncited $**; **PPTX soft-strip helper** (cells → `—`); optional raise_if helper still hard-blocks when fully wiped (Prompt 5 warn-only, does not rewrite); **bullet citation strip** |
| `backend/tests/test_attribution_verify.py` | Causal extract; allowed driver pass; invented driver fail-closed; empty allowlist strips causal; numeric-only unaffected; commentary generate embeds attribution package + strips invented cause; deck allowlist; bullet attribution strip; **interactive surgical strip**; **forward-looking forecast/pipeline grounding**; PPTX soft-strip; optional raise_if helper (Prompt 5 does not call it); Copilot blob allowlist; **Copilot structured waterfall/cash attribution**; **deal-count / logo / dominance**; **multi-driver AND/comma require-all** |
| `backend/tests/test_commentary_service.py` | Sparse inputs keep numbers under interactive policy; evidence package in prompt; happy path with `_sources` cites |
| `backend/tests/test_outlook_ts_src_actuals_alignment.py` | Production outlook `TS_DATA.Actual` ↔ `SRC.actuals` within $1; divergence / one-side-missing fail |
| `frontend/scripts/verify-outlook-hydrate.mjs` | Partial live hydrate replaces period rows + prunes closed demo Actual residue (no reseed) |
| `frontend/scripts/verify-provenance-tieout.mjs` | `data-source` attrs; annotateDom; client A–F runTieOut pass/fail; HTML WARN advisory; export not blocked; C5/F4 forecast soft; `forceBlock` escape hatch |

---

## 6. Matt review checklist

- [ ] Confirm live paths match product risk: commentary generate + MD&A Prompt 2 + Prompt 5 + board regenerate + Copilot structured packages for this increment
- [ ] Confirm citation formats are the right bar (including Prompt 5 PPTX string literals)
- [ ] Confirm warehouse tags with honest nulls are acceptable
- [ ] Confirm DOM overlay + **advisory** client A–F + HTML companion match product risk (hard ID at import/close, not export)
- [ ] Confirm remaining open items (import-time actuals gate; live warehouse SQL HTML; D2–D4/E/B2/F5 without tables) are acceptable follow-ups
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
- [x] Client `runTieOut` advisory on live export / FINAL promote (HTML companion; not hard-block)
- [x] Client Rule Sets A–F + client HTML tie-out report; forecast C5/F4 soft after close
- [x] Citation verify on Prompt 5 PPTX string literals + board regenerate bullets

---

### Honesty — citation + warehouse tags

| Wired | Not wired |
|-------|-----------|
| Post-LLM citation check on commentary generate, MD&A Prompt 2, Copilot, **Prompt 5 PPTX literals**, **board regenerate bullets** | Every chart datapoint / commentary number forced to cite at render time |
| `_sources` tags include `org_id` / `loaded_at` / `is_final` (honest nulls when unknown) | Older freeze packs without tagged `_sources` |
| Freeze packs: org + loaded_at + is_final=true | — |
| Live Copilot: org + loaded_at + is_final=false | — |
| Prompt 5 payload attaches `_sources` from deck evidence flatten; citation **warn-only** on export | Gold/adapt reference scripts may omit `(source.key)` in KPI cells; invent still soft-strips; **deck still exports** |

### Honesty — DOM overlay + client A–F gate

| Wired | Not wired |
|-------|-----------|
| DOM `data-source` / title / aria on Board + FE material KPIs; audit overlay hotkey | Every chart datapoint / commentary number tagged |
| Client catalog fallback when hydrate omits `_sources` | Outlook API always emitting `_sources` for UI (consumes when present) |
| Client Rule Sets A–F when SRC/TS/WF/engine/display present; FAIL → WARN + HTML; export/promote proceed | Import/close fail-closed for production actuals; live warehouse SQL HTML report |
| Client HTML tie-out report (advisory companion); C5/F4 forecast soft after close | D2–D4 / E warehouse quota-ops / B2 bank balances / F5 payroll soft without those tables in client |
| Prefers hydrate `_sources` when present for overlay labels | — |

---

_End of AI claim-verify coverage checklist_
