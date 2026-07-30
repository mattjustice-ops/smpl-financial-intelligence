# Risk Assessment Policy

> **STATUS: APPROVED** — Effective 2026-07-27. Approved by Matt Justice (executive sponsor).  
> Not legal advice. Not evidence of SOC 2 certification. Approving policies ≠ SOC 2 certified; open evidence items remain. SMPL is **not** SOC 2 certified until a CPA Type I report is in hand.

| Field | Value |
|-------|--------|
| Policy ID | P10 |
| Owner | Matt Justice (Security owner / Executive sponsor) |
| Applies to | Risks to Security, Availability, and Confidentiality of the SMPL production platform |
| Related criteria | Security (CC3); Availability; Confidentiality |
| Version | 1.0 |
| Effective date | 2026-07-27 |
| Created | 2026-07-26 |
| Last updated | 2026-07-27 |

---

## 1. Purpose

Establish how SMPL identifies, evaluates, treats, and accepts risks that could affect the confidentiality, integrity (operational), or availability of systems and customer data in Type I scope.

**Out of scope for this Type I register:** Processing Integrity of FP&A math; Trust Services Privacy (both deferred per [../00_decision_log.md](../00_decision_log.md)).

## 2. Scope

- Production stack (Customer Data): Vercel, Railway, Neon, Auth.js, Resend, Stripe, GitHub, Anthropic; privileged ops paths. Sanity = marketing only (outside product DPA). OpenAI not live.
- People/process: solo-founder concentration, access, change, vendors, incidents, backups.
- Customer data paths: CSV / white-glove loads; future read-only connectors (no GL write-back).

## 3. Roles

| Role | Holder | Responsibility |
|------|--------|----------------|
| Executive sponsor | Matt Justice | Accepts residual risk; approves this policy |
| Security owner | Matt Justice | Runs assessments; maintains register; drives treatments |
| Engineering owner | Matt Justice | Implements technical treatments |

## 4. Cadence

| Trigger | Action |
|---------|--------|
| At least **annually** | Full review of this register + treatment status |
| Material stack / vendor change | Spot update (new subprocessor, region, auth model) |
| Sev1–2 incident | Post-incident risk update ([P04](./P04_incident_response_plan.md)) |
| Before Type I fieldwork | Confirm register reflects live controls |

## 5. Method (lightweight)

1. **Identify** — assets, threats, vulnerabilities (people, process, technology, vendors).
2. **Assess** — likelihood (L) and impact (I) on a 1–3 scale; risk score = L × I.
3. **Treat** — mitigate, transfer (vendor/contract), accept, or avoid.
4. **Record** — owner, status, residual risk, next review.
5. **Accept** — executive sponsor accepts residual risks that remain open.

| Score | Meaning |
|-------|---------|
| 1–2 | Low — monitor |
| 3–4 | Medium — scheduled treatment |
| 6 | High — priority before Type I where feasible |
| 9 | Critical — immediate treatment or formal accept |

## 6. Initial risk register (working — updated 2026-07-27)

