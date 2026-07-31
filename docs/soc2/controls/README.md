# Data integrity & tie-out — normative design targets

> **Not SOC 2 certification.** These documents are **normative product / control design targets** for how SMPL prevents phantom numbers and wrong-context packaging in board/customer-facing outputs. Shipping status is labeled honestly below — do not claim full framework layers are live in production unless code and evidence show they are.

## Documents in this folder

| File | Role |
|------|------|
| [WAREHOUSE_GATE_NEAR_TERM_PLAN.md](./WAREHOUSE_GATE_NEAR_TERM_PLAN.md) | **Near-term plan (2–4 weeks)** — calculate → validate → AI explains validated evidence → fail closed; LIVE/PARTIAL/OPEN matrix; board must-haves vs nice-to-haves |
| [ai_claim_verify.md](./ai_claim_verify.md) | **Founder review checklist** — P15 fail-closed claim-verify: what shipped, tolerances, covered vs open paths, tests |
| [ai_attribution_verify.md](./ai_attribution_verify.md) | **Live on primary AI paths** — non-numeric driver/attribution verify (commentary, Prompt 2, Prompt 5, board regenerate, Copilot structured packages) |
| [fe_board_single_source.md](./fe_board_single_source.md) | **Production FE↔Board hydrate** — shared outlook API/builder confirmed + TS↔SRC $1 regression; demo dual-seed left alone |
| [data_integrity_framework.md](./data_integrity_framework.md) | Provenance (`_sources`), Claude runtime rules, build-time `data-source` tags, automated tie-out report, commentary second-pass verification, close review checklist |
| [data_sources_tieout_prompt.md](./data_sources_tieout_prompt.md) | Per-visual warehouse mapping + Rule Sets A–F + `runTieOut()` publish block |
| [reconcile_financial_statements.md](./reconcile_financial_statements.md) | FE ↔ Board closed-actuals diff + severity bands (`rounding` / `investigate` / `significant_miss`) — honest demo `data_mismatch` inventory |
| [financial_dashboard_cf_re_logic.md](./financial_dashboard_cf_re_logic.md) | **Customer / production** CF + RE construction methodology (`RE_BASE`, openings, three-rollup, dept-299). Does **not** change SMPL Demo Co / Board / FE demo behavior |

**Policy linkage:** [P15 AI / LLM Data Handling](../policies/P15_ai_llm_data_handling.md) §4.7 / §5 encodes these as required control design (machine-primary, fail-closed). IR Scenario B in [ir-tabletop.md](../runbooks/ir-tabletop.md) cites them as how prevention is *expected* to work.

## Product posture (non-negotiable)

- **Primary controls** = backend / automated **fail-closed** gates: provenance, `_sources`, structural claim verify, freeze-ID binding, tie-out / second-pass verification.
- **Not** human review before every send / **not** “users must re-validate.”
- **Human role** = incident response, exceptions, **periodic control testing** (see adaptation of Part 6 below).
- Embellishment / wrong-context packaging must be prevented by **system design**, not hope.

## Adaptation of source Part 6 (human sign-off)

The integrity framework’s Part 6 (“Finance review sign-off before every deployment”) is adapted for SMPL SOC 2 / product posture as follows:

| Source framing | SMPL adaptation |
|----------------|-----------------|
| Human sign-off of every tie-out report as the day-to-day deploy gate | **Automated** tie-out / commentary verification as deploy or release **gates** (fail closed on FAIL) |
| Finance checklist as primary control | Same checklist items become **periodic control testing** / exception review — not the primary gate for every board/customer package |
| “Human approves release” as Guarantee 4 | Humans approve **exceptions** and run **periodic tests**; day-to-day release safety is machine-primary |

Do **not** reintroduce “human review before send” as the primary control in policy, sales language, or IR root-cause framing.

## Implemented vs required design (honest snapshot — 2026-07-30)

Code search / product surface as of this write-up. Labels:

- **Implemented (partial)** — real code path exists; may be incomplete vs the full framework
- **Required control design / roadmap** — normative target; not shipping as specified

