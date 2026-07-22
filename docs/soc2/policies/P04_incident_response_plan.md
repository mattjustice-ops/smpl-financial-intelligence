# Incident Response Plan

> **STATUS: DRAFT — NOT APPROVED**  
> Template for SOC 2 Type I readiness. Not company policy until approved.  
> Not legal advice. Not evidence of SOC 2 compliance.

| Field | Value |
|-------|--------|
| Policy ID | P04 |
| Owner | Security owner |
| Applies to | Suspected or confirmed security / availability incidents affecting SMPL or customer data |
| Related criteria | Security; Availability |
| Version | 0.1-draft |
| Effective date | _TBD on approval_ |

---

## 1. Purpose

Define how SMPL detects, contains, eradicates, recovers from, and communicates about security and availability incidents.

## 2. Roles

| Role | During an incident |
|------|---------------------|
| Security owner | Incident commander (or designates); decides severity & customer notice |
| Engineering owner | Technical containment, forensics lite, restore |
| Executive sponsor | Escalation; external comms approval for material incidents |
| Ops / CS | Customer channel if notified |

**Primary contact (fill):** _[! Matt — name + channel]_

## 3. What counts as an incident

Examples (not exhaustive):

- Unauthorized access to production systems or tenant data
- Suspected credential compromise / missing MFA on admin account
- Ransomware, malware, or destructive change in prod
- Prolonged unplanned outage affecting committed availability
- Accidental cross-tenant data exposure
- Subprocessor breach that may affect SMPL customers

## 4. Severity (working model)

| Severity | Example | Response target (draft) |
|----------|---------|-------------------------|
| Sev1 | Confirmed breach of customer data; total prod outage | Immediate; exec + eng engaged |
| Sev2 | Likely compromise; major degradation | Same business day |
| Sev3 | Limited impact; contained quickly | Next business day triage |
| Sev4 | Suspicious event; no confirmed impact | Track and investigate |

## 5. Process

1. **Detect / report** — Anyone reports to security owner via _[channel TBD]_.
2. **Triage** — Confirm scope; assign severity; start timeline notes.
3. **Contain** — Revoke access, rotate secrets, isolate systems as needed.
4. **Eradicate & recover** — Fix root cause; restore from known-good backup if needed.
5. **Communicate** — Internal first; customer notification when legally/contractually required or material risk to their data (exec approval).
6. **Post-incident** — Blameless write-up within 10 business days for Sev1–2; update controls/policies if needed.

## 6. Evidence to keep

- Timeline notes, decisions, who was notified
- Tickets / PR links for fixes
- Access revoke / secret rotation records

## 7. Tabletop

Run a lightweight tabletop at least annually (or before Type I fieldwork). Record date and attendees.

## 8. Approval

| Approver | Signature / name | Date |
|----------|------------------|------|
| Executive sponsor | _DRAFT — not signed_ | |

---

_End of DRAFT P04_
