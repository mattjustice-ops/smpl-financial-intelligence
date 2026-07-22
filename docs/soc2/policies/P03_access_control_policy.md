# Access Control Policy

> **STATUS: DRAFT — NOT APPROVED**  
> Template for SOC 2 Type I readiness. Not company policy until approved.  
> Not legal advice. Not evidence of SOC 2 compliance.

| Field | Value |
|-------|--------|
| Policy ID | P03 |
| Owner | Security owner |
| Applies to | All systems that store or process customer data or production secrets |
| Related criteria | Security (CC6); Confidentiality |
| Version | 0.1-draft |
| Effective date | _TBD on approval_ |

---

## 1. Purpose

Ensure only authorized individuals access SMPL production systems and customer data, with least privilege and MFA on admin paths.

## 2. Systems in scope

At minimum (see inventory template): GitHub, Vercel, Railway, Neon, Sanity, Stripe, Resend, Anthropic console, corporate email/IdP, Ops/privileged DB paths, compliance platform when chosen. Product auth: Auth.js magic link + org membership (`organization_id` multi-tenant model).

## 3. Requirements

1. **Unique accounts** — no shared logins for systems touching customer data.
2. **MFA** — enforced on admin/cloud accounts (GitHub, Vercel, Railway, Neon, email/IdP, Stripe, etc.).
3. **Least privilege** — grant only what the role requires; prefer read-only for white-glove where possible.
4. **Inventory** — maintain [../03_access_inventory_template.md](../03_access_inventory_template.md); who has access, why, MFA status.
5. **Joiner / mover / leaver** — grant on approval; revoke **same day** on offboarding or role change that removes need.
6. **Periodic review** — at least quarterly; dated sign-off is audit evidence.
7. **Secrets** — production secrets only in provider env/secret stores; not in git.
8. **Privileged / white-glove** — named operators; documented justification; revoke after POC/ticket/offboarding.

## 4. Customer (end-user) access

- Org-scoped access via product auth; customer SSO is backlog and not a Type I blocker if scoped honestly.
- Tenant isolation: Org A must not read Org B data (engineering evidence required).

## 5. Encryption (document reliance)

- In transit: TLS on edge/API.
- At rest: managed Postgres (Neon) and provider defaults — document configuration + provider controls.

## 6. Evidence artifacts

| Control | Example evidence |
|---------|------------------|
| MFA | Console screenshots or compliance-platform status |
| Inventory / review | Dated spreadsheet + reviewer sign-off |
| Offboarding | Completed revoke checklist |

## 7. Approval

| Approver | Signature / name | Date |
|----------|------------------|------|
| Executive sponsor | _DRAFT — not signed_ | |

---

_End of DRAFT P03_
