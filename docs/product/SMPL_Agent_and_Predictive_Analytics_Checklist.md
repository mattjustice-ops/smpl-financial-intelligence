# SMPL Agent, Model Creation & Tie-Out Checklist

> **Purpose:** Practical checklist for building or refreshing customer models, agent context, and close packages — incorporating external finance-AI learnings (Fluvo CFO webinar, Aug 2026) and SMPL’s existing validation posture.  
> **Not marketing:** Use for product, onboarding, and agent prompt design only.

**Related:** [SMPL_Predictive_Planning_Intelligence_Framework.md](./SMPL_Predictive_Planning_Intelligence_Framework.md) · [Reporting_Logic.md](../Reporting_Logic.md) · [Close_Process.md](../Close_Process.md) · [AI_SKILL_PRACTICES.md](../AI_SKILL_PRACTICES.md) · [Architecture_Master.md](../Architecture_Master.md) · [CUSTOMER_CLOSE_WORKFLOW.md](../CUSTOMER_CLOSE_WORKFLOW.md) · [soc2/controls/data_sources_tieout_prompt.md](../soc2/controls/data_sources_tieout_prompt.md)

**Last updated:** 2026-08-28

---

## 1. Foundation before prompts (context pyramid)

Most finance-AI failures are missing foundation, not missing prompt tricks. Order of operations:

| Layer | What “done” looks like | SMPL home |
|-------|------------------------|-----------|
| **Connected, reconciled data** | Source extracts loaded; waterfalls and statements agree at `$1` tolerance | Warehouse load + [Reporting_Logic](../Reporting_Logic.md) validation catalog |
| **Governed context** | One tenant definition for ARR, bookings date, pipeline stages, fiscal calendar | Onboarding discovery + `Reporting_Logic` + tenant settings (document; do not invent) |
| **Prompts / models / apps** | Agent or export runs only after layers 1–2 pass | Copilot, Prompt 2/5, forecast engine |

**Rule:** Do not ask the agent to “fix” a model until tie-outs explain the gap. Fix data or definitions first.

---

## 2. Pre-flight completeness (before model build or export)

Ask everything **once**, in one pass — do not start computing with silent gaps (Fluvo PGCI **Checks** step).

### Data load pre-flight

- [ ] **Scope locked:** `organization_id`, `scenario`, `start_period`, `end_period`, `as_of_period`
- [ ] **P0 datasets present** (see [Close_Process](../Close_Process.md)): GL actuals, MRR waterfall, cash bridge, balance sheet, deferred revenue waterfall
- [ ] **P1 if RevOps close:** pipeline waterfall, opportunities, marketing actuals
- [ ] **Source systems identified:** CRM, billing sub-ledger (Stripe / Chargebee / **Maxio** if present), ERP/GL, HRIS
- [ ] **Completeness signal:** customer knows % loaded and what is blocking (aligns with Close Workflow Load Integrity)

### Definition pre-flight

- [ ] **New ARR / bookings date policy** captured (close-date vs service-start — one policy per tenant)
- [ ] **ARR vs GAAP revenue** — waterfalls are SoT for ARR; deferred waterfall + IS for revenue (never derive ARR from revenue)
- [ ] **Combined cutover** for board: which months are Actual vs Forecast

### Model / agent pre-flight

- [ ] **Plan before execute:** for spreadsheet or forecast edits, agent states planned changes and missing inputs before writing cells (see [AI_SKILL_PRACTICES](../AI_SKILL_PRACTICES.md) §3)
- [ ] **Unresolved inputs → flag, don’t invent** — Copilot asks; export paths use insufficient-evidence / don’t-know
- [ ] **Validation pre-check run:** `GET /api/v1/export/validation?...` before distributing Excel or deck

If any P0 item is missing or ambiguous, **stop** — do not publish with `block_on_failure=false` and pretend the package is certified.

---

## 3. Cross-system tie-out patterns (stand by the numbers)

Finance hallucinations are caught only by **auditing numbers**, not by reading prose. These patterns must hold after every load (tolerance `$1.00` fail-closed unless noted).

