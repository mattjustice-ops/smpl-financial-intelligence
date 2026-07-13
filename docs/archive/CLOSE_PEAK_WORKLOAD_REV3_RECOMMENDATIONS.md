# Close Peak Workload Rev 3 — Final Lock Recommendations

**Status:** Supplement for team review  
**Applies to:** `Close_Peak_Workload_Alignment_Brief_Rev3.md`  
**Purpose:** Resolve the last open items before locking backlog order and first paid close cut line

Rev 3 is in good shape and ready to circulate for lock. This document captures the remaining decisions and small clarifications needed so the brief can be treated as final without a full Rev 4 rewrite.

---

## Overall assessment

Rev 3 successfully merges:

- Rev 2 core design (durable queues, freeze blobs, ingest as peak-critical)
- Rev 2 Tightening Supplement (min ship set, measurable split trigger, STALE policy, owners)
- Principal Architect Review (four workload classes, Close Session, Close Ready, queue isolation, cost monitoring, §9 long-term direction)

The scope boundary with the target Financial Intelligence Engine is maintained correctly. §9 stays informational and should not expand near-term build scope.

**Verdict:** Circulate Rev 3 for lock. Resolve the five items below in §8, then lock backlog order.

---

## 1. Default the stale-blob Prompt 5 decision

**Gap:** §4B and §8 still present two equal options: allow Prompt 5 on a stale labeled blob vs hard-block until rebuild completes.

**Recommendation — adopt as default for first paid close:**

| Scenario | Behavior |
|----------|----------|
| Last `COMPLETE` blob exists; new ingest made blob `STALE` | **Allow** Prompt 5; deck and UI show **"Data as of [timestamp]"** prominently |
| No prior `COMPLETE` blob exists | **Hard-block** Prompt 5 until first freeze reaches `COMPLETE` |
| User explicitly requests live refresh | Rate-limited live rebuild path; usage-metered |

**Rationale:** Close week cannot stall on a late CSV upload when a usable prior snapshot exists. Hard-block only when there is nothing trustworthy to serve.

**Team decision needed:**

- [ ] Confirm default above, or choose hard-block-until-rebuild for all stale cases
- [ ] Confirm stale CTA copy: "Close context updating — last complete view: [as-of]"

---

## 2. Clarify Close Ready vs Must Ship for first paid close

**Gap:** §4F says only `Close Ready` organizations generate executive reports, but §6a Must Ship does not include Close Ready or freeze blob v1. That can accidentally block go-live.

**Recommendation — define two phases explicitly:**

### Phase 1 — First paid close (Must Ship path)

**Close Ready (operational definition):**

```
validation passed
+ freeze blob COMPLETE (manual or on-validation-pass trigger)
+ as-of transparency on all served context
```

Observation / Calculations / Evidence / Narratives criteria from §4F are **not required** until Class 2 is broken out as its own stage.

### Phase 2 — Cohort B and beyond

Full Close Ready gate per §4F once Financial Intelligence steps exist as isolated Class 2 work.

**Add one sentence to Rev 3 §4F:**

> For first paid close, Close Ready operationally equals validation passed + freeze blob COMPLETE; fuller criteria activate when Class 2 work is broken out.

**Team decision needed:**

- [ ] Confirm Phase 1 operational definition
- [ ] Confirm freeze blob v1 stays **Should Ship** (not Must Ship) — or elevate to Must Ship if a signed customer requires it

---

## 3. Clarify queue topology: target vs day-one

**Gap:** §4G describes four isolated queues as the structural fix; §6a says ingest/export split can wait unless §2's measurable trigger fires. Readers may think Rev 3 requires four queues on day one.

**Recommendation — add explicit staging language:**

| Stage | Topology |
|-------|----------|
| **First paid close** | Shared worker pool acceptable with `org_id` + job kind correlation logging (§2) |
| **Target topology (§4G)** | Queue A (Ingestion), Queue B (FI — reserved), Queue C (Prompt 5), Queue D (Copilot) |
| **Pull-forward trigger** | §2 measurable thresholds — split A/C early if correlation signals fire during close week |

**One-liner for Rev 3:**

> §4G is the target topology; first paid close may use a shared pool with correlation logging until the measurable trigger or Cohort B schedule requires isolation.

**Team decision needed:**

- [ ] Confirm shared pool is acceptable for first paid close
- [ ] Confirm who reviews §2 trigger signals during first close week

---

