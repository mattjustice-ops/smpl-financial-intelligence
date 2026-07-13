# Close Peak Workload — Alignment Brief (Rev 4 — Lock Candidate)

**Canonical location:** `docs/CLOSE_PEAK_WORKLOAD.md`  
**Supersedes:** Rev 1–3 and supplements — see [archive/](./archive/) for history  
**Status:** Proposed for lock — supersedes Rev 3 and incorporates the Rev 3 Final Lock Recommendations + Principal Architect Review  
**Owner:** TBD  
**Goal:** Resolve every remaining open decision so this brief can be locked and backlog order finalized.

**Related docs:** [Close_Process.md](./Close_Process.md) (customer close workflow) · [REPORTING_EXPORT.md](../backend/docs/REPORTING_EXPORT.md) (export implementation today)

---

## 0. Scope note

This document hardens the **current production system** (Prompt 5, Copilot, Railway, Neon) — it does not describe or replace the target Financial Intelligence Engine (FIE) architecture being designed in parallel. This separation has been confirmed correct across three rounds of review and is not revisited further in this revision.

The core idea here — a coherent, point-in-time, precomputed view of "the business as of close," served many times instead of rebuilt live — is the same shape of answer the target architecture reaches independently via the Observation Engine's Snapshots. This document is a rehearsal of that model, not a replacement for it.

---

## Status: items resolved through Rev 3 (no further action)

| Item | Where resolved |
|---|---|
| Minimum ship set | §6a |
| Measurable ingest/export split trigger | §2, Class 1 |
| Late-ingest / STALE policy | §4B |
| Mid-month peak subordination | §1 |
| Four workload classes | §2 |
| Close Session lineage | §4E |
| Cost-per-unit monitoring | §5 |
| Long-term FIE alignment without scope creep | §0, §9 |
| Prompt-cache customer-data guardrail | §4D |

Rev 4 resolves the remaining decisions the team flagged against Rev 3 — defaults, phasing, topology staging, and customer-facing visibility — so nothing here should require a Rev 5 rewrite, only the human decisions (names, date) still marked TBD.

---

## 1. Problem statement

Our customers are B2B SaaS finance teams. They close the books on roughly the same calendar — typically the first few business days after month-end.

That means Prompt 5, Copilot, and ingestion will be hit hard on the same ~4 days of the month, not spread evenly. We design for peak close concurrency, not average daily traffic.

**Planning assumptions (working):**

| Assumption | Working value | Notes |
|---|---|---|
| Busy window | ~4 days / month | Days customers need decks + Q&A most |
| Secondary peak | Mid-month, lower intensity | Sized as headroom on close-week capacity, not a second architecture |
| Near-term cohort | 10 → 20–40 orgs | First paid customers through early scale |
| Data volume | See tiered scale below | Planning input, not an automatic Must Ship expander — see §5's clarification |
| Peak shape | Many orgs, same morning | Not one org with huge traffic |

**Data scale tiers (planning input):**

```
Prototype            ~1 GB
     ↓
Early Customer        50–100 GB
     ↓
Enterprise             500 GB+
     ↓
Long-Term              Multi-terabyte historical datasets
```

**Clarification (new):** these tiers inform capacity planning and cohort certification — they do not, on their own, expand what's required to ship first paid close. Cohort A can certify on the §6a Must Ship list regardless of the long-range planning horizon. The data-volume override (§5) applies per signed customer, when a specific customer's actual volume exceeds proven capacity — it advances requirements for that customer's cohort tier, not the global Must Ship bar.

---

## 2. Workload profile — four independent workload classes

### Class 1 — Ingestion

| Attribute | Today | Close-peak implication |
|---|---|---|
| Includes | CSV uploads, connector sync, validation, canonical population | Same 4-day window as everything else |
| Failure mode | A backed-up ingest queue silently delays every downstream deck and Copilot session | Bottleneck relocates upstream if not isolated |

**Measurable trigger for splitting ingest/export pools:**

