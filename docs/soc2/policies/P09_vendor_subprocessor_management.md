# Vendor / Subprocessor Management Policy

> **STATUS: APPROVED** — Effective 2026-07-27. Approved by Matt Justice (executive sponsor).  
> Not legal advice. Not evidence of SOC 2 certification. Approving policies ≠ SOC 2 certified; open evidence items remain. SMPL is **not** SOC 2 certified until a CPA Type I report is in hand.

| Field | Value |
|-------|--------|
| Policy ID | P09 |
| Owner | Matt Justice (Security owner) |
| Applies to | Vendors that process or store customer data or production infrastructure |
| Related criteria | Security (CC9); Confidentiality |
| Version | 1.0 |
| Effective date | 2026-07-27 |
| Last expanded | 2026-07-26 |

---

## 1. Purpose

Ensure material vendors/subprocessors are inventoried, reviewed, and documented before (or promptly after) they process customer data — sized for a small SaaS that relies on managed cloud providers.

## 2. Inventory

Maintain [../02_subprocessors.md](../02_subprocessors.md). Current named processors include:

| Vendor | Role |
|--------|------|
| Vercel | Customer web app / edge |
| Railway | API / workers |
| Neon | Postgres warehouse + auth |
| Resend | Transactional email (magic links) |
| Anthropic | LLM commentary API |
| Stripe | Billing |
| GitHub | Source control / CI |
| Sanity | CMS (boundary TBD if customer-named) |

Conditional vendors (OpenAI fallback, APM, analytics) are added only if live in production.

## 3. Onboarding a new subprocessor

1. Document purpose, data categories, and region (if known).
2. Prefer vendors with SOC 2 / ISO reports; collect under NDA when available (store **outside** git).
3. Update subprocessors list and customer-facing notice path (DPA exhibit / security pack) **before** or promptly after go-live.
4. Security owner (Matt Justice) approves material new processors.
5. For AI vendors: confirm keys stay on API only; prompt data categories documented ([P06](./P06_data_classification_and_handling.md)).

## 4. Ongoing review

- At least **annually** for material processors, or on material change (region, product use, breach news).
- Track “vendor report collected?” in the subprocessors table.
- Remove unused vendors from the active list when confirmed unused.
- **[!]** Confirm regions / unused vendors / whether OpenAI is live (Week 2–3 checklist).

## 5. Customer commitments

- Customer DPA / MSA subprocessor language is part of the consolidated **Customer DPA / MSA** legal workstream ([../PROGRESS.md](../PROGRESS.md); [P10](./P10_risk_assessment.md) R16) — do not invent signed DPA terms in this policy.
- Sales language: list known processors honestly; never claim SMPL is SOC 2 certified; do not overstate vendor certifications without a collected report.

## 6. Explicitly not subprocessors (typical)

| Party | Why |
|-------|-----|
| Customer’s NetSuite / Salesforce / ERP / warehouse | Customer-controlled source systems; SMPL reads data they provide |
| Board recipients of customer-exported files | Customer-controlled distribution |

## 7. Evidence

| Artifact | Location |
|----------|----------|
| Named list | [../02_subprocessors.md](../02_subprocessors.md) |
| Vendor reports | Local/NDA folder (not in git) — **[!]** collect before Type I |
| Approvals | This policy approval + decision notes |

## 8. Approval

| Approver | Signature / name | Date |
|----------|------------------|------|
| Executive sponsor | Matt Justice | 2026-07-27 |

---

_End of APPROVED P09_
