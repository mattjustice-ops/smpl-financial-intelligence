# Information Security Policy

> **STATUS: APPROVED** — Effective 2026-07-27. Approved by Matt Justice (executive sponsor).  
> Not legal advice. Not evidence of SOC 2 certification. Approving policies ≠ SOC 2 certified; open evidence items remain. SMPL is **not** SOC 2 certified until a CPA Type I report is in hand.

| Field | Value |
|-------|--------|
| Policy ID | P01 |
| Owner | Matt Justice (Security owner / Executive sponsor) |
| Applies to | All personnel and contractors with access to SMPL systems or customer data |
| Related criteria | Security (governance / CC1–CC2 themes); Availability; Confidentiality |
| Version | 1.0 |
| Effective date | 2026-07-27 |
| Last expanded | 2026-07-26 |

---

## 1. Purpose

Protect the confidentiality, integrity, and availability of SMPL systems and customer data in line with our business as a B2B SaaS financial intelligence platform (FP&A / ARR / close / board export).

## 2. Scope

Applies to production systems in the SOC 2 system boundary (see [../01_system_boundary.md](../01_system_boundary.md)):

- Customer web app (Vercel / Next.js)
- API services (Railway / FastAPI)
- Datastore (Neon / Postgres)
- Authentication (Auth.js magic link + org membership)
- Billing (Stripe), transactional email (Resend), LLM API usage (Anthropic; keys on API only)
- Source control / CI (GitHub) and deploy paths to production
- Privileged ops paths that can touch tenant data (ops console, white-glove loads, break-glass DB)

## 3. Roles

| Role | Name (current) | Responsibility |
|------|----------------|----------------|
| Executive sponsor | Matt Justice | Approves this policy; accepts residual risk; external security language |
| Security owner | Matt Justice | Maintains this policy; access reviews, IR, vendor risk |
| Engineering owner | Matt Justice | Implements technical controls (change, logging, env separation) |
| Ops / CS privileged access | Matt Justice | Tenant support access; white-glove data loads |
| All personnel | — | Follow acceptable use; report security issues promptly |

## 4. Principles

1. **Least privilege** — access only as needed for the role.
2. **Defense in depth** — layered controls (auth, encryption, review, monitoring).
3. **Customer data stewardship** — financial warehouse data is confidential; SMPL does **not** write back to customer GL/ERP. Active-relationship immutability (nothing silently rewritten) is a different axis from retention/deletion after offboarding — see [P08](./P08_retention_and_deletion.md).
4. **Evidence over intent** — controls must be operable and leave audit artifacts.
5. **Honest external language** — say “pursuing SOC 2” / “SOC 2 readiness in progress.” Never claim SOC 2 certified until a CPA firm issues a report.

## 5. Control themes (summary)

Detailed procedures live in sibling policies. This policy requires that SMPL maintain:

| Theme | Policy / artifact |
|-------|-------------------|
| Acceptable use | [P02](./P02_acceptable_use_policy.md) |
| Access control + MFA on admin/cloud | [P03](./P03_access_control_policy.md), [../03_access_inventory_template.md](../03_access_inventory_template.md) |
| Incident response | [P04](./P04_incident_response_plan.md) |
| Change management / SDLC | [P05](./P05_change_management_policy.md), [../CHANGE_MANAGEMENT.md](../CHANGE_MANAGEMENT.md) |
| Data classification & handling | [P06](./P06_data_classification_and_handling.md) |
| Customer data / confidentiality procedures | [P07](./P07_customer_data_confidentiality_procedures.md) |
| Retention & deletion | [P08](./P08_retention_and_deletion.md) |
| Vendor / subprocessor management | [P09](./P09_vendor_subprocessor_management.md), [../02_subprocessors.md](../02_subprocessors.md) |
| Risk assessment | [P10](./P10_risk_assessment.md) |
| Business continuity / DR | [P11](./P11_business_continuity_disaster_recovery.md) |
| Backup & restore | [P12](./P12_backup_and_restore.md) |
| AI / LLM data handling | [P15](./P15_ai_llm_data_handling.md) (draft — ready for approval; not yet approved) |

## 6. Risk acceptance

Material residual risks (e.g. deferred Processing Integrity, Privacy skip, single-person ownership concentration) are accepted by the executive sponsor until roles are split or scope is expanded with an auditor.

## 7. Reporting

Personnel report suspected security incidents or policy violations to the security owner immediately (see IR plan). Primary contact: **Matt Justice**.

## 8. Review

Review at least annually, or after material stack/org change. Approvals recorded in the policy index.

## 9. Approval

| Approver | Signature / name | Date |
|----------|------------------|------|
| Executive sponsor | Matt Justice | 2026-07-27 |

---

_End of APPROVED P01_
