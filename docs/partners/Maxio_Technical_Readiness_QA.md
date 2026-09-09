# Maxio Technical Readiness Q&A

> **Audience:** Matt + technical SCs in Maxio partner meetings  
> **Companion:** [Maxio_Partner_Meeting_Prep_Trust_Budget_PPI.md](./Maxio_Partner_Meeting_Prep_Trust_Budget_PPI.md)  
> **As of:** 2026-09-08 — body reconciled to shipped Plan Assurance / Budget Engine  
> **Labels:** **Shipped** / **Partial** / **Missing** / **Docs only** — do not invent features

---

## The one-paragraph story (say this first, then take questions)

Maxio gives SaaS finance teams governed recurring-revenue actuals. SMPL takes those actuals together with the customer's GL, CRM and workforce data, implements the financial environment, builds the operating budget, evaluates the plan against prior-year performance, models the distribution of year-end outcomes, and turns the result into board-ready decision support. **Maxio stays the recurring-revenue foundation, and the customer does not have to undertake a major FP&A implementation.**

---

## Top 10 tough questions (crisp answers)

### 1. “Can I click a Forecast ARR / pipeline cell and see the deals?”

**Partial → strong on Pipeline; uneven elsewhere.**

- **Shipped (example to extend):** `/app` Executive Flow → Pipeline waterfall. Click `pipeline_created` / `closed_won` / `closed_lost` / `slipped_pipeline` → `GET /api/v1/waterfalls/pipeline/drilldown` → opportunity rows from `{actual|budget|forecast}_opportunity_movements`, plus optional `pipeline_cell_opportunities_tie` validation.
- **Code:** `frontend/components/ExecutiveFlowDashboard.tsx` (`PipelineWaterfallTable`); `backend/app/services/dashboard/pipeline_opportunity_drilldown_service.py`; route in `waterfall_routes.py`.
- **Also shipped (cash):** same dashboard pattern for cash bridge → GL / workforce lines via `/api/v1/waterfalls/cash-flow/drilldown`.
- **Missing / Partial:** Board HTML Pipeline tab is mostly chart narrative (not the same cell→API drill). Not every Forecast KPI (e.g. every MRR waterfall cell) has first-class opportunity drill in UI yet. Beginning/ending pipeline balances correctly refuse drill (`drilldown_available=false`).

### 2. “What are Actuals made of — can I get to GL?”

**Partial.**

- Actuals live in `actual_*` warehouse tables (statements, waterfalls, bridges) loaded Path A / CSV / demo; GL detail via `gl_actuals` / `Actual_gl_detail` (and Management P&L ▶ GL expand in Board).
- Cash bridge cell → GL composition is **Shipped** (API + Executive Flow UI).
- Full “every Actual P&L line → named GL accounts with $1 tie in UI” is **Partial** (engines + some UI; not a universal cite-at-click trust home).

### 3. “What is Budget made of — opportunities or pure GL?”

**There is a real Budget Engine. Budget is calculated from drivers, not just loaded as a scenario.** *(Answer corrected 2026-09-08 — the previous "parallel scenario load, not a separate engine" answer predated the Budget Engine.)*

Walk the six layers in this order; it answers the question and pre-empts the next three:

| # | Layer | What it is | Status |
|---|-------|-----------|--------|
| 1 | **Inputs & assumptions** | Explicit driver set: YoY ending-ARR growth, churn/contraction mix, blended CPL and channel mix, quota/ramp/attrition, pipeline coverage, hiring plan, opex, DSO/DPO, cash floor | **Shipped** |
| 2 | **Deterministic Budget Engine** | A closed formula graph in fixed dependency order — pipeline/GTM funnel → ARR schedule → bookings capacity → deferred/revenue → headcount & opex → three statements. Every month is computed, not typed | **Shipped** |
| 3 | **Budget outputs** | Promote writes `budget_mrr_waterfall`, `budget_income_statement`, `budget_cash_flow_statement`, `budget_balance_sheet`, `budget_bookings_summary`. `budget_opportunity_movements`, `budget_pipeline_waterfall` and `Budget_gl_detail` are supported when loaded | **Shipped** |
| 4 | **Plan Assurance** | Tests those outputs against a 15-constraint registry, named stress cases and a 1,000-draw simulation — all re-running the *same* formula graph | **Shipped** |
| 5 | **Historical context** | Assembles prior-year evidence and compares plan shape against it (see Q9 for exactly which years are actuals vs derived) | **Shipped / Partial** |
| 6 | **LLM evaluation** | Reads the structured packet and produces a qualitative assessment and explanation. Never computes, edits or invents a financial value | **Shipped** |

