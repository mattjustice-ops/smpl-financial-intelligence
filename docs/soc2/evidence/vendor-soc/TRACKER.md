# Vendor SOC / ISO report tracker

**Owner:** Matt Justice  
**Scaffold created:** 2026-07-29  
**Public research pass:** 2026-07-29 (agent — no Matt console / no Allow)  
**Collection status:** **not complete** — P0 Trust Centers researched; **no Type II reports marked received**. Public Stripe SOC 3 summary only (see notes). Readiness only — not SOC 2 certified.

How to store files: [README.md](./README.md) · Request copy: [REQUEST_TEMPLATES.md](./REQUEST_TEMPLATES.md) · Inventory: [../../02_subprocessors.md](../../02_subprocessors.md) · Research notes: [PUBLIC_RESEARCH_2026-07-29.md](./PUBLIC_RESEARCH_2026-07-29.md)

**Status values:** `not started` | `researched` | `public summary available` | `requested` | `nda signed` | `received` | `reviewed` | `n/a` | `blocked`

> **Honesty rule:** `public summary available` = marketing page and/or public SOC 3 / ISO directory listing only. **Never** treat that as Type II `received`. `received` / `reviewed` require a private-store file (or documented portal-only review date) for the **target** report type.

---

## P0 — Product Customer Data subprocessors

