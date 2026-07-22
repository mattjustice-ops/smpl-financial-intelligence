# Vendor / Subprocessor Management Policy

> **STATUS: DRAFT — NOT APPROVED**  
> High-priority stub for Type I readiness. Not company policy until approved.  
> Not legal advice. Not evidence of SOC 2 compliance.

| Field | Value |
|-------|--------|
| Policy ID | P09 |
| Owner | Matt Justice (Security owner) |
| Applies to | Vendors that process or store customer data or production infrastructure |
| Related criteria | Security (CC9); Confidentiality |
| Version | 0.1-draft |
| Effective date | _TBD on approval_ |
| Created | 2026-07-22 |

---

## 1. Purpose

Ensure material vendors/subprocessors are inventoried, reviewed, and documented before (or promptly after) they process customer data.

## 2. Inventory

Maintain [../02_subprocessors.md](../02_subprocessors.md). Current named processors include: Vercel, Railway, Neon, Resend, Anthropic, Stripe, GitHub, Sanity (boundary TBD).

## 3. Onboarding a new subprocessor

1. Document purpose, data categories, and region (if known).
2. Prefer vendors with SOC 2 / ISO reports; collect under NDA when available.
3. Update subprocessors list and customer-facing notice path (DPA exhibit / security pack) **before** or promptly after go-live.
4. Security owner (Matt) approves material new processors.

## 4. Ongoing review

- At least **annually** for material processors, or on material change (region, product use, breach news).
- Track “vendor report collected?” in the subprocessors table.
- Remove unused vendors from the active list when confirmed unused.

## 5. Customer commitments

- Customer DPA / MSA language for subprocessors is a **[!]** legal item — do not invent signed DPA terms in this draft.
- Sales language: list known processors honestly; do not claim certifications SMPL or vendors lack.

## 6. Evidence

| Artifact | Location |
|----------|----------|
| Named list | [../02_subprocessors.md](../02_subprocessors.md) |
| Vendor reports | Local/NDA folder (not in git) — **[!]** collect |
| Approvals | This policy approval + decision notes |

## 7. Approval

| Approver | Signature / name | Date |
|----------|------------------|------|
| Executive sponsor | _DRAFT — not signed — Matt Justice must approve_ | |

---

_End of DRAFT P09_
