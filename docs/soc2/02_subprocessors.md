# Subprocessors (named list)

Vendors that process or store customer data (or auth-related personal data) in the course of delivering SMPL. Use for DPA exhibits, security questionnaires, and SOC 2 vendor evidence.

Collect each vendor’s SOC 2 / ISO report under NDA where available. Review cadence: at least annually for material processors, or on material change ([P09](./policies/P09_vendor_subprocessor_management.md)).

Parent: [../SOC2_TYPE1_KICKOFF.md](../SOC2_TYPE1_KICKOFF.md) · Boundary: [01_system_boundary.md](./01_system_boundary.md) · Scoreboard: [PROGRESS.md](./PROGRESS.md)

**Status (2026-07-28):** Named list aligned to **known-good production** stack. Regions left **TBD** unless confirmed from evidence/console. Do **not** publish externally until Matt answers Q1–Q10 in the boundary doc. **Not** SOC 2 certified.

---

## Active / expected subprocessors (production)

| Vendor | Purpose | Data typically involved | Region / notes | Vendor report collected? |
|--------|---------|-------------------------|----------------|--------------------------|
| **Vercel** | Host customer-facing Next.js app / edge (`www.smpl-ai.com`, project `smpl-financial-intelligence`) | Session cookies, app traffic, env-held secrets | **TBD** — confirm plan / deployment region in Vercel console | [ ] |
| **Railway** | Host FastAPI (`sfi-api-production`) | API traffic, app logs, env-held secrets (incl. LLM keys) | **TBD** — confirm service region in Railway console | [ ] |
| **Neon** | Managed Postgres (`smpl-auth-prod` / branch `production`) | Customer financial facts, auth/org data | **AWS us-east-1** — from restore evidence endpoint hostname (`*.us-east-1.aws.neon.tech`); Matt confirm Q5 | [ ] |
| **Resend** | Transactional email (magic links, notifications) | Email addresses, message content | **TBD** | [ ] |
| **Anthropic** | LLM API for AI narrative / commentary | Prompt context derived from engine outputs (may include customer metrics) | Keys on Railway only; not in browser. Processing region **TBD** | [ ] |
| **Stripe** | Billing / subscriptions | Billing contact, payment metadata (card data via Stripe) | **TBD** | [ ] |
| **GitHub** | Source control, CI (may hold secrets config, not customer warehouse) | Code, CI logs; avoid customer dumps in repos | **TBD** / provider multi-region | [ ] |
| **Sanity** | CMS (blog / glossary / studio) — project `sda23ulo`, dataset `production` | Marketing content; confirm if any customer-named content | Region **TBD**. **Boundary TBD — Matt Q1** (keep on list until NO) | [ ] |

**Auth.js** is application software running on Vercel — not a separate subprocessor vendor.

---

## Infrastructure (usually not “Customer Data” subprocessors)

| Vendor | Purpose | Status |
|--------|---------|--------|
| **Squarespace** | DNS / domain admin for `smpl-ai.com` | Confirmed MFA’d; expect **DNS-only** (Matt Q8). Omit from DPA Customer Data exhibit if YES DNS-only; still inventoriable for access |

---

## Conditional / confirm before publishing externally

| Vendor | Purpose | Status |
|--------|---------|--------|
| **OpenAI** (or other LLM) | Code supports fallback if key set; production deploy docs use **Anthropic** | **TBD — Matt Q2**. Add only if live on production Railway |
| **HubSpot** | SMPL sales CRM / request-quote sync (prospect data) | **TBD — Matt Q7**. Often org tool; may appear on questionnaires |
| Google Workspace / Microsoft 365 | Corporate email / IdP | Org tool; often listed in security questionnaire |
| Error / APM tooling | e.g. Sentry — if enabled with request context | **TBD — Matt Q6** |
| Product analytics | If capturing user PII | **TBD — Matt Q6 / Q10** |
| Staging hosts (`sfi-api-staging`, Vercel Preview, other Neon projects) | Non-prod | **TBD — Matt Q3**. Not the Type I production system; document if they hold Customer Data |

---

## Explicitly unused / do not list (until evidence of use)

| Party | Why |
|-------|-----|
| OpenAI | **Do not list on external DPA** until Matt confirms live in production (Q2) |
| Invented “US-only” claims for Vercel/Railway/etc. | Regions **TBD** — do not promise geography without console confirmation |

---

## Explicitly not subprocessors (typical)

| Party | Why |
|-------|-----|
| Customer’s NetSuite / Salesforce / ERP / CRM | Customer’s systems; SMPL is the processor of data they provide |
| End-customer’s board recipients of exported files | Customer-controlled distribution of exports |

---

## Matt region confirmation checklist (fill — leave TBD if unknown)

| Vendor | Confirmed region / note | Confirmed by / date |
|--------|-------------------------|---------------------|
| Neon | AWS us-east-1 (evidence 2026-07-27) — pending Matt Q5 | |
| Vercel | **TBD** | |
| Railway | **TBD** | |
| Resend | **TBD** | |
| Anthropic | **TBD** | |
| Stripe | **TBD** | |
| Sanity | **TBD** | |
| GitHub | **TBD** / multi-region OK | |

---

## Change log

| Date | Change | Owner |
|------|--------|-------|
| 2026-07-22 | Initial named list from SMPL stack; regions marked for Matt confirm | Kickoff |
| 2026-07-28 | Aligned to production hosts; Neon us-east-1 from restore evidence; OpenAI/HubSpot/APM/staging conditional; no invented regions | Agent (Week 2 vendors) |
