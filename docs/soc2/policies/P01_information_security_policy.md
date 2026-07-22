# Information Security Policy

> **STATUS: DRAFT — NOT APPROVED**  
> Template for SOC 2 Type I readiness. Do not treat as company policy until executive sponsor approves and records the date in [../04_policy_index.md](../04_policy_index.md).  
> Not legal advice. Not evidence of SOC 2 compliance.

| Field | Value |
|-------|--------|
| Policy ID | P01 |
| Owner | Security owner (proposed: Matt Justice — TBD confirm) |
| Applies to | All personnel and contractors with access to SMPL systems or customer data |
| Related criteria | Security (governance / CC1–CC2 themes) |
| Version | 0.1-draft |
| Effective date | _TBD on approval_ |

---

## 1. Purpose

Protect the confidentiality, integrity, and availability of SMPL systems and customer data in line with our business as a B2B SaaS financial intelligence platform.

## 2. Scope

Applies to production systems in the SOC 2 system boundary (see [../01_system_boundary.md](../01_system_boundary.md)): customer app, API, datastore, auth, billing, email, LLM API usage, source control/CI, and privileged ops paths that can touch tenant data.

## 3. Roles

| Role | Responsibility |
|------|----------------|
| Executive sponsor | Approves this policy; accepts residual risk |
| Security owner | Maintains this policy; coordinates access reviews, IR, vendor risk |
| Engineering owner | Implements technical controls (change, logging, env separation) |
| All personnel | Follow acceptable use; report security issues promptly |

## 4. Principles

1. **Least privilege** — access only as needed for the role.
2. **Defense in depth** — layered controls (auth, encryption, review, monitoring).
3. **Customer data stewardship** — financial warehouse data is confidential; no GL/ERP write-back.
4. **Evidence over intent** — controls must be operable and leave audit artifacts.
5. **Honest external language** — do not claim SOC 2 until a CPA firm issues a report.

## 5. Control themes (summary)

Detailed procedures live in sibling policies. This policy requires that SMPL maintain:

- Access control with MFA on admin/cloud accounts ([P03](./P03_access_control_policy.md))
- Change management for production code ([P05](./P05_change_management_policy.md))
- Incident response ([P04](./P04_incident_response_plan.md))
- Acceptable use ([P02](./P02_acceptable_use_policy.md))
- Vendor / subprocessor awareness ([../02_subprocessors.md](../02_subprocessors.md))
- Backup and recovery practices (Availability)
- Confidentiality handling for customer financial data

## 6. Reporting

Personnel report suspected security incidents or policy violations to the security owner immediately (see IR plan).

## 7. Review

Review at least annually, or after material stack/org change. Approvals recorded in the policy index.

## 8. Approval

| Approver | Signature / name | Date |
|----------|------------------|------|
| Executive sponsor | _DRAFT — not signed_ | |

---

_End of DRAFT P01_
