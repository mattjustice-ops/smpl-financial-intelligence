# Warehouse gate — near-term plan (2–4 weeks)

> **Not SOC 2 certification.** Product integrity plan so blog / sales CTAs about
> “calculate → validate → AI explains only validated evidence → fail closed”
> match what actually ships.  
> **Inventory date:** 2026-07-30 (post-merge of P15 integrity finish / client A–F).  
> **Source of truth for live vs open:** [README.md](./README.md), [ai_claim_verify.md](./ai_claim_verify.md), [ai_attribution_verify.md](./ai_attribution_verify.md), [fe_board_single_source.md](./fe_board_single_source.md), [data_integrity_framework.md](./data_integrity_framework.md), [data_sources_tieout_prompt.md](./data_sources_tieout_prompt.md).  
> **Policy:** [P15 §4.7 / §4.8](../policies/P15_ai_llm_data_handling.md)

---

## Why this plan exists

Matt’s product goal (and the story behind blog CTAs): numbers are **calculated**
by the engine/warehouse, **validated** by automated gates, and **AI only narrates
validated evidence** — or the path **fails closed** (omit / don’t-know / hard-block).

Today that story is **mostly true on primary AI paths**, **partially true on
publish/tie-out**, and **not true** for the full normative framework (live
warehouse SQL tie-out report, every chart datapoint cited at render time, etc.).
This plan closes the gap that board-facing packages still care about — without
pretending the entire integrity framework is done.

---

## 1. Definition of done — “warehouse gate live everywhere”

### Plain English (founder)

A customer-visible board / MD&A / commentary / Copilot package cannot ship a
material dollar, percent, growth multiple, or causal driver story unless:

1. The figure came from the **engine / warehouse / freeze** (not the model),
2. Automated checks **agreed** it matches evidence within **$1.00** (actuals),
3. Citations resolve to real `_sources` / provenance when material numbers appear,
4. Wrong-cause stories are stripped or blocked when drivers aren’t allowlisted,
5. On **FAIL**, the product **stops** (omit, don’t-know, or hard-block) — it does
   not quietly ship unsupported claims.

“Everywhere” for this near-term bar means: **every path that produces or publishes
board-facing narrative or a FINAL / MD&A package** — not every pixel in offline
demo HTML, and not a CPA-grade warehouse SQL report for every cell.

### Technical (eng)

| Gate type | Near-term “live everywhere” means |
|-----------|-----------------------------------|
| **Calculate** | Production Board + FE hydrate from one outlook builder / warehouse tables; TS↔SRC actuals aligned within **$1**; freeze packs bind MD&A / Copilot / export context where required |
| **Validate (tie-out)** | Client `runTieOut` Rule Sets **A–F** (when local structures exist) **block** live MD&A export + FINAL forecast promote on FAIL; client HTML report downloaded on block; remaining warehouse-only checks (D2–D4 / E / B2 / F5 without tables) either wired with real data or explicitly **skipped with fail-closed policy** documented — not silently assumed PASS |
| **Validate (AI numeric)** | `claim_verify.py` on commentary generate, MD&A Prompt 2, Prompt 5 (string literals), board regenerate, Copilot structured packages; `TOL_ACTUALS = $1.00` non-negotiable |
| **Validate (attribution)** | `attribution_verify.py` on the same paths; multi-driver AND; empty allowlist + causal claim → fail closed |
| **Validate (citation)** | `citation_verify.py` on the same paths; material money/%/Nx must cite `_sources` token / table.column / formula_id / path |
| **AI explains only validated evidence** | Evidence + `_sources` (+ attribution package) embedded in prompts; post-LLM structural verify before emit; soft strip where product chooses; hard-block when fully wiped / matrix mismatch / Prompt 5 invent |
| **Fail closed** | No fail-open on missing evidence, invented numbers, invented drivers, or uncited material claims on wired paths |