| Signal | Threshold (draft) |
|---|---|
| Export queue wait P95 | > 10 min, correlated with an active ingest job from a different org |
| Export job start delay | > 5 min from queued → running, while ingest worker utilization > 80% |
| Customer-visible | Support/ops log: "deck stuck because upload still processing" |
| Repeat | Same pattern 2+ times in one close week |

Log `org_id` + job kind (ingest vs. export) on shared workers now, so correlation can be proven, not debated.

### Class 2 — Financial Intelligence

Observation generation, methodology execution, calculations, evidence assembly — currently embedded inside Prompt 5's generation step. Long-term direction in §9; no scope change to this document today.

### Class 3 — Executive Experience

Prompt 5, Copilot, PPTX/XLSX generation, downloads. Today's job model (`ThreadPoolExecutor(max_workers=2)`, in-memory) is the primary near-term risk — see §4A.

### Class 4 — Platform Infrastructure

Queue, database, storage, cache, Redis, Claude — the shared substrate underneath the three classes above.

---

## 3. Design principle

**Precompute before the crush; serve during the crush.**

```
Pre-close (T−3 … T0)          Close peak (T+1 … T+4)         Post-close (T+5+)
─────────────────────          ──────────────────────         ────────────────
Ingest + validate              Serve frozen context packs     Light refresh
Build (org, period) blobs      Fair queue for Prompt 5        Archive / prep next month
Nightly / on-ready freeze      Cap Copilot live rebuilds      Cost + capacity review
```

**Executive Experience Philosophy:** the executive experience should primarily consume precomputed Financial Intelligence rather than trigger live analytical computation during month-end. This is the link between today's freeze-blob work and the long-term direction in §9.

---

## 4. Proposed job & context model

### A. Durable export jobs (Prompt 5 / packages)

| Rule | Proposal |
|---|---|
| Persistence | Job state in DB (or Redis + DB), not process RAM only |
| Global workers | Sized for peak (e.g. 6–12), not 2 |
| Per-org concurrency | Max 1 heavy Prompt 5 per org at a time |
| Fairness | Avoid pure FIFO stampede; optional priority for first close export vs Nth regenerate |
| UX | Async job + ETA — never block HTTP until PPTX finishes; see Customer Progress Messaging, below |
| Caps | Soft/hard limit: N Prompt 5 runs per org per close period |

**Customer Progress Messaging (new):** customers tolerate waiting significantly better when they can see work completed, not just a static "Queued" state. Communicate progress as discrete, checked-off stages, not a spinner:

```
Preparing Executive Package

✓ Validation Complete
✓ Financial Intelligence Ready
✓ Narrative Ready
  Building PowerPoint...

Estimated Time Remaining: 7 minutes
```

This reuses states already tracked internally (§4F, §4E) — it is a presentation of existing signal, not a new system to build.

### B. Materialized close context ("freeze blob")

- **Sectioned context pack:** ARR / CFS / GTM / pipeline summary / KPIs / validation status
- **Refresh triggers:** ingest complete, validation pass, scheduled pre-close cron, explicit "freeze for close"
- **Completeness state:** a blob is either `COMPLETE` or it does not exist yet — no partial state, ever.
- **As-of transparency:** every response served from a frozen blob surfaces its timestamp.
- **Late-ingest / staleness policy:**

  | Event | System behavior | User-facing |
  |---|---|---|
  | New ingest starts for `(org, period)` | Mark existing blob `STALE`; never serve a partial rebuild | "Close context updating — last complete view: [as-of timestamp]" |
  | Ingest completes + validation passes | Queue async freeze rebuild; serve last `COMPLETE` blob (labeled stale) until the new one lands | Same as-of label; optional "Refresh close context" CTA |
  | Ingest fails validation | Blob stays at prior `COMPLETE`; validation errors surfaced | Fail-closed on new freeze; old blob still labeled correctly |

- **Stale-blob Prompt 5 default (resolved — new):**

  | Scenario | Behavior |
  |---|---|
  | Last `COMPLETE` blob exists; new ingest made it `STALE` | **Allow** Prompt 5; deck and UI show "Data as of [timestamp]" prominently |
  | No prior `COMPLETE` blob exists at all | **Hard-block** Prompt 5 until the first freeze reaches `COMPLETE` |
  | User explicitly requests live refresh | Rate-limited live rebuild path; usage-metered |

  **Rationale:** close week cannot stall on a late CSV upload when a usable prior snapshot exists. Hard-block is reserved for the one case where there is genuinely nothing trustworthy to serve.

