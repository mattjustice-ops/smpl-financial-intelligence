# Data integrity & tie-out — normative design targets

> **Not SOC 2 certification.** These documents are **normative product / control design targets** for how SMPL prevents phantom numbers and wrong-context packaging in board/customer-facing outputs. Shipping status is labeled honestly below — do not claim full framework layers are live in production unless code and evidence show they are.

## Documents in this folder

| File | Role |
|------|------|
| [ai_claim_verify.md](./ai_claim_verify.md) | **Founder review checklist** — P15 fail-closed claim-verify: what shipped, tolerances, covered vs open paths, tests |
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
| `/commentary/generate` post-LLM claim verify | **Implemented on this path** | `claim_verify.py`: evidence package in prompt + post-LLM numeric verify (TOL_ACTUALS $1) + don't-know / omit on fail — **live on `/api/v1/commentary/generate` only** |
| MD&A Prompt 2 post-LLM claim strip | **Partial — implemented** | Nested commentary strings verified against payload evidence; unverifiable cells → don't-know; all-unverifiable variance sheet **blocks emit** |
| Board slide regenerate / Prompt 5 deck / Copilot | **Required design / roadmap** | Not yet wired to the same fail-closed helper — follow-up |
| `_sources` provenance object on every LLM payload | **Required design / roadmap** | Framework Part 1 — not present as product-wide `_sources` contract (commentary path ships a flatter `evidence_package.values` map) |
| Claude may only state values present in evidence | **Partial — implemented** | Prompt rules + structural verify on commentary generate + MD&A Prompt 2; not all customer-visible AI paths |
| Second-pass commentary verification (block on unverifiable) | **Partial — implemented** | Live on `/commentary/generate` (strip/don't-know) + MD&A Prompt 2 (strip + hard block when variance sheet fully unverifiable / matrix mismatch) |
| DOM `data-source` attributes + audit overlay | **Required design / roadmap** | Framework Part 3 |
| Full `runTieOut()` Rule Sets A–F as publish gate | **Required design / roadmap** | Tie-out prompt Part 3–4; pieces of tie-out exist; full cross-platform gate not claimed live |
| Human review before every send as primary control | **Not the control** (by design) | Rejected posture — see P15 |

**Safer as gates are built:** Policy and IR language already require machine-primary fail-closed behavior. Product safety and trust rise as the roadmap layers above are implemented and fail-closed in production — not when humans re-check every package.

## Changelog

| Date | Change |
|------|--------|
| 2026-07-30 | Claim-verify helper live on `/commentary/generate` + MD&A Prompt 2 (evidence package + post-LLM verify + hard block on matrix mismatch / fully unverifiable variance sheet). Founder checklist: [ai_claim_verify.md](./ai_claim_verify.md). Board slide regenerate / Prompt 5 / Copilot still follow-ups. Not SOC 2 certified. |
| 2026-07-29 | Added financial_dashboard_cf_re_logic.md — customer/production GL→statements methodology; demo/lab surfaces explicitly carved out |
| 2026-07-29 | Added reconcile_financial_statements.md; closed-actuals severity bar ($0.01 rounding / ≤$1 investigate / >$1 significant_miss); tie-out prompt + framework language tightened so $100/$1K are not called “rounding” for statement actuals |
| 2026-07-28 | Copied normative framework + tie-out prompt from Matt Downloads; README states adaptation of Part 6 and honest implemented-vs-target labels |

---

_End of controls README_
