# Data Classification & Handling Policy

> **STATUS: DRAFT — NOT APPROVED**  
> High-priority stub expanded for Type I readiness. Not company policy until approved.  
> Not legal advice. Not evidence of SOC 2 compliance.

| Field | Value |
|-------|--------|
| Policy ID | P06 |
| Owner | Matt Justice (Security owner) |
| Applies to | All personnel handling SMPL or customer data |
| Related criteria | Confidentiality; Security |
| Version | 0.1-draft |
| Effective date | _TBD on approval_ |
| Created | 2026-07-22 |

---

## 1. Purpose

Classify data so it is handled, stored, and shared appropriately — especially customer financial warehouse data.

## 2. Classification levels

| Level | Examples | Handling |
|-------|----------|----------|
| **Public** | Marketing site copy, public blog, published brand assets | No special controls beyond brand accuracy |
| **Internal** | Internal docs, non-customer ops notes, non-secret configs | Company accounts only; no public repos for sensitive internals |
| **Confidential** | Customer financial facts, org membership, board/close exports, support tickets with customer metrics | Need-to-know; tenant isolation; no unsanctioned AI paste; encrypted in transit/at rest via providers |
| **Restricted / secrets** | Production DB URLs, API keys, Auth secrets, Stripe keys, break-glass credentials | Env/secret stores only; MFA on admin; rotate on exposure |

## 3. Customer financial data (Confidential)

- Stored in Neon (multi-tenant `organization_id` model).
- Accessible to authorized org users via the product; privileged ops only via named operators (Matt Justice).
- **No GL/ERP write-back** — SMPL reads/reconciles; does not write to customer source systems.
- Exports (Excel, decks) remain Confidential; customer controls downstream distribution.

## 4. Auth & billing data

- Email addresses and session data: Confidential; processed via Auth.js + Resend + session stores.
- Payment card data: Stripe; SMPL does not store full PAN.

## 5. AI / LLM prompts

- Prefer aggregated / freeze context; minimize raw PII in prompts.
- Keys on API only (Railway). Align with future P15 when drafted.
- AI output is not the system of record for numbers.

## 6. Handling rules (summary)

1. Label or treat by default: when unsure, treat as Confidential.
2. Do not commit Confidential or Restricted data to git.
3. Share externally only under NDA/contract or customer direction.
4. Retention/deletion: see [P08](./P08_retention_and_deletion.md).

## 7. Approval

| Approver | Signature / name | Date |
|----------|------------------|------|
| Executive sponsor | _DRAFT — not signed — Matt Justice must approve_ | |

---

_End of DRAFT P06_
