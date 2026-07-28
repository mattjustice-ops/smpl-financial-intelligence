# Policy index (Type I starter set)

Track drafting and approval. Status values: **Not started** · Draft · In review · Approved · Needs update.

Parent: [../SOC2_TYPE1_KICKOFF.md](../SOC2_TYPE1_KICKOFF.md) · Scoreboard: [PROGRESS.md](./PROGRESS.md) · Criteria map: [../SMPL_SOC2_Readiness_Reference_v2.md](../SMPL_SOC2_Readiness_Reference_v2.md)

Platform templates (Vanta/Drata/etc.) are acceptable starting points later; customize for SMPL (multi-tenant finance data, white-glove loads, Anthropic prompts, no GL write-back).

**Approved ≠ SOC 2 certified.** P01–P12 are approved company policy as of 2026-07-27; **P15** approved 2026-07-28. Open evidence items (IR tabletop, vendor reports, DPA, etc.) remain. SMPL is **not** SOC 2 certified until an independent CPA Type I report is in hand.

---

## Core policies

| ID | Policy | Trust Services themes | Owner | Status | Approved date | Location / link |
|----|--------|----------------------|-------|--------|---------------|-----------------|
| P01 | Information Security Policy | Security (governance) | Matt Justice | **Approved** | 2026-07-27 | [policies/P01_information_security_policy.md](./policies/P01_information_security_policy.md) |
| P02 | Acceptable Use Policy | Security (people) | Matt Justice | **Approved** | 2026-07-27 | [policies/P02_acceptable_use_policy.md](./policies/P02_acceptable_use_policy.md) |
| P03 | Access Control Policy | Security (CC6); Confidentiality | Matt Justice | **Approved** | 2026-07-27 | [policies/P03_access_control_policy.md](./policies/P03_access_control_policy.md) |
| P04 | Incident Response Plan | Security; Availability | Matt Justice | **Approved** | 2026-07-27 | [policies/P04_incident_response_plan.md](./policies/P04_incident_response_plan.md) |
| P05 | Change Management / Secure SDLC | Security (CC8) | Matt Justice | **Approved** | 2026-07-27 | [policies/P05_change_management_policy.md](./policies/P05_change_management_policy.md) |
| P06 | Data Classification & Handling | Confidentiality | Matt Justice | **Approved** | 2026-07-27 | [policies/P06_data_classification_and_handling.md](./policies/P06_data_classification_and_handling.md) |
| P07 | Customer Data / Confidentiality Procedures | Confidentiality | Matt Justice | **Approved** | 2026-07-27 | [policies/P07_customer_data_confidentiality_procedures.md](./policies/P07_customer_data_confidentiality_procedures.md) |
| P08 | Retention & Deletion | Confidentiality | Matt Justice | **Approved** | 2026-07-27 | [policies/P08_retention_and_deletion.md](./policies/P08_retention_and_deletion.md) |
| P09 | Vendor / Subprocessor Management | Security (CC9) | Matt Justice | **Approved** | 2026-07-27 | [policies/P09_vendor_subprocessor_management.md](./policies/P09_vendor_subprocessor_management.md) |
| P10 | Risk Assessment (documented) | Security (CC3) | Matt Justice | **Approved** | 2026-07-27 | [policies/P10_risk_assessment.md](./policies/P10_risk_assessment.md) |
| P11 | Business Continuity / Disaster Recovery | Availability | Matt Justice | **Approved** | 2026-07-27 | [policies/P11_business_continuity_disaster_recovery.md](./policies/P11_business_continuity_disaster_recovery.md) |
| P12 | Backup & Restore (incl. restore test) | Availability | Matt Justice | **Approved** | 2026-07-27 | [policies/P12_backup_and_restore.md](./policies/P12_backup_and_restore.md) |
| P13 | Vulnerability Management | Security (CC7) | Matt Justice | Not started | | |
| P14 | Logging & Monitoring | Security; Availability | Matt Justice | Not started | | |
| P15 | AI / LLM Data Handling | Security; Confidentiality | Matt Justice | **Approved** (v1.1 draft amendment pending Allow) | 2026-07-28 | [policies/P15_ai_llm_data_handling.md](./policies/P15_ai_llm_data_handling.md) |
| P16 | White-glove / Privileged Support Access | Confidentiality; Security | Matt Justice | Not started | | |
| P17 | Security Awareness Training | Security (people) | Matt Justice | Not started | | |

---

## Related sales / legal artifacts (not SOC policies, but unblock buyers)

| Artifact | Status | Location |
|----------|--------|----------|
| Customer DPA / MSA (**single legal workstream**) | Not started — **[!]** counsel + Matt; also [P10](./policies/P10_risk_assessment.md) R16 | Covers privacy, retention windows, subprocessors (was previously flagged separately in P07/P08/P09) |
| Security one-pager | **Draft** (honest “pursuing SOC 2”) | [SECURITY_ONE_PAGER.md](./SECURITY_ONE_PAGER.md) |
| Change / deploy path (ops) | **Draft** | [CHANGE_MANAGEMENT.md](./CHANGE_MANAGEMENT.md) |
| Public or NDA subprocessors list | Draft (named) | [02_subprocessors.md](./02_subprocessors.md) |

---

## Approval record

| Policy ID | Approver (exec sponsor) | Date | Version |
|-----------|-------------------------|------|---------|
| P01 | Matt Justice | 2026-07-27 | 1.0 |
| P02 | Matt Justice | 2026-07-27 | 1.0 |
| P03 | Matt Justice | 2026-07-27 | 1.0 |
| P04 | Matt Justice | 2026-07-27 | 1.0 |
| P05 | Matt Justice | 2026-07-27 | 1.0 |
| P06 | Matt Justice | 2026-07-27 | 1.0 |
| P07 | Matt Justice | 2026-07-27 | 1.0 |
| P08 | Matt Justice | 2026-07-27 | 1.0 |
| P09 | Matt Justice | 2026-07-27 | 1.0 |
| P10 | Matt Justice | 2026-07-27 | 1.0 |
| P11 | Matt Justice | 2026-07-27 | 1.0 |
| P12 | Matt Justice | 2026-07-27 | 1.0 |
| P15 | Matt Justice | 2026-07-28 | 1.0 (1.1 draft pending Allow) |

---

## Change history

| Date | Change |
|------|--------|
| 2026-07-22 | P01–P05 expanded; P06, P08, P09, P11, P12 drafted; owners → Matt Justice |
| 2026-07-26 | P07 + P10 created; P06/P08/P09/P11/P12 expanded to approval-ready drafts; P01–P12 marked **Draft — ready for approval** (not approved) |
| 2026-07-27 | Matt review fixes (immutability vs retention; R15 Railway job interrupt; R16 consolidated DPA; P15 draft-next); **P01–P12 Approved** by Matt Justice. Reminder: approval ≠ SOC 2 certified. |
| 2026-07-27 | **P15** AI/LLM draft created (ready for approval, not approved); platform deferred DIY logged in decision log. |
| 2026-07-28 | **P15 Approved** by Matt Justice (redline: hallucination §4.7, logging/retention 30 days, P04/P08 companion edits). Approval ≠ SOC 2 certified. |
| 2026-07-28 | **P15 v1.1 draft amendment** (machine-primary grounding / fail-closed / freeze-ID binding; human review not primary) + IR Scenario B / P04 companion — **pending Matt Allow**. Do not treat as Allowed until confirmed. |