**The remaining gaps are process, not engine** — keep these separate or you'll sound like the engine is missing:

- **Version approval is thin.** Lifecycle is `draft` → `final` → `superseded` with **no `submitted` state**, so "sent for approval, not yet approved" isn't auditable.
- **Feasibility does not gate promotion.** A plan with failing constraints can still be promoted. Validation gates *export*; feasibility does not gate *approval*. Open product decision.
- **Annual planning calendar / cadence** is documented but not a guided UI.
- Methodology is now written: [SMPL_Budget_Methodology.md](../product/SMPL_Budget_Methodology.md).

**One-liner:** "Budget isn't a CSV we loaded — it's calculated from a driver set through the same formula graph we then stress-test. What's still maturing is the approval workflow around it, not the math."

### 4. “How do you isolate tenants on warehouse load?”

**Shipped.**

- Every fact load is scoped by `organization_id`. Loader replaces **org-scoped** rows in the target physical table (`delete … where organization_id = :id` then insert) — see `load_physical_table_rows` / demo CSV loader.
- Cross-org membership gates exist on org fetch; tenant isolation evidence under `docs/soc2/evidence/tenant-isolation-2026-07-29.md`.
- Path A scripts require explicit `-OrganizationId`.

### 5. “What happens if two people load the same org at once?”

**Missing as a dedicated warehouse-load mutex; Partial elsewhere.**

- **Warehouse CSV / Path A:** last completed load **wins** (org-scoped replace). No `pg_advisory_lock`, no “load in progress” gate blocking a second ingest for the same org found in code.
- **Shipped related:** durable **export** jobs enforce **max 1 heavy export per org** (`ExportJobConflictError` in `export_jobs.py`; tested in `test_export_jobs.py`).
- **Docs only (close peak):** `docs/CLOSE_PEAK_WORKLOAD.md` — per-org concurrency for Prompt 5, queue isolation target, freeze STALE/COMPLETE. That brief is about close/export/AI peak, **not** a mocked multi-person warehouse ETL UI.
- **Docs only (actual locks):** `Forecasting_Assumptions.md` — “Locked actual / no overwrites” with future `period_close_status`; close workflow has `close_lock_events` for close session lock, not CSV load mutex.

**Say in room:** Org isolation is real; concurrent warehouse loads are last-write-wins today; we serialize heavy exports per org; full load-job queue + lock UX is roadmap.

### 6. “Is the Maxio connector live?”

**Missing (scaffold only).**

- Scripts: `maxio_sandbox_probe.py`, `maxio_export_to_smpl.py`. Blocked historically on AB site + API key.
- **Revised posture:** Do **not** treat credentials as the unlock for this meeting. Demo Path A / CSV / Demo Co; partner value is governed FI on Maxio-shaped billing actuals when data is present.
- **Three candidate paths, and we should not pre-judge which fits where:** Maxio **MCP** (governed queries and approved AI tasks), the **REST API**, and **standardized exports**. Each may suit a different use case — an interactive governed question is not the same requirement as a repeatable warehouse load. Treat "which path for which use case" as an agenda item for the technical session, not a settled assumption.

### 7. “How do you prove numbers without Neon?”

**Partial.**

- **Shipped:** validation catalog / export pre-check, freeze packs, AI claim-verify on primary paths, pipeline cell tie check, provenance overlay (Ctrl+Shift+A) when `_sources` present.
- **Gap:** polished always-visible reconciliation checklist / trust home for execs — still the founder demo gap.

### 8. “Do you replace Abacum / Maxio FP&A?”

**Additional customer lane — not a displacement ask.** *(Reframed 2026-09-08. The previous "preferred / successor partner" answer was the right ambition but the wrong opening ask: Nick has an existing relationship to protect and we have no joint Maxio customer result yet.)*

