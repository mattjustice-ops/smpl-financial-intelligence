# FIE-BUILD-002 Engineering Playbook v1.0 — Issue List

**Document:** SMPL_FIE_BUILD_002_Engineering_Playbook_v1_0.docx  
**Companion:** FIE-BUILD-001 Implementation Plan v1.0  
**Status:** Approve after fixes  
**Generated:** 2026-07-06

---

## P0 — Broken cross-references (fix before handoff)

| ID | Location | Problem | Fix |
|----|----------|---------|-----|
| P0-1 | §1 (Engineering Philosophy), line ~18 | References "Section 16's **AI Usage Matrix** (FIE-BUILD-001)" | BUILD-001 §16 is **Engineering Acceptance Criteria**; no AI Usage Matrix exists. Retarget to **FIE-003 §1.2–1.3** and **FIE-005 §1.3**, or add an AI Usage Matrix section to BUILD-001. |
| P0-2 | §9 (Performance Standards), line ~203 | References "**FIE-BUILD-001's Performance Targets** section" | Section does not exist in BUILD-001 v1.0. Remove reference or cite **per-service Performance Targets** in owning BIS/FIE specs only. |
| P0-3 | §14 (Anti-Patterns), §17 (Explainability), §18 (Customer Trust) | References "**Product Acceptance Criteria**" in FIE-BUILD-001 | Section does not exist in BUILD-001 v1.0. Retarget to **BUILD-001 §13** (What Cannot Be Mocked), **§16** (Engineering Acceptance Criteria), and **§18** (Production Cutover). |
| P0-4 | Final Engineering Review, line ~561 | References "**FIE-BUILD-001's Complexity Assessment**" | Section does not exist in BUILD-001 v1.0. Add Complexity Assessment to BUILD-001 or remove this reference. |
| P0-5 | §6 (API Standards), line ~145 | References "**FIE-BUILD-001's Tool Gateway note**" | Tool Gateway note was recommended but is not in BUILD-001 v1.0. Add one ASSUMED line to BUILD-001 **or** cite **EIS-001/EIS-002** directly in BUILD-002 §6. |

---

## P1 — Terminology and brownfield gaps

| ID | Location | Problem | Fix |
|----|----------|---------|-----|
| P1-1 | §7 (Event Standards), event envelope | Event envelope uses **`tenant_id`**; API envelope, logging, and DB standards use **`customer_id`** | Standardize on **`customer_id`** platform-wide, or define explicit alias rule (`tenant_id` = `customer_id`) in §7 and Appendix C examples. |
| P1-2 | §2 (Repository Organization) | Assumes greenfield `platform/services/` layout | No guidance for existing **saas-financial-intelligence** monolith (`backend/app/`, prototype warehouse). Add **§2.1 Brownfield Bootstrap**: e.g. Phase 0–2 as modules inside existing repo; extract to `platform/services/` when contract tests pass. |
| P1-3 | §2 (Repository Organization) | No prototype coexistence guidance | BUILD-001 §0/§18 covers prototype parallel-run; playbook should echo: prototype code stays until per-customer cutover; new services must not read prototype tables except via explicit migration/adapter path. |

---

## P2 — Process and POC alignment

| ID | Location | Problem | Fix |
|----|----------|---------|-----|
| P2-1 | §4 (Standard Service Build Sequence), Step 12 | Testing listed **last** | Conflicts with BUILD-001 §9 (contract tests before feature work). Add note: **five platform-critical contracts** (BUILD-001 §8) get contract tests at **Steps 5–7**, not only at Step 12. |
| P2-2 | §10 (Security), §13 (Definition of Done) | Reads production-strict on **BIS-005 promotion** | BUILD-001 §12 allows **auto-approve** for POC-stage knowledge promotion. Add: *"POC-stage governance bypasses per BUILD-001 §12 must be feature-flagged and labeled temporary — never permanent policy."* |

---

## P3 — Maintenance and clarity (v1.1 acceptable)