**Explicitly out of near-term DoD** (still OPEN / nice-to-have — see §4):

- Live warehouse SQL HTML report (`tieout_report_{org}_{month}.html` with per-cell queries)
- Every chart datapoint / every commentary number forced to cite at **DOM render** time
- Second Claude “auditor” call from the normative framework Part 5 (we use structural helpers instead — keep that)
- Finance PDF close checklist as primary gate (rejected posture — machine-primary)
- Demo Board/FE dual-seed equality (leave alone; do not reseed)

---

## 2. Current state matrix (path × gate type × status)

Labels: **LIVE** = fail-closed on that gate for that path · **PARTIAL** = real code, incomplete vs DoD · **OPEN** = not shipping as specified · **N/A** = not the control for that path.

| Path / surface | Calculate (single-source / freeze) | Tie-out publish gate | Numeric claim_verify | Attribution verify | Citation verify | `_sources` / warehouse tags | DOM `data-source` |
|----------------|------------------------------------|----------------------|----------------------|--------------------|-----------------|-----------------------------|-------------------|
| `/api/v1/commentary/generate` | LIVE (inputs → evidence package) | N/A | **LIVE** (soft strip / don’t-know) | **LIVE** | **LIVE** | **LIVE** (v1 + honest nulls) | N/A |
| MD&A Prompt 2 | PARTIAL (freeze when required) | N/A (emit gate = claim path) | **LIVE** (harder: matrix / full wipe → hard block) | **LIVE** | **LIVE** | **LIVE** on payload builders | N/A |
| MD&A Prompt 5 deck | PARTIAL (freeze / deck evidence) | N/A | **LIVE** (hard block on string-literal $/%/Nx) | **LIVE** (soft-strip; hard-block if all fail) | **LIVE** (PPTX literals; soft-strip / hard-block when wiped) | **LIVE** from deck flatten | N/A |
| Board slide regenerate | PARTIAL (slide + freeze blob) | N/A | **LIVE** (soft strip / don’t-know) | **LIVE** | **LIVE** (bullets) | PARTIAL (via flatten / freeze) | N/A |
| Board Copilot | PARTIAL (bundle/TS/cash + freeze sections) | N/A | **LIVE** (structured + blob supplement) | **LIVE** | **LIVE** | **LIVE** (org/loaded_at; is_final=false live) | N/A |
| Live MD&A export (Board) | LIVE hydrate path | **PARTIAL — LIVE client A–F** | via package generation above | via above | via above | PARTIAL (consumes when hydrate has `_sources`) | **PARTIAL — LIVE UI KPIs** |
| FINAL forecast promote (FE) | LIVE hydrate path | **PARTIAL — LIVE client A–F** | N/A (UI promote) | N/A | N/A | PARTIAL | **PARTIAL — LIVE UI KPIs** |
| Production FE ↔ Board hydrate | **LIVE** (shared outlook API/builder; residue prune) | N/A | N/A | N/A | N/A | PARTIAL (API does not always emit `_sources` for UI) | **PARTIAL** |
| Client `runTieOut` A–F | Uses local SRC/TS/WF/engine/display | **PARTIAL** — skips D2–D4 / E warehouse / B2 bank / F5 without data | N/A | N/A | N/A | Prefers hydrate `_sources`; catalog fallback | Tied to overlay |
| Live warehouse SQL tie-out HTML | OPEN | **OPEN** | N/A | N/A | N/A | OPEN (per-cell warehouse query report) | OPEN |
| Chart arrays / layout coords (Prompt 5) | — | — | **OPEN** (not scanned) | OPEN | OPEN | — | — |
| Every chart datapoint cite at render | — | — | OPEN | OPEN | OPEN | OPEN | OPEN |
| Offline demo seeds | Dual-seed **by design** | Demo warns only (not live gate) | N/A | N/A | N/A | N/A | Catalog / demo |

### Gate-stack summary (honest)