- Abacum is Maxio's **current** FP&A/planning partner (**confirmed 2026-08-31**). Acknowledge it plainly and do not position against it.
- **The ask:** *"We believe SMPL serves an additional customer lane within Maxio's base — growth companies with lean finance teams that want sophisticated planning and financial intelligence but don't want to implement and administer a traditional FP&A platform."*
- **Why that lane is real:** a traditional FP&A implementation asks a two- or three-person finance team to redesign its systems, own a modelling tool, and run change management. That team often has the need and not the capacity. SMPL does the implementation and hands back a working environment (see Q10).
- **Differentiation, stated without comparison:** governed billing actuals, CRM ≠ billing ≠ ERP tie-outs, calculate → validate → explain, board packages, evidence-bound AI, and a plan that gets stress-tested rather than just built.
- Do **not** invent Abacum feature matrices, win rates, or claim "we already replace Abacum in production." Not a Maxio replacement either — Maxio owns quote-to-cash and rev-rec actuals.

**Earn preferred positioning in this order:** validate the distinct lane → complete technical validation → run one joint design-partner implementation → produce measurable results → *then* discuss preferred positioning.

**One-liner:** "Abacum is Maxio's FP&A partner and we're not asking you to revisit that. We think there's a different lane in your base — lean finance teams that want this capability without running an FP&A platform themselves. We'd like to test that with one joint customer."

### 9. “Do you do anything predictive, or is this just reporting?” *(added 2026-09-08)*

**Shipped — Budget Engine → Overview / Analytics (Plan Assurance).**

**Say the architecture in four layers.** This is more accurate than "the AI narrates," and it is the strongest version of the story:

> The **deterministic engine** calculates the plan. The **historical-context layer** assembles the relevant prior-period evidence. The **predictive analytics layer** models potential outcomes. The **LLM evaluates and explains** the plan using that structured evidence — without computing or altering any financial value.

The LLM is doing real qualitative evaluation: is this plan aggressive, is the shape credible, which risk should the board look at first. What it is barred from is producing or changing a number.

**What runs, lane by lane** — all four re-use the *same* formula graph that builds the plan:

- **Historical context / outlier review** — assembles prior-year monthly series (ARR, net new, revenue, EBITDA, opex, marketing, MQLs, cash, headcount) and scans the plan against them: YoY step-ups vs the prior year's own growth rate, H1/H2 tilt flips, peak-quarter shifts, Jun→Dec path divergence, cross-metric inversions (marketing ↑ while MQLs ↓), efficiency drift. Findings carry severity, a lens tag, and a metric citation.
- **Status** — the structured assurance packet turned into an executive assessment: ARR commitment and December path, net new, revenue, EBITDA, GTM coverage, sales capacity, headcount, December cash vs floor.
- **Scenario stress** — named deterministic lever shocks (growth −3/−5pp, CPL +15/30%, attrition +2/5pp, churn mix ×1.4, plus combination and liquidity cases) recording Δ Dec ARR / Δ Dec cash / Δ FY EBITDA with break · watch · hold outcomes.
- **Monte Carlo** — 1,000 draws (see the precise description below).
- **Constraint registry + risk strip** — 15 hard/soft validations: ARR path and bridge, GRR floor, December and intra-year cash floor, NB/CS coverage, bench cover, pipeline coverage, GTM MQL/spend/mix identities, Jan HC lock, EBITDA, S&M tie.

**How the simulation actually works — use this wording, it survives a technical question:**

> The model samples four annual operating assumptions — YoY ARR growth, a CPL multiplier, sales attrition and pipeline coverage — once per draw, then propagates that draw through the **full monthly formula graph**: funnel → ARR schedule → capacity → statements → cash. Every trial is therefore a complete, internally consistent twelve-month plan. Each trial's **entire monthly cash path is retained**, so across 1,000 trials the model reports a **P10–P90 band for every month**, the distribution of the **intra-year cash trough**, and which month is tightest — alongside the year-end distributions for December ARR, December cash and FY EBITDA.

**The number that lands in the room:** `P(any month below floor)` is materially higher than `P(December below floor)`. A plan can end the year comfortably and still need financing in July. Both figures are shown side by side, and the tightest month is named.

Priors are stated on screen, not hidden: Δ growth ~ N(0, 3.2pp), CPL ~ LogNormal(0, 0.28), attrition ~ N(base, 2.5pp) truncated at 0, pipeline cover ~ N(base, 0.55×) truncated at 1×, drawn independently.