| Layer | Status | Notes |
|-------|--------|-------|
| Freeze pack required for some export / MD&A paths | **Partial — implemented** | e.g. `freeze_pack_required` hard-block when no COMPLETE/STALE pack; freeze context passed into commentary prompts |
| Financial / close tie-out validations | **Partial — implemented** | Close workflow financial integrity blockers; statement validation services; export validation summaries |
| MDA variance commentary vs period matrix check | **Partial — implemented (harder)** | `verify_variance_commentary_tieout(..., fail_closed=True)` **blocks MD&A Prompt 2 emit on value mismatch**; missing rows still soft-warn |
| `/commentary/generate` post-LLM claim verify | **Implemented (interactive)** | Numeric + citation soft-warn (board numbers trusted); attribution / forward surgical strip — [ai_claim_verify.md](./ai_claim_verify.md) |
| MD&A Prompt 2 post-LLM claim strip | **Partial — implemented (strict)** | Nested commentary strings verified against payload evidence; unverifiable cells → don't-know; all-unverifiable variance sheet **blocks emit** |
| Prompt 5 deck generation claim verify | **Implemented (soft-strip + export)** | Widened evidence (actuals ≤ close, forecast after close, pipeline/deals, bridges) + attribution forward keys embedded in Prompt 5; post-LLM soft-strip of unmatched $ / % / Nx in PPTX **string literals** (KPI/table cells → `—`); citation **warn-only** (uncited board cells kept); attribution soft-strip; deck **exports**. Prompt 2 remains stricter. |
| Board slide regenerate claim verify | **Implemented (interactive)** | Numeric + citation soft-warn; attribution / forward surgical strip; all-story-wiped → don't-know |
| Copilot runtime claim verify | **Implemented (interactive)** | Packages from bundle/TS/cash (+ freeze `sections`); numeric/citation soft-warn; story strip; `_sources` tags on values |
| Driver / attribution (non-numeric) claim verify | **Implemented on primary paths** | Helper + deal-count / logo / dominance + forward/pipeline grounding. Design + gaps: [ai_attribution_verify.md](./ai_attribution_verify.md) |
| Production single-source confirmation (FE + Board Platform) | **Confirmed + hydrate residue fix** | Shared outlook API/builder; TS↔SRC $1 regression; merge replace + prune closed Actuals — [fe_board_single_source.md](./fe_board_single_source.md) |
| `_sources` provenance object on every LLM payload | **Partial — implemented (v1 + tags)** | Evidence packages attach `_sources` (WAREHOUSE catalog / COMPUTED / ENGINE_PATH) with `org_id` / `loaded_at` / `is_final` (honest nulls). DOM overlay consumes when present — [ai_claim_verify.md](./ai_claim_verify.md) |
| Post-LLM citation verify | **Implemented on primary paths** | **Strict** on Prompt 2 (hard-block when fully wiped); Prompt 5 **warn-only** (board cells trusted); **interactive soft-warn** on commentary generate / board regenerate / Copilot — [ai_claim_verify.md](./ai_claim_verify.md) |
| Claude may only state values present in evidence | **Partial — implemented** | Prompt rules + structural verify; interactive surfaces trust board numbers and gate story / forecast-pipeline grounding |
| Second-pass commentary verification (block on unverifiable) | **Partial — implemented** | Interactive: soft-warn numbers + surgical story strip; Prompt 5 soft-strip + export; Prompt 2 hard-block when variance fully wiped |
| DOM `data-source` attributes + audit overlay | **Partial — implemented (UI)** | Board/FE KPIs via `smpl-provenance.js`; hydrate `_sources` when present; `Ctrl+Shift+A` overlay — [fe_board_single_source.md](./fe_board_single_source.md) |
| Full `runTieOut()` Rule Sets A–F as publish gate | **Partial — advisory client A–F** | Export-time client A–F + HTML report are **advisory** (WARN; deck/promote proceed); C5/F4 forecast soft after close; hard production-actuals ID at import/close (roadmap); Prompt 5 AI verify soft-strips + exports; Prompt 2 still harder; live SQL warehouse HTML still roadmap |
| Human review before every send as primary control | **Not the control** (by design) | Rejected posture — see P15 |

**Safer as gates are built:** Policy and IR language already require machine-primary fail-closed behavior. Product safety and trust rise as the roadmap layers above are implemented and fail-closed in production — not when humans re-check every package.

## Changelog

