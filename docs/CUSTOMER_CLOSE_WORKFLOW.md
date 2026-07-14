# Customer Close Workflow — Product Specification

**Status:** Proposed for freeze (implementation-ready pending final DRI names)  
**Owner (DRI):** Product — *name TBD before freeze meeting*  
**Engineering DRI:** TBD  
**Date:** 2026-07-14  
**Baseline incorporated:** [CUSTOMER_CLOSE_DATA_READINESS.md](./CUSTOMER_CLOSE_DATA_READINESS.md) (alignment brief) · Product Design Review (Customer Close Workflow) · Review reconciliation vs Close Peak Rev 4  
**Related:** [Close_Process.md](./Close_Process.md) · [CLOSE_PEAK_WORKLOAD.md](./CLOSE_PEAK_WORKLOAD.md) (Rev 4) · ABS-012 · BIS-003 · BIS-004 · FIE-001 · FIE-003 · FIE-005 · BUILD-005 · BUILD-008  

**Purpose:** Define the **canonical customer journey for every reporting period** so engineering builds one coherent workflow—not isolated Lock / receipt / freeze features.

**Non-goals:** Redesign ABS / BIS / FIE / BUILD. Introduce no new platform services. This is a **product workflow refinement** over existing Close Session, freeze packs, validation, Prompt 5, Copilot, and Ops readiness.

---

## 1. Product philosophy

The customer should always know three things **without Engineering or Operations**:

1. What data has successfully loaded (**Load Integrity**).  
2. Whether they are ready to lock the close (**Ready to Lock**).  
3. What is preventing executive reporting (**blocking conditions**, explained).

Agents amplify the product—they never replace missing product functionality and never invent readiness (fail-closed).

Confidence journey the UI should teach:

```
Data Confidence  →  Financial Confidence  →  Executive Confidence
   (load)              (financial)              (certified / published)
```

---

## 2. What we already shipped (do not double-count)

Keep shipping under Close Peak; this workflow **feeds** them:

| Already shipped / in flight | Role in this workflow |
|---|---|
| Freeze packs COMPLETE / STALE | Artifact behind FREEZING → READY FOR EXECUTIVE REVIEW |
| Ops / cron prewarm | Safety net; not the primary customer trigger |
| Prompt 5 hard-block without servable pack | Consumes Certified / freeze pack; fail-closed |
| Ops readiness + Prompt 5 remaining | Internal view of the same lifecycle |
| Durable jobs, concurrency, trust strip | Peak reliability |
| Close Session | **Authoritative lineage object** for Lock events, freeze, exports |

---

## 3. Canonical name and product boundary

**Canonical name:** Customer Close Workflow  

**Product boundary (Lock):**

| Before Lock — Data Operations | After Lock — Financial Intelligence (serving) |
|---|---|
| Upload / ingest | Observation / freeze pack consumption |
| Load receipts & correction | Calculation / evidence (Phase 2 reserved) |
| Load integrity + financial integrity | Narratives, Prompt 5, Copilot |
| Ready-to-Lock checklist | Certified Close artifacts |

This boundary matches FIE’s “consume precomputed / labeled close context” direction (Close Peak §9) without standing up Class 2 services ahead of schedule.

---

## 4. Vocabulary reconciliation (required)

| Term | Audience | Definition |
|---|---|---|
| **Lock** | Customer action | Explicit “I am done loading for this close phase.” **Lock produces Close Ready work**—it is *not* the same word as Close Ready. |
| **Close Ready (Phase 1)** | Internal gate (§4F) | `financial validation pass/warning` + freeze `COMPLETE` + as-of transparency. Result of successful Lock → validate → freeze. |
| **Ready for Executive Review** | Customer ladder (§6) | Customer-facing label when Close Ready Phase 1 is true. |
| **Close Certified / Certified Close** | Customer + system | Freeze succeeded; certification metadata published for decks/Copilot. |
| **Preparing Close / Close Validation** | Customer ladder | Pre-Lock / pre-certification stages (see §6). |

**Lock vs Close Ready (explicit):**  
**Lock is the customer-initiated action that produces Close Ready.** Close Ready is the *resulting* internal gate state. Two audiences, one pipeline—never two competing product concepts.

**Customer ladder mapping:**

```
Preparing Close          →  OPEN, LOADING DATA
Close Validation         →  VALIDATING, READY TO LOCK
(Locked / Freezing)      →  LOCKED, FREEZING          (brief transitional labels)
Ready for Executive Review →  READY FOR EXECUTIVE REVIEW  (= Close Ready Phase 1)
Close Certified          →  PUBLISHED / Certified Close
(Reopened)               →  REOPENED → back into Preparing / Validation with new Lock version
```