- **Principle, unchanged:** never serve a partially-built blob. Stale-and-labeled is fine; silent freshness is not.

- **Consumers:** Copilot prefers the frozen pack; Prompt 5 uses the frozen pack plus structured metrics; regenerate reuses the pack rather than rebuilding warehouse bundles.

### C. Copilot under peak load

| Mode | When | Behavior |
|---|---|---|
| Frozen | Default in close window | Answer from freeze blob; fast first token; as-of timestamp shown |
| Live rebuild | Drilldowns / "refresh context" only | Explicit, rate-limited, usage-metered |
| Guardrails | Always | Per-org concurrency; Claude backoff on 429; no unbounded parallel blob rebuilds |

### D. Tenant fairness & Claude protection

- Per-org + global AI concurrency limits
- Prompt caching on stable system prompts only — never customer-specific data, across orgs or across periods for the same org
- Alert on queue depth, wait time, Claude 429s, Neon p95
- Deploy freeze during peak close days unless hotfix
- Optional: pre-warm freeze blobs night-before for orgs that finished ingest

### E. Close Session

An immutable record created once per organization per reporting cycle, referenced by everything produced during that close:

```
Organization → Close Session Created → Validation Complete → Calculations Complete
→ Narratives Complete → Freeze Blob Complete → Executive Review → Publish → Archive
```

Every Prompt 5 deck, Copilot response, export, and evidence reference generated during a close carries its Close Session ID — one object support can look up, one lineage anchor, no change required to §4A–D's job model. **Should Ship**, not Must Ship (§6a).

### F. Close Readiness ("Close Ready") gate — phased definition (resolved — new)

Only `Close Ready` organizations generate executive reports. Rev 3 defined the full gate; Rev 4 splits it into two phases so it can't accidentally block first paid close:

**Phase 1 — First paid close (Must Ship path):**

```
Close Ready (Phase 1) =  validation passed
                        + freeze blob COMPLETE (manual or on-validation-pass trigger)
                        + as-of transparency on all served context
```

Observation / Calculations / Evidence / Narratives criteria are **not required** until Class 2 (Financial Intelligence) is broken out as its own stage.

**Phase 2 — Cohort B and beyond:**

```
Close Ready (Phase 2) =  Validation Complete + Observation Complete + Calculations Complete
                        + Evidence Complete + Narratives Complete + Freeze Complete
```

The full gate from Rev 3 activates once Class 2 exists as isolated work — nothing here is discarded, it's sequenced.

### G. Queue isolation — target topology, staged (resolved — new)

§4G describes the **target** topology, not a day-one requirement:

| Stage | Topology |
|---|---|
| First paid close | Shared worker pool acceptable, with `org_id` + job kind correlation logging (§2, Class 1) |
| Target topology | Queue A (Ingestion) · Queue B (Financial Intelligence — reserved) · Queue C (Prompt 5) · Queue D (Copilot) |
| Pull-forward trigger | §2's measurable thresholds — split A/C early if correlation signals fire during a close week |

```
Queue A — Ingestion
Queue B — Financial Intelligence  (reserved; activates as Class 2 is broken out)
Queue C — Prompt 5
Queue D — Copilot
```

---

## 5. Capacity framing (how we talk about "ready")

Ask: **Can we handle N concurrent Prompt 5 jobs + M Copilot sessions for 4 days straight with wait time < X and zero silent job loss?**

**Cohort gates**

| Cohort | Orgs (guide) | Must prove before certifying |
|---|---|---|
| A | ~5 | Durable jobs; no silent loss; basic per-org lock |
| B | ~15 | Freeze blobs for Copilot + Prompt 5; queue wait P95 target; Claude caps |
| C | ~40 | Worker scale-out; stronger fairness; alerts + close-week runbook |