| Pattern | Left side | Right side | Notes |
|---------|-----------|------------|-------|
| **Bookings → ARR** | CRM / pipeline `closed_won` | MRR waterfall `new_arr` | Primary RevOps tie; see `closed_won_arr_ties_mrr_new_business` |
| **Billing → ARR** | Billing sub-ledger contract MRR/ARR | MRR waterfall movements | When **Maxio** (or Stripe/Chargebee) is SoT for subscriptions, CRM is secondary for *actual* new ARR |
| **Billing → GL** | Billing recognized revenue / deferred | ERP GL revenue + deferred balance | Maxio → NetSuite/QBO/Rillet/Intacct; SMPL reads both, does not post |
| **Deferred rollforward** | Beginning + billings − recognized | Ending deferred | SoT for billings vs GAAP revenue |
| **Cash chain** | Bridge ending cash | Balance sheet cash; CFS net change | Bank timing soft ~$1k separate from statement identity |
| **Forecast seed** | Actual ending (ARR, cash) | Forecast period beginning | Break here → all forward periods wrong |

**Maxio customer pattern:** CRM still drives **pipeline / forecast**; Maxio drives **billing / ARR actuals / rev-rec**; ERP drives **audited GL**. SMPL reconciles across all three — it does not replace Maxio or the ERP. No native Maxio connector yet; Path A CSV/export until partner sandbox ([INTEGRATIONS_SETUP](../INTEGRATIONS_SETUP.md#maxio-partnership-track--wave-1-billing)).

**Opportunity drilldown:** `SUM(opportunity movements by waterfall_type) = pipeline waterfall row` — same bar as closed-won ↔ new ARR.

---

## 4. Fail-closed export & “stand by the numbers”

| Gate | Behavior |
|------|----------|
| Export with `block_on_failure=true` | HTTP **409** if any validation `status=fail` |
| Validation tab in close package | Every check named; `$1` miss = fail, not “rounding” |
| AI commentary / Copilot | Numbers from API only; claim-verify strips invented figures |
| Board / MD&A | No publish on failed closed-actuals ties; warnings documented in variance commentary |

**Stand by the numbers:** If leadership asks “is this right?”, the answer is the validation JSON + drilldown to source rows — not a confident narrative. Multi-thousand-dollar gaps are **data_mismatch**, never hand-waved as rounding.

---

## 5. Agent & predictive analytics guardrails

**Product principle:** Most planning software helps Finance build the plan. [Predictive Planning Intelligence](./SMPL_Predictive_Planning_Intelligence_Framework.md) should help Finance determine whether the business can actually deliver it. Progression: **Plan → Test → Observe → Reassess → Act**. Keep layers separate: Deterministic Finance Engine | PPI | Generative AI/LLM | Finance judgment.

When extending agent or predictive features:

- [ ] **Deterministic base first** — warehouse + validation produce the forecast envelope; ML/predictive layers propose outlooks inside that envelope, not alternate facts
- [ ] **PPI vs LLM** — statistical / feasibility outputs are PPI; LLM only narrates structured finance + PPI payloads ([framework §1–§4](./SMPL_Predictive_Planning_Intelligence_Framework.md))
- [ ] **Naming** — warehouse Scenario = Actual/Budget/Forecast; do not call CRM deal probability, bookings outlook bands, **or Monte Carlo breach frequency** “Probability of Attainment”
- [ ] **Skipped ≠ passed** — a check whose inputs are missing must surface as `skipped`, never as green
- [ ] **Evidence package** — thick context (freeze block, attribution, `_sources`) before model call ([AI_SKILL_PRACTICES](../AI_SKILL_PRACTICES.md) §6)
- [ ] **Definition skills > commentary skills** — promote metric policies into docs/code, not one-off prose macros
- [ ] **Prune unused recipes** after 2–3 closes — fewer durable SOPs beat a skill graveyard

Predictive analytics (partner conversations): iteration/outlook exploration is additive to validated actuals — customers still need tie-outs and fail-closed export before board send. Full capability map + phased plan: [SMPL_Predictive_Planning_Intelligence_Framework.md](./SMPL_Predictive_Planning_Intelligence_Framework.md).

---

## 6. Quick reference — who owns the tie

| Control | Owner | Platform check |
|---------|-------|----------------|
| GL ↔ TB | Controller | External ERP; `gl_actuals` load |
| Closed won ↔ new ARR | RevOps + FP&A | `closed_won_arr_ties_mrr_new_business` |
| Billing ↔ ARR | RevOps / billing ops | MRR waterfall vs billing export |
| Deferred ↔ subledger | Accounting | Deferred waterfall vs ERP |
| Cash ↔ bank | Treasury | Bridge vs bank (soft timing) |
| Export package | CFO | Validation tab green or explained |

---

## 7. Predictive Planning Intelligence — Phase 1 checklist

> ~~Plan-first. Do **not** start Monte Carlo / ML engines until Phase 1 exits.~~ **Updated 2026-09-08.** Monte Carlo shipped 09-07 (client-side) and the Phase 1 backend landed 09-08. Detail + reconciliation: [framework §0.1](./SMPL_Predictive_Planning_Intelligence_Framework.md) and [§5 Phase 1](./SMPL_Predictive_Planning_Intelligence_Framework.md#phase-1--test-the-plan-feasibility-constraints-what-has-to-be-true).

### Preconditions (reuse existing engine)

- [ ] Forecast version exists (draft or final) with regenerable driver schedules
- [ ] P0 tie-outs green for Actual cutover / roll-forward (same bar as §2–§4)
- [ ] Known inputs available: ending cash (bridge), pipeline coverage or bookings totals, workforce/GTM capacity where modeled

### Phase 1 build / acceptance

- [x] **Constraints registry** — 15 constraints with tenant + version overlay · `app/services/predictive_planning/constraints.py`
- [x] **Feasibility runner** — pass/warn/fail/advisory + skipped; does not mutate waterfalls · `feasibility.py`
- [x] **What Has to Be True** — structured `must_close` / `must_confirm` / `must_hold` conditions with levers · `what_has_to_be_true.py`
- [x] **API/schema** — assessment DTO with `_sources`; additive routes only · `/api/v1/predictive-planning/*`
- [ ] **Assess a selected forecast version** — DTO accepts a version id; no caller sends one yet
- [ ] **Persist assessments** keyed by `(organization_id, forecast_version_id, as_of)` — needed before an assessment can be cited in a board package
- [ ] **Single-source the thresholds** — rules are duplicated in Budget Engine JS and the Python registry; parity is currently held by test, not by architecture
- [ ] **LLM (optional)** — if narrated, consumes assessment + finance evidence only; claim-verify
- [x] **Backward compatible** — close/board export paths unchanged; fail-closed validation untouched
- [ ] **Copy audit** — UI/docs do not label CRM probability, bookings confidence, or simulation breach frequency as plan Probability of Attainment

### Explicitly later (not Phase 1)

- [x] ~~Monte Carlo / trial simulation~~ → Phase 3 — **shipped early, client-side only.** Not reproducible server-side or attachable to an export
- [ ] ~~Calibrated plan PoA / Assumption Risk / Trajectory objects~~ → Phase 2 — **still open.** Sensitivity curves exist; no ranked risk object
- [ ] ~~Forecast accuracy store + customer-specific learning~~ → Phase 4
- [ ] ~~Long-range + hybrid method registry~~ → Phase 5

---

## External learnings incorporated

| Source | Takeaway | SMPL action |
|--------|----------|-------------|
| Fluvo CFO webinar (2026-08-26) | Context pyramid; PGCI + Checks; pre-flight questions; plan-before-execute; audit every number | §1–§4 above; [AI_SKILL_PRACTICES](../AI_SKILL_PRACTICES.md) |
| Predictive Planning Intelligence (founder framework, 2026-08) | Plan→Test→Observe→Reassess→Act; PPI between finance engine and LLM; help Finance know if the business can deliver the plan | §5, §7; [SMPL_Predictive_Planning_Intelligence_Framework.md](./SMPL_Predictive_Planning_Intelligence_Framework.md) |
| Maxio partnership (Kevin/Nick, 2026-08) | Billing/rev-rec sub-ledger; CRM→Maxio→ERP stack; Maxio strong on actuals not FP&A forecast | §3 Maxio pattern; [INTEGRATIONS_SETUP](../INTEGRATIONS_SETUP.md) |
| Prior stack notes (Rillet, Intacct) | Gated ERP APIs — outreach parallel to wave 1; same tie-out rules once loaded | [INTEGRATIONS_SETUP](../INTEGRATIONS_SETUP.md) wave 2 |

*No Datadog finance webinar notes in repo — only operational monitoring mention in GO_LIVE_GL6.*
