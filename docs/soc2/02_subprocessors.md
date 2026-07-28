# Subprocessors (named list)

Vendors that process or store customer data (or auth-related personal data) in the course of delivering SMPL. Use for DPA exhibits, security questionnaires, and SOC 2 vendor evidence.

Collect each vendor’s SOC 2 / ISO report under NDA where available. Review cadence: at least annually for material processors, or on material change ([P09](./policies/P09_vendor_subprocessor_management.md)).

Parent: [../SOC2_TYPE1_KICKOFF.md](../SOC2_TYPE1_KICKOFF.md) · Boundary: [01_system_boundary.md](./01_system_boundary.md) · Scoreboard: [PROGRESS.md](./PROGRESS.md)

**Status (2026-07-28):** Named Customer Data list locked from Matt Q1–Q10. **Neon = AWS us-east-1**; **other vendor regions remain TBD** (do not invent). Sanity / HubSpot / OpenAI / APM **not** on product Customer Data exhibit. **Not** SOC 2 certified.

---

## Active Customer Data subprocessors (production product DPA exhibit)

| Vendor | Purpose | Data typically involved | Region / notes | Vendor report collected? |
|--------|---------|-------------------------|----------------|--------------------------|
| **Vercel** | Host customer-facing Next.js app / edge (`www.smpl-ai.com`, project `smpl-financial-intelligence`) | Session cookies, app traffic, env-held secrets | **TBD** — confirm plan / deployment region in Vercel console | [ ] |
| **Railway** | Host FastAPI (`sfi-api-production`) | API traffic, app logs, env-held secrets (incl. LLM keys) | **TBD** — confirm service region in Railway console | [ ] |
| **Neon** | Managed Postgres (`smpl-auth-prod` / branch `production`) | Customer financial facts, auth/org data | **AWS us-east-1** — confirmed Matt Q5 (2026-07-28); restore evidence `*.us-east-1.aws.neon.tech` | [ ] |
| **Resend** | Transactional email (magic links, notifications) | Email addresses, message content | **TBD** | [ ] |
| **Anthropic** | LLM API for AI narrative / commentary | Prompt context derived from engine outputs (may include customer metrics) | Keys on Railway only; not in browser. Processing region **TBD** | [ ] |
| **Stripe** | Billing / subscriptions | Billing contact, payment metadata (card data via Stripe) | **TBD** | [ ] |
| **GitHub** | Source control, CI (may hold secrets config, not customer warehouse) | Code, CI logs; avoid customer dumps in repos | **TBD** / provider multi-region | [ ] |

**Auth.js** is application software running on Vercel — not a separate subprocessor vendor.

Matt Q10 **NO** (2026-07-28): no other production vendors process Customer Data beyond this known stack.

---

## Infrastructure / marketing (not Customer Data subprocessors for product DPA)

| Vendor | Purpose | Status |
|--------|---------|--------|
| **Squarespace** | DNS / domain admin for `smpl-ai.com` | **DNS-only** (Matt Q8 **YES** 2026-07-28). Omit from DPA Customer Data exhibit; still inventoriable for access |
| **Sanity** | Marketing CMS (blog / glossary / studio) — project `sda23ulo`, dataset `production` | **Outside Type I product boundary** (Matt Q1 **NO**). Marketing/website vendor only — not Customer Data subprocessor for product DPA. Region **TBD** if ever listed for questionnaires |
| **HubSpot** | SMPL sales CRM / request-quote (prospect data) | **Sales CRM only** (Matt Q7 **NO**) — not on customer product DPA exhibit; may appear on security questionnaires as org tool |

---

## Explicitly unused / do not list on product DPA

| Party | Why |
|-------|-----|
| **OpenAI** | **Not live** on production Railway (Matt Q2 **NO** 2026-07-28). Code-only fallback — omit from external Customer Data list until live |
| **Error / APM / product analytics** (e.g. Sentry, PostHog) | **None** live in prod app with request/user context (Matt Q6 **NO**) |
| Invented “US-only” claims for Vercel/Railway/etc. | Regions **TBD** except Neon us-east-1 — do not promise geography without console confirmation |

---

## Non-prod (not Type I production system)

| Environment | Status |
|-------------|--------|
| Staging / Preview (`sfi-api-staging`, Vercel Preview, related non-prod) | **Exists**; holds **no Customer Data** (Matt Q3 2026-07-28). Out of Type I production system; still under change/access policy |

---

## Explicitly not subprocessors (typical)

| Party | Why |
|-------|-----|
| Customer’s NetSuite / Salesforce / ERP / CRM | Customer’s systems; SMPL is the processor of data they provide |
| End-customer’s board recipients of exported files | Customer-controlled distribution of exports |

---

## Region confirmation checklist

| Vendor | Confirmed region / note | Confirmed by / date |
|--------|-------------------------|---------------------|
| Neon | **AWS us-east-1** | Matt Q5 **YES** 2026-07-28 (evidence 2026-07-27) |
| Vercel | **TBD** | |
| Railway | **TBD** | |
| Resend | **TBD** | |
| Anthropic | **TBD** | |
| Stripe | **TBD** | |
| GitHub | **TBD** / multi-region OK | |
| Sanity (marketing only) | **TBD** — not on product DPA | Matt Q1 **NO** (boundary) |

---

## Change log

| Date | Change | Owner |
|------|--------|-------|
| 2026-07-22 | Initial named list from SMPL stack; regions marked for Matt confirm | Kickoff |
| 2026-07-28 | Aligned to production hosts; Neon us-east-1 from restore evidence; OpenAI/HubSpot/APM/staging conditional; no invented regions | Agent (Week 2 vendors) |
| 2026-07-28 | **Matt Q1–Q10 locked** — Sanity/HubSpot off product DPA; OpenAI/APM unused; staging exists (no Customer Data); Neon us-east-1 confirmed; other regions remain TBD | Matt Justice (answers); Agent (docs) |