| ID | Location | Problem | Fix |
|----|----------|---------|-----|
| P3-1 | Appendix A | Eleven **identical** service checklists (~150 lines duplicated) | Replace with one shared checklist template + service-specific addenda (already noted in Final Engineering Review). |
| P3-2 | Cross-document citations | Both BUILD-001 and BUILD-002 have **Section 16** with different meanings | Always prefix citations: **"BUILD-001 §16"** vs **"BUILD-002 §16"** in both documents. |
| P3-3 | §9, §11 | Performance and Observability restate per-service spec content | Intentional consolidation; optional v1.1 shorten to cross-references once teams internalize pattern. |

---

## Related BUILD-001 issues (same export batch)

These were flagged in the BUILD-001 review; fix in BUILD-001 or cross-link from BUILD-002.

| ID | Priority | Problem | Fix |
|----|----------|---------|-----|
| B1-1 | P1 | Phase 3 labeled "FIE-002 + Addendum A"; Milestone 3 defers Addendum A | Phase 3 = **FIE-002 core** only; Addendum A as optional parallel track. |
| B1-2 | P1 | GPES-001 testing vs Path A CSV POC mismatch | Label GPES = Path B acceptance; Section 4 golden path = Path A POC acceptance. |
| B1-3 | P1 | **MCR** not listed as BLOCKED | Add BLOCKED: MCR — not required for narrow ARR POC; required before module activation / entitlements. |
| B1-4 | P2 | Title says FIE only; Phases 0–1 are BIS | Subtitle or scope line: Platform + FIE, or split PLATFORM-BUILD-001 pointer. |
| B1-5 | P2 | CEP MAPPING-CONFIRMED workflow for Path A | Add BLOCKED/ASSUMED for production Path A ingest UX. |
| B1-6 | P2 | Tool Gateway / monolith assumption | One ASSUMED line: MVP modular monolith; extract per EIS-002 when services split. |
| B1-7 | P3 | §5 "ARR waterfall" wording | Clarify: subscription movement in source CSV, not BIS-004 waterfall reconciliation. |

---

## Suggested fix order

1. **P0-1 through P0-5** — unblocks engineers from chasing phantom BUILD-001 sections  
2. **P1-1** — prevents tenant/customer drift in events vs APIs  
3. **P1-2, P1-3** — unblocks team working in existing repo  
4. **P2-1, P2-2** — aligns playbook with BUILD-001 POC exceptions  
5. **B1-1 through B1-3** — align BUILD-001 with playbook citations  
6. **P3-*** — v1.1 cleanup  

---

## Paste-ready BUILD-002 §18 replacement (P0-3)

> The platform must always allow a customer to inspect Evidence, Lineage, Methodology, Definitions, Assumptions, Calculations, Confidence, and Narratives — no black boxes. The authoritative trust checklist is **FIE-BUILD-001 §13** (What Cannot Be Mocked), **§16** (Engineering Acceptance Criteria), and **§18** (Production Cutover). Engineers building any customer-facing feature must treat those sections as required review gates, not optional context.

---

## Paste-ready BUILD-002 §1 AI boundary fix (P0-1)

> See **FIE-003 §1.2–1.3** (calculation is deterministic, no LLM) and **FIE-005 §1.3** (reasoning about, not recomputing, FIE-003 outputs) for the full AI boundary.

---

## Paste-ready BUILD-002 §2.1 Brownfield Bootstrap (P1-2)

> **Brownfield bootstrap (ASSUMED):** The production codebase today is a modular monolith under `backend/app/` with a prototype warehouse layer. Phases 0–2 MAY implement BIS/FIE modules inside that structure before physical extraction to `platform/services/`. Extraction to peer service directories is required before Milestone 7 cutover. New target-architecture code MUST NOT read prototype aggregate tables (`actual_mrr_waterfall`, etc.) except through an explicit, feature-flagged migration or comparison adapter per FIE-BUILD-001 §18.