**Data-volume override:** applies per signed customer whose actual volume exceeds the cohort's proven capacity — advances certification requirements for that customer specifically, not the global Must Ship bar (§1's clarification).

**Capacity certification — beyond org count:**

- Maximum concurrent Prompt 5 throughput
- Maximum concurrent Copilot throughput
- Ingest throughput (Class 1)
- Financial Intelligence throughput (Class 2, once broken out)
- Queue durability
- Recovery after failure
- Operational Confidence maintained throughout the test window

**Cost monitoring:**

| Metric | Why it matters |
|---|---|
| Claude cost per organization | Baseline unit economics |
| Cost per Prompt 5 | Direct cost of the most expensive per-click action |
| Cost per Copilot session | Direct cost of interactive load |
| Cost per close cycle | The number that matters for a given org's margin |
| Cost per Financial Intelligence Object (once Class 2 exists) | Forward-looking, tracked from the start |

**Example SLA targets (first paid cohort — draft)**

| Metric | Draft target |
|---|---|
| Concurrent Prompt 5 workers | 4–8 durable workers |
| Per-org heavy export | 1 at a time |
| Queue wait P95 (close window) | < 15–20 minutes |
| Copilot latency (frozen blob) | < 5–10 s to first token |
| Job durability | Survive Railway restart |
| Claude | Caps + 429 backoff; no unbounded parallel |

---

## 6. Month-End Readiness Dashboard (new)

Rev 3 introduced many operational states independently — validation, calculations, narratives, freeze, queue, Operational Confidence, Close Ready. This section brings them into one view rather than leaving each as a separate thing someone has to check.

**One authoritative view per organization, per close period:**

- Close Session ID (§4E)
- Validation Status
- Calculation Status
- Narrative Status
- Freeze Blob Status (`COMPLETE` / `STALE`, §4B)
- Queue Status (§4G)
- Operational Confidence
- Close Ready (Phase 1 or Phase 2, §4F)
- Last Successful Refresh
- As-of Timestamp

**Audience (new — resolves who this is actually for):**

| Audience | Uses it for |
|---|---|
| Operations | Real-time close-week triage — is anything stuck, and where |
| Customer Success | Answering "why isn't my customer's deck ready yet" without paging engineering |
| Engineering | Diagnostics, correlation with §2's measurable thresholds |
| Support | First-line answer to a customer ticket, before escalation |

This introduces no new architecture — it organizes existing operational states (already tracked individually across §4B, §4E, §4F, §4G, §5) into one dashboard, designed for day-to-day decision-making, not engineering diagnostics alone.

### Close Readiness Visibility — customer-facing states (new)

Close Ready (§4F) is an internal gate. Customers should see their own progress in their own terms, not the internal state machine:

```
Preparing Close  →  Close Validation  →  Ready for Executive Review  →  Close Certified
```

This ladder is the customer-facing translation of the Month-End Readiness Dashboard above and the Customer Progress Messaging in §4A — a customer always understands *why* reporting is or isn't currently available, without needing to know what "Close Ready Phase 1" means internally.

---

## 7. What is explicitly out of scope (for this workload update)

- Changing Prompt 5 slide quality / layout rules (separate track)
- Full ERP close / GL posting (see [Close_Process.md](./Close_Process.md) — we are reporting + reconciliation)
- Customer-facing self-serve usage dashboards (nice-to-have after hard caps)
- Multi-region HA (not required for first cohorts)
- Reimplementing this concurrency model inside the target FIE architecture — §9 names the direction; it does not change this document's scope
- Breaking Class 2 (Financial Intelligence) out as its own isolated stage — named as a reserved seam (§2, §4F, §4G), not built in this revision
- **Detailed operational procedures (new):** incident response, customer communication scripts, escalation paths, and full close-week support processes belong in a future **Month-End Operations Runbook** — recognized here as a natural next document once real production experience exists, not built inside this brief

---

## 8. Team prompt — lock decisions

### Resolved this revision (confirm or override)