| Date | Change |
|------|--------|
| 2026-07-31 | Prompt 5 soft-strip hotfix: citation warn-only (stop wiping uncited KPI/table cells into don't-know essays); short failed cells → `—`. Demo dual seeds untouched. Not SOC 2 certified. |
| 2026-07-31 | Prompt 5 evidence package widened (actual/forecast/pipeline/bridges + `series_kind` tags) and prompts tightened so rich board narrative can use package context; invent still soft-strips; soft-export retained. Demo dual seeds untouched. Not SOC 2 certified. |
| 2026-07-31 | Prompt 5 deck export: numeric + citation soft-strip unmatched PPTX string literals (export continues); attribution surgical strip; prefer export over hard-block. Prompt 2 stays stricter. Export-time warehouse / client A–F validation unchanged (advisory). Demo dual seeds untouched. Not SOC 2 certified. |
| 2026-07-31 | Interactive AI policy retune: commentary generate / board regenerate / Copilot soft-warn numeric + citation (board numbers trusted); attribution + forward/pipeline surgical strip. Prompt 2 stays strict; Prompt 5 later retuned to soft-strip + export. Demo dual seeds untouched. Not SOC 2 certified. |
| 2026-07-31 | Export-time client A–F → **advisory** (MD&A deck + FINAL promote proceed; HTML WARN companion). Forecast C5/F4 soft after close. Hard identification documented at import/close — not presentation pull. Demo dual seeds untouched. Not SOC 2 certified. |
| 2026-07-30 | Near-term warehouse-gate plan: [WAREHOUSE_GATE_NEAR_TERM_PLAN.md](./WAREHOUSE_GATE_NEAR_TERM_PLAN.md) — DoD, path×gate matrix, phased workstreams, board must-haves, verify plan, claim boundaries. Not SOC 2 certified. |
| 2026-07-30 | Client `runTieOut` Rule Sets A–F (skip when data absent) + client HTML tie-out report as publish gate; Prompt 5 + board regenerate citation verify on string literals/bullets. Live warehouse SQL HTML report still open. Demo dual seeds untouched. Not SOC 2 certified. |
| 2026-07-30 | DOM `data-source` overlay + audit hotkey on Board/FE KPIs; partial client `runTieOut` (Rule C/A) gates live MD&A export + FINAL forecast promote. Demo dual seeds untouched. Not SOC 2 certified. |
| 2026-07-30 | Post-LLM citation verify + warehouse tags (`org_id` / `loaded_at` / `is_final` honest nulls) + multi-driver AND attribution rule. $1 bar unchanged. Not SOC 2 certified. |
| 2026-07-30 | Evidence `_sources` tags on primary packages; richer attribution (deal-count / logos / magnitude dominance); FE hydrate replace+prune closed Actual residue (no demo reseed). $1 bar unchanged. Not SOC 2 certified. |
| 2026-07-30 | Copilot structured evidence/attribution packages (commentary/MD&A parity flatten); freeze stores packages in sections; production FE↔Board single-source confirmed + TS↔SRC $1 regression. Demo seeds untouched. Not SOC 2 certified. |
| 2026-07-30 | Attribution verify extended to Prompt 5 (soft-strip string literals; hard-block when fully wiped), board slide regenerate (per-bullet), Copilot thin blob-label wire. $1 numeric bar unchanged. Not SOC 2 certified. |
| 2026-07-30 | Attribution verify v1: helper + commentary generate + MD&A Prompt 2 (allowlist from structured fields; empty allowlist strips causal claims). Prompt 5 / board / Copilot still follow-up. Not SOC 2 certified. |
| 2026-07-30 | Extended claim-verify to Prompt 5 (hard block on PPTX string-literal $/%), board slide regenerate (soft strip), Copilot thin blob wire. Attribution design: [ai_attribution_verify.md](./ai_attribution_verify.md). Guarantee 4 corrected to machine-primary. Not SOC 2 certified. |
| 2026-07-30 | Claim-verify helper live on `/commentary/generate` + MD&A Prompt 2 (evidence package + post-LLM verify + hard block on matrix mismatch / fully unverifiable variance sheet). Founder checklist: [ai_claim_verify.md](./ai_claim_verify.md). Board slide regenerate / Prompt 5 / Copilot still follow-ups. Not SOC 2 certified. |
| 2026-07-29 | Added financial_dashboard_cf_re_logic.md — customer/production GL→statements methodology; demo/lab surfaces explicitly carved out |
| 2026-07-29 | Added reconcile_financial_statements.md; closed-actuals severity bar ($0.01 rounding / ≤$1 investigate / >$1 significant_miss); tie-out prompt + framework language tightened so $100/$1K are not called “rounding” for statement actuals |
| 2026-07-28 | Copied normative framework + tie-out prompt from Matt Downloads; README states adaptation of Part 6 and honest implemented-vs-target labels |

---

_End of controls README_