**Honest limits — do not overclaim:**
- Monte Carlo output is **stress frequency under stated priors** (`P(breach | lever noise)`), **not** calibrated Probability of Attainment. Calibration is Phase 2.
- Annual assumptions are drawn **once per trial** and then propagated through the months. Shocks are **not independently resampled month to month**, and this is not a day-by-day simulation. Say "we sample annual operating assumptions and propagate each draw through the monthly cash schedule" — that is precise and defensible.
- Monthly bands are **cross-sectional percentiles across draws**, not a single traced path. The P10 line is not one scenario's journey.
- Sensitivity curves cover **two** levers (growth, CPL), not all four.
- Prior-year (FY26) comparisons use loaded actuals **where present**, with plan-value fallbacks for gaps. The **two-years-back series is derived by backcast, not loaded** — so "we compare against the prior year's own growth rate" is fair, "we have three years of loaded actuals" is not.
- Feasibility runs on the **Budget** surface; it is not yet keyed to a promoted forecast version, and assessments are not persisted, so an assessment is a live read rather than a citable artifact.
- Forecast Engine and Board reach Analytics via cross-links and an exec hand-off band; a **native** shared-package view in those hosts is deferred backlog.

**Trust point worth making:** every lane has a deterministic narrative fallback. If the LLM is unavailable the analysis still renders, labelled as deterministic. The finding does not depend on the model being up.

**Maxio tie-in:** this is the layer that consumes trusted billing actuals and answers "can the plan built on them actually be delivered" — the part absent from Maxio's own reporting and enablement surface.

### 10. “Who does the implementation, and what does my customer have to do?” *(added 2026-09-08)*

**SMPL does the implementation. This is a top-three partnership argument, not an operational footnote.**

- **SMPL builds the environment.** We take the customer's existing stack and data largely as-is — Maxio billing, their GL, their CRM, their workforce data — and stand up the warehouse, mappings, tie-outs, budget and board surfaces.
- **The customer does not redesign its systems.** No re-architecture, no data-model migration, no rip-and-replace. **Maxio stays exactly where it is** and keeps owning quote-to-cash and rev-rec.
- **Customer participation is validation and decision-making** — confirm mappings, confirm definitions, approve the plan. Not months of internal build.
- **Total cost is the honest differentiator:** far less internal finance labour and change management than a self-administered FP&A platform. That is the whole reason the lean-team lane exists.
- **Repeatable for Maxio-standard stacks.** Because Maxio normalizes billing objects, an implementation on a standard Maxio configuration is a known shape and can plausibly be packaged predictably.

**Honest limits:** native connectors are **not GA** — today's path is white-glove load of Maxio-shaped exports plus the customer's GL/CRM files. Packaging is a **credible direction, not a published SKU** — do not quote a fixed price or timeline in the room. And we have no joint Maxio design-partner result yet; that is precisely the ask.

**One-liner:** "The customer doesn't implement anything. We take the stack as it is, including Maxio, and build the environment. Their job is to validate and decide."

---

## Demo strategy without Maxio API

1. Demo Co / Path A CSV already shaped like CRM + billing + ERP.  
2. Show `/app` Pipeline cell → opportunities + tie banner.  
3. Show cash / GL drill where data exists.  
4. Show validation + freeze as-of (trust without SQL).  
5. Diagram CRM ≠ Maxio ≠ ERP; say Path A lands Maxio exports into `billing_arr` when a customer is ready.  
6. Optional: self-serve Chargify sandbox signup is public — **nice-to-have**, not meeting-critical.

---

## Related code pointers

| Topic | Path |
|-------|------|
| Pipeline drill UI | `frontend/components/ExecutiveFlowDashboard.tsx` |
| `/app` host | `frontend/app/app/page.tsx` |
| Pipeline drill service | `backend/app/services/dashboard/pipeline_opportunity_drilldown_service.py` |
| Cash/GL drill | `backend/app/services/dashboard/cash_flow_gl_drilldown_service.py` |
| Org-scoped load replace | `backend/app/services/demo_csv/loader.py` |
| Export per-org lock | `backend/app/services/reporting/export/export_jobs.py` |
| Close-peak concurrency design | `docs/CLOSE_PEAK_WORKLOAD.md` |
| Path A | `docs/GO_LIVE_POC_DIRECT_DATA_ACCESS.md` |
