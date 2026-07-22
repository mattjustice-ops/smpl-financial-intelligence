# Acceptable Use Policy

> **STATUS: DRAFT — NOT APPROVED**  
> Template for SOC 2 Type I readiness. Not company policy until approved.  
> Not legal advice. Not evidence of SOC 2 compliance.

| Field | Value |
|-------|--------|
| Policy ID | P02 |
| Owner | Security owner |
| Applies to | Employees, contractors, and others with SMPL accounts or devices used for work |
| Related criteria | Security (people) |
| Version | 0.1-draft |
| Effective date | _TBD on approval_ |

---

## 1. Purpose

Set expectations for responsible use of SMPL systems, accounts, and customer data.

## 2. Allowed use

- Use company systems and accounts for authorized business purposes.
- Protect credentials; use unique accounts; enable MFA where required.
- Handle customer financial and auth data only as needed for the job.
- Follow change and access procedures before production changes or privileged ops.

## 3. Prohibited use

- Sharing passwords or MFA codes; using shared admin logins for prod.
- Storing production secrets or customer dumps in git, tickets, or personal drives.
- Writing back to a customer’s GL/ERP from SMPL (product does not do this; personnel must not attempt workarounds).
- Sending raw sensitive customer data to personal email, unsanctioned AI tools, or public channels.
- Circumventing access controls, logging, or tenant isolation.
- Using production data in personal projects or unsanctioned demos.

## 4. Customer data & AI

- Prefer aggregated / governed freeze context when using LLM features.
- Anthropic (and any other LLM) API keys stay on the backend only — not in browser or static exports.
- AI commentary is not the system of record for numbers.

## 5. Devices & endpoints

- Keep work devices reasonably patched and locked when unattended.
- Report lost/stolen devices that may hold company access promptly.

## 6. Acknowledgement

New personnel acknowledge this policy at onboarding (process TBD — security owner). Re-acknowledge when material revisions ship.

## 7. Approval

| Approver | Signature / name | Date |
|----------|------------------|------|
| Executive sponsor | _DRAFT — not signed_ | |

---

_End of DRAFT P02_
