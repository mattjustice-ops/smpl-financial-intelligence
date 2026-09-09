# SMPL.ai Budget Methodology

> **Purpose:** How an annual operating Budget is built, locked, tested and observed in SMPL. This is the planning cycle that Predictive Planning Intelligence tests against.
> **Audience:** FP&A leads, RevOps, Accounting, and customer-facing teams explaining the planning cycle. Not marketing copy.
> **Status labels:** **Shipped** = code in product · **Partial** = real path, incomplete UX · **Missing** = not built
> **Related:** [SMPL_Predictive_Planning_Intelligence_Framework.md](./SMPL_Predictive_Planning_Intelligence_Framework.md) · [Budget_Engine_Spec.md](./Budget_Engine_Spec.md) · [Forecasting_Assumptions.md](../Forecasting_Assumptions.md) · [Reporting_Logic.md](../Reporting_Logic.md)

**Last updated:** 2026-09-08 — first formalization. The Budget Engine shipped 09-04 → 09-07 before this document existed; content below is written from the shipped implementation, not from intent.

---

## 0. The one-paragraph version

A Budget is a **plan**, not an actual. It is built from an explicit driver set in a fixed dependency order (pipeline → ARR → deferred revenue → cash → statements → validate), saved as a **draft** version, tested for feasibility, and then **promoted to final** — at which point it becomes immutable and the prior final is superseded. Actuals never flow into the Budget model; they arrive alongside it for variance. Billing systems such as Maxio supply the actuals the Budget is measured against — they do not supply the Budget.

---

## 1. Planning calendar

| Window | Activity | Output |
|--------|----------|--------|
| Annual build | Driver set agreed; Budget constructed for the full fiscal year by month | `draft` Budget version |
| Pre-approval | Feasibility and stress testing; What Has to Be True reviewed | Assessment (see §9) |
| Approval | Promote to `final`; Jan opening balances locked to prior-December | `final` Budget version |
| Monthly | Actual close lands; Budget vs Actual vs Forecast variance | Variance pack |
| Monthly | Forecast overlay re-cut against the unchanged Budget baseline | Forecast version |
| Mid-year | Optional reforecast — a **Forecast** exercise, never a Budget edit | Forecast version |

**Combined cutover rule.** The Combined scenario reads Actual for closed periods and the active plan for open periods. The cutover is the last closed period, not a manual choice. A Budget is never partially overwritten by Actuals.

**Why the Budget does not get edited mid-year.** If the baseline moves, variance loses meaning and the board cannot tell whether performance or the yardstick changed. Mid-year revision belongs in the Forecast.

---

## 2. Owners

| Role | Owns | Does not own |
|------|------|--------------|
| **FP&A** | The Budget model, driver set, version promotion | Pipeline inputs, close |
| **RevOps** | Pipeline, coverage, win rates, quota and ramp assumptions | Statement build |
| **Accounting** | Actual close, GL mapping, opening balances | Plan drivers |
| **Admin / Owner (system role)** | Only roles permitted to save or promote a Budget version — **Shipped**, enforced in `budget_version_service.py` | — |
| **Finance judgment** | Accepting the plan and shipping it to the board | Being replaced by a model verdict |

---

## 3. Driver set for Budget

A subset of the forecast driver catalog. Budget-specific because they are annual commitments rather than rolling estimates.

| Group | Drivers |
|-------|---------|
| Growth | YoY ending-ARR growth %, net new by month, component mix, pipeline coverage multiple |
| Retention | Churn mix, contraction mix, GRR / NRR floors |
| GTM | Blended CPL, channel mix and weights, MQL targets, program spend, marketing-to-S&M ratio |
| Capacity | AE and CS headcount, quota, ramp, existing bench cover %, hiring plan by month |
| Cost | Departmental opex, EBITDA target |
| Cash | DSO / DPO, minimum cash floor (December and intra-year) |

