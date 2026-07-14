# Customer Close Data Readiness — Alignment Brief

**Status:** Proposed for team validation  
**Owner:** TBD  
**Date:** 2026-07-14  
**Related:** [Close_Process.md](./Close_Process.md) · [CLOSE_PEAK_WORKLOAD.md](./CLOSE_PEAK_WORKLOAD.md) (Rev 4) · current freeze / Prompt 5 / Ops readiness work

**Purpose of this note:** Get product, eng, and ops on the same page about the *customer data → lock → freeze → decks* gap, separate from peak-concurrency hardening already underway.

---

## 1. Overarching problem statement

Our platform already supports **loading data**, **validation tie-outs**, and **close outputs** (board decks, commentary / Copilot). What we do **not** yet give customers is a clear, self-serve control loop that answers:

> “Have I finished loading what I intend for this close month, did it load cleanly, and am I unlocked for the next phase (decks / commentary) — without needing engineering?”

Today those steps are fragmented:

| Reality today | Gap |
|---|---|
| Customers load (and re-load) data throughout the month — cash collections, closed-won, GL, etc. | Continuous ingest is expected; “done loading for close” is not a first-class signal |
| Freeze packs precompute close context for Prompt 5 / Copilot | Freeze is largely ops/auto-driven; customers don’t explicitly declare readiness |
| Validation exists for financial tie-outs | Load **receipts** (staged vs applied, row-level failures) and self-serve fix/unload are thin or eng-mediated |
| Close Peak work hardens concurrency, freeze COMPLETE/STALE, Prompt 5 gates, Ops visibility | That protects *our* ability to serve peak; it does not complete the *customer’s* load → lock → unlock journey |

**If we don’t address this:** every close week, eng/ops become the helpdesk for “did my file load?”, “can I undo two bad rows?”, and “why can’t I generate a deck?” — and Agent standups won’t scale if the product still lacks receipts, lock, and self-serve correction.

**If we do:** customers own the path from data → certified close pack → decks; Agents and Ops amplify that path instead of substituting for it.

---

## 2. What we are already doing (so we don’t double-count)

These are **in flight / shipped** under Close Peak workload hardening — keep shipping them; do not reopen as net-new “data readiness” scope:

| Item | Intent |
|---|---|
| Freeze packs (COMPLETE / STALE) | Servable close-context snapshots; never silent partial packs |
| Night-before / Ops prewarm | Ops safety net so close morning isn’t cold |
| Prompt 5 hard-block without servable pack | Dec starts only when COMPLETE or labeled STALE exists |
| Ops readiness (check IDs, Prompt 5 remaining, Phase 1 ready) | Internal triage during close week |
| Durable jobs, concurrency, trust strip, Close Session | Peak reliability + lineage |

**This brief is about the customer-facing control plane that feeds those mechanisms**, not replacing them.

---

## 3. Recommendations by addressable item

### A. Explicit customer “ready for close outputs” (Lock)

**Recommendation:** Add a customer-facing **Lock close month** (or “Ready for board / commentary”) action per org + `as_of_period`.

- Continuous mid-month loads remain allowed **until** lock.
- Lock means: “I do not intend to load more for this phase.”
- Lock triggers (or requires) validation, then freeze COMPLETE, then unlocks decks / commentary paths that depend on the pack.
- Further loads after lock either blocked with a clear unlock path, or allowed with **STALE** + re-lock (product decision — recommend: allow with explicit “reopen / re-lock” so late cash isn’t a support ticket).

**Not recommended:** Auto-freeze on every successful load — too eager for mid-month update patterns.

**Team check:** Do we agree Lock is the customer signal that bridges ingest to freeze/decks?

---

### B. Freeze lifecycle relative to Lock (not instead of prewarm)

**Recommendation:** Treat freeze as the **system consequence of Lock + validation**, with Ops prewarm as backup.

| Trigger | Role |
|---|---|
| Customer Lock (+ validation pass/warning) | Primary path — builds COMPLETE pack |
| Ops / cron prewarm | Safety net for white-glove and cold starts |
| New ingest while COMPLETE exists | Mark STALE; Prompt 5 may still serve labeled STALE per Close Peak §4B |

