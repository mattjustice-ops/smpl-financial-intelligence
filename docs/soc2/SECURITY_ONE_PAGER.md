# SMPL.ai — Security one-pager

**Audience:** Customers and prospects (security questionnaires, early diligence).  
**Status:** Draft for internal use / share under NDA as needed.  
**Last updated:** 2026-07-27  
**Owner:** Matt Justice

> **Honest framing:** SMPL is **pursuing SOC 2 Type I** (Security + Availability + Confidentiality). We are **not** SOC 2 certified and do **not** claim “SOC 2 compliant” until an independent CPA firm issues a report.

---

## Product

SMPL.ai is a B2B SaaS financial intelligence platform (FP&A / ARR / close / board export). We help finance teams read and reconcile finance data. **SMPL does not write back to the customer’s GL or ERP.**

---

## Trust & compliance posture

| Topic | Current state |
|-------|----------------|
| SOC 2 | **Readiness in progress** toward Type I (Security + Availability + Confidentiality). Processing Integrity deferred. Privacy not in first engagement. |
| Certification | **None yet** — no CPA report issued |
| Policies | P01–P12 approved internally (2026-07-27); P15 AI/LLM draft in review. Approving policies ≠ SOC 2 certified |
| Compliance platform | Deferred DIY for now (internal docs + scoreboard); revisit if enterprise requires a formal GRC tool or at CPA Type I engagement |

---

## Architecture & tenant isolation

- **Multi-tenant** application model keyed by organization (`organization_id`).
- Customer users access only their organization’s data via authenticated sessions.
- Privileged support / white-glove data loads are limited to named operators and are not a substitute for customer admin access.

*Isolation evidence (Org A cannot read Org B) is part of our readiness workstream — ask for the latest test artifact if required under NDA.*

---

## Authentication

- **Auth.js magic-link** (email) for customer login.
- Organization membership / invites control who can join a tenant.
- Customer SSO is on the product backlog and is **not** required for our current SOC 2 Type I scope narrative.

---

## Encryption & infrastructure (high level)

| Control | Practice |
|---------|----------|
| In transit | TLS to the application and API (hosted on modern cloud edge/API platforms) |
| At rest | Customer data in managed Postgres with provider encryption-at-rest defaults |
| Secrets | Production secrets in host env/secret stores — not in application source |
| Card payments | **Stripe**; SMPL does not store full payment card numbers |

Production stack (named for diligence): **Vercel** (web), **Railway** (API), **Neon** (Postgres), **GitHub** (source/CI). See subprocessors below.

---

## AI / LLM usage

- AI narrative / commentary uses **Anthropic** via API calls from the **backend only**.
- API keys are **not** exposed in the browser or static exports.
- Model output is **not** the system of record for financial numbers; governed engine / warehouse outputs are.
- We minimize unnecessary raw personal data in prompts where practical.

---

## Subprocessors (summary)

Vendors that process or store customer-related data in delivering the service typically include:

| Vendor | Role |
|--------|------|
| Vercel | Host customer-facing application |
| Railway | Host API / application services |
| Neon | Managed Postgres datastore |
| Resend | Transactional email (e.g. magic links) |
| Anthropic | LLM API for commentary features |
| Stripe | Billing / subscriptions |
| GitHub | Source control and CI (code; not customer warehouse dumps) |
| Sanity | Marketing CMS (blog/glossary); confirm if customer-named content applies |

A fuller internal list lives in `docs/soc2/02_subprocessors.md`. Regions and unused vendors are confirmed as part of readiness. Customer DPA / legal exhibit is a separate legal workstream.

---

## Change management (summary)

- Code changes via **GitHub** pull requests.
- Frontend deploys to **Vercel**; API deploys to **Railway**.
- Production promotion is limited to authorized operators.

---

## Incident response

We maintain a draft incident response plan covering detection, containment, recovery, and customer notification when material. Primary security contact: **Matt Justice**.

---

## What we will not claim

- That SMPL is “SOC 2 certified” or “SOC 2 compliant” before a CPA report exists.
- That Processing Integrity (e.g. audited ARR math) is in scope for the first Type I.
- That MFA, restore tests, or vendor-report collection are complete until evidence exists.

---

## Contact

Security / compliance questions: **Matt Justice** (executive sponsor & security owner).

---

_Document control: internal draft aligned with `docs/soc2/PROGRESS.md`. Update when scope or stack changes._
