# Retention & Deletion Policy

> **STATUS: DRAFT — NOT APPROVED**  
> Template for SOC 2 Type I readiness. Not company policy until approved.  
> Not legal advice. Not evidence of SOC 2 compliance. SMPL is **not** SOC 2 certified.  
> Retention periods below are **working defaults** pending counsel / Matt approval and DPA language.

| Field | Value |
|-------|--------|
| Policy ID | P08 |
| Owner | Matt Justice (Security owner) |
| Applies to | Customer and operational data held by SMPL |
| Related criteria | Confidentiality |
| Version | 0.2-draft |
| Effective date | _TBD on approval_ |
| Last expanded | 2026-07-26 |

---

## 1. Purpose

Define how long SMPL retains data and how deletion / offboarding works when customers leave or request removal — implementable for a solo-founder SaaS using Neon, Auth.js, and managed providers.

## 2. Scope

- Active customer warehouse and auth/org data in Neon
- Backups (Neon / provider windows)
- Application and deploy logs (Vercel, Railway)
- Billing records (Stripe as system of record)
- Security / IR / access-review artifacts
- Marketing CMS (Sanity) if customer-named content exists

**Privacy** Trust Services criteria are deferred for Type I; contractual privacy obligations still belong in the customer DPA/MSA (**[!]** legal).

## 3. Working retention defaults (DRAFT — confirm with counsel)

| Data category | Working retention | Notes |
|---------------|-------------------|-------|
| Active customer warehouse data | Duration of subscription + service | Primary store: Neon |
| Auth / org membership | Duration of account + short grace (target ≤ 90 days) | Magic-link auth tables |
| White-glove staging files | Delete after successful load or POC close (target ≤ 30 days) | Local/ops copies — do not keep indefinitely |
| Backups | Per Neon / provider backup window | Restore tests under [P12](./P12_backup_and_restore.md); honest lag after deletion |
| Application / deploy logs | Provider defaults (Vercel, Railway) | Avoid logging secrets or full Confidential dumps |
| Billing records | Per Stripe + legal/tax needs | Stripe is system of record for payments |
| Security / IR records | ≥ 1 year or longer if investigation open | Timeline notes, access reviews |
| Marketing CMS (Sanity) | While published / needed | Boundary TBD if customer-named |

**[!]** Matt + counsel: lock contractual retention language in DPA / MSA before promising customers specific windows.

## 4. Customer offboarding / deletion request

1. Confirm requestor authority (customer admin / contract contact).
2. Disable product access for the org (invites/seats + auth).
3. Delete or anonymize Confidential warehouse + auth data for that org within an agreed window (working target: **30–90 days** after offboarding confirmation — **finalize with counsel**).
4. Delete white-glove staging copies associated with that org.
5. Note backups may retain data until backup expiry; document this limitation honestly to the customer.
6. Record completion date, who performed it, and org id (audit evidence).

## 5. Legal hold

Suspend deletion if litigation or regulatory hold applies — executive sponsor (Matt Justice) decides and records the hold.

## 6. Evidence

| Artifact | Example |
|----------|---------|
| Offboarding completion | Dated note: org, actions, operator |
| Retention defaults | This approved policy (+ DPA when signed) |
| Backup lag disclosure | Customer/comms note when relevant |

## 7. Related

- Classification: [P06](./P06_data_classification_and_handling.md)
- Confidentiality procedures: [P07](./P07_customer_data_confidentiality_procedures.md)
- Backups: [P12](./P12_backup_and_restore.md)

## 8. Approval

| Approver | Signature / name | Date |
|----------|------------------|------|
| Executive sponsor | _DRAFT — not signed — Matt Justice must approve_ | |

---

_End of DRAFT P08_