**Team check:** Primary freeze owner = customer Lock; prewarm stays secondary?

---

### C. Load receipts (staged vs applied + row errors)

**Recommendation:** Every load produces a durable **receipt** customers can see:

- *Example good:* 1000 staged → 1000 applied  
- *Example partial:* 1000 staged → 998 applied; rows X/Y failed with error codes `#1`, `#2` and human-readable reasons  

Receipts feed Lock eligibility (“you still have unresolved row errors”) and Ops triage.

**Team check:** Is load receipt Must Ship before Agents, or same phase?

---

### D. Self-serve unload / correct without engineering

**Recommendation:** Customers can:

1. Unload a prior load (or a load batch) for a dataset + period, **or**  
2. Correct / re-upload the specific failing rows / file  

…without opening an eng ticket. Product surfaces + APIs first; Agents call those same APIs.

**Team check:** Scope for v1 — full dataset unload only, or row-level correct as well?

---

### E. Validation placement in the path

**Recommendation:** Two layers, both visible:

1. **Load integrity** — staged/applied/errors (Item C)  
2. **Close / financial validation** — existing tie-outs (cash bridge, closed-won ↔ ARR, FS checks, etc.)  

Lock should require (or strongly gate on) both being acceptable. Existing board validation + trust strip stay; don’t invent a third parallel scorecard.

**Team check:** Must Lock require financial validation pass/warning, or only load integrity with financial validation as a soft gate?

---

### F. AI Agents — amplifier, not system of record

**Recommendation:** Design Agent(s) **on top of** Lock, receipts, unload/correct, and freeze status — shared playbooks for all customers, not one bespoke agent per tenant.

| Agent is good at | Agent must not be |
|---|---|
| Explaining row errors; walking unload/re-upload; answering “am I ready to lock?” | The only place readiness is recorded |
| Close-week surge via shared standby capacity + clear escalation to Ops | A substitute for missing product APIs |

Standby capacity for close week is real; scale it as **shared agent + product surfaces**, not N custom deployments.

**Team check:** Agents after (or in parallel with polish on) A–D, never instead of A–D?

---

### G. Ops / CS visibility (extends what we shipped)

**Recommendation:** Extend Ops readiness rows with:

- Last load receipt summary (staged / applied / error count)  
- Lock state + locked_at  
- Freeze status (already)  
- Prompt 5 remaining (already)  

So Ops can answer “who’s stuck before decks?” without chatting every customer.

**Team check:** Enough to extend current Ops tab, or separate “Customer data readiness” view later?

---

## 4. Suggested phasing (for same-page planning)

| Phase | Addressable items | Outcome |
|---|---|---|
| **Now (continue)** | Close Peak hardening already shipped / in flight | Peak-safe decks + freeze + Ops triage |
| **Next (Must for self-serve close)** | C receipts → D unload/correct → A Lock → B freeze-from-lock → E gates | Customers finish data → unlock decks without eng |
| **Then (scale)** | F Agents on those APIs + G Ops extensions | Close-week support scales with customers |

Exact cut line for “first paid close” should be decided against [CLOSE_PEAK_WORKLOAD.md](./CLOSE_PEAK_WORKLOAD.md) §6a and signed-customer commitments — this brief argues **receipts + Lock** are the highest-leverage additions to that story.

---

## 5. Decisions we need from the group

1. Is **customer Lock** the official bridge from ingest to freeze/decks?  
2. After Lock, are further loads **blocked until reopen**, or **allowed with STALE + re-lock**?  
3. Is **load receipt + self-serve correct/unload** Must Ship for first cohort, or Cohort B?  
4. Must Lock wait on **financial validation**, or only **load integrity**?  
5. Are **Agents** Phase “Then,” with product surfaces landing first?

Please annotate agree / disagree / amend on each item (A–G) and the five decisions above.

---

## 6. One-sentence summary for Slack / standup

We’re aligning that **Close Peak hardening keeps the system alive at month-end**, while the next product beat is a **customer-owned load receipt → Lock → validate → freeze → decks** path, with Agents amplifying that path rather than replacing it.