1. **Stale-blob Prompt 5 default:** allow on labeled `STALE` blob when a last `COMPLETE` exists; hard-block only when no `COMPLETE` blob exists at all (§4B).
2. **Close Ready Phase 1:** validation passed + freeze blob `COMPLETE` + as-of transparency, for first paid close; full gate activates at Cohort B / Class 2 (§4F).
3. **Queue topology:** shared pool with correlation logging is acceptable for first paid close; §4G is the target, not a day-one requirement (§4G).
4. **Data-scale tiers:** planning/certification input only; do not expand global Must Ship scope; apply per-customer via the data-volume override (§5).

### Still needs names / dates (fill before lock meeting)

| Area | Owns (fill name/role) | First deliverable |
|---|---|---|
| Queue / infra | _____________ | Durable jobs + worker config + correlation logging |
| Freeze blob / product | _____________ | `COMPLETE`-only spec, as-of UI, STALE policy |
| Close Session / Close Ready | _____________ | Data model + Phase 1 operational gate |
| Month-End Readiness Dashboard | _____________ | v1 view for Ops/CS/Support, per §6 |
| Close-week ops | _____________ | Alerts, on-call, deploy-freeze, first-close retro |
| **First paid close DRI** | _____________ | Readiness checklist against §6a Must Ship |

Also name:
- First paid close date / cohort this cut line applies to: _____________
- Confirm no signed customer is blocked by anything in §6a "Can wait": _____________

### Lock checklist (use in review meeting)

- [ ] Must Ship list (§6a) confirmed
- [ ] Stale Prompt 5 default confirmed (§4B)
- [ ] Close Ready Phase 1 definition confirmed (§4F)
- [ ] Queue topology staging confirmed (§4G)
- [ ] Owners + first paid close DRI + date filled (above)
- [ ] No signed customer blocked by "Can wait" items
- [ ] §2 measurable thresholds confirmed or substituted
- [ ] Backlog order (§6b) locked

---

## 6a. Minimum ship set for first paid close

| Tier | Item | Rationale |
|---|---|---|
| **Must ship** | Durable export jobs (survive Railway restart) | No silent job loss during close week |
| **Must ship** | Per-org concurrency: max 1 heavy Prompt 5 per org | Stops regenerate loops and org self-starvation |
| **Must ship** | As-of transparency on any context path served (frozen or live) | Trust during close; §4B |
| **Must ship** | Basic queue visibility for ops (depth, wait time, failed jobs) | First close is a rehearsal; we need signal |
| Should ship | Freeze blob v1: manual or on-validation-pass trigger; `COMPLETE`-only rule | Biggest latency/cost win; also Close Ready Phase 1 dependency (§4F) |
| Should ship | Close Session (§4E) | High support/lineage value; no dependency on other Must Ship items |
| Should ship | Month-End Readiness Dashboard v1 (§6) | Ops/CS/Support triage during first close week |
| Can wait (Cohort B) | Full automated pre-close cron + night-before pre-warm | Valuable; not blocking first close if manual freeze works |
| Can wait (Cohort B) | Separate ingest vs. export worker pools (§4G target topology) — unless §2's trigger fires first | Accepted near-term risk; fix on trigger, not on schedule |
| Can wait (Cohort B) | Prompt 5 regenerate caps (product UI + enforcement) | Soft limits / ops policy OK for first close |
| Can wait (Cohort B) | Close Ready Phase 2 (§4F), close-week runbook polish, full alert suite | Phase 1 gate + basic on-call is the minimum |

## 6b. Full workstream order

1. Durable export queue — replace in-memory `max_workers=2`
2. Per-org + global concurrency limits — Prompt 5 + Copilot
3. Month-end freeze / materialized context — completeness state, as-of display, late-ingest/STALE policy, stale-blob default (§4B)
4. Close Session (§4E)
5. Month-End Readiness Dashboard v1 (§6)
6. Customer Progress Messaging UI (§4A)
7. Queue isolation — triggered per §2's measurable thresholds if not already scheduled by Cohort B
8. Prompt 5 regenerate caps
9. Close-week ops — alerts + deploy freeze policy
10. Close Ready Phase 2 (§4F) — once Class 2 exists
11. Optional stagger — night-before blob build; white-glove export slots
12. Later: indexes / incremental ingest; partitioning / cold archive; Month-End Operations Runbook (§7)

