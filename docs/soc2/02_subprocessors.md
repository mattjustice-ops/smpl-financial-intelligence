# Subprocessors (named list)

Vendors that process or store customer data (or auth-related personal data) in the course of delivering SMPL. Use for DPA exhibits, security questionnaires, and SOC 2 vendor evidence.

Collect each vendor’s SOC 2 / ISO report under NDA where available. Review cadence: at least annually for material processors, or on material change.

Parent: [../SOC2_TYPE1_KICKOFF.md](../SOC2_TYPE1_KICKOFF.md)

---

## Active / expected subprocessors

| Vendor | Purpose | Data typically involved | Region / notes | Vendor report collected? |
|--------|---------|-------------------------|----------------|--------------------------|
| **Vercel** | Host customer-facing Next.js app / edge | Session cookies, app traffic, env-held secrets | Confirm plan region | [ ] |
| **Railway** | Host FastAPI API / workers | API traffic, app logs, env-held secrets | Confirm plan region | [ ] |
| **Neon** | Managed Postgres (warehouse + auth tables) | Customer financial facts, auth/org data | Confirm project region | [ ] |
| **Resend** | Transactional email (magic links, notifications) | Email addresses, message content | | [ ] |
| **Anthropic** | LLM API for AI narrative / commentary | Prompt context derived from engine outputs (may include customer metrics) | Keys on API only; not in browser | [ ] |
| **Stripe** | Billing / subscriptions | Billing contact, payment metadata (card data via Stripe) | | [ ] |
| **GitHub** | Source control, CI (may hold secrets config, not customer warehouse) | Code, CI logs; avoid customer dumps in repos | | [ ] |
| **Sanity** | CMS (blog / glossary / studio) | Marketing content; confirm if any customer-named content | Boundary TBD | [ ] |

---

## Conditional / confirm before publishing externally

| Vendor | Purpose | Status |
|--------|---------|--------|
| OpenAI (or other LLM) | Fallback commentary if used in prod | TBD — add if live |
| Google Workspace / Microsoft 365 | Corporate email / IdP | Org tool; often listed in security questionnaire |
| Error / APM tooling | e.g. Sentry — if enabled with request context | TBD |
| Analytics | Product analytics that may capture user PII | TBD |

---

## Explicitly not subprocessors (typical)

| Party | Why |
|-------|-----|
| Customer’s NetSuite / Salesforce / ERP | Customer’s systems; SMPL is the processor of data they provide |
| End-customer’s board recipients of exported files | Customer-controlled distribution of exports |

---

## Change log

| Date | Change | Owner |
|------|--------|-------|
| | Initial named list from SMPL stack | |
