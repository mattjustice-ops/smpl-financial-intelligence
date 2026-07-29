# Vendor report request templates

Copy-paste language for Trust Center / support portals. Replace bracketed fields. Use corporate email **mattjustice@smpl-ai.com**.

**Do not** claim SMPL is SOC 2 certified. You are collecting **vendor** reports for SMPL’s own readiness / customer questionnaires / future CPA fieldwork.

After sending a request, set the vendor row in [TRACKER.md](./TRACKER.md) to `requested` and note the date.

---

## Generic Trust Center / NDA portal (Vercel, Railway, Neon, Anthropic, …)

Use when the portal asks for a business justification or message:

```
Company: SMPL (smpl-ai.com)
Requester: Matt Justice, Founder / Security owner
Email: mattjustice@smpl-ai.com
Use case: We are a B2B SaaS (financial intelligence) preparing SOC 2 Type I readiness
and maintaining vendor due diligence under our Vendor / Subprocessor Management policy.
We use [VENDOR] for [PURPOSE — e.g. hosting our production API / Postgres / LLM API].

Please grant access to your current SOC 2 Type II report (and ISO 27001 certificate if available).
We will store the report under NDA outside public repositories and review it annually
or on material change.

Thank you,
Matt Justice
```

---

## Vercel

1. Open https://security.vercel.com/
2. Request access to the **SOC 2 Report** (and related docs as needed).
3. If stuck: email privacy@vercel.com with the generic template (Vendor = Vercel; Purpose = host customer-facing Next.js / edge for www.smpl-ai.com).

```
Subject: SOC 2 report access request — SMPL (smpl-ai.com)

Hello Vercel Privacy / Trust team,

Please grant our account access to Vercel’s current SOC 2 Type II report via the Trust Center
(security.vercel.com). We use Vercel to host our production customer application.

Company: SMPL · Contact: Matt Justice · mattjustice@smpl-ai.com

Thank you,
Matt Justice
```

---

## Railway

1. Open https://trust.railway.com/ (sign in with the Railway account email).
2. Request access to **SOC 2 Type II** (prefer Type II over public SOC 3 alone).
3. Purpose line: host FastAPI production API (`sfi-api-production`).

```
Subject: Trust Center — SOC 2 Type II access (SMPL)

We use Railway to host our production API. Please approve access to the current
SOC 2 Type II report in the Railway Trust Center for mattjustice@smpl-ai.com.

Matt Justice · SMPL · smpl-ai.com
```

---

## Neon

1. Open https://trust.neon.com/
2. Request **SOC 2** (and ISO docs if listed). Note: full SOC 2 may require a **paid** plan — if rejected, contact sales@neon.tech.
3. Purpose: managed Postgres for production customer financial / auth data (project region AWS us-east-1).

```
Subject: Neon Trust Center — SOC 2 / ISO report access (SMPL)

Hello Neon,

We are a paid [confirm plan] customer using Neon Postgres for production (AWS us-east-1).
Please approve Trust Center access for our current SOC 2 Type II report and ISO 27001
certificate (if available) for vendor due diligence / SOC 2 readiness.

Contact: Matt Justice · mattjustice@smpl-ai.com · SMPL (smpl-ai.com)

Thank you
```

---

## Stripe

1. Prefer Dashboard: https://dashboard.stripe.com/settings/compliance and https://dashboard.stripe.com/settings/documents
2. Public overview / SOC 3: https://docs.stripe.com/security
3. If Dashboard does not expose SOC 2: use support chat or security request with template below.

```
Subject: Request — Stripe SOC 2 Type II report (existing customer)

Hello Stripe,

We are an existing Stripe Billing customer (SMPL / smpl-ai.com). Please provide access to
the current SOC 1 / SOC 2 Type II reports under NDA for vendor due diligence as we prepare
SOC 2 Type I readiness. Contact: Matt Justice, mattjustice@smpl-ai.com.

We already have MFA on the Dashboard account. Happy to complete any click-through NDA.

Thank you,
Matt Justice
```

---

## Anthropic

1. Open https://trust.anthropic.com/
2. Request SOC 2 Type II / ISO documentation as offered.
3. Purpose: Claude API for AI narrative/commentary; keys on Railway only (see P15).

```
Subject: Trust Portal — compliance documentation request (SMPL)

Hello Anthropic Trust / Compliance,

Please grant access to Anthropic’s current SOC 2 Type II report and ISO 27001 / ISO 42001
certificates via the Trust Portal for vendor due diligence. We use the Anthropic API for
optional AI commentary in our B2B SaaS (prompts derived from our engine outputs; no model training commitments per our customer posture).

Matt Justice · mattjustice@smpl-ai.com · SMPL (smpl-ai.com)
```

---

## Resend

1. Log in → **Settings → Documents** (see https://resend.com/docs/knowledge-base/downloading-documents).
2. Download SOC 2 Type II + keep PDF outside git.
3. If Documents page missing the report:

```
Subject: SOC 2 report download — Resend account (SMPL)

Hello Resend,

We use Resend for transactional email (magic links / notifications). Please confirm how to
download the current SOC 2 Type II report for our account (Settings → Documents) or send
secure access instructions to mattjustice@smpl-ai.com.

Matt Justice · SMPL · smpl-ai.com
```

---

## GitHub

1. Org → **Settings → Security → Compliance** (see GitHub docs on accessing compliance reports).
2. Download whatever is available for the current plan; note gaps if SOC 2 Type II is Enterprise-only.
3. Overview: https://github.com/trust-center/

```
Subject: (Usually not needed — use org Compliance downloads)

If Compliance page is empty or missing SOC 2 Type II: open a GitHub Support ticket noting
organization name, that we need SOC 2 Type II for vendor due diligence, and our plan tier.
Contact: Matt Justice · mattjustice@smpl-ai.com
```

---

## Sanity (optional / marketing only)

Not on product Customer Data DPA. Only if a questionnaire asks.

```
Subject: Security documentation / SOC 2 request — SMPL (marketing CMS only)

Hello Sanity,

We use Sanity for marketing content only (not product Customer Data). Please share how to
obtain the current SOC 2 Type II report under NDA for our vendor inventory / questionnaire pack.

Matt Justice · mattjustice@smpl-ai.com · SMPL (smpl-ai.com)
```

---

## Squarespace (optional / DNS only)

```
Subject: Security / SOC report availability — DNS customer (smpl-ai.com)

Hello Squarespace Support,

We use Squarespace for DNS/domain administration for smpl-ai.com only (not hosting customer
application data). For vendor inventory completeness, please advise whether a SOC 2 report
is available to our plan and how to request it under NDA.

Matt Justice · mattjustice@smpl-ai.com
```

---

## Google Workspace / IdP (optional)

```
Subject: (Usually self-serve via Google Cloud / Workspace compliance resources)

Document in TRACKER.md that Google Workspace / Cloud compliance reports were reviewed
via https://cloud.google.com/security/compliance (and admin console resources if available).
Store any downloaded PDFs outside git.
```

---

## After you receive a report

1. Save PDF to private store ([README.md](./README.md)).
2. Update [TRACKER.md](./TRACKER.md): `received` → then `reviewed` after skim.
3. Flip “Vendor report collected?” in [02_subprocessors.md](../../02_subprocessors.md) only when reviewed.
4. Do **not** update PROGRESS to “complete” until P0 vendors are at least `reviewed` (or honestly `blocked` with plan/access reason).
