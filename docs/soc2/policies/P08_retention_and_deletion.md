# Retention & Deletion Policy

> **STATUS: DRAFT — NOT APPROVED**  
> High-priority stub for Type I readiness. Not company policy until approved.  
> Not legal advice. Not evidence of SOC 2 compliance. Retention periods below are **working defaults** pending counsel/Matt approval.

| Field | Value |
|-------|--------|
| Policy ID | P08 |
| Owner | Matt Justice (Security owner) |
| Applies to | Customer and operational data held by SMPL |
| Related criteria | Confidentiality |
| Version | 0.1-draft |
| Effective date | _TBD on approval_ |
| Created | 2026-07-22 |

---

## 1. Purpose

Define how long SMPL retains data and how deletion / offboarding works when customers leave or request removal.

## 2. Working retention defaults (DRAFT — confirm with counsel)

| Data category | Working retention | Notes |
|---------------|-------------------|-------|
| Active customer warehouse data | Duration of subscription + service | Primary store: Neon |
| Auth / org membership | Duration of account + short grace | Magic-link auth tables |
| Backups | Per Neon / provider backup window | Restore tests under [P12](./P12_backup_and_restore.md) |
| Application / deploy logs | Provider defaults (Vercel, Railway) | Avoid logging secrets or full dumps |
| Billing records | Per Stripe + legal/tax needs | Stripe is system of record for payments |
| Security / IR records | ≥ 1 year or longer if investigation open | Timeline notes, access reviews |
| Marketing CMS (Sanity) | While published / needed | Boundary TBD if customer-named |

**[!]** Matt + counsel: lock contractual retention language in DPA / MSA.

## 3. Customer offboarding / deletion request

1. Confirm requestor authority (customer admin / contract contact).
2. Disable product access for the org.
3. Delete or anonymize Confidential warehouse + auth data for that org within an agreed window (target: **30–90 days** after offboarding confirmation — **finalize with counsel**).
4. Note backups may retain data until backup expiry; document this limitation honestly.
5. Record completion date (audit evidence).

## 4. Legal hold

Suspend deletion if litigation or regulatory hold applies — executive sponsor decides.

## 5. Approval

| Approver | Signature / name | Date |
|----------|------------------|------|
| Executive sponsor | _DRAFT — not signed — Matt Justice must approve_ | |

---

_End of DRAFT P08_