Do **not** invent a long-lived customer-facing “Locked” rung parallel to this ladder—use Lock as the *action*, and keep ladder terms aligned with Close Peak §6.

---

## 5. Formal state machine

### 5.1 Customer-visible states

| State | Meaning |
|---|---|
| `OPEN` | Period close session exists; no meaningful loads yet (or reset after reopen). |
| `LOADING_DATA` | At least one load in progress or applied; checklist incomplete. |
| `VALIDATING` | Load integrity and/or financial integrity running or awaiting resolution. |
| `READY_TO_LOCK` | Platform computed eligibility; Lock CTA enabled. |
| `LOCKED` | Customer Lock accepted (immutable Lock event recorded). |
| `FREEZING` | Freeze pack build in progress. |
| `READY_FOR_EXECUTIVE_REVIEW` | Close Ready Phase 1 true; decks/Copilot allowed on certified/servable pack. |
| `PUBLISHED` | Customer/org has published executive materials for this lock version (or first successful Prompt 5 marked published—product may equate with Certified for Phase 1). |
| `REOPENED` | Customer reopened for further loads; prior packs/decks **unchanged**. |

### 5.2 Internal system states (not primary customer UI)

| Internal | Notes |
|---|---|
| Close Session status | Existing: `open` → `validation_complete` → `freeze_complete` → `archived` (extend carefully; see §10) |
| Freeze blob | `missing` / building / `COMPLETE` / `STALE` |
| Close Ready Phase 1 / 2 | Gate boolean + reason codes |
| Queue status | Export job depth / failures |
| Lock version `N` | Append-only event on Close Session lineage |

### 5.3 Valid transitions

```
OPEN → LOADING_DATA
LOADING_DATA ↔ VALIDATING
VALIDATING → READY_TO_LOCK | LOADING_DATA
READY_TO_LOCK → LOCKED | LOADING_DATA | VALIDATING
LOCKED → FREEZING
FREEZING → READY_FOR_EXECUTIVE_REVIEW | VALIDATING (freeze fail → explain + unblock)
READY_FOR_EXECUTIVE_REVIEW → PUBLISHED | REOPENED
PUBLISHED → REOPENED
REOPENED → LOADING_DATA | VALIDATING
```

After REOPENED + successful re-lock: new Lock version → FREEZING → new READY_FOR_EXECUTIVE_REVIEW (new pack). Prior deck/pack for Lock version N−1 remains immutable.

### 5.4 Invalid transitions (examples)

- Skip to `LOCKED` without `READY_TO_LOCK`.  
- `LOCKED` → `PUBLISHED` without freeze COMPLETE (Phase 1).  
- Mutate historical freeze pack or Lock event in place.  
- Agent or UI asserting Ready for Executive Review when Close Ready is false.  
- Prompt 5 starting with no COMPLETE/STALE pack (existing hard-block).

---

## 6. Integrity model (two independent concepts)

### 6.1 Load Integrity

- File / batch received  
- Rows staged  
- Rows applied  
- Row errors (code + message + row identity)  
- Durable **load receipt** per load  

### 6.2 Financial Integrity

Existing close / export validations (tie-outs): cash, ARR, revenue, statements, board metrics—surfaced today via validation APIs and trust strip. Do **not** invent a third scorecard; separate **presentation** of load vs financial.

Customers see both independently on the Close Checklist.

---

## 7. Ready to Lock, checklist, and blocking explanations

### 7.1 Ready to Lock

Platform computes eligibility. Customer never wonders “Am I finished?”

**Default Phase 1 checklist (configurable per org later):**

- Required datasets present for the close period (e.g. GL, CRM/closed-won, Billing, Headcount, Cash—org profile may subset)  
- Load integrity: no unresolved **critical** row errors  
- Financial integrity: validation status `pass` or `warning` (not `fail`) for Lock  
- No blocking jobs / freeze already mid-flight conflict  

When all pass → `READY_TO_LOCK`.

### 7.2 Customer Close Checklist (tax-software style)

Each item: **Completed | Remaining | Blocking | Warning** with deep link to fix.

### 7.3 Explain blocking (never bare “Cannot Lock”)

Examples:

- Missing Salesforce upload  
- 3 unresolved row errors  
- ARR reconciliation incomplete  
- Cash bridge failed  

Same fail-closed clarity as Prompt 5’s 409 messages.

---

## 8. Versioned Lock events (immutability)

Treat Lock as an **immutable event**, not a toggled boolean.

```
Close Session (org × as_of_period lineage)
  └─ Lock Event v1  →  Freeze Pack v1  →  Dec/Copilot outputs stamped with session + lock_version
  └─ Reopen
  └─ Lock Event v2  →  Freeze Pack v2  →  new outputs
```