| Stack layer | Status | Notes |
|-------------|--------|-------|
| Helpers: `claim_verify` / `citation_verify` / `attribution_verify` | **LIVE** | Reusable; $1 bar locked |
| Primary AI emit paths (commentary, P2, P5, board regen, Copilot) | **LIVE** | Soft vs hard-block differs by surface — intentional |
| FE↔Board single-source | **LIVE** | Demo dual-seed left mismatched on purpose |
| DOM provenance + client A–F publish gate | **PARTIAL** | Shipable gate; not warehouse SQL |
| Normative framework Parts 4/7 live SQL report | **OPEN** | Biggest honesty gap vs “full warehouse gate” language |
| Framework Part 5 second-LLM auditor | **OPEN / superseded** | Structural helpers are the shipping control; do not reintroduce dual-LLM as primary |

---

## 3. Phased workstreams (2–4 weeks)

Owners: **Matt** = product accept / risk call · **Eng/agent** = implement + tests · **Both** = smoke together.

Effort: **S** ≤1 day · **M** 2–3 days · **L** ~1 week.

### Phase 0 — Lock the story (days 0–2)

| ID | Work | Owner | Effort | Depends on |
|----|------|-------|--------|------------|
| P0.1 | Matt accept this plan’s DoD + “will not claim” list (§6) | Matt | S | — |
| P0.2 | Confirm soft-strip vs hard-block matrix still matches risk (commentary soft; P2/P5 hard when fully wiped; board soft) | Matt | S | P0.1 |
| P0.3 | Blog / CTA language audit: only claim what §2 marks LIVE; point “warehouse gate” CTAs at this plan until Phase 2 exits | Matt + eng/agent | S | P0.1 |

**Exit:** Written accept in PR comment or decision log; no marketing claim of full SQL tie-out.

### Phase 1 — Board-package must-haves (week 1)

Close honesty gaps that can still let a board package look “gated” when it isn’t.

| ID | Work | Owner | Effort | Depends on |
|----|------|-------|--------|------------|
| P1.1 | **Outlook API `_sources` for UI** — emit `_sources` (or `meta._sources`) on production hydrate so DOM overlay isn’t mostly catalog fallback | Eng/agent | M | FE↔Board builder |
| P1.2 | **Publish-gate skip policy** — when D2–D4 / E / B2 / F5 skip for missing warehouse tables, log structured skip reasons on the client HTML report; never treat skip as PASS in founder language | Eng/agent | S–M | Client A–F |
| P1.3 | **Freeze freshness / binding smoke** — board regenerate + Copilot + Prompt 5: invent dollar / invent driver / drop citation → don’t-know or hard-block (document results) | Both | S | Live helpers |
| P1.4 | **Hardening: Prompt 5 chart string leakage** — scan any remaining PPTX text nodes that can carry $/% outside current string-literal pass (still may exclude pure chart arrays) | Eng/agent | M | claim/citation on P5 |
| P1.5 | Older freeze packs without tagged `_sources` / `attribution_package` — document behavior (blob fallback) + decide: rebuild freeze on open, or fail closed if tags missing for customer-facing emit | Matt decide → eng | S | P0.2 |

**Exit:** Live MD&A export + FINAL promote + Prompt 5 emit cannot pass a known invent scenario; hydrate overlay shows warehouse tags when live data exists; skip reasons visible.

### Phase 2 — Warehouse-backed publish proof (weeks 2–3)

Move from “client structures agree” toward “we can prove warehouse agreement” for board closes — without boiling the ocean.

