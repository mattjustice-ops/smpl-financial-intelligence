# Access Control Policy

> **STATUS: APPROVED** — Effective 2026-07-27. Approved by Matt Justice (executive sponsor).  
> Not legal advice. Not evidence of SOC 2 certification. Approving policies ≠ SOC 2 certified; open evidence items remain. SMPL is **not** SOC 2 certified until a CPA Type I report is in hand.

| Field | Value |
|-------|--------|
| Policy ID | P03 |
| Owner | Matt Justice (Security owner) |
| Applies to | All systems that store or process customer data or production secrets |
| Related criteria | Security (CC6); Confidentiality |
| Version | 1.0 |
| Effective date | 2026-07-27 |
| Last expanded | 2026-07-26 |

---

## 1. Purpose

Ensure only authorized individuals access SMPL production systems and customer data, with least privilege and MFA on admin paths.

## 2. Systems in scope

At minimum (see [../03_access_inventory_template.md](../03_access_inventory_template.md)):

| System | Typical privileged use |
|--------|------------------------|
| GitHub | Org/repo admin, merge to `main`, secrets config |
| Vercel | Frontend deploy, env vars |
| Railway | API deploy, env vars, service logs |
| Neon | Postgres admin, branches, connection strings |
| Sanity | CMS project admin (if customer-named content) |
| Stripe | Billing admin |
| Resend | Email sending / domain |
| Anthropic | API keys / console |
| Corporate email / IdP | Identity, magic-link delivery |
| Ops / white-glove tooling | Tenant loads, privileged support |
| Direct DB / break-glass | Emergency data access |
| Domain DNS / registrar | smpl-ai.com and related |

Product auth: Auth.js **magic link** + org membership (`organization_id` multi-tenant model). Customer SSO is backlog and not a Type I blocker if scoped honestly.

## 3. Requirements

1. **Unique accounts** — no shared logins for systems touching customer data. **Confirmed 2026-07-26:** no shared prod passwords.
2. **MFA** — enforced on admin/cloud accounts listed above. **[x]** Primary consoles verified 2026-07-26 (GitHub, Vercel, Railway, Neon, email/IdP, Stripe, Sanity via Google IdP, Resend, Anthropic via Google IdP — not Anthropic-native TOTP; Squarespace DNS). Ops/break-glass = same MFA as Neon/Railway (solo; no separate login).
3. **Least privilege** — grant only what the role requires; prefer read-only for white-glove where possible.
4. **Inventory** — maintain the access inventory; who has access, why, MFA status (keep MFA column current as Matt verifies remaining rows).
5. **Joiner / mover / leaver** — grant on approval; revoke **same day** on offboarding or role change that removes need.
6. **Periodic review** — at least quarterly; dated sign-off is audit evidence.
7. **Secrets** — production secrets only in provider env/secret stores (Vercel, Railway); not in git.
8. **Privileged / white-glove** — named operators (currently Matt Justice); documented justification; revoke after POC/ticket/offboarding.

## 4. Customer (end-user) access

- Org-scoped access via product auth; invites/seats control who joins an org.
- Tenant isolation: Org A must not read Org B data (engineering evidence required before Type I — test plan + results).
- Passwordless magic link: treat email compromise as account risk; MFA on corporate email/IdP is critical.

## 5. Encryption (document reliance)

- **In transit:** TLS on edge/API (Vercel, Railway).
- **At rest:** managed Postgres (Neon) and provider defaults — document configuration + provider controls; collect vendor reports under NDA when available.
- Card data: handled by Stripe; SMPL does not store full PAN.

## 6. Evidence artifacts

| Control | Example evidence |
|---------|------------------|
| MFA | Console screenshots or compliance-platform status — cloud + DNS done 2026-07-26 (Anthropic via Google IdP); ops/break-glass = Neon/Railway MFA |
| Inventory / review | Dated inventory + reviewer sign-off |
| Offboarding | Completed revoke checklist |
| Tenant isolation | Test results Org A ≠ Org B |

## 7. Current ownership note

As of 2026-07-26, Matt Justice holds executive, security, engineering, and ops/CS privileged-access ownership. Access inventory lists Matt as account owner; MFA verified on primary cloud consoles (including Anthropic via Google IdP and Squarespace DNS); ops/break-glass covered by Neon/Railway MFA (solo; no separate login).

## 8. Approval

| Approver | Signature / name | Date |
|----------|------------------|------|
| Executive sponsor | Matt Justice | 2026-07-27 |

---

_End of APPROVED P03_