| ID | Risk | L | I | Score | Treatment | Residual | Owner | Status |
|----|------|---|---|-------|-----------|----------|-------|--------|
| R01 | Solo-founder concentration (all roles = Matt) | 3 | 3 | 9 | Document procedures; MFA; backups; eventual hire/split roles | High — **accepted** until team grows | Matt | Accept |
| R02 | Admin account compromise (cloud consoles) | 2 | 3 | 6 | MFA on admin paths; unique accounts; inventory; same-day revoke | Medium | Matt | Mitigate (MFA live 2026-07-26) |
| R03 | Cross-tenant data exposure | 2 | 3 | 6 | `organization_id` model; isolation tests before Type I; IR playbook | Medium until test evidence | Matt | Mitigate |
| R04 | Secret leakage (git, logs, tickets) | 2 | 3 | 6 | Secrets in Vercel/Railway only; no dumps in git; rotate on exposure | Medium | Matt | Mitigate |
| R05 | Provider outage (Vercel / Railway / Neon) | 2 | 3 | 6 | Monitor status; redeploy path; backups/PITR ([P11](./P11_business_continuity_disaster_recovery.md), [P12](./P12_backup_and_restore.md)). Distinct from R15 (routine redeploy job interrupt). | Medium — vendor-dependent | Matt | Mitigate / transfer |
| R06 | Backup unusable / untested restore | 2 | 3 | 6 | Neon backups + restore test before Type I. Runbook ready 2026-07-27 ([../runbooks/neon-restore-test.md](../runbooks/neon-restore-test.md)); **PITR throwaway pass** 2026-07-27 ([../evidence/neon-restore-test-2026-07-27.md](../evidence/neon-restore-test-2026-07-27.md)). | Low–Medium (tested) | Matt | Mitigate |
| R07 | Unauthorized privileged / white-glove access | 2 | 3 | 6 | Named operators; inventory; revoke after POC; least privilege | Medium | Matt | Mitigate |
| R08 | Subprocessor breach or weak vendor controls | 2 | 2 | 4 | Inventory ([../02_subprocessors.md](../02_subprocessors.md)); collect SOC/ISO under NDA; annual review ([P09](./P09_vendor_subprocessor_management.md)) | Medium | Matt | Mitigate (reports open) |
| R09 | LLM prompt leakage of Confidential metrics | 2 | 2 | 4 | Keys on API only; minimize raw PII; no consumer AI paste ([P02](./P02_acceptable_use_policy.md)); full policy = [P15](./P15_ai_llm_data_handling.md) (**Approved** 2026-07-28) | Low–Medium | Matt | Mitigate |
| R10 | Magic-link / email compromise → account takeover | 2 | 2 | 4 | MFA on corporate email/IdP; org invites control; treat email as auth factor | Medium | Matt | Mitigate |
| R11 | Unreviewed production change | 2 | 2 | 4 | Required PR to `main`; documented deploy path ([P05](./P05_change_management_policy.md)) | Low–Medium | Matt | Mitigate (ruleset live) |
| R12 | Accidental GL/ERP write-back or connector misuse | 1 | 3 | 3 | Product constraint: read-only; prohibit workarounds ([P07](./P07_customer_data_confidentiality_procedures.md)) | Low | Matt | Mitigate / avoid |
| R13 | Overclaiming SOC 2 certification in sales | 2 | 2 | 4 | Approved language only; one-pager; AUP prohibition | Low if followed | Matt | Mitigate |
| R14 | Incomplete retention/deletion after offboarding | 2 | 2 | 4 | Operable steps in [P08](./P08_retention_and_deletion.md); contractual windows via **R16** (single DPA workstream) | Medium until DPA locked | Matt | Mitigate |
| R15 | Railway restart/redeploy interrupts in-flight export jobs | 3 | 2 | 6 | **Known architecture:** export work still runs in-process via `ThreadPoolExecutor` (`backend/.../export_jobs.py`); job **metadata/artifacts** are durable in Postgres, but a Railway restart/redeploy kills the worker — queued/running jobs are marked failed (“Interrupted by restart”; customer must regenerate). More common than full provider outage (R05). Treatment: durable worker/queue that can resume, or honest customer UX + ops playbook. | Medium — accepted short-term | Matt | Mitigate (open) |
| R16 | Unsigned / incomplete Customer DPA–MSA (privacy, retention, subprocessors) | 2 | 3 | 6 | **Single legal workstream** — counsel + Matt; track in [../PROGRESS.md](../PROGRESS.md) + this row. **Sent to counsel 2026-07-29** — awaiting redline / customer-ready draft; R16 **not** closed. Firm: unspecified. Matt attested send via chat (agent did not email) — [../evidence/dpa-counsel-sent-2026-07-29.md](../evidence/dpa-counsel-sent-2026-07-29.md); pack [../legal/COUNSEL_SEND_PACKAGE.md](../legal/COUNSEL_SEND_PACKAGE.md). P07/P08/P09 cross-reference here; do not treat as three separate policy gaps. | Medium until signed | Matt | Mitigate (open — sent to counsel; not closed) |

## 7. Risk acceptance (standing)

The executive sponsor explicitly accepts for Type I readiness planning:

1. **Single-person ownership concentration (R01)** until roles are split.
2. **No multi-region / multi-cloud failover** — recovery relies on provider capabilities + documented restore ([P11](./P11_business_continuity_disaster_recovery.md)).
3. **Deferred Processing Integrity and Privacy** — not attested in this Type I scope.
4. **Vendor dependence** for encryption-at-rest, physical security, and some availability controls — managed via [P09](./P09_vendor_subprocessor_management.md).

## 8. Linkage to controls

| Theme | Policy / artifact |
|-------|-------------------|
| Access / MFA | [P03](./P03_access_control_policy.md), access inventory |
| Incidents | [P04](./P04_incident_response_plan.md) |
| Change | [P05](./P05_change_management_policy.md) |
| Confidentiality | [P06](./P06_data_classification_and_handling.md), [P07](./P07_customer_data_confidentiality_procedures.md) |
| Vendors | [P09](./P09_vendor_subprocessor_management.md) |
| Continuity / backup | [P11](./P11_business_continuity_disaster_recovery.md), [P12](./P12_backup_and_restore.md) |
| Export job availability | R15 — ThreadPoolExecutor + durable Postgres metadata |
| Customer DPA / MSA (legal) | R16 — single workstream; [../PROGRESS.md](../PROGRESS.md) |
| AI / LLM handling | [P15](./P15_ai_llm_data_handling.md) — **Approved** 2026-07-28 |

## 9. Evidence

- This approved policy + dated register updates
- Decision log for scope deferrals
- Treatment evidence (MFA screenshots, branch protection, restore test notes, vendor report folder)

## 10. Approval

| Approver | Signature / name | Date |
|----------|------------------|------|
| Executive sponsor | Matt Justice | 2026-07-27 |

---

_End of APPROVED P10_