| ID | Work | Owner | Effort | Depends on |
|----|------|-------|--------|------------|
| P2.1 | **Server-side tie-out subset for board close** — backend job or API that runs Rule Sets **A, B (statement cash), C, F** against warehouse / outlook payload for `org_id` + `close_month`; FAIL blocks the same publish surfaces as client gate (or blocks freeze COMPLETE → export) | Eng/agent | L | Outlook builder, client gate contract |
| P2.2 | **HTML report v1 (server)** — generate downloadable report for A/B/C/F results (org, month, per-check PASS/FAIL/SKIP, tolerance). Not yet full Part 4 per-cell SQL library | Eng/agent | M–L | P2.1 |
| P2.3 | Wire D2–D4 / E / B2 / F5 **only where warehouse tables exist** in prod schema; otherwise remain SKIP with reason (honest) | Eng/agent | M | P2.1 |
| P2.4 | Regression tests: invent mismatch → FAIL blocks export/promote; aligned demo/customer fixture → PASS | Eng/agent | M | P2.1–P2.2 |
| P2.5 | Matt commentary trial: one real (or staging) close — generate Prompt 2 + Prompt 5 + Copilot Q; confirm invent/driver/citation failures; accept residual soft-strip surfaces | Matt | S | Phase 1 + P2.2 |

**Exit (near-term “warehouse gate live everywhere” for board packages):** Server A/B/C/F + client A–F + AI claim/attribution/citation stack all fail-closed on board-facing publish/emit. Still **not** claiming full Part 4/7 SQL library.

### Phase 3 — Nice-to-have / stretch (week 3–4, defer freely)

| ID | Work | Owner | Effort | Depends on |
|----|------|-------|--------|------------|
| P3.1 | Live warehouse SQL per-cell report (framework Part 4/7) | Eng/agent | L+ | Schema + query library |
| P3.2 | DOM tags on every chart datapoint / table cell | Eng/agent | L | Overlay module |
| P3.3 | Force cite-at-render for every commentary number in UI | Eng/agent | L | Citation formats |
| P3.4 | Prompt 5 pure chart-array numeric scan | Eng/agent | M | Risk call from Matt |
| P3.5 | Periodic control-testing checklist PDF (Part 6 adapted — not primary gate) | Matt | S | — |

---

## 4. Must-have for board-facing packages vs nice-to-have

### Must-have (before saying the CTA story without caveats)

- [x] Numeric claim_verify on commentary, Prompt 2, Prompt 5, board regen, Copilot *(LIVE)*
- [x] Attribution verify on those paths *(LIVE)*
- [x] Citation verify on those paths *(LIVE)*
- [x] Production FE↔Board single-source + $1 TS↔SRC guard *(LIVE)*
- [x] Client A–F `runTieOut` blocks live MD&A export + FINAL promote *(PARTIAL but shippable)*
- [ ] Phase 1: hydrate `_sources` for UI + honest SKIP reporting + invent smoke *(open)*
- [ ] Phase 2: server-side A/B/C/F warehouse-backed publish proof + HTML report v1 *(open)*
- [ ] Matt accept soft vs hard-block matrix + commentary trial *(open)*

### Nice-to-have (do not block CTA honesty if Phase 1–2 done)

- Full Part 4 live SQL per-cell HTML report
- D2–D4 / E / B2 / F5 when tables don’t exist yet
- Chart-array scanning / every DOM datapoint tagged
- Second-LLM commentary auditor
- Demo seed reconciliation
- Finance sign-off of every package (rejected as primary control)

---

## 5. How we verify

### Automated tests (keep green; extend in Phase 1–2)

| Suite | What it proves |
|-------|----------------|
| `backend/tests/test_claim_verify.py` | $1 bar; invent → don’t-know; PPTX literals; Copilot `_sources` |
| `backend/tests/test_citation_verify.py` | Cite required; PPTX / bullet strip; hard-block when fully wiped |
| `backend/tests/test_attribution_verify.py` | Drivers / logos / dominance / multi-driver AND |
| `backend/tests/test_commentary_service.py` | Generate path embeds evidence; invent dollars → don’t-know |
| `backend/tests/test_outlook_ts_src_actuals_alignment.py` | FE↔Board actuals $1 |
| `frontend/scripts/verify-outlook-hydrate.mjs` | Replace + prune residue (no reseed) |
| `frontend/scripts/verify-provenance-tieout.mjs` | `data-source`; client A–F; HTML report; live gate blocks |
| **New (Phase 2)** | Server A/B/C/F FAIL → export/promote blocked; PASS fixture green |

