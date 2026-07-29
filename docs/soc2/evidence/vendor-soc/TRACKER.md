# Vendor SOC / ISO report tracker

**Owner:** Matt Justice  
**Scaffold created:** 2026-07-29  
**Collection status:** **not complete** — infrastructure ready; **no reports marked received**. Readiness only — not SOC 2 certified.

How to store files: [README.md](./README.md) · Request copy: [REQUEST_TEMPLATES.md](./REQUEST_TEMPLATES.md) · Inventory: [../../02_subprocessors.md](../../02_subprocessors.md)

**Status values:** `not started` | `requested` | `nda signed` | `received` | `reviewed` | `n/a` | `blocked`

---

## P0 — Product Customer Data subprocessors

| Vendor | Report type (target) | Request URL / portal | Status | Owner | Notes |
|--------|----------------------|----------------------|--------|-------|-------|
| **Vercel** | SOC 2 Type II (Security, Confidentiality, Availability claimed) | [Trust Center](https://security.vercel.com/) · [Compliance docs](https://vercel.com/docs/security/compliance) · help: privacy@vercel.com | not started | Matt | Request SOC 2 via Trust Center NDA/access flow. Do not commit PDF. |
| **Railway** | SOC 2 Type II (+ SOC 3 public summary often available) | [Trust Center](https://trust.railway.com/) · [Compliance docs](https://docs.railway.com/enterprise/compliance) | not started | Matt | Sign in with Railway account email; request full Type II (not only SOC 3). |
| **Neon** | SOC 2 Type II; ISO 27001 / 27701 (as available) | [Trust Center](https://trust.neon.com/) · [Compliance docs](https://neon.com/docs/security/compliance) · sales@neon.tech | not started | Matt | Trust Center: SOC 2 often **paid customers only**; review plan eligibility. Region for SMPL: AWS us-east-1. |
| **Stripe** | SOC 2 Type II (+ SOC 1); public SOC 3 | [Security overview](https://docs.stripe.com/security) · Dashboard [Compliance](https://dashboard.stripe.com/settings/compliance) / [Documents](https://dashboard.stripe.com/settings/documents) · SOC 3 linked from security page | not started | Matt | Full SOC 2 on request / under NDA via Dashboard or support. Public SOC 3 is summary only — still prefer Type II for auditor pack. Do not commit NDA PDF. |
| **Anthropic** | SOC 2 Type II; ISO 27001; ISO 42001 (as available) | [Trust Portal](https://trust.anthropic.com/) · [Certifications FAQ](https://privacy.claude.com/en/articles/10015870-what-certifications-has-anthropic-obtained) | not started | Matt | Request compliance docs via Trust Portal. Align with [P15](../../policies/P15_ai_llm_data_handling.md). |
| **Resend** | SOC 2 Type II | [SOC 2 page](https://resend.com/security/soc-2) · Account **Settings → Documents** ([how-to](https://resend.com/docs/knowledge-base/downloading-documents)) | not started | Matt | Logged-in Documents download for customers. Confirm period still current when pulled. |

---

## P1 — CI / source (not customer warehouse)

| Vendor | Report type (target) | Request URL / portal | Status | Owner | Notes |
|--------|----------------------|----------------------|--------|-------|-------|
| **GitHub** | SOC 2 Type II / SOC 3 / ISO 27001 (plan-dependent) | [Trust Center](https://github.com/trust-center/) · Org **Settings → Security → Compliance** ([docs](https://docs.github.com/en/organizations/keeping-your-organization-secure/managing-security-settings-for-your-organization/accessing-compliance-reports-for-your-organization)) | not started | Matt | Free/org plans may only see a subset (e.g. SOC 3, ISO cert). Enterprise Cloud unlocks fuller SOC 2 downloads — note plan limits honestly if Type II unavailable. |

---

## P2 — Inventory / questionnaires (not product Customer Data DPA)

| Vendor | Report type (target) | Request URL / portal | Status | Owner | Notes |
|--------|----------------------|----------------------|--------|-------|-------|
| **Sanity** | SOC 2 Type II (claimed) | [Security](https://www.sanity.io/security) · contact / sales for formal report ([contact](https://www.sanity.io/contact)) | not started | Matt | Marketing CMS only — **outside** product Type I / DPA exhibit (Matt Q1). Optional for questionnaires. |
| **Squarespace** | SOC 2 (often Enterprise-gated) | [Security](https://www.squarespace.com/security) · [Measures](https://www.squarespace.com/measures) · support / enterprise sales | not started | Matt | DNS-only for `smpl-ai.com` — not Customer Data subprocessor. Collect only if questionnaire asks; expect limited self-serve evidence. |
| **Google** (corporate email / IdP) | SOC 2 / ISO for Google Workspace / Cloud | [Google Cloud compliance](https://cloud.google.com/security/compliance) · [Workspace security](https://workspace.google.com/security/) · admin console compliance resources | not started | Matt | Auth/MFA IdP for several consoles (Anthropic, Sanity). Not a product Customer Data subprocessor for SMPL app data path; useful for access inventory evidence. |

---

## Explicitly deferred / n/a

| Vendor | Status | Notes |
|--------|--------|-------|
| **HubSpot** | n/a (deferred) | Sales CRM only (Matt Q7) — not on product DPA. Revisit if questionnaires demand. |
| **OpenAI** | n/a | Not live in production (Matt Q2). Add if/when live. |
| **Auth.js** | n/a | Library on Vercel — covered by Vercel + app controls, not a separate SOC vendor. |

---

## Progress log

| Date | Event |
|------|-------|
| 2026-07-29 | Scaffold: README, TRACKER, REQUEST_TEMPLATES. All P0–P2 rows **not started**. No PDFs collected. |

---

_Update this file when a request is sent or a report is reviewed. Never mark `received` / `reviewed` without a private-store file (or documented portal-only review date)._
