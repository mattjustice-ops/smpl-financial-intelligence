# Maxio partner meeting prep — Trust, Budget methodology, PPI

> **Audience:** Matt (founder) — Maxio extended partner meeting + product planning  
> **Companion one-pager:** `C:\Users\mattj\Downloads\SMPL_Maxio_Week_Prep_One_Pager.md`  
> **Technical Q&A (long form):** [Maxio_Technical_Readiness_QA.md](./Maxio_Technical_Readiness_QA.md)  
> **Status labels:** **Shipped** = code in product · **Partial** = real path, incomplete UX · **Docs / roadmap** = architecture or plan only · **Missing** = not built · **Speculation** = not verified in repo  
> **As of:** 2026-09-08 — **body reconciled.** Stale statements were corrected in place, not just superseded in §0, so nothing below needs mental overriding under meeting pressure.  
> **Do not claim in-room:** live native Maxio API connector · issued SOC 2 report · named customer logos · Abacum “win” data or feature matrices · **calibrated** Probability of Attainment · month-level resampling · three years of loaded actuals · persisted/citable plan assessments · multi-user warehouse load locking · preferred/successor partner status as today’s ask · a fixed implementation price

---

## 0. Changed since 2026-08-31

Plan Assurance and the Budget Engine shipped **2026-09-04 → 09-07** (PRs #140/#142; `a16fb28`, `2377359`, `35cba1f`, `895ff32`, `d338a43`). The PPI Phase 1 backend landed **09-08**. The Aug 31 briefing understated the product; **that has now been fixed throughout the body**, and the posture on Abacum, MCP and the meeting format has been reframed.

| Aug 31 position | Position as of 2026-09-08 |
|---|---|
| PPI Feasibility / PoA / Monte Carlo — **Docs only** | **Shipped and demoable.** 1,000-draw simulation through the Budget formula graph; empirical μ/σ and breach frequencies; histograms; sensitivity on two levers |
| Feasibility runner — **Roadmap** | **Shipped** — 15-constraint risk strip. Not yet keyed to a promoted forecast version |
| Constraints registry — **Roadmap** | **Shipped 09-08** — declarative registry with tenant + version overlay (`app/services/predictive_planning/constraints.py`) |
| What Has to Be True — **Roadmap** | **Shipped 09-08** — structured `must_close` / `must_confirm` / `must_hold` conditions with levers |
| Budget = another scenario load | **Budget Engine shipped** — calculated from a driver set. Methodology written: [SMPL_Budget_Methodology.md](../product/SMPL_Budget_Methodology.md) |
| Ask = **preferred / successor** FP&A partner; displace Abacum | **Reframed** — an *additional customer lane* (lean finance teams). Preferred positioning is earned after a joint result. See §6.2 |
| MCP = ungoverned-answer risk, and the assumed data pipe | **Reframed** — governed foundation we extend. MCP / API / exports is a per-use-case question for the technical session |
| Implementation = "Path A white-glove load" footnote | **Elevated to a top-three argument** — SMPL implements; customer validates and decides. See §6.4 |
| Agenda = 45–60 min extended | **12-minute walkthrough today**; the 45-minute technical session is the *ask*. See §11 |
| "Do not start Monte Carlo" | **Superseded** — built |

**Still true and unchanged:** no live Maxio connector, no issued SOC 2, no customer logos, no Abacum teardown, no multi-user warehouse load lock.

**Naming discipline that now matters more, not less:**
- Simulation output is **stress frequency under stated priors** / `P(breach | lever noise)` — **not** calibrated Probability of Attainment until Phase 2.
- Monthly cash bands **shipped 09-08**: each draw now retains its full 12-month path, so P10–P90 by month, the intra-year trough distribution, and the tightest month are real measured outputs. Levers are still drawn **once per trial** and propagated — not resampled monthly.
- Prior-year comparisons use **loaded actuals where present**; the deeper series is **backcast**.
- Feasibility assessments are a **live read**, not persisted or citable in a board package.

**Source of truth for this section:** [Plan_Assurance_Predictive_Presentation_Brief.md](../product/Plan_Assurance_Predictive_Presentation_Brief.md) · [Plan_Assurance_Demo_Deferred_Backlog.md](../product/Plan_Assurance_Demo_Deferred_Backlog.md)

**Primary sources (repo truth):**  
[INTEGRATIONS_SETUP.md](../INTEGRATIONS_SETUP.md) · [SMPL_BUILD_OUT_MAPS.md](../architecture/SMPL_BUILD_OUT_MAPS.md) · [WAREHOUSE_GATE_NEAR_TERM_PLAN.md](../soc2/controls/WAREHOUSE_GATE_NEAR_TERM_PLAN.md) · [soc2/controls/README.md](../soc2/controls/README.md) · [SMPL_Predictive_Planning_Intelligence_Framework.md](../product/SMPL_Predictive_Planning_Intelligence_Framework.md) · [SMPL_Agent_and_Predictive_Analytics_Checklist.md](../product/SMPL_Agent_and_Predictive_Analytics_Checklist.md) · [Forecasting_Assumptions.md](../Forecasting_Assumptions.md) · [Reporting_Logic.md](../Reporting_Logic.md) · [GO_LIVE_POC_DIRECT_DATA_ACCESS.md](../GO_LIVE_POC_DIRECT_DATA_ACCESS.md) · [CLOSE_PEAK_WORKLOAD.md](../CLOSE_PEAK_WORKLOAD.md) · [Maxio_Technical_Readiness_QA.md](./Maxio_Technical_Readiness_QA.md)

---

## 1. Problem statement — show trust without hand-checking Neon

**Founder pain:** Leadership and partners ask “are these numbers right?” Today the honest answer often requires Matt (or ops) to open Neon / warehouse rows and re-tie by hand. That does not scale for Maxio co-sell, design partners, or board packages.

**What “good” looks like (product, not SOC theater):**

1. Every board / close / Copilot number is **calculated** from warehouse / engines (not invented by the LLM).
2. Automated **validation** exposes pass/fail with named checks, period, scenario, and version stamps — visible in UI / export, not only in API JSON.
3. When something fails, Finance sees a **remediation path** (which source / which tie), not a green dashboard.
4. AI **explains** only validated evidence packages — claim / citation / attribution gates already exist on primary paths.
5. Matt never needs a SQL console to *show* checks-and-balances in a partner or customer meeting.

**Marketing theme already in motion:** calculate → validate → explain (blog cluster / warehouse-gate plan). Product UX for “validation status as a first-class surface” is the gap between story and demo.

---

## 2. What we already have (honest inventory)

### 2.1 Shipped product (can demo with Demo Co / Path A data)

| Capability | Where | Honest limit |
|------------|--------|--------------|
| Deterministic waterfalls + 3-statement / Combined | Warehouse `actual_*` / `budget_*` / `forecast_*`; board + FE | SoT hierarchy documented; dual demo seeds left alone by design |
| Validation catalog + export pre-check | `GET /api/v1/export/validation`, financial-statement validation, close integrity | API + Validation tab in close package; **not** a polished “trust home” for execs |
| Fail-closed export option | `block_on_failure` → HTTP 409 on fail | Must be turned on; not every path hard-blocks |
| Freeze packs (COMPLETE / STALE) | Close-context blobs; MD&A / Copilot binding | Required on some export/MD&A paths; STALE labeled |
| AI claim / attribution / citation verify | Commentary, Prompt 2 (stricter), Prompt 5 (soft-strip + export), board regenerate, Copilot | **Primary AI paths** — not every chart datapoint at DOM render |
| Evidence packages + `_sources` (v1) | LLM payloads | Partial; honest nulls when missing |
| DOM provenance overlay | `smpl-provenance.js`, Ctrl+Shift+A | Partial on Board/FE KPIs when hydrate has tags |
| Forecast draft → **Promote to Final** | `forecast_version_service` / FE | Writes `forecast_*`; advisory client A–F at promote |
| Driver forecast chain | `driver_forecast/*`, Forecasting_Assumptions | Deterministic Plan layer strong |
| Path A white-glove load | Scripts + CSV → Neon | Native connectors **not** GA |
| Workforce / GTM validation strip | Workforce UI | Narrow domain, useful Phase 1 PPI seed |
| **Budget Engine** (shipped 09-04 → 09-07) | `/budget-engine`, wired into app shell | Budget is **calculated** from a driver set through a closed formula graph — not a CSV load. Approval workflow still thin (no `submitted` state) |
| **Plan Assurance** — 15-constraint risk strip, historical outlier review, named stress cases, 1,000-draw Monte Carlo | `/budget-engine?tab=analytics` | Runs on the Budget surface; not keyed to a promoted forecast version; assessments not persisted |
| **PPI Phase 1 backend** (09-08) | `app/services/predictive_planning/*`, `/api/v1/predictive-planning/*` | Constraints registry, feasibility runner, What Has to Be True, assessment DTO. Thresholds still duplicated in Budget Engine JS |
| **SMPL-performed implementation** | Path A load + mapping + tie-out, done by us | Native connectors **not** GA; packaging is a direction, not a published SKU. **This is a top-three argument — see §6.4** |

### 2.2 Docs / architecture (strong story; do not overclaim as live UX)

| Asset | Role |
|-------|------|
| Map 3 validation/trust canvas + Mermaid | Load → Calculate → Validate → Freeze → Explain |
| Data integrity framework | Normative provenance / tie-out design target |
| Warehouse-gate near-term plan | Honest LIVE / PARTIAL / OPEN matrix (2026-07-31 inventory) |
| PPI framework + Agent checklist §7 | Phase 1–5 plan. **Phase 1 shipped 09-08; Phase 3 simulation shipped 09-07 (client-side). Phases 2, 4, 5 open** — see framework §0.1 |
| Forecasting_Assumptions | Drivers, roll-forward, Budget vs Forecast vs Actual |
| Maxio partnership track in INTEGRATIONS_SETUP | Kevin/Nick notes; scaffold scripts; credentials **nice-to-have**, not meeting unlock |
| Blog themes | calculate→validate→explain; financial-data-validation; connected-systems |

### 2.3 Explicitly NOT ready

| Claim | Reality |
|-------|---------|
| Native Maxio connector live | Scaffold only (`maxio_sandbox_probe.py`, `maxio_export_to_smpl.py`); **credentials likely not landing for this meeting** — Path A / CSV / demo |
| Live Maxio ARR in Demo Co from API | No — Path A CSV / demo only; treat Maxio-shaped billing files as the demo path |
| Full warehouse SQL tie-out HTML report | OPEN / roadmap |
| Every chart cell cite-at-render | OPEN |
| ~~PPI Feasibility / PoA / Monte Carlo — Docs only~~ | **Feasibility and Monte Carlo are SHIPPED and demoable.** Still not ready: **calibrated Probability of Attainment** (Phase 2), trajectory and forecast-accuracy objects, month-level resampling |
| Budget methodology productized as a **guided cycle UI** | Engine shipped; methodology **written** ([SMPL_Budget_Methodology.md](../product/SMPL_Budget_Methodology.md)). Still missing: guided annual-cycle UI, `submitted` approval state, feasibility as a promotion gate |
| SOC 2 Type I issued | Pursuing / readiness docs only — deflect per sales KB |
| Abacum feature matrix / win rates / SOC claims | **Do not invent** — no teardown in repo; see §6 for the confirmed partner fact and the **additional-lane** frame |
| Preferred / successor partner status as today's ask | **Retired** — wrong opening ask without a joint customer result; see §6.2 |
| Packaged implementation pricing / timeline | Direction only — do **not** quote a number |
| Three years of loaded actuals behind the outlier review | Prior year uses loaded actuals where present; the deeper series is **backcast** |
| Customer logos / design-partner counts | Deflect until approved |

---

## 3. Trust / verification methodology proposal

**Goal:** A repeatable **evidence package** Finance (and Maxio SCs) can open without Neon.

### 3.1 UX surfaces (build toward — prioritize for “show trust”)

| Surface | Purpose | Ship posture |
|---------|---------|--------------|
| **Reconciliation status strip** | Org + period + scenario: green / warn / fail count; one click into failures | Partial APIs exist → **productize as always-visible strip** on Board / Close / Export |
| **Validation checklist UI** | Named checks from catalog (bookings↔ARR, cash bridge↔BS, deferred rollforward, billing↔ARR when Maxio loaded) | Catalog shipped → **checklist UI** is the founder gap |
| **Period / version stamps** | `as_of_period`, scenario, forecast_version_id, freeze pack id, loaded_at | Partial in freeze / payloads → make **visible in header of every export + board chrome** |
| **Variance pack** | Actual vs Budget vs Forecast for ARR, bookings, cash, EBITDA — with drill to waterfall rows | Variance slides / MD&A exist → package as downloadable **Variance Evidence Pack** (xlsx/HTML) |
| **Cite-to-calc** | Click KPI → `_sources` / table.column / formula | Overlay partial → deepen for meeting demo KPIs only first |
| **AI explain bound to pack** | Copilot answers only from freeze + validation-passed evidence | Primary paths LIVE — demo this; do not invent SOC language |

### 3.2 Evidence package contents (what Claude can help draft — safely)

Claude / Cursor should draft **methodologies and checklists**, not fake certifications.

**Safe to draft with Claude:**

1. **Tenant Validation Methodology** — which ties run at load vs close vs export; $1 actuals bar; soft bank timing (~$1k) vs statement identity.
2. **Maxio customer tie-out playbook** — CRM closed-won ↔ MRR new ARR; Maxio billing/ARR ↔ MRR waterfall; Maxio rev-rec/deferred ↔ ERP; cash ↔ bank (soft).
3. **Board Provenance one-pager** — freeze COMPLETE, as-of stamp, validation summary, “AI did not compute these dollars.”
4. **Variance commentary SOP** — Prompt 2 fail-closed vs Prompt 5 soft-strip honesty.
5. **Partner demo script** — which screens show checks without SQL.

**Do not invent:**

- SOC 2 “certified,” CPA-attested tie-outs, “audit-ready” as legal claim  
- Live Maxio sync SLAs  
- “100% of numbers cited at render” until OPEN items close  
- Customer logos or win rates vs Abacum  

### 3.3 Method labels (copy discipline)

| Say | Do not say |
|-----|------------|
| Automated tie-outs at $1 on closed actuals | “Audited by SMPL” |
| Fail-closed on wired AI / export paths | “Impossible to be wrong” |
| Path A / CSV today; native Maxio on partner track | “Maxio native connector GA” |
| SOC 2 Type I in progress | “We are SOC 2 certified” |
| Plan Assurance tests whether the plan can be delivered | “AI predicts your ARR” |
| Stress frequency under stated priors · `P(breach | lever noise)` | “Probability of Attainment” (until Phase 2 calibration) |
| Annual assumptions sampled once, propagated through the **monthly** cash schedule → P10–P90 by month + trough | “We resample shocks every month” / “day-by-day simulation” |
| Plan compared against **prior-year** actuals where loaded | “Three years of loaded actuals” |
| The LLM **evaluates and explains** from structured evidence | The LLM computes, edits or invents a financial value |
| **We** implement; the customer validates and decides | A fixed implementation price or timeline |

---

## 4. Budget methodology — gaps today + recommended outline

### 4.1 Gaps today

> **Updated 2026-09-08.** The Budget Engine shipped, so "Budget is just another scenario load" is no longer true. The remaining gaps are **process and workflow**, not engine or math — keep the two separate in the room.

| Area | Today | Gap |
|------|-------|-----|
| Scenario spine | Actual / Budget / Forecast / Combined in warehouse | ~~Budget treated like another scenario load~~ — **Budget Engine shipped**: calculated from drivers through a closed formula graph |
| Drivers | Forecast driver catalog strong; **Budget driver set now documented** | Lock calendar still not a guided UI |
| Versions | `draft` → `final` → `superseded` **shipped**, admin/owner only | **No `submitted` state** — "sent for approval, not yet approved" is not auditable |
| Promote | Governed: requires table rows, supersedes prior final, loads five budget tables | **Feasibility does not gate promotion** — a failing plan can be promoted. Open product decision |
| Vs actuals | Combined + variance patterns | Budget vs Actual operating cadence documented in methodology; **not yet a customer-facing guide** |
| Maxio | Billing actuals feed ARR SoT when loaded | Budget bookings still plan/CRM-driven when opportunity files loaded — must stay explicit; schema supports `budget_opportunity_movements` |

### 4.2 Recommended Budget Methodology outline — ✅ written 2026-09-08

**Now a real document:** [SMPL_Budget_Methodology.md](../product/SMPL_Budget_Methodology.md). It follows the outline below with three corrections found by reading the code rather than the plan:

- **Version states are `draft` → `final` → `superseded`**, not Working → Submitted → Approved. There is no `submitted` state, so the approval step is not auditable today.
- **Feasibility does not gate promotion.** A plan with failing constraints can be promoted. Validation gates export; feasibility does not gate approval. Flagged as an open product decision, not a bug.
- **Promotion is governed** — admin/owner only, requires table rows, supersedes the prior final, and loads five budget warehouse tables.

Original outline, retained for reference:

1. **Planning calendar** — annual build window; mid-year refresh; monthly Forecast overlay; Combined cutover rule.  
2. **Owners** — FP&A owns Budget; RevOps owns pipeline inputs; Accounting owns Actual close.  
3. **Driver set for Budget** — subset of Forecasting_Assumptions (growth, churn, NRR, headcount, marketing, DSO/DPO, min cash).  
4. **Build sequence** — same dependency order as forecast (pipeline → ARR → deferred → cash → statements → validate).  
5. **Version states** — Working → Submitted → Approved (Final); no silent driver edits after Approved.  
6. **Roll-forward at year start** — prior Actual ending → Budget beginning where applicable.  
7. **Promote / lock** — only admin/owner; validation gate before Final.  
8. **Monthly observe** — Budget vs Actual vs Forecast; material variance pack for board.  
9. **AI role** — suggest driver diffs; never write Budget Final without human approve.  
10. **Maxio note** — Budget is plan; Maxio supplies billing actuals for variance — not a substitute for the Budget model.
11. **Drilldown note** — extend Pipeline cell→opportunity pattern to Budget scenario when `budget_opportunity_movements` is loaded; GL lines use `budget_gl_detail` / statement tables.

---

## 5. Predictive analytics / PPI — what to say vs what’s not ready

**Principle (verbatim from framework):** Most planning software helps Finance *build* the plan. PPI helps Finance know whether the business can *deliver* it. **Plan → Test → Observe → Reassess → Act.**

### 5.1 Phase 1 — shipped, not asked for

| Deliverable | Status |
|-------------|--------|
| Constraints registry (15 constraints, tenant + version overlay) | **Shipped** 09-08 |
| Feasibility runner (pass / warn / fail / advisory / skipped) | **Shipped** 09-08 |
| What Has to Be True structured list | **Shipped** 09-08 — `must_close` / `must_confirm` / `must_hold` with levers |
| Assessment DTO + `_sources`; no waterfall mutation | **Shipped** 09-08 — `/api/v1/predictive-planning/*` |
| Named stress cases + 1,000-draw Monte Carlo | **Shipped** 09-07 (client-side) |
| Historical outlier review vs prior year | **Shipped** 09-07 |
| Keyed to a **promoted forecast version** | **Partial** — DTO accepts a version id; no caller sends one |
| Assessment **persistence** (citable in a board package) | **Missing** — next step |
| Calibrated Probability of Attainment | **Missing** — Phase 2, do not claim |

**What this changes in the room:** the predictive layer is no longer a roadmap ask. Demo it. The honest remaining gap is that an assessment is a **live read, not a stored artifact** — so it is not yet something you cite in a board packet.

### 5.2 The four-layer architecture (say it this way)

> The **deterministic engine** calculates the plan. The **historical-context layer** assembles the relevant prior-period evidence. The **predictive analytics layer** models potential outcomes. The **LLM evaluates and explains** the plan using that structured evidence — without computing or altering any financial value.

This is stronger and more accurate than "the LLM narrates." The model performs genuine qualitative evaluation — is this plan aggressive, is the shape credible, which risk comes first — while remaining barred from producing a number. Every lane also has a **deterministic fallback narrative**, so the analysis still renders if the model is unavailable.

### 5.3 What to say in the Maxio meeting

- We **calculate, validate and board-package** SaaS actuals; Maxio is the natural billing SoT in the CRM → Maxio → ERP stack.  
- **We build the operating budget in a real engine**, then test whether it can be delivered — feasibility, historical comparison, stress cases and simulation.  
- **We do the implementation.** The customer's stack, Maxio included, stays as it is (§6.4).  
- **The ask is a customer lane, not a partner swap:** growth companies with lean finance teams that want this capability without implementing and administering an FP&A platform.  
- Bookings "confidence", CRM probability and simulation breach frequency are **not** Probability of Attainment — we will not misuse those words.

### 5.4 What not to overclaim

- **Calibrated Probability of Attainment** — Phase 2. Simulation output is stress frequency under stated priors.  
- **Month-level resampling** — levers are drawn once per trial and propagated. Monthly bands are cross-sectional percentiles across draws, not one traced path.  
- **Depth of history** — prior year uses loaded actuals where present; the deeper series is backcast.  
- **Persisted / citable assessments** — feasibility is a live read, not yet a stored artifact keyed to a promoted version.  
- **Trajectory, assumption-risk ranking, forecast-accuracy learning** — Phases 2 and 4.  
- **Abacum displacement** — not the ask today, and no feature matrices or win rates in any case.  
- **Packaged implementation pricing** — a direction, not a SKU.

---

## 6. Maxio vs Abacum competitive frame

### 6.1 Confirmed + repo truth

| Fact | Source |
|------|--------|
| Stack: CRM → pipeline; **Maxio → billing/ARR actuals (+ rev-rec)**; ERP → GL | INTEGRATIONS_SETUP; Agent checklist §3 |
| Maxio partnership: Kevin 2026-08-21, Nick 2026-08-26; learn.maxio open; AB API scaffold ready — **credentials nice-to-have, not meeting unlock** | INTEGRATIONS_SETUP |
| **Abacum is Maxio’s current FP&A / planning partner** | **Confirmed** — Matt / partner confirmation **2026-08-31** |
| Mosaic/Drivetrain cited as prior FP&A integrations on Maxio side; Mosaic→HiBob billing bundle = signal some customers want **independent** FI | INTEGRATIONS_SETUP (partnership notes) |
| Sales KB has Mosaic competitive entry; **no Abacum feature teardown / win-rate entry** | `knowledge_base.json` — do not invent matrices |
| Native connectors not GA; Path A CSV today | BUILD_OUT_MAPS; sales KB connectors |

### 6.2 Partnership value proposition (say this)

> **Reframed 2026-09-08.** The old framing — preferred / successor partner, displace Abacum, customers should not keep both — is the eventual ambition, not today's ask. Nick has a relationship to protect and we have no joint Maxio customer result. Leading with displacement makes him defend rather than explore.

**The ask:** *"We believe SMPL serves an additional customer lane within Maxio's base — growth companies with lean finance teams that want sophisticated planning and financial intelligence but don't want to implement and administer a traditional FP&A platform."*

1. **A different lane, not a swap** — the constraint in that segment is capacity, not features. A two- or three-person finance team has the need and no ability to run a planning platform.  
2. **We do the implementation** — customer's stack as-is, Maxio intact, customer validates and decides (§6.4).  
3. **CRM ≠ billing ≠ ERP** — Maxio customers still fight three truths; SMPL reconciles and board-packages them.  
4. **Trusted ARR + board + validation** — evidence-bound narrative, fail-closed on wired paths.  
5. **Plan Assurance, demoable today** — the plan gets tested against constraints, history and simulation, not just built.  
6. **Complement Maxio, don't cannibalize** — Maxio owns quote-to-cash and rev-rec actuals; SMPL owns close integrity, Combined views, planning/forecast, board/MD&A, and plan deliverability.  
7. **Co-sell ICP** — growth SaaS ~$10–100M, often post–first audit; VC/PE sometimes require Maxio (**partner note**).

**Earn preferred positioning in this order:** validate the lane → technical validation → one joint design-partner implementation → measurable results → *then* preferred positioning.

### 6.3 Still unlabeled / do not invent

| Item | Discipline |
|------|------------|
| Abacum feature matrix, win rates, SOC claims | **Do not invent** — no teardown in repo |
| Abacum as full FP&A suite | Category framing only; no product claims |
| Preferred / successor / displacement language | **Not today's ask.** Do not raise it, and do not imply customers should drop Abacum |
| "Customers want less software, not more" as an Abacum argument | Retired — it reads as displacement. The lane argument stands on capacity, not consolidation |
| Commercial motion | Additional lane → design partner → results. **Unproven commercially** — no production replacement claims |

**If they raise Abacum (confirmed partner):** "Abacum is your FP&A partner and we're not asking you to revisit that. We think there's a different lane in your base — lean finance teams that want this capability without running a platform themselves. We'd like to test that with one joint customer."

### 6.4 SMPL performs the implementation — a top-three argument

This has been buried as "Path A white-glove load." It is one of the three strongest things to say.

- **SMPL builds the environment.** We stand up the warehouse, mappings, tie-outs, budget and board surfaces.
- **The customer does not redesign its systems.** Existing stack and data taken largely as-is.
- **Maxio remains intact and central.** No change to their billing configuration.
- **Customer participation is validation and decision-making** — confirm mappings and definitions, approve the plan.
- **Standard Maxio configurations are a known shape**, so those implementations could plausibly be packaged predictably.
- **Total cost includes far less internal finance labour and change management** than a self-administered platform.

**Why Nick cares:** it reaches customers his current FP&A partner realistically cannot serve, without asking him to move anyone off anything.

**Honest limits:** native connectors not GA (white-glove load today); packaged pricing is a direction, not a SKU; no joint Maxio implementation yet.

---

## 7. Drilldown readiness (extend the Pipeline pattern)

**Founder ask:** Checks need drilldown — Forecast → opportunities; Actuals → GL; Budget → clarify composition.

### 7.1 Pattern to extend (Shipped — `/app` Pipeline)

| Layer | What it does | Where |
|-------|--------------|--------|
| UI | Pipeline waterfall table; click movement cell; show opp count; load detail panel + tie pass/fail | `frontend/components/ExecutiveFlowDashboard.tsx` → `PipelineWaterfallTable`; hosted on `/app` via `frontend/app/app/page.tsx` |
| API | `GET /api/v1/waterfalls/pipeline/drilldown?organization_id&scenario&period&waterfall_type&expected_amount` | `backend/app/api/waterfall_routes.py` |
| Service | Reads `{scenario}_opportunity_movements`; maps movement types; signs closed_won/lost/slipped; optional `pipeline_cell_opportunities_tie` | `pipeline_opportunity_drilldown_service.py` |
| Types with drill | `pipeline_created`, `closed_won`, `closed_lost`, `slipped_pipeline` | Beginning/ending balances → `drilldown_available=false` with explicit message |
| Twin pattern | Cash bridge cell → GL / workforce lines | `cash_flow_gl_drilldown_service.py` + same dashboard |

**Not the same thing:** Board HTML “Pipeline” sub-tab (`frontend/public/board/index.html` `_sPipeline`) is chart/KPI narrative — **does not** call the drilldown API. Forecast Engine “Pipeline Detail” is deal lists from embedded `SRC.opp_pipeline` seed — useful UX metaphor, not warehouse-tied.

### 7.2 Readiness by scenario (honest)

| Check | Desired drill | Status | Notes |
|-------|---------------|--------|-------|
| Forecast pipeline / bookings movements | → opportunities | **Shipped** (when `forecast_opportunity_movements` loaded) | Primary pattern |
| Actual pipeline movements | → opportunities | **Shipped** (same API, Actual scenario) | Needs Actual opportunity-movements CSV loaded |
| Actual cash / P&L | → GL | **Partial** | Cash drill **Shipped**; Management P&L ▶ GL in Board; not universal every cell |
| Budget pipeline | → opportunities | **Partial / data-dependent** | Schema + templates include `Budget_OpportunityMovements.csv` — **not** “pure GL only.” Same drilldown endpoint when Budget movements loaded |
| Budget statements | → GL / plan lines | **Partial** | `Budget_gl_detail` + `budget_*` statement tables exist; methodology UX thin |
| Every Forecast ARR KPI | → deals | **Missing / uneven** | Do not claim all Forecast numbers drill to opps today |

**Product next step:** Reuse Pipeline cell→API→tie panel for any board/check surface that today dead-ends at a headline number.

---

## 8. Concurrent load posture (what Matt remembered)

**Verdict:** Multi-person **warehouse load** locking was **not** shipped as a product mockup. What exists is (a) org isolation + last-write-wins replace, (b) **export** per-org concurrency, (c) close-peak **docs** for queues / Prompt 5 locks.

| Concern | Status | Evidence |
|---------|--------|----------|
| Org isolation on load | **Shipped** | `organization_id` on facts; Path A `-OrganizationId`; loader delete+insert scoped to org |
| Overwrite policy | **Shipped (last write wins)** | `load_physical_table_rows`: replace org-scoped rows in the versioned physical table |
| Load “in progress” / advisory lock | **Missing** | No `pg_advisory_lock` / warehouse load mutex found |
| Concurrent multi-person CSV load UX | **Missing** | Two loaders on same org = race; last complete replace wins |
| Heavy export concurrency | **Shipped** | `export_jobs.py` — max 1 heavy job per org (`ExportJobConflictError`); `test_per_org_concurrency_lock` |
| Close-peak job queues / fairness | **Partial + Docs** | Durable export jobs + progress stages **Shipped**; four-queue topology + Cohort A “basic per-org lock” in `CLOSE_PEAK_WORKLOAD.md` = **design target**, shared pool OK day-one |
| Locked actuals (no overwrite closed periods) | **Docs / Partial** | Intent in `Forecasting_Assumptions.md`; `period_close_status` future; close session `close_lock_events` ≠ CSV load lock |

**Say in room:** “Tenants can’t see each other’s rows. Reloads replace that org’s table slice. We serialize heavy board exports per org. We have not yet productized a multi-user warehouse load lock — Path A is ops-controlled today.”

---

## 9. Revised Maxio approach (credentials likely NOT coming)

**Shift:** Meeting success ≠ live Advanced Billing pull.

| Old framing | New framing |
|-------------|-------------|
| Ask for site+key as the unlock | Show governed FI readiness on Path A / CSV / Demo Co |
| Blocked until AB probe | Scaffold remains; credentials are a **follow-up nicety** |
| Live Maxio ARR in product this week | Maxio-**shaped** billing CSVs into `billing_arr` when/if they share exports |

**Still useful to ask (soft, not blocker):** sandbox site+key later; MCP / API / export scope **as a per-use-case question**; the customer-lane validation; the technical-session date — the agenda must not stall if they say no on credentials.

**Demo without API:** Board + validation/freeze, **Budget Engine + Plan Assurance**, `/app` Pipeline drill if time, CRM≠billing≠ERP diagram, Path A playbook. Optional public Chargify sandbox signup is not required for the partner narrative.

---

## 10. Technical Q&A (meeting crib)

Full answers: **[Maxio_Technical_Readiness_QA.md](./Maxio_Technical_Readiness_QA.md)**. Top eight:

1. Forecast → deals? **Partial/Shipped on Pipeline pattern** — extend elsewhere.  
2. Actuals → GL? **Partial** — cash/GL paths exist; not universal.  
3. Budget composition? **Real Budget Engine** — calculated from a driver set through a closed formula graph; `budget_*` tables are the *output*. Gaps are approval workflow, not math.  
4. Tenant isolation? **Shipped.**  
5. Two people load same org? **Missing load mutex; last-write-wins; export lock Shipped.**  
6. Maxio connector live? **Missing (scaffold); Path A demo.** MCP / API / exports — which fits which use case is a technical-session question.  
7. Trust without Neon? **Partial** — validation/freeze/claim-verify; trust-home UX gap.  
8. Replace Abacum? **Not the ask.** Additional customer lane: lean finance teams that won't administer an FP&A platform. No feature or win-rate fiction.  
9. Anything predictive? **Yes — shipped and demoable.** Feasibility, historical outlier review, stress cases, 1,000-draw simulation. Not calibrated PoA.  
10. Who implements? **We do.** Stack as-is, Maxio intact, customer validates and decides.

---

## 11. Meeting agenda / demo script

> **Replaced 2026-09-08.** The 45–60 minute extended agenda below was written for a different meeting. Today is a **12-minute partner walkthrough**. The long session is what you are *asking for*, not what you are running.

### 11.A Today — 12-minute partner walkthrough

| Min | Block | Goal |
|-----|-------|------|
| 1 | **The Maxio customer gap** | Their curriculum ends at trustworthy actuals. Ask the question; let Nick confirm it |
| 2 | **Board + trusted actuals** | Calculate → validate → explain. Validation and as-of stamp, no Neon |
| 2 | **Budget Engine** | Budget is *calculated* from a driver set, not loaded — walk the formula graph briefly |
| 2 | **Historical plan evaluation** | Outlier review: plan shape vs prior year, with severity and citations |
| 3 | **Cash distribution + risk drivers** | Monthly P10–P90 cash band with the floor drawn in, the intra-year trough distribution, and the contrast that sells it: **P(any month below floor) vs P(December below floor)** — a plan can end the year fine and still need financing in July. Then the 15-check strip |
| 1 | **Done-for-you implementation** | We implement; stack as-is; Maxio intact; customer validates and decides |
| 1 | **The next-meeting ask** | Validate the customer lane + book the 45-minute technical session |

**Total: 12 minutes.** If time is cut, drop the historical lane before the cash distribution — the distribution is the thing Maxio's own reporting cannot do.

### 11.B What you are asking for — 45-minute technical session

| Item | Detail |
|------|--------|
| **Who** | Partnerships + solutions consulting + product/integrations |
| **Data paths** | Which of **MCP / REST API / standardized exports** fits which use case — governed queries vs repeatable warehouse loads are different requirements |
| **Data objects** | Object mapping and reconciliation: CRM closed-won ↔ MRR new ARR, Maxio billing/ARR ↔ MRR waterfall, rev-rec/deferred ↔ ERP |
| **Joint customer profile** | Define the lean-finance-team lane precisely enough to identify candidates |
| **Design partner** | Scope one joint implementation, run by SMPL |

### Demo script (do / don’t)

**Do show**

1. Board / executive flow: ARR from MRR waterfall SoT, with the as-of stamp.  
2. Validation summary — name a failing check if demo data has one; better than fake green.  
3. **Budget Engine**: the driver set and the fact that every month is computed.  
4. **Plan Assurance**: the 15-check risk strip, the historical outlier findings, and the Monte Carlo — monthly cash band, trough distribution, and the tightest-month callout.  
5. `/app` Pipeline waterfall: click Closed Won → opportunity list + tie banner (if time).  
6. Forecast promote story (draft → final) as governance — not as "AI forecast."  
7. Diagram: CRM ≠ Maxio ≠ ERP → SMPL reconcile; Path A lands billing exports.

**Do not show / claim**

- Live pull from Maxio production/sandbox API (credentials unlikely).  
- "We have multi-user warehouse load locking."  
- SOC 2 report.  
- ~~PPI simulation / PoA meters~~ → **simulation is fine to show**, including the monthly P10–P90 band and trough. Do not label breach frequency as Probability of Attainment, do not claim shocks are resampled monthly, and do not imply three years of loaded actuals.  
- Preferred / successor partner framing or Abacum displacement — **not today's ask**.  
- A fixed implementation price or timeline.  
- Invented customer logos.  
- Hand SQL in Neon as the trust proof.  
- That Board HTML Pipeline tab is the same as `/app` drilldown.

### Asks to leave with

1. **Confirm the customer lane** — does the base include lean finance teams that want this without administering an FP&A platform? *(the one that matters)*  
2. **Book the 45-minute technical session** — partnerships + SC + product/integrations (§11.B).  
3. Agreement to **scope one design-partner implementation** if the lane checks out.  
4. **Confirm the curriculum gap** — planning/board content missing? Interest in co-built enablement?  
5. Partner certification track to complete.  
6. Sample Maxio CSV / export, or AB sandbox site + key — **soft, last**, explicitly not the unlock.

---

## 12. This week’s build / doc priorities (ordered, realistic)

| # | Priority | Type | Outcome |
|---|----------|------|---------|
| 1 | **Path A / demo readiness** — Maxio-shaped billing CSV map + Demo Co narrative without live API | Ops / doc | Meeting does not depend on credentials |
| 2 | **Trust without Neon** — one-pager + (if capacity) Reconciliation status strip / Validation checklist UI stub | Doc + small UX | Founder can demo checks-and-balances |
| 3 | **Drilldown extend plan** — document Pipeline pattern; stub next surfaces (Forecast ARR cells, Budget when movements exist) | Doc / small UX | Answers “click the number” |
| 4 | ~~Draft Budget Methodology~~ ✅ **done 09-08** — [SMPL_Budget_Methodology.md](../product/SMPL_Budget_Methodology.md) | Doc | Planning cycle language; clarify Budget ≠ mystery GL |
| 5 | **Concurrent load honesty card** — last-write-wins + export lock + CLOSE_PEAK roadmap (no fake mockup) | Doc | Technical Q&A ready |
| 6 | ~~PPI Phase 1 acceptance checklist — schedule eng only after trust UI strip exists / do not start Monte Carlo~~ **Superseded 09-08** — Monte Carlo shipped 09-07 and the Phase 1 backend (constraints registry, feasibility, WHTT, assessment API) landed 09-08. Remaining: persist assessments, single-source the thresholds | Plan | Phase 1 objects built |
| 7 | Sales KB: optional `maxio-partnership` + **additional-customer-lane** framing (not preferred/successor) | Content | Meeting aide |
| 8 | learn.maxio P0 paths (optional credibility) | Learning | Speaking credit |

**Explicitly defer this week:** waiting on Nick for site+key as a blocker, native connector framework package, Core rev-rec deep integration, PPI Phase 2–4 engines, SOC 2 claims, Abacum feature matrix fiction, inventing warehouse load locks.

---

## Quick reference — five sharp talking points

**The central story — lead with this:**

> Maxio gives SaaS finance teams governed recurring-revenue actuals. SMPL takes those actuals together with the customer's GL, CRM and workforce information, **implements the financial environment**, builds the operating budget, evaluates the plan against historical performance, models the distribution of future cash outcomes, and turns the results into board-ready decision support. **Maxio remains the recurring-revenue foundation, and the customer does not have to undertake a major FP&A implementation.**

1. **CRM ≠ billing ≠ ERP** — Maxio owns billing/ARR actuals; SMPL is the governed FI layer that reconciles and board-packages across the stack.  
2. **Trust is a product surface** — calculate → validate → explain, so nobody hand-checks Neon.  
3. **We build the plan and then test it** — Budget Engine plus Plan Assurance: 15 constraints, historical comparison, stress cases, 1,000-draw simulation. Demoable today; not calibrated PoA.  
4. **We do the implementation** — stack as-is, Maxio intact, customer validates and decides. Far less internal finance labour than a self-administered platform.  
5. **An additional customer lane, not a partner swap** — lean finance teams that want this capability without running an FP&A platform. Preferred positioning is earned after a joint result, not asked for today.

---

## Related paths

| Artifact | Path |
|----------|------|
| This briefing | `docs/partners/Maxio_Partner_Meeting_Prep_Trust_Budget_PPI.md` |
| Technical Q&A | `docs/partners/Maxio_Technical_Readiness_QA.md` |
| Executive one-pager | `C:\Users\mattj\Downloads\SMPL_Maxio_Week_Prep_One_Pager.md` |
| Maxio setup | `docs/INTEGRATIONS_SETUP.md` (§ Maxio) |
| Trust map | `docs/architecture/SMPL_BUILD_OUT_MAPS.md` (Map 3) |
| Gate honesty | `docs/soc2/controls/WAREHOUSE_GATE_NEAR_TERM_PLAN.md` |
| Close-peak concurrency design | `docs/CLOSE_PEAK_WORKLOAD.md` |
| Path A | `docs/GO_LIVE_POC_DIRECT_DATA_ACCESS.md` |
| PPI | `docs/product/SMPL_Predictive_Planning_Intelligence_Framework.md` |
| Forecast/Budget spine | `docs/Forecasting_Assumptions.md` |
