# Vendor SOC / ISO report tracker

**Owner:** Matt Justice  
**Scaffold created:** 2026-07-29  
**Public research pass:** 2026-07-29 (agent — no Matt console / no Allow)  
**This-week working pack:** [WORKING_PACK_2026-08.md](./WORKING_PACK_2026-08.md)  
**Matt session kit:** [SESSION_CHECKLIST_2026-07-31.md](./SESSION_CHECKLIST_2026-07-31.md) · Review after download: [REVIEW_CHECKLIST.md](./REVIEW_CHECKLIST.md)  
**Collection status:** **not complete** — Railway + Neon + Stripe + Anthropic + Resend Type II **received** (review pending); Vercel access **requested** (waiting). Readiness only — not SOC 2 certified.

How to store files: [README.md](./README.md) · Request copy: [REQUEST_TEMPLATES.md](./REQUEST_TEMPLATES.md) · Inventory: [../../02_subprocessors.md](../../02_subprocessors.md) · Research notes: [PUBLIC_RESEARCH_2026-07-29.md](./PUBLIC_RESEARCH_2026-07-29.md)

**Status values:** `not started` | `researched` | `public summary available` | `requested` | `nda signed` | `received` | `reviewed` | `n/a` | `blocked`

> **Honesty rule:** `public summary available` = marketing page and/or public SOC 3 / ISO directory listing only. **Never** treat that as Type II `received`. `received` / `reviewed` require a private-store file (or documented portal-only review date) for the **target** report type.

---

## P0 — Product Customer Data subprocessors

