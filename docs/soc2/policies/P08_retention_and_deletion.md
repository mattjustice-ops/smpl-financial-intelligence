# Retention & Deletion Policy

> **STATUS: APPROVED** — Effective 2026-07-27. Approved by Matt Justice (executive sponsor).  
> Not legal advice. Not evidence of SOC 2 certification. Approving policies ≠ SOC 2 certified; open evidence items remain. SMPL is **not** SOC 2 certified until a CPA Type I report is in hand.

| Field | Value |
|-------|--------|
| Policy ID | P08 |
| Owner | Matt Justice (Security owner) |
| Applies to | Customer and operational data held by SMPL |
| Related criteria | Confidentiality |
| Version | 1.0 |
| Effective date | 2026-07-27 |
| Last updated | 2026-07-27 |

---

## 1. Purpose

Define how long SMPL retains data and how deletion / offboarding works when customers leave or request removal — implementable for a solo-founder SaaS using Neon, Auth.js, and managed providers.

**Immutability vs retention (not in conflict):** During an active customer relationship, warehouse / financial facts are not silently rewritten — corrections are handled as explicit new loads or documented adjustments, not quiet overwrites. That **immutability / integrity** axis is separate from **retention and deletion** after a customer leaves or requests removal. Auditors and customers should not read retention windows as permission to mutate history in place, nor read immutability as a promise to keep data forever after offboarding.

Retention periods below remain **working defaults** until contractual language is locked in the consolidated Customer DPA / MSA legal workstream ([../PROGRESS.md](../PROGRESS.md); [P10](./P10_risk_assessment.md) R16).

## 2. Scope

- Active customer warehouse and auth/org data in Neon
- Backups (Neon / provider windows)
- Application and deploy logs (Vercel, Railway)
- Billing records (Stripe as system of record)
- Security / IR / access-review artifacts
- Marketing CMS (Sanity) if customer-named content exists

**Privacy** Trust Services criteria are deferred for Type I; contractual privacy / DPA obligations are tracked as **one** legal workstream — see §3 note and [P10](./P10_risk_assessment.md) R16 (not separate open flags in each policy).

## 3. Working retention defaults (confirm with counsel)

| Data category | Working retention | Notes |
|---------------|-------------------|-------|
| Active customer warehouse data | Duration of subscription + service | Primary store: Neon |
| Auth / org membership | Duration of account + short grace (target ≤ 90 days) | Magic-link auth tables |
| White-glove staging files | Delete after successful load or POC close (target ≤ 30 days) | Local/ops copies — do not keep indefinitely |
| Backups | Per Neon / provider backup window | Restore tests under [P12](./P12_backup_and_restore.md); honest lag after deletion |
| Application / deploy logs | Provider defaults (Vercel, Railway) | Avoid logging secrets or full Confidential dumps |
| AI prompt / debug logs (Confidential) | ≤ 30 days, then delete or truncate of Confidential content | Debug/troubleshooting only; not the system of record for numbers; see P15 §5 |
| Billing records | Per Stripe + legal/tax needs | Stripe is system of record for payments |
| Security / IR records | ≥ 1 year or longer if investigation open | Timeline notes, access reviews |
| Marketing CMS (Sanity) | While published / needed | Boundary TBD if customer-named |

Contractual retention windows: see consolidated **Customer DPA / MSA** action item in [../PROGRESS.md](../PROGRESS.md) and risk **R16** in [P10](./P10_risk_assessment.md) — do not invent signed terms here.

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
| Executive sponsor | Matt Justice | 2026-07-27 |

---

_End of APPROVED P08_
