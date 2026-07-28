# Acceptable Use Policy

> **STATUS: APPROVED** — Effective 2026-07-27. Approved by Matt Justice (executive sponsor).  
> Not legal advice. Not evidence of SOC 2 certification. Approving policies ≠ SOC 2 certified; open evidence items remain. SMPL is **not** SOC 2 certified until a CPA Type I report is in hand.

| Field | Value |
|-------|--------|
| Policy ID | P02 |
| Owner | Matt Justice (Security owner) |
| Applies to | Employees, contractors, and others with SMPL accounts or devices used for work |
| Related criteria | Security (people) |
| Version | 1.0 |
| Effective date | 2026-07-27 |
| Last expanded | 2026-07-22 |

---

## 1. Purpose

Set expectations for responsible use of SMPL systems, accounts, and customer data.

## 2. Allowed use

- Use company systems and accounts for authorized business purposes.
- Protect credentials; use unique accounts; enable MFA where required ([P03](./P03_access_control_policy.md)).
- Handle customer financial and auth data only as needed for the job.
- Follow change and access procedures before production changes or privileged ops ([P05](./P05_change_management_policy.md), [P16](./P16_white_glove_privileged_support_access.md) when drafted).
- Prefer sanitized or minimized data in demos, tickets, and screenshots.

## 3. Prohibited use

- Sharing passwords or MFA codes; using shared admin logins for prod.
- Storing production secrets or customer dumps in git, tickets, Slack/email, or personal drives.
- Writing back to a customer’s GL/ERP from SMPL (product does not do this; personnel must not attempt workarounds).
- Sending raw sensitive customer data to personal email, unsanctioned AI tools, or public channels.
- Circumventing access controls, logging, or tenant isolation.
- Using production data in personal projects or unsanctioned demos.
- Claiming SMPL is “SOC 2 certified” or “SOC 2 compliant” in sales or marketing before a CPA report exists.

## 4. Customer data & AI

- Prefer aggregated / governed freeze context when using LLM features.
- Anthropic (and any other LLM) API keys stay on the backend only — not in browser, Vercel client env, or static exports.
- AI commentary is not the system of record for numbers; engine/warehouse outputs are.
- Do not paste production customer data into consumer AI products (ChatGPT web, etc.) unless explicitly approved for that use case.
- Full AI/LLM posture: [P15](./P15_ai_llm_data_handling.md) (**Approved** 2026-07-28).

## 5. Devices & endpoints

- Keep work devices reasonably patched and locked when unattended.
- Use full-disk encryption where the OS supports it (recommended for laptops with prod access).
- Report lost/stolen devices that may hold company access promptly to Matt Justice.

## 6. Communications & social

- Do not disclose customer names, metrics, or credentials in public forums.
- Security questionnaires and customer security packs must align with [../SECURITY_ONE_PAGER.md](../SECURITY_ONE_PAGER.md) and approved language (“pursuing SOC 2”).

## 7. Acknowledgement

New personnel acknowledge this policy at onboarding (process owned by security owner). Re-acknowledge when material revisions ship.

## 8. Enforcement

Violations may result in access revocation and, for contractors/employees, disciplinary action up to termination of engagement. Suspected incidents follow [P04](./P04_incident_response_plan.md).

## 9. Approval

| Approver | Signature / name | Date |
|----------|------------------|------|
| Executive sponsor | Matt Justice | 2026-07-27 |

---

_End of APPROVED P02_