**Required rule (Review fix 2):**  
Re-lock always produces a **new** frozen snapshot and new lock_version. It **never** modifies the pack an already-generated deck was built from. March’s board deck always matches what March said at Lock vN.

**Data model intent:** Lock events, load-receipt summaries, and freeze linkage live as **fields/events on the existing Close Session lineage**—not a parallel “readiness” service. Prefer append-only `close_lock_events` (and receipts) keyed by `close_session_id` over a second source of truth.

**Default reopen policy:** Allow further loads after reopen → mark prior COMPLETE pack **STALE** for live paths as needed → customer re-locks → new COMPLETE. Do not silently rewrite history.

---

## 9. Close Certification

After freeze succeeds for Lock version N, surface:

| Field | Example |
|---|---|
| Certified Close | true |
| Certified Period | `2026-06` |
| Certification Timestamp | ISO-8601 |
| Close Session ID | UUID |
| Lock Version | integer |
| Freeze Status | COMPLETE |

Prompt 5 and Copilot **consume Certified Close / servable freeze artifacts** (existing as-of + freeze headers). Prewarm remains Ops backup and does not by itself equal customer certification unless product explicitly marks it (default: prewarm prepares pack; customer Lock still required for “Certified” badge—Ops prewarm alone ≠ customer Lock).

**Note:** Ops prewarm may create COMPLETE packs for cold-start safety; customer **Certified Close** still requires Lock event for the workflow UI. Prompt 5 hard-block continues to use servable freeze (COMPLETE/STALE) so white-glove ops paths still work—label source honestly (customer-certified vs ops-prewarmed) in as-of / trust UI.

---

## 10. API implications (extend existing surfaces; no new platform service)

Extend current API workers—board, export, ops, Close Session—not a new microservice.

| Concern | Suggested surface |
|---|---|
| Workflow status | `GET .../close-workflow` (org + period) → state, checklist, blockers, lock_version, certification |
| Lock | `POST .../close-workflow/lock` |
| Reopen | `POST .../close-workflow/reopen` |
| Load receipts | `GET/POST` on ingest paths; list by session |
| Unload / correct | Product APIs on ingest (existing upload routes extended) |
| Ops readiness | Extend existing Ops close-readiness row with lock_version, receipt summary, workflow state |
| Prompt 5 / Copilot | Keep freeze gate; stamp `close_session_id` + `lock_version` on jobs |

Agents call **only** these APIs; never invent state.

---

## 11. Database implications

No new platform database. Extend current Neon schema around Close Session:

| Change | Purpose |
|---|---|
| `close_lock_events` (append-only) | lock_version, locked_at, locked_by, checklist_snapshot_json |
| `close_load_receipts` (or equivalent on ingest tables) | staged/applied/error counts + row error details |
| Close Session columns (optional denorm) | `workflow_state`, `current_lock_version`, `certified_at` |
| Freeze metadata | Already stores validation_check_ids; add `lock_version` / `close_session_id` |

Unique `(org, period)` Close Session remains the lineage root; versions hang off it.

---

## 12. Required backend services (modules, not new platforms)

| Module | Responsibility |
|---|---|
| Close workflow service | State machine transitions, Ready-to-Lock computation, Lock/Reopen |
| Load receipt service | Persist/serve receipts; feed checklist |
| Existing freeze blob service | Build on Lock (primary); prewarm (secondary) |
| Existing validation / export validation | Financial integrity |
| Existing Close Session service | Lineage + certification fields |
| Agent tools (later) | Thin wrappers over workflow APIs; fail-closed |

---

## 13. Agents (fail-closed rule)

Agents amplify A–D product surfaces.

**Rule:** The Agent reads Lock, receipt, freeze, and workflow state **directly** and **never infers or guesses** readiness. If state is ambiguous or contested, the Agent says so explicitly. Same fail-closed rigor as Prompt 5’s hard-block.

---

## 14. UX recommendations

1. Single **Close** hub for the period (not scattered upload vs board vs export).  
2. Top strip: workflow state + “what’s blocking executive reporting.”  
3. Checklist with Completed / Remaining / Blocking / Warning.  
4. Dual panels: Load Integrity | Financial Integrity.  
5. Lock CTA only in `READY_TO_LOCK`; disabled states explain why.  
6. After Lock: progress FREEZING → Certified Close card (session ID, timestamp, lock version).  
7. Reopen is intentional, confirms “prior decks stay tied to Lock vN.”  
8. Confidence steps: Data → Financial → Executive.

---

## 15. Human approval (reserved — do not implement now)

Reserve extension points on Lock / Publish without redesign:

```
… → READY_FOR_EXECUTIVE_REVIEW → [Controller Approval] → [CFO Approval] → PUBLISHED
```

Store approval events as future append-only rows on Close Session lineage.

---

## 16. Phasing (reconciled with Close Peak §6a)

| Phase | Scope | Outcome |
|---|---|---|
| **Now** | Continue Close Peak hardening | Peak-safe serving |
| **Next (Workflow Must)** | Load receipts **pulled forward** (required for Lock eligibility + checklist) → self-serve unload/correct (v1: unload batch + re-upload; row-level later) → Ready-to-Lock + Lock/Reopen events → freeze-from-Lock → Certified Close UI → Ops row extensions | Customer-owned Data Ops → FI serving |
| **Then** | Agents on workflow APIs; optional human approvals; Close Ready Phase 2 when Class 2 exists | Scale support |

**Receipts vs §6a:** Receipts were not on the original Must Ship list; **this workflow pulls receipts forward** because Ready-to-Lock and explained blockers cannot be honest without them. Treat receipts as **Workflow Must**, not optional Cohort B polish.

---

## 17. Future extensibility (no redesign)

- Domain-required dataset profiles (ABS-012 multi-path aware).  
- BIS-004-style immutable validation_run IDs when full Validation Platform lands—workflow already expects append-only integrity results.  
- FIE-001 Composite Snapshots / FIE-003 calculation runs attach to same Close Session + lock_version when Class 2 activates (Close Ready Phase 2).  
- FIE-005 narratives consume Certified Close artifacts only.  
- BUILD-005 ops alert on workflow stuck states; BUILD-008 success playbooks teach the checklist.

---

## 18. Final review answers

### 1. Does this become the canonical Customer Close Workflow for SMPL?

**Yes — recommended.** Once DRIs named and this doc frozen, all APIs, UI, Prompt 5, Copilot, Agents, Ops, and CS reference this lifecycle.

### 2. Remaining customer experience gaps before implementation?

Clarify at freeze meeting (defaults recommended below):

| Gap | Recommended default |
|---|---|
| Exact required datasets for Ready-to-Lock | Org plan profile; start with GL + Cash + CRM closed-won + headcount if present in entitlements |
| `PUBLISHED` vs first deck | Phase 1: Certified Close ≡ READY_FOR_EXECUTIVE_REVIEW after freeze; “Published” optional when first Prompt 5 succeeds |
| Prewarm vs Certified badge | Prewarm may create COMPLETE; **Certified** requires customer Lock event |
| Row-level correct vs unload+reupload | v1 unload/reupload; row-level Cohort B |
| Owner name | Fill before lock meeting |

### 3. Alignment with frozen specs

| Spec | Alignment |
|---|---|
| **ABS-012** | Path-agnostic: workflow cares that domains loaded into Canonical, not CSV vs API. Structural fail messages match explained blockers. |
| **BIS-003** | Loads converge to Canonical; immutable source refs ↔ immutable Lock/freeze lineage. |
| **BIS-004** | Load vs financial integrity mirrors structural vs business validation; append-only results ↔ versioned locks. Workflow does **not** own CAL—surfaces evidence for Lock. |
| **FIE-001** | Freeze / Certified Close is the production rehearsal of Observation/Composite Snapshot; Lock is an explicit capture trigger. No new Observation service required now. |
| **FIE-003** | Dec/reporting consume freeze/certified artifacts; no live invent-when-missing (matches hard-block). |
| **FIE-005** | Narratives/Copilot consume certified context; Agents fail-closed. |
| **BUILD-005** | Ops readiness extends with workflow state / lock version / receipts. |
| **BUILD-008** | Customer success teaches checklist + Lock; Agents amplify playbooks. |
| **Close Peak Rev 4** | Lock produces Close Ready; ladder mapping preserved; STALE policy + Close Session lineage; no parallel model. |

### 4. Implementation-ready for engineering?

**Yes, with freeze caveats:**  

- Treat this document as the authoritative Customer Close Workflow once DRIs are named.  
- Implement along **§16 Next** slice order (receipts → unload/reupload → checklist/Ready-to-Lock → Lock events → freeze-from-Lock → certification UI → Ops extensions).  
- Do **not** wait on Agents or human approvals.

**Recommendation:** Freeze this as the authoritative Customer Close Workflow and begin the §16 Next implementation slice.

---

## 19. One-sentence summary

**Customer Close Workflow** is the canonical period journey from load → Ready to Lock → versioned Lock → freeze → Certified Close → executive review, with Load and Financial integrity visible separately, blockers explained, Close Session as lineage, and Agents fail-closed on real state—without redesigning ABS/BIS/FIE.