**Rule:** a driver either belongs to the deterministic engine or it does not exist. There is no informal spreadsheet override that the engine cannot reproduce.

---

## 4. Build sequence

The dependency order is not a preference; downstream steps read upstream outputs.

```
1. Pipeline / GTM funnel      MQLs, coverage, program spend
2. ARR schedule               BOP + net new − churn − contraction → EOP by month
3. Bookings / capacity        AE need vs plan headcount; CS coverage
4. Deferred revenue & revenue Recognition from the ARR schedule
5. Headcount & opex           Jan locked to prior December; hiring by month
6. Statements                 Income statement → cash flow → balance sheet
7. Validate                   Tie-outs and identities (§8)
```

**Jan headcount lock.** January opening headcount must equal the prior-December forecast lock. A Budget that opens on a different number is restating history, and the `jan_hc` constraint fails hard on it.

---

## 5. Version states

**Shipped** — `budget_version_service.py`. Note this differs from earlier planning language that described Working → Submitted → Approved. The implemented lifecycle has three states and no separate submission step:

| State | Meaning | Rules |
|-------|---------|-------|
| `draft` | Under construction | Editable. Multiple drafts may coexist |
| `final` | Approved operating plan | **Immutable** — editing returns `409 Cannot edit a final budget version`. Promotion requires table rows to exist |
| `superseded` | A prior final, replaced | Set automatically when a new version is promoted; retained for history |

**Gap — Partial.** There is no explicit `submitted` state, so "sent for approval but not yet approved" is not representable in the data model. Teams currently signal it out of band. Add the state if the review step needs an audit trail.

---

## 6. Roll-forward at year start

Prior-year Actual ending balances become Budget beginning balances where the line is a balance rather than a flow: cash, balance-sheet accounts, ARR beginning-of-period, and headcount. Flow items (net new, revenue, spend) start from the plan, not from prior Actual.

Beginning ARR is a **lock**, not a driver. The `arr_bridge` constraint enforces `BOP + FY net new = December EOP`, so a changed opening balance cannot be absorbed silently.

---

## 7. Promote and lock

**Shipped.** Promotion is a governed transition, not a save:

1. Caller must hold `admin` or `owner` on the organization.
2. The version must carry table rows — an empty version cannot be promoted.
3. Any existing `final` version is marked `superseded`.
4. Budget tables load into the warehouse: `budget_mrr_waterfall`, `budget_income_statement`, `budget_cash_flow_statement`, `budget_balance_sheet`, `budget_bookings_summary`.
5. `status` becomes `final` and `promoted_at` is stamped.

**Gap — Partial.** Feasibility is **not** currently a hard gate on promotion. A plan with failing constraints can be promoted. Validation tie-outs gate export; plan feasibility does not gate approval. Whether it should is a product decision — see §9.

---

## 8. Validation vs feasibility

Two different questions, deliberately separate. Conflating them is the most common way trust breaks.

| | Validation | Feasibility |
|---|---|---|
| Question | Is the plan arithmetically correct? | Can the business deliver the plan? |
| Example | Does the ARR bridge tie to `$1`? | Is pipeline coverage thick enough to produce the required MQLs? |
| On failure | Fail closed — exports blocked | Warn — a business judgment, surfaced not blocked |
| Tolerance | `$1` | Policy thresholds |

**A PPI warn is not a validation pass, and a validation pass is not a feasible plan.**

---

## 9. Testing the plan (Plan Assurance)

**Shipped 09-04 → 09-07.** Once a Budget exists, it is tested against stated constraints rather than reviewed by eye:

