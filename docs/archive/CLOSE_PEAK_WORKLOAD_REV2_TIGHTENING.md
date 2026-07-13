# Close Peak Workload — Rev 2 Tightening Recommendations

**Status:** Supplement to `Close_Peak_Workload_Alignment_Brief_Rev2.md`  
**Purpose:** Close remaining gaps before the team locks backlog order and go-live cut lines  
**Audience:** Engineering, product, ops — same group reviewing Rev 2

Rev 2 is in good shape. This doc captures five items that should be decided or written into the brief before we treat it as final.

---

## 1. Minimum ship set for first paid close

**Gap:** Rev 2 reorders the backlog well but does not say what must ship before the **first paying customer’s close** vs what can wait until **cohort B (~15 orgs)**.

Without an explicit cut line, lower-priority items (e.g. separate ingest/export pools at #4) can block or delay go-live by accident.

### Proposed cut line (draft — team confirm)

| Tier | Ship before first paid close | Rationale |
|------|------------------------------|-----------|
| **Must ship** | Durable export jobs (survive Railway restart) | No silent job loss during close week |
| **Must ship** | Per-org concurrency: max 1 heavy Prompt 5 per org | Stops regenerate loops and org self-starvation |
| **Must ship** | As-of transparency on any context path we serve (frozen or live) | Trust during close; aligns with Rev 2 §4B |
| **Must ship** | Basic queue visibility for ops (depth, wait time, failed jobs) | First close is a rehearsal; we need signal |
| **Should ship** | Freeze blob v1: manual or on-validation-pass trigger; COMPLETE-only rule | Biggest latency/cost win for Copilot + Prompt 5 |
| **Can wait (cohort B)** | Full automated pre-close cron + night-before pre-warm | Valuable; not blocking first close if manual freeze works |
| **Can wait (cohort B)** | Separate ingest vs export worker pools | Accepted near-term risk per Rev 2 §2 — fix on trigger |
| **Can wait (cohort B)** | Prompt 5 regenerate caps (product UI + enforcement) | Soft limits / ops policy OK for first close |
| **Can wait (cohort B)** | Close-week runbook polish, deploy-freeze policy, full alert suite | Minimum: someone on-call + queue/Claude alerts |

### Team decision needed

- [ ] Agree or revise the **Must ship** list above
- [ ] Name the **first paid close date / cohort** this cut line applies to
- [ ] Confirm nothing in **Can wait** is a blocker for a specific signed customer

---

## 2. Shared ingest/export pool — measurable trigger (not vibes)

**Gap:** Rev 2 correctly labels shared worker pools as an **accepted near-term risk** with trigger “first observed instance of ingest delaying another org’s export.” That’s directionally right but too vague for close week.

### Proposed trigger (draft)

Treat separate pools as **required for cohort B** (or earlier) when **any** of the following is true during close window:

| Signal | Threshold (draft) |
|--------|---------------------|
| Export queue wait P95 | > 10 min **and** correlated with active ingest job from a **different** org |
| Export job start delay | > 5 min from `queued` → `running` while ingest worker utilization > 80% |
| Customer-visible | Support or ops log: “deck stuck because upload still processing” |
| Repeat | Same pattern **2+ times** in one close week |

### Ops note

Log **org_id + job kind** (ingest vs export) on shared workers so we can prove correlation in one close week, not debate it in Slack at 9am.

### Team decision needed

- [ ] Agree thresholds or substitute concrete numbers
- [ ] Assign who reviews the signal during first close week (owner in §5)

---

## 3. Late ingest after a COMPLETE freeze blob

**Gap:** Rev 2 defines COMPLETE-only blobs and as-of display. It does not say what happens when **new data lands after** a blob was frozen (e.g. T+2 CSV upload after night-before freeze).

This is the main close-week footgun for “why doesn’t my deck match what I just uploaded?”

### Proposed policy (draft)

| Event | System behavior | User-facing |
|-------|-----------------|-------------|
| New ingest **starts** for `(org, period)` | Mark existing blob `STALE` (or drop COMPLETE flag); do **not** serve partial rebuild | “Close context updating — last complete view: [as-of timestamp]” |
| Ingest **completes** + validation **passes** | Queue async freeze rebuild; until COMPLETE, serve **last COMPLETE** blob only (labeled stale) or block Prompt 5 if no prior COMPLETE | Same as-of label; optional “Refresh close context” CTA |
| Ingest **fails** validation | Blob stays prior COMPLETE; validation errors surfaced | Fail-closed on *new* freeze; old blob still labeled |
| User runs Prompt 5 while blob is STALE | Allow only if **last COMPLETE** exists and UI shows stale as-of; optional hard block until rebuild COMPLETE (product choice) | Deck header/footer: “Data as of [timestamp]” |

**Principle:** Never serve a partially-built blob. Stale-and-labeled is OK; silent freshness is not.

### Team decision needed

- [ ] Confirm **STALE** vs **drop COMPLETE** naming
- [ ] Product: **allow deck on stale blob** vs **block until rebuild COMPLETE**
- [ ] Who triggers manual re-freeze before first automated cron exists

---

## 4. Secondary mid-month peak — keep it subordinate

**Gap:** Rev 2 adds a **secondary peak** (board / forecast review). Good — but it should not dilute the primary ~4-day close design.

### Recommended one-liner for Rev 2 §1

> **Secondary peak:** Mid-month board/forecast activity is real but lower intensity. We size it as **headroom on close-week capacity**, not a second architecture or separate freeze model.

### Implication

- Same durable queue, same blob pattern, same fairness rules
- No separate “mid-month SLA table” unless metrics prove we need one after first season

### Team decision needed

- [ ] Agree subordinate framing or document a second peak that needs different treatment

---

## 5. Owners (draft assignments)

**Gap:** Rev 2 §8 “Decide” still has TBD owners. Even draft names make the brief actionable.

| Area | Owns | First deliverable |
|------|------|-------------------|
| **Queue / infra** | TBD | Durable jobs + worker config + correlation logging (§2) |
| **Freeze blob / product** | TBD | COMPLETE-only spec, as-of UI, late-ingest policy (§3) |
| **Close-week ops** | TBD | Alerts, on-call, deploy-freeze, first-close retrospective |
| **Alignment doc** | TBD | Merge decisions from this supplement into Rev 2 → Rev 3 |

### Team decision needed

- [ ] Fill TBD with names or roles
- [ ] Single DRI for “first paid close” readiness checklist

---

## Suggested merge into Rev 3

When the team agrees, add to the main brief:

1. New subsection **§6a — Minimum ship set (first paid close)** — table from §1 above  
2. Expand **§2 risk note** — measurable trigger from §2 above  
3. New bullet under **§4B** — late-ingest invalidation policy from §3 above  
4. One sentence in **§1** — secondary peak subordination from §4 above  
5. Fill **§8 Decide** — owners from §5 above  

---

## One-paragraph summary (for Slack / email)

> Rev 2 is ready to align on. Before we lock the backlog, we need five tightenings: (1) explicit **must-ship vs cohort-B** cut for first paid close, (2) **measurable trigger** for splitting ingest/export pools, (3) **late-ingest policy** after a COMPLETE freeze blob, (4) keep **mid-month peak** as headroom not a second architecture, and (5) **named owners**. This supplement drafts positions for each — please confirm or edit so we can publish Rev 3.

---

## Revision log

| Date | Change |
|------|--------|
| 2026-07-12 | Initial supplement from Rev 2 review |