| Vendor | Report type (target) | Request URL / portal | Status | Owner | Notes |
|--------|----------------------|----------------------|--------|-------|-------|
| **Vercel** | SOC 2 Type II (Security, Confidentiality, Availability claimed) | [Trust Center](https://security.vercel.com/) · [Compliance docs](https://vercel.com/docs/security/compliance) · help: privacy@vercel.com | researched | Matt | **2026-07-29 public research:** Docs claim SOC 2 Type II (Sec/Conf/Avail) + ISO 27001:2022 ([Schellman cert directory](https://www.schellman.com/certificate-directory?certificateNumber=1868222-1) — public listing, not the SOC PDF). Trust Center is SafeBase — **Get access** / login for private reports (SOC 2, pentest, PCI packs). No Type II PDF obtained. Matt: open Trust Center → Get access → NDA/request → download Type II to private store. |
| **Railway** | SOC 2 Type II (+ SOC 3 public summary often available) | [Trust Center](https://trust.railway.com/) · [Compliance docs](https://docs.railway.com/enterprise/compliance) | researched | Matt | **2026-07-29 public research:** Docs + Railway blog: SOC 2 Type II + SOC 3; **SOC 3 = public download**; Type II / pentest / HIPAA = Trust Center request (sign in with Railway account email). Agent did **not** pull SOC 3 binary (SafeBase UI). No Type II obtained. Matt: trust.railway.com → download public SOC 3 (optional) + request Type II. |
| **Neon** | SOC 2 Type II; ISO 27001 / 27701 (as available) | [Trust Center](https://trust.neon.com/) · [Compliance docs](https://neon.com/docs/security/compliance) · sales@neon.tech | researched | Matt | **2026-07-29 public research:** Trust Center banner: **SOC 2 available to paid customers only**; access requests reviewed ~2 business days. Docs claim SOC 2 Type I/II, SOC 3, ISO 27001/27701. Neon security page: SOC 3 summary without NDA via Trust Center (still portal). No Type II obtained. Region for SMPL: AWS us-east-1. Matt: sign in as paid customer → request SOC 2 (+ ISO if listed). |
| **Stripe** | SOC 2 Type II (+ SOC 1); public SOC 3 | [Security overview](https://docs.stripe.com/security) · Dashboard [Compliance](https://dashboard.stripe.com/settings/compliance) / [Documents](https://dashboard.stripe.com/settings/documents) · [Public SOC 3 PDF](https://docs.stripecdn.com/ebe9bebbdc5210a59ca18de4917ff3b152961a83fa3a98fbb81c758792472389.pdf) | public summary available | Matt | **2026-07-29:** Public **SOC 3** linked from Stripe security docs — period **2024-10-01 → 2025-09-30** (Sec/Avail/Conf); auditor Coalfire. Saved gitignored copy: `private/2026-07-29_stripe_soc3_2024-10-2025-09.pdf` (summary only — **not** Type II). Full SOC 1/SOC 2 Type II = Dashboard / request under NDA. Do not commit NDA PDF. |
| **Anthropic** | SOC 2 Type II; ISO 27001; ISO 42001 (as available) | [Trust Portal](https://trust.anthropic.com/) · [Certifications FAQ](https://privacy.claude.com/en/articles/10015870-what-certifications-has-anthropic-obtained) | researched | Matt | **2026-07-29 public research:** FAQ (updated ~2026-03-16) claims SOC 2 Type I & II, ISO 27001:2022, ISO/IEC 42001:2023, HIPAA-ready BAA for commercial products. Trust Portal fetch failed / needs interactive access — **report downloads require Matt login**. Align with [P15](../../policies/P15_ai_llm_data_handling.md). No report PDF obtained. |
| **Resend** | SOC 2 Type II | [SOC 2 page](https://resend.com/security/soc-2) · Account **Settings → Documents** ([how-to](https://resend.com/docs/knowledge-base/downloading-documents)) | researched | Matt | **2026-07-29 public research:** Marketing/docs claim SOC 2 Type II; period **2025-02-01 → 2026-02-01**; auditor Advantage Partners (+ Vanta). **Full report only via logged-in** [Settings → Documents](https://resend.com/settings/documents). No PDF obtained without Matt login. |

---

## P1 — CI / source (not customer warehouse)

| Vendor | Report type (target) | Request URL / portal | Status | Owner | Notes |
|--------|----------------------|----------------------|--------|-------|-------|
| **GitHub** | SOC 2 Type II / SOC 3 / ISO 27001 (plan-dependent) | [Trust Center](https://github.com/trust-center/) · Org **Settings → Security → Compliance** ([docs](https://docs.github.com/en/organizations/keeping-your-organization-secure/managing-security-settings-for-your-organization/accessing-compliance-reports-for-your-organization)) | researched | Matt | **2026-07-29 public research:** Org Compliance page can expose SOC 3, CSA CAIQ, ISO/IEC 27001:2022 for download when available to the org plan. Fuller SOC 2 often **Enterprise Cloud**. Public trust-center hub is FAQ/marketing — not a self-serve Type II dump. Matt: Org Settings → Security → Compliance → Download/View. Note plan limits honestly. |

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

## Matt-only clicks remaining (P0 + GitHub)

When Matt is back (console login / Allow as needed) — **exact path per vendor:**

1. **Vercel** — [security.vercel.com](https://security.vercel.com/) → **Get access** → complete NDA/access → download **SOC 2 Type II** → store outside git (`~/Documents/SMPL/soc2/vendor-reports/` or `private/`).
2. **Railway** — [trust.railway.com](https://trust.railway.com/) → sign in (Railway account email) → download public **SOC 3** (optional) + request/download **SOC 2 Type II**.
3. **Neon** — [trust.neon.com](https://trust.neon.com/) → sign in as **paid** customer → request **SOC 2** (and ISO if listed) → wait ~2 business days if gated.
4. **Stripe** — Dashboard → **Settings → Compliance / Documents** → request/download **SOC 2 Type II** (and SOC 1 if needed). Public SOC 3 already noted; not a substitute for Type II in auditor pack.
5. **Anthropic** — [trust.anthropic.com](https://trust.anthropic.com/) → sign in (Google IdP) → request/download SOC 2 + ISO packs.
6. **Resend** — [resend.com/settings/documents](https://resend.com/settings/documents) → download **SOC 2** Type II (confirm period still current).
7. **GitHub (P1)** — Org → **Settings → Security → Compliance** → Download/View available reports; note if Type II missing on current plan.

After each download: update this tracker to `received` / `reviewed` + date + period. Never commit NDA PDFs.

---

## Progress log

| Date | Event |
|------|-------|
| 2026-07-29 | Scaffold: README, TRACKER, REQUEST_TEMPLATES. All P0–P2 rows **not started**. No PDFs collected. |
| 2026-07-29 | **Public research pass (no Matt console):** P0 + GitHub Trust Centers / docs reviewed. Statuses → `researched` or `public summary available` (Stripe SOC 3 only). **No Type II received.** Stripe public SOC 3 saved under gitignored `private/`. Notes: [PUBLIC_RESEARCH_2026-07-29.md](./PUBLIC_RESEARCH_2026-07-29.md). |

---

_Update this file when a request is sent or a report is reviewed. Never mark `received` / `reviewed` without a private-store file (or documented portal-only review date)._