- **Outlier review** — plan shape vs prior year: YoY step changes, H1/H2 tilt flips, cross-metric inversions, efficiency drift.
- **Feasibility** — 15 constraints across ARR path and bridge, GRR floor, December and intra-year cash floor, NB and CS coverage, bench cover, pipeline coverage, GTM MQL / spend / mix identities, January headcount lock, EBITDA, and the S&M tie. Each returns pass, warn, fail or advisory. **A constraint whose inputs are missing returns `skipped`, never a pass.**
- **What Has to Be True** — the failed and warned constraints restated as explicit conditions: what must close, what must be confirmed, and what holds today but breaks under stress.
- **Scenario stress** — named deterministic lever shocks (growth −3/−5pp, CPL +15/30%, attrition +2/5pp, churn mix ×1.4, combination and liquidity cases) recording Δ December ARR, Δ December cash and Δ FY EBITDA with break / watch / hold outcomes.
- **Monte Carlo** — 1,000 annual lever draws re-run through the same formula graph, reporting breach frequency and sensitivity.

**Naming discipline.** Monte Carlo output is **stress frequency under stated priors** — the chance a constraint breaks given the stated lever noise. It is **not** a calibrated Probability of Attainment. Do not relabel it.

**Layer discipline.** The deterministic engine owns every dollar. Plan Assurance tests the plan against the constraint registry. The LLM narrates structured findings and never computes or edits a number.

**Constraint governance.** Thresholds live in the registry at `backend/app/services/predictive_planning/constraints.py` and can be overridden per organization and per plan version. Precedence, highest first: version override, tenant override, packet value, registry default. Changing a default is a product decision.

**Gap — Partial.** Feasibility currently runs against the plan held in the Budget Engine, not against a promoted version id, and assessments are not persisted. Until that closes, an assessment is a live read rather than a citable artifact.

---

## 10. Monthly observe cadence

| Step | Comparison | Audience |
|------|-----------|----------|
| Close completes | Actual for the period | Accounting → FP&A |
| Variance | Actual vs Budget | FP&A |
| Re-cut | Forecast vs Budget baseline | FP&A → leadership |
| Material variance | Explained by driver, not by line | Board pack |

Variance is explained at the **driver** level. "Revenue missed by $400K" is not an explanation; "MQL volume held but win rate fell 4pp, so net new landed short" is.

---

## 11. AI role

- **May** summarize plan shape, narrate feasibility and stress findings, and propose driver diffs for review.
- **May not** compute or edit a Budget figure, promote a version, or write a `final` Budget.
- Every narrated number must exist in the structured payload it was given; claim-verify applies to Budget commentary exactly as it does to board commentary.

---

## 12. Maxio and billing actuals

Maxio is the source of **billing actuals** — the ARR and revenue reality the Budget is measured against. It is not a source of Budget. The distinction to keep explicit with customers:

- Budget bookings are plan and CRM driven. When opportunity files are loaded they populate `budget_opportunity_movements`, which is still a **plan** table.
- Actual ARR reflects billing once loaded.
- Variance is therefore Budget (plan) vs Actual (billing) — never plan vs plan.

**Do not claim** a live native Maxio connector. Data arrives by loaded files today.

---

## 13. Drilldown

**Partial.** The shipped pattern is the `/app` Executive Flow pipeline waterfall: click a cell → `GET /api/v1/waterfalls/pipeline/drilldown` → opportunity rows from `{actual|budget|forecast}_opportunity_movements`. Beginning and ending balances correctly refuse drill-down.

Extending this to every Budget cell is open work. GL-level lines resolve through `budget_gl_detail` and the statement tables.

---

## 14. Known gaps

Tracked honestly so this document does not drift the way the PPI framework did.

| Gap | Status |
|-----|--------|
| No `submitted` version state — approval step is not auditable | Partial |
| Feasibility is not a gate on promotion | Open product decision |
| Assessments not persisted or keyed to a promoted version | Missing |
| Constraint thresholds duplicated between Budget Engine JS and the Python registry | Missing — single source not yet established |
| Budget vs Actual operating cadence not yet a customer-facing guide | Missing |
| Drilldown coverage uneven outside the pipeline pattern | Partial |
