# FIE-BUILD-005 Production Operations v1.0 — Issue List (BUILD-005 only)

**Document:** SMPL_FIE_BUILD_005_Production_Operations_v1_0.docx  
**Prior BUILD docs:** Frozen — no edits recommended to BUILD-001 through BUILD-004  
**Status:** Freeze after P2 fix; P3 optional  
**Generated:** 2026-07-06

---

## P2 — Fix before freeze (edit BUILD-005 only)

| ID | Location | Problem | Fix (in BUILD-005 only) |
|----|----------|---------|-------------------------|
| **B5-1** | §4 Operational Observability — Business Monitoring row (~line 79) | Traces To column reads **"FIE-BUILD-001's Capacity Expansion Guidelines (FIE-BUILD-003)"** — BUILD-001 does not own that section; the citation is wrong **inside this document** | Change Traces To to: **FIE-BUILD-003's Capacity Expansion Guidelines** (or **FIE-BUILD-003 §9, Capacity Expansion Guidelines**). No change to BUILD-003 required. |

### Paste-ready replacement (B5-1)

**Business Monitoring row — Traces To column:**

> FIE-BUILD-003's Capacity Expansion Guidelines

---

## P3 — Optional polish (BUILD-005 only, v1.0.1)

| ID | Location | Problem | Fix (in BUILD-005 only) |
|----|----------|---------|-------------------------|
| **B5-2** | §11 Operational Runbooks | Table E11.1 indexes failure categories but does not require each row to have an **authored, linked runbook document** on-call can open | Add one ASSUMED sentence after Table E11.1: *"Each indexed runbook category must have a written, version-controlled operational procedure linked from this handbook before the platform is certified for Production — the index is the catalog; the runbook artifacts are the procedures."* |
| **B5-3** | §6 or §7 (Financial Integrity / Customer Health) | No operational guidance when a customer is in **prototype vs FIE parallel-run** during cutover — a period when two number sources may coexist | Add optional ASSUMED paragraph in §7 Financial Integrity Monitoring (or §6 Customer Health): *"During per-customer cutover parallel-run (per frozen BUILD-001 §18 / BUILD-004 §12 rollback hierarchy), Operational Confidence and Customer Health monitoring must include reconciliation status for that customer — unreconciled divergence between prototype-derived and FIE-derived output for the same period is at minimum a Financial Integrity investigation (SEV-2 if customer-visible)."* References frozen docs; does not modify them. |
| **B5-4** | §12 Disaster Recovery | RPO/RTO described qualitatively but no placeholder for **numeric targets** at implementation time | Add one ASSUMED line in §12: *"Concrete RPO and RTO values are set at implementation time, recorded in operational configuration, and reviewed under §19's Operational Governance cadence — this section defines what they govern, not the numbers themselves."* |

---

## Not issues (no BUILD-005 change needed)

| Item | Why |
|------|-----|
| BUILD-003 Capacity Expansion Guidelines content | Frozen and correct; only BUILD-005's **citation** was wrong (B5-1) |
| BUILD-004 Release Success Criteria / observation window | BUILD-005 §6 Customer Health and §4 synthetic monitoring already cover post-release trust; explicit cross-ref optional, not required |
| Numeric SLO/SLA values in §16 | Intentionally directional; internal SLO tighter than customer SLA is stated |

---

## Fix order

1. **B5-1** — correct the citation in §4 (~30 seconds)  
2. **B5-2, B5-3, B5-4** — optional v1.0.1 batch  

---

## Verdict (unchanged)

| | |
|---|---|
| **Freeze?** | **Yes** — after B5-1 |
| **Grade** | **A-** ( **A** after B5-1 ) |