## 4. Fill owners and first paid close date

**Gap:** Rev 3 status is "Proposed for lock" but Owner and single DRI are still TBD. Without names and a date, the Must Ship cut line is not actionable.

**Recommendation — fill before lock meeting:**

| Area | Owns (fill name/role) | First deliverable |
|------|----------------------|-------------------|
| Queue / infra | _____________ | Durable jobs + worker config + correlation logging |
| Freeze blob / product | _____________ | COMPLETE-only spec, as-of UI, STALE policy |
| Close Session / Close Ready | _____________ | Data model + Phase 1 operational gate |
| Close-week ops | _____________ | Alerts, on-call, deploy-freeze, first-close retro |
| First paid close DRI | _____________ | Readiness checklist against §6a Must Ship |

**Also name:**

- First paid close date / cohort this cut line applies to: _____________
- Confirm no signed customer is blocked by anything in §6a "Can wait": _____________

**Team decision needed:**

- [ ] All TBD slots filled
- [ ] Single DRI named for first paid close readiness

---

## 5. Keep data-scale tiers from expanding Must Ship

**Gap:** §1 enterprise data-scale tiers (50–100 GB early, 500 GB+ enterprise) are good for planning but could be read as requiring Cohort C infrastructure before first paid close.

**Recommendation:**

- Use data-scale tiers for **capacity planning and cohort certification**, not as an automatic Must Ship scope expander
- **Cohort A (~5 orgs)** can certify on: durable jobs, per-org lock, as-of transparency, basic queue visibility — even while planning horizon includes large enterprise customers
- Apply **data-volume override** (§5) when a signed customer’s actual volume exceeds the cohort’s proven capacity — advance certification requirements for that customer, not necessarily for all Must Ship items globally

**Team decision needed:**

- [ ] Confirm Cohort A Must Ship list is sufficient for first paid close regardless of planning-tier assumptions
- [ ] Flag any signed customer whose data volume forces early pull-forward of Cohort B items

---

## 6. Items already resolved in Rev 3 (no further action)

These were open in Rev 2 / the Tightening Supplement and are now adequately addressed in Rev 3:

| Item | Where resolved |
|------|----------------|
| Minimum ship set | §6a |
| Measurable ingest/export split trigger | §2 Class 1 |
| Late-ingest / STALE policy | §4B |
| Mid-month peak subordination | §1 |
| Four workload classes | §2 |
| Close Session lineage | §4E |
| Cost-per-unit monitoring | §5 |
| Long-term FIE alignment without scope creep | §0, §9 |
| Prompt-cache customer-data guardrail | §4D |

---

## 7. Suggested Rev 3.1 micro-edits (optional)

If the team agrees with recommendations §1–3 above, merge these three sentences into Rev 3 without a full rewrite:

1. **§4B (after STALE table):** Default for first paid close: allow Prompt 5 on stale labeled blob if last COMPLETE exists; hard-block only if no COMPLETE exists.

2. **§4F (after Close Ready definition):** For first paid close, Close Ready operationally equals validation passed + freeze blob COMPLETE.

3. **§4G (after queue diagram):** §4G is target topology; first paid close may use shared pool with correlation logging until §2 trigger or Cohort B.

---

## 8. Lock checklist (use in review meeting)

- [ ] Must Ship list (§6a) confirmed
- [ ] Stale Prompt 5 default decided (§1 above)
- [ ] Close Ready Phase 1 definition confirmed (§2 above)
- [ ] Queue topology staging confirmed (§3 above)
- [ ] Owners + first paid close DRI + date filled (§4 above)
- [ ] No signed customer blocked by "Can wait" items
- [ ] §2 measurable thresholds confirmed or substituted
- [ ] Backlog order (§6b) locked

---

## One-paragraph summary (for Slack / email)

> Rev 3 is ready to lock. Before we finalize backlog order, we need five small decisions: (1) default **allow labeled stale Prompt 5** when a last COMPLETE blob exists, (2) define **Close Ready for first paid close** as validation passed + freeze COMPLETE only, (3) confirm **§4G is target topology** — shared pool OK on day one with correlation logging, (4) **name owners + first paid close DRI and date**, and (5) keep **data-scale tiers** as planning/certification inputs, not automatic Must Ship expansion. Full detail in the Rev 3 Recommendations supplement.

---

## Revision log

| Date | Change |
|------|--------|
| 2026-07-12 | Compiled from Rev 3 review — final lock recommendations |