| Vendor | Report type (target) | Request URL / portal | Status | Next action (Matt) | Owner | Notes |
|--------|----------------------|----------------------|--------|--------------------|-------|-------|
| **Vercel** | SOC 2 Type II (Security, Confidentiality, Availability claimed) | [Trust Center](https://security.vercel.com/) · [Compliance docs](https://vercel.com/docs/security/compliance) · help: privacy@vercel.com | requested | **Waiting** SafeBase / Trust Center approval. When approved → download Type II → `~/Documents/SMPL/soc2/vendor-reports/`. Do **not** mark `received` until PDF exists. | Matt | **2026-08-03 session:** Matt confirmed access **requested / pending approval** — Type II **not** received. Prior research: Docs claim SOC 2 Type II (Sec/Conf/Avail) + ISO 27001:2022 ([Schellman cert directory](https://www.schellman.com/certificate-directory?certificateNumber=1868222-1) — public listing, not the SOC PDF). |
| **Railway** | SOC 2 Type II (+ SOC 3 public summary often available) | [Trust Center](https://trust.railway.com/) · [Compliance docs](https://docs.railway.com/enterprise/compliance) | received | Run [REVIEW_CHECKLIST](./REVIEW_CHECKLIST.md) skim → flip to `reviewed`. | Matt | **2026-08-03:** Matt confirmed Type II + bridge letter in private store (outside git): `~/Documents/SMPL/soc2/vendor-reports/2026-08-03_railway_soc2-type2_period-ending-2025-04-22.pdf` (filename from vendor “4.22.25” report date — period end ~2025-04-22; confirm on cover at review) and `2026-08-03_railway_soc2-bridge-letter_asof-2026-04.pdf`. **Review pending** — not marked `reviewed`. Do not commit PDFs. |
| **Neon** | SOC 2 Type II; ISO 27001 / 27701 (as available) | [Trust Center](https://trust.neon.com/) · [Compliance docs](https://neon.com/docs/security/compliance) · sales@neon.tech | received | Run [REVIEW_CHECKLIST](./REVIEW_CHECKLIST.md) skim → flip to `reviewed`. | Matt | **2026-08-03:** Access granted; Type II **received**. Vendor filename “Databricks Neon SOC 2 Type 2 + HIPAA 2026”; private store (outside git): `~/Documents/SMPL/soc2/vendor-reports/2026-08-03_neon_soc2-type2-hipaa_2026.pdf`. Confirm exact report period on cover at review. **Review pending**. Do not commit PDFs. Region: AWS us-east-1. |
| **Stripe** | SOC 2 Type II (+ SOC 1); public SOC 3 | [Security overview](https://docs.stripe.com/security) · Dashboard [Compliance](https://dashboard.stripe.com/settings/compliance) / [Documents](https://dashboard.stripe.com/settings/documents) · [Public SOC 3 PDF](https://docs.stripecdn.com/ebe9bebbdc5210a59ca18de4917ff3b152961a83fa3a98fbb81c758792472389.pdf) | received | Run [REVIEW_CHECKLIST](./REVIEW_CHECKLIST.md) skim → flip to `reviewed`. | Matt | **2026-08-03:** Type II + bridge letter **received** (current Type II + bridge = target set; previous Type II kept as archive). Private store (outside git): `2026-08-03_stripe_soc2-type2_current.pdf`, `2026-08-03_stripe_soc2-bridge-letter.pdf`, `2026-08-03_stripe_soc2-type2_previous.pdf`. Confirm periods on covers at review. Public SOC 3 still on file separately — not a substitute. **Review pending**. Do not commit PDFs. |
| **Anthropic** | SOC 2 Type II; ISO 27001; ISO 42001 (as available) | [Trust Portal](https://trust.anthropic.com/) · [Certifications FAQ](https://privacy.claude.com/en/articles/10015870-what-certifications-has-anthropic-obtained) | received | Run [REVIEW_CHECKLIST](./REVIEW_CHECKLIST.md) skim → flip to `reviewed`. | Matt | **2026-08-03:** Access granted; **SOC 2 Type II** (required) + SOC 3 (bonus) + CSA STAR L2 (bundled in SOC 2 PDF) **received**. Private store (outside git): `2026-08-03_anthropic_soc2-type2-csa-star-l2_2025.pdf`, `2026-08-03_anthropic_soc3_type2_2025.pdf`. Confirm periods on covers at review. **Review pending**. Do not commit PDFs. |
| **Resend** | SOC 2 Type II | [SOC 2 page](https://resend.com/security/soc-2) · Account **Settings → Documents** ([how-to](https://resend.com/docs/knowledge-base/downloading-documents)) | received | Run [REVIEW_CHECKLIST](./REVIEW_CHECKLIST.md) skim → flip to `reviewed`. Confirm period on cover (marketing claim ~2025-02-01 → 2026-02-01). Optional next: **GitHub** (P1) or wait on **Vercel**. | Matt | **2026-08-03:** Type II **received**. Vendor file `resend-soc-2-type-ii-report.pdf`; private store (outside git): `~/Documents/SMPL/soc2/vendor-reports/2026-08-03_resend_soc2-type2.pdf`. Confirm exact period on cover at review. **Review pending**. Do not commit PDFs. |

---

## P1 — CI / source (not customer warehouse)

| Vendor | Report type (target) | Request URL / portal | Status | Next action (Matt) | Owner | Notes |
|--------|----------------------|----------------------|--------|--------------------|-------|-------|
| **GitHub** | SOC 2 Type II / SOC 3 / ISO 27001 (plan-dependent) | [Trust Center](https://github.com/trust-center/) · Org **Settings → Security → Compliance** ([docs](https://docs.github.com/en/organizations/keeping-your-organization-secure/managing-security-settings-for-your-organization/accessing-compliance-reports-for-your-organization)) | researched | **Bonus after P0:** Org → Settings → Security → Compliance → Download/View; note if Type II missing on plan. | Matt | **2026-07-29 public research:** Org Compliance can expose SOC 3, CSA CAIQ, ISO/IEC 27001:2022 when available. Fuller SOC 2 often **Enterprise Cloud**. No PDF obtained. |

---

## P2 — Inventory / questionnaires (not product Customer Data DPA)

| Vendor | Report type (target) | Request URL / portal | Status | Next action (Matt) | Owner | Notes |
|--------|----------------------|----------------------|--------|--------------------|-------|-------|
| **Sanity** | SOC 2 Type II (claimed) | [Security](https://www.sanity.io/security) · contact / sales for formal report ([contact](https://www.sanity.io/contact)) | not started | Defer until questionnaire asks. | Matt | Marketing CMS only — **outside** product Type I / DPA exhibit (Matt Q1). Optional for questionnaires. |
| **Squarespace** | SOC 2 (often Enterprise-gated) | [Security](https://www.squarespace.com/security) · [Measures](https://www.squarespace.com/measures) · support / enterprise sales | not started | Defer until questionnaire asks. | Matt | DNS-only for `smpl-ai.com` — not Customer Data subprocessor. |
| **Google** (corporate email / IdP) | SOC 2 / ISO for Google Workspace / Cloud | [Google Cloud compliance](https://cloud.google.com/security/compliance) · [Workspace security](https://workspace.google.com/security/) · admin console compliance resources | not started | Optional IdP evidence after P0 session. | Matt | Auth/MFA IdP for several consoles. Not a product Customer Data subprocessor for SMPL app data path. |

---

## Explicitly deferred / n/a

| Vendor | Status | Notes |
|--------|--------|-------|
| **HubSpot** | n/a (deferred) | Sales CRM only (Matt Q7) — not on product DPA. Revisit if questionnaires demand. |
| **OpenAI** | n/a | Not live in production (Matt Q2). Add if/when live. |
| **Auth.js** | n/a | Library on Vercel — covered by Vercel + app controls, not a separate SOC vendor. |

---

## Matt-only clicks remaining (P0 + GitHub)

**This-week pack:** [WORKING_PACK_2026-08.md](./WORKING_PACK_2026-08.md) (targets, store paths, status board, stakeholder language).  
**Executable session:** [SESSION_CHECKLIST_2026-07-31.md](./SESSION_CHECKLIST_2026-07-31.md) (ordered checkboxes + reply format).  
**After download:** [REVIEW_CHECKLIST.md](./REVIEW_CHECKLIST.md).

When Matt is back (console login / Allow as needed) — **exact path per vendor:**

1. **Vercel** — Access **requested 2026-08-03** (waiting approval). When approved → download **SOC 2 Type II** → `~/Documents/SMPL/soc2/vendor-reports/`. **Not received yet.**
2. **Railway** — **Received 2026-08-03** (Type II + bridge letter in private store). Review pending via [REVIEW_CHECKLIST](./REVIEW_CHECKLIST.md).
3. **Neon** — **Received 2026-08-03** (Databricks Neon SOC 2 Type 2 + HIPAA 2026 in private store). Review pending via [REVIEW_CHECKLIST](./REVIEW_CHECKLIST.md).
4. **Stripe** — **Received 2026-08-03** (current Type II + bridge letter + previous Type II archive in private store). Review pending via [REVIEW_CHECKLIST](./REVIEW_CHECKLIST.md).
5. **Anthropic** — **Received 2026-08-03** (SOC 2 Type II + CSA STAR L2 required pack; SOC 3 bonus/archive in private store). Review pending via [REVIEW_CHECKLIST](./REVIEW_CHECKLIST.md).
6. **Resend** — **Received 2026-08-03** (Type II in private store). Review pending via [REVIEW_CHECKLIST](./REVIEW_CHECKLIST.md).
7. **GitHub (P1, optional)** — Org → **Settings → Security → Compliance** → Download/View available reports; note if Type II missing on current plan.
8. **Vercel (open)** — Check email / SafeBase for access approval → download Type II when granted.

After each download: update this tracker to `received` / `reviewed` + date + period. Never commit NDA PDFs. After the session, use the reply block in the session checklist to batch-update statuses.

---

## Progress log

| Date | Event |
|------|-------|
| 2026-07-29 | Scaffold: README, TRACKER, REQUEST_TEMPLATES. All P0–P2 rows **not started**. No PDFs collected. |
| 2026-07-29 | **Public research pass (no Matt console):** P0 + GitHub Trust Centers / docs reviewed. Statuses → `researched` or `public summary available` (Stripe SOC 3 only). **No Type II received.** Stripe public SOC 3 saved under gitignored `private/`. Notes: [PUBLIC_RESEARCH_2026-07-29.md](./PUBLIC_RESEARCH_2026-07-29.md). |
| 2026-07-31 | **Session kit:** [SESSION_CHECKLIST_2026-07-31.md](./SESSION_CHECKLIST_2026-07-31.md) — ordered P0 clicks, private-store paths, post-session TRACKER reply format. Added **Next action** column. Statuses unchanged — **still no Type II received**. |
| 2026-08-03 | **Stakeholder week:** pointed meeting brief at this tracker + session kit — [../../STAKEHOLDER_WEEK_BRIEF.md](../../STAKEHOLDER_WEEK_BRIEF.md). Statuses unchanged — **still no Type II received**. Matt portal session still required. |
| 2026-08-03 | **Working pack:** [WORKING_PACK_2026-08.md](./WORKING_PACK_2026-08.md) + [REVIEW_CHECKLIST.md](./REVIEW_CHECKLIST.md) — P0 download targets, private store rules, review skim, honest status board. Statuses unchanged — **still no Type II received**. |
| 2026-08-03 | **Portal session:** Vercel → `requested` (Matt: access requested / pending approval). Type II **not** received. Moving to Railway next. |
| 2026-08-03 | **Railway:** Type II + bridge letter **received** (private store outside git). Status → `received`; **review pending**. Filenames logged in row notes. Next: Neon. |
| 2026-08-03 | **Neon:** Access granted; Databricks Neon SOC 2 Type 2 + HIPAA 2026 **received** (private store outside git). Status → `received`; **review pending**. Next: Stripe. |
| 2026-08-03 | **Stripe:** Current Type II + bridge letter + previous Type II archive **received** (private store outside git). Status → `received`; **review pending**. Next: Anthropic. |
| 2026-08-03 | **Anthropic:** SOC 2 Type II + CSA STAR L2 (required) and SOC 3 (bonus) **received** (private store outside git). Status → `received`; **review pending**. Next: Resend. |
| 2026-08-03 | **Resend:** Type II **received** (private store outside git). Status → `received`; **review pending**. P0 downloads done except Vercel (waiting). Optional: GitHub P1. |

---

_Update this file when a request is sent or a report is reviewed. Never mark `received` / `reviewed` without a private-store file (or documented portal-only review date)._