### Manual smoke (Phase 1 exit)

1. Live hydrate Board + FE for one org/month → `Ctrl+Shift+A` shows warehouse-ish tags (not only catalog) when `_sources` present.
2. Break a Rule C/A identity in client data → MD&A export / FINAL promote **blocked**; HTML report downloads with FAIL (and SKIP reasons if any).
3. Prompt 5 / commentary: ask model path to invent a dollar and a driver → omit / don’t-know / hard-block as designed.

### Commentary trial (Phase 2 exit — Matt)

One staging or friendly close:

| Step | Pass criteria |
|------|---------------|
| Generate MD&A Prompt 2 | No invented $; citations present or stripped; matrix mismatch cannot emit |
| Generate Prompt 5 | Invent in slide text blocked; fully wiped attribution/citation → hard block |
| Copilot 3 questions (ARR bridge, cash, “why”) | Wrong-cause → don’t-know; numbers cite or don’t-know |
| Export / promote after intentional FAIL | Blocked with report |

Record date + org + freeze ID in a short note under `docs/soc2/` evidence or PR description. **Not** SOC 2 evidence of certification.

---

## 6. What we will NOT claim until done

Until Phase 1 + Phase 2 exit criteria are met, do **not** say publicly or in sales:

| Do not claim | True today / after plan |
|--------------|-------------------------|
| “Full warehouse tie-out on every number” | Client A–F + AI gates; live SQL report still OPEN |
| “SOC 2 certified” / “SOC 2 compliant” because gates exist | Readiness only until CPA Type I report |
| “Every chart and cell is provenance-tagged” | Material KPI overlay only |
| “AI cannot be wrong about drivers” | Allowlist v1 — not a full ARR-bridge attribution engine |
| “Prompt 5 verifies chart arrays” | String literals (and planned text nodes) only |
| “Demo Board and FE always match” | Dual-seed left alone on purpose |
| “Human Finance signs every package” | Rejected as primary control (machine-primary) |
| “D2–D4 / E / B2 / F5 always run” | Skipped when warehouse tables absent |

**Safe to say now (with care):** On primary commentary / MD&A / Copilot paths, AI narrative is checked against engine evidence for material numbers, citations, and allowlisted drivers, and fails closed when checks fail; live publish of MD&A export and FINAL promote is blocked when client tie-out Rule Sets A–F fail.

**Safe to say after Phase 2:** Board-facing packages are blocked unless warehouse-backed A/B/C/F tie-outs and AI claim/attribution/citation gates pass (fail closed).

---

## 7. Pointers

| Doc | Use |
|-----|-----|
| [README.md](./README.md) | Implemented vs roadmap snapshot + changelog |
| [ai_claim_verify.md](./ai_claim_verify.md) | Path-level LIVE/PARTIAL/OPEN + founder checklist |
| [ai_attribution_verify.md](./ai_attribution_verify.md) | Driver allowlist behavior |
| [fe_board_single_source.md](./fe_board_single_source.md) | Hydrate + DOM + client A–F |
| [data_integrity_framework.md](./data_integrity_framework.md) | Normative design (many Part 9 boxes still open) |
| [data_sources_tieout_prompt.md](./data_sources_tieout_prompt.md) | Rule Sets A–F design |
| [P15](../policies/P15_ai_llm_data_handling.md) | Policy: calculate → validate → fail closed |

---

## 8. Changelog

| Date | Change |
|------|--------|
| 2026-07-30 | Initial near-term plan from honest inventory of controls docs post P15 integrity finish. Not SOC 2 certified. |

---

_End of warehouse gate near-term plan_
