# Data Classification & Handling Policy

> **STATUS: APPROVED** — Effective 2026-07-27. Approved by Matt Justice (executive sponsor).  
> Not legal advice. Not evidence of SOC 2 certification. Approving policies ≠ SOC 2 certified; open evidence items remain. SMPL is **not** SOC 2 certified until a CPA Type I report is in hand.

| Field | Value |
|-------|--------|
| Policy ID | P06 |
| Owner | Matt Justice (Security owner) |
| Applies to | All personnel handling SMPL or customer data |
| Related criteria | Confidentiality; Security |
| Version | 1.0 |
| Effective date | 2026-07-27 |
| Last expanded | 2026-07-26 |

---

## 1. Purpose

Classify data so it is handled, stored, and shared appropriately — especially customer financial warehouse data on a B2B SaaS FP&A platform.

## 2. Scope

Applies to data in or flowing through the production system boundary ([../01_system_boundary.md](../01_system_boundary.md)): Neon warehouse, Auth.js/org data, Vercel/Railway runtime and logs, Resend, Stripe metadata, Anthropic prompts, Sanity content (if customer-named), and privileged ops staging files.

## 3. Classification levels

| Level | Examples | Handling |
|-------|----------|----------|
| **Public** | Marketing site copy, public blog, published brand assets | No special controls beyond brand accuracy |
| **Internal** | Internal docs, non-customer ops notes, non-secret configs | Company accounts only; no public repos for sensitive internals |
| **Confidential** | Customer financial facts, org membership, board/close exports, support tickets with customer metrics, white-glove staging loads | Need-to-know; tenant isolation; no unsanctioned AI paste; encrypted in transit/at rest via providers |
| **Restricted / secrets** | Production DB URLs, API keys, Auth secrets, Stripe keys, break-glass credentials | Env/secret stores only (Vercel, Railway); MFA on admin; rotate on exposure |

**Default:** when unsure, treat as **Confidential**.

## 4. Customer financial data (Confidential)

- Stored in Neon under a multi-tenant `organization_id` model.
- Accessible to authorized org users via the product; privileged ops only via named operators (currently Matt Justice) — see [P07](./P07_customer_data_confidentiality_procedures.md).
- **No GL/ERP write-back** — SMPL reads/reconciles; does not write to customer source systems. Future connectors are **read-only**.
- Exports (Excel, decks) remain Confidential; customer controls downstream distribution.

## 5. Auth & billing data

- Email addresses and session data: Confidential; processed via Auth.js + Resend + session stores.
- Payment card data: Stripe; SMPL does not store full PAN.
- Magic-link email compromise is an account risk — MFA on corporate email/IdP is required for admin paths ([P03](./P03_access_control_policy.md)).

## 6. AI / LLM prompts

- Prefer aggregated / freeze context; minimize raw PII in prompts.
- Anthropic API keys on Railway (API) only — never in browser, Vercel client env, or static exports.
- AI output is not the system of record for numbers.
- Do not paste production Confidential data into consumer AI tools unless explicitly approved ([P02](./P02_acceptable_use_policy.md)).
- Align with **[P15](./P15_ai_llm_data_handling.md)** (AI / LLM Data Handling) — **Draft — ready for approval** (not yet approved).

## 7. Handling rules

1. Label or treat by default classification above.
2. Do not commit Confidential or Restricted data to git (including sample dumps with real customer facts).
3. Share externally only under NDA/contract or customer direction.
4. Prefer sanitized data in demos, tickets, and screenshots.
5. Retention/deletion: [P08](./P08_retention_and_deletion.md).
6. Encryption in transit (TLS at edge/API) and at rest (Neon / provider defaults) — document reliance; collect vendor reports under NDA when available ([P09](./P09_vendor_subprocessor_management.md)).

## 8. Evidence

| Control | Example evidence |
|---------|------------------|
| Classification in practice | This policy + onboarding acknowledgement (P02) |
| Secrets hygiene | Spot-check: no secrets in git; env stores used |
| AI key placement | Railway env only |

## 9. Approval

| Approver | Signature / name | Date |
|----------|------------------|------|
| Executive sponsor | Matt Justice | 2026-07-27 |

---

_End of APPROVED P06_