---

## 9. Long-term architectural alignment (informational — no scope change)

This section does not change anything in §1–8. Prompt 5 is not the long-term computational bottleneck. As the platform matures, the Financial Intelligence pipeline itself becomes the workload that matters most:

```
ERP / CRM / Billing / HRIS → Canonical → Validation → Observation → Methodology
→ Calculation → Evidence → Narratives → Freeze → Prompt 5 / Copilot
```

Prompt 5 and Copilot ultimately become a presentation layer consuming precomputed Financial Intelligence, not a component driving live computation. Every reserved seam in this document — Class 2 (§2), Queue B reserved (§4G), Close Ready Phase 2 (§4F) — exists so this evolution happens by activating what's already named here, not by redesigning this document later.

---

## Final Review

**1. Are any operational responsibilities still misplaced?**
No. The Month-End Readiness Dashboard (§6) and Customer Progress Messaging (§4A) both explicitly reuse existing tracked states rather than introducing new ones — they are presentation, not new architecture. Detailed runbook content is explicitly deferred to a future Month-End Operations Runbook (§7), not absorbed into this brief.

**2. Does any content belong in a future Operations Runbook rather than this document?**
Yes, by design — §7 now names this explicitly: incident response, customer communication scripts, escalation paths, and close-week support processes. Nothing currently in this document should move there; it's a forward pointer, not a pending extraction.

**3. Does the document preserve deterministic execution while providing an excellent customer experience during peak close?**
Yes. The stale-blob default (§4B) and Close Ready phasing (§4F) both resolve ambiguity in favor of always-labeled, never-silent behavior — a customer can be served a stale answer, but never an unlabeled or partially-built one. Customer Progress Messaging and Close Readiness Visibility (§6) improve experience without changing what's actually computed or when.

**4. Is Rev 4 ready to freeze as the operational month-end workload strategy for the production platform?**
Yes, conditional on the human decisions still marked TBD in §8 (owners, first paid close date, DRI) — those are organizational facts this document cannot supply on its own. Every open design question raised across Rev 2 through the Rev 3 review is now resolved with an explicit default, phase, or staged topology. Recommend locking Rev 4 once §8's TBDs are filled in the review meeting.

---

## One-paragraph summary (for email / Slack)

Rev 4 closes every remaining open decision from the Rev 3 review: Prompt 5 defaults to serving a labeled stale blob when a last-complete snapshot exists (hard-block only if none exists at all), Close Ready is phased so a lightweight Phase 1 gate covers first paid close while the full gate waits for Class 2, queue isolation is confirmed as the target topology rather than a day-one requirement, and data-scale tiers are locked as planning inputs rather than automatic scope expanders. New this round: a Month-End Readiness Dashboard consolidating every operational state into one view for Ops/CS/Support, checklist-style customer progress messaging, and a customer-facing Close Readiness ladder distinct from the internal gate. What's left is not design — it's names, a date, and a DRI. Once §8 is filled in the lock meeting, this is ready to freeze.

---

## Revision log

| Date | Change |
|---|---|
| 2026-07-12 | Initial draft for team alignment |
| 2026-07-12 | Rev 2: scope note; ingest/validation elevated to peak-critical; freeze-blob completeness + as-of display; prompt-caching guardrail; data-volume cohort override |
| 2026-07-12 | Rev 3: four workload classes; Close Session; Close Ready gate; queue isolation; expanded capacity certification + cost monitoring; enterprise data-scale tiers; Executive Experience Philosophy; §9 long-term alignment |
| 2026-07-12 | Rev 4: stale-blob default resolved; Close Ready phased (Phase 1/2); queue topology staged (shared pool day-one, target topology later); data-scale tiers confirmed as planning-only; Month-End Readiness Dashboard + audience; Customer Progress Messaging; Close Readiness Visibility customer ladder; Operations Runbook forward pointer; lock checklist; Final Review Q&A |
| 2026-07-12 | Canonical copy committed to `docs/CLOSE_PEAK_WORKLOAD.md`; Rev 1–3 moved to `docs/archive/` |
