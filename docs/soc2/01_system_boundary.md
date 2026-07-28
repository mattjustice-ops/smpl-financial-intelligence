# System boundary (production = Type I system)

What auditors mean by “the system.” Refine with the audit firm. Keep this **named** (internal). Customer-facing diagrams may stay abstracted.

Parent: [../SOC2_TYPE1_KICKOFF.md](../SOC2_TYPE1_KICKOFF.md) · Scoreboard: [PROGRESS.md](./PROGRESS.md) · Subprocessors: [02_subprocessors.md](./02_subprocessors.md) · Readiness: [../SMPL_SOC2_Readiness_Reference_v2.md](../SMPL_SOC2_Readiness_Reference_v2.md)

**Status:** Known-good **production** boundary documented from deploy docs + code + Neon restore evidence (2026-07-28). Matt must answer the **YES/NO/TBD** questions below to close Week 2–3 boundary items. **Not** auditor-final. **Not** a claim of SOC 2 certification.

---

## Product in one line

SMPL.ai — B2B SaaS financial intelligence (FP&A / ARR / close / board export). Reads and reconciles customer finance data; **does not** write back to customer GL/ERP.

---

## Type I system = production

For SOC 2 Type I readiness, **the in-scope system is the production financial intelligence platform** that serves real customers and demo tenants on live hosts below. Local developer laptops, throwaway restore-test branches, and non-prod experiments are **out of the product system** (still covered by org policies where people/process apply).

| Surface | Production identity (known-good) | Source |
|---------|----------------------------------|--------|
| Canonical web | `https://www.smpl-ai.com` (apex `smpl-ai.com` → www) | `frontend/lib/site.ts`, GO_LIVE / domain setup |
| Vercel project hostname | `https://smpl-financial-intelligence.vercel.app` | [CHANGE_MANAGEMENT.md](./CHANGE_MANAGEMENT.md), [GO_LIVE_PROD_DEPLOY.md](../GO_LIVE_PROD_DEPLOY.md) |
| API | `https://sfi-api-production.up.railway.app` (`sfi-api-production`) | GO_LIVE, Railway scripts |
| Datastore | Neon project **`smpl-auth-prod`** · branch **`production`** | [evidence/neon-restore-test-2026-07-27.md](./evidence/neon-restore-test-2026-07-27.md) |
| DNS / registrar | **Squarespace** for `smpl-ai.com` | Access inventory; MFA 2026-07-26 |

---

## In scope (production financial intelligence platform)

| Component | Provider / tech | Role | Status |
|-----------|-----------------|------|--------|
| Customer-facing web app | **Vercel** (Next.js) | UI, Auth.js session edge, marketing + `/app` | Confirmed production |
| Authentication | **Auth.js** magic link (email) | Login, org invites/seats — library on Vercel, not a separate host | Confirmed; SSO = backlog |
| API services | **Railway** FastAPI (`sfi-api-production`) | REST, exports, commentary, privileged ops paths | Confirmed production |
| Primary datastore | **Neon** Postgres (`smpl-auth-prod` / `production`) | Multi-tenant warehouse + auth/org tables | Confirmed; region **AWS us-east-1** (see subprocessors) |
| Transactional email | **Resend** | Magic links, product email | Confirmed stack |
| LLM / AI commentary | **Anthropic** (API keys on Railway only) | Narrative drafts from engine outputs; not system of record for numbers | Confirmed primary; OpenAI fallback → **TBD** |
| Billing | **Stripe** | Subscriptions / checkout | Confirmed stack |
| Source control & CI | **GitHub** | Code, PRs, deploy triggers → Vercel / Railway | Confirmed |
| CMS (marketing content) | **Sanity** (`sda23ulo` / dataset `production`) | Blog / glossary / studio on marketing site | Present in prod web; **boundary in/out → Matt Q1** |
| DNS | **Squarespace** | Domain DNS for `smpl-ai.com` (not app host) | Confirmed; not a customer-data processor by default |
| Secrets / env | Vercel + Railway env stores | Production secrets | Confirmed locations |
| Ops / white-glove | `/app/ops`, direct data load tooling, privileged Neon/Railway access | Tenant support & POC loads | Named operator: **Matt Justice** (solo) |
| Production CI/CD | GitHub → Vercel FE / Railway API | Promote to prod | Who can promote: **Matt Justice** |

### Data categories (flows to name on diagrams)

- Auth identifiers (email, session, org membership)
- Financial warehouse facts (GL-derived, ARR, pipeline, headcount, etc.)
- Export artifacts (Excel close packs, board decks)
- Prompt context to LLM (prefer aggregated / freeze context; minimize raw PII)
- Billing contact / subscription metadata (Stripe; no full PAN at SMPL)

---

## Typically out of scope (or separately controlled)

| Item | Notes |
|------|-------|
| Customer source systems (NetSuite, Salesforce, HubSpot CRM as *customer’s* systems, etc.) | Customer-controlled; SMPL reads via upload/share |
| Local developer laptops | Acceptable use / endpoint policy — not “the product system” |
| Neon throwaway restore-test branches | Evidence only; must not change Railway `DATABASE_URL` |
| Processing Integrity of FP&A methodology | **Deferred** — not in first Type I |
| Privacy Trust Services criteria | **Deferred** for Type I scope |

---

## Related / not automatic Type I “product” subprocessors

| Item | Notes | Matt |
|------|-------|------|
| **Squarespace** | DNS / domain admin only | Confirm still DNS-only (Q8) |
| **HubSpot** (SMPL sales) | Request-quote / marketing CRM path in frontend — prospect data, not warehouse Customer Data | Confirm list as org CRM vs product subprocessor (Q7) |
| **OpenAI** | Code supports fallback if `OPENAI_API_KEY` set; deploy path documents **Anthropic** on Railway | Confirm **not** live in prod unless YES (Q2) |
| **Error / APM / product analytics** | No Sentry/PostHog/etc. confirmed in production boundary from repo alone | Confirm unused or name if live (Q6) |
| **Staging / Preview** | Repo references `sfi-api-staging`, Vercel Preview, sandbox branches | Confirm whether separate staging exists and if it holds Customer Data (Q3) |

---

## Multi-tenant & product constraints (known)

| Fact | Source / note |
|------|----------------|
| Tenant isolation model | `organization_id` multi-tenant design — **evidence still required** (Org A cannot read Org B) |
| Auth | Auth.js magic link; org invites/seats; customer SSO = backlog |
| No GL write-back | Product reads/reconciles; does not write back to customer GL/ERP |
| AI | Anthropic API keys on **Railway only**; narrative from engine outputs; not system of record for numbers ([P15](./policies/P15_ai_llm_data_handling.md)) |
| Privileged ops | Solo founder: Matt Justice via MFA’d Neon / Railway / ops emails |

---

## Matt confirmation pack — YES / NO / TBD

Answer each. Do **not** invent regions. Closing these closes PROGRESS items “Confirm boundary matches production” and “Confirm vendor regions / unused vendors.”

| # | Question | Options | Default recommendation (not decided) |
|---|----------|---------|--------------------------------------|
| **Q1** | Include **Sanity** in the Type I system description / customer subprocessors exhibit? | **YES** (marketing CMS on prod web) / **NO** (org-policy only; marketing-only, no customer-named content) / **TBD** | Prefer **YES** if any customer-named or customer-authored content can land in Sanity; else **NO** with “marketing-only” note |
| **Q2** | Is **OpenAI** (or any non-Anthropic LLM) **live** on production Railway today? | **YES** (add as subprocessor) / **NO** (code-only fallback; omit from external list) / **TBD** | Prefer **NO** until Railway prod env is confirmed to have a live key |
| **Q3** | Does a **staging / sandbox** stack exist (separate Neon project and/or `sfi-api-staging` + Vercel Preview) that can hold Customer Data? | **YES** (name projects) / **NO** (prod + local only) / **TBD** | Document names if YES; keep staging out of “production system” but under change/access policy |
| **Q4** | Confirm production hostnames above (`www.smpl-ai.com`, Vercel project host, `sfi-api-production`, Neon `smpl-auth-prod`) are still accurate | **YES** / **NO** (correct below) / **TBD** | Expected **YES** |
| **Q5** | Confirm **Neon** production region is **AWS us-east-1** (from restore evidence endpoint) | **YES** / **NO** (state correct region) / **TBD** | Expected **YES** |
| **Q6** | Any **error/APM/analytics** vendor live in production with request/user context (e.g. Sentry)? | **YES** (name it) / **NO** / **TBD** | Prefer **NO** if unused |
| **Q7** | List **HubSpot** on customer-facing subprocessors (sales CRM / request-quote), or keep as org tool only? | **YES** (list) / **NO** (org tool; questionnaire only) / **TBD** | Often **NO** for product DPA exhibit; **YES** for security questionnaires |
| **Q8** | Is **Squarespace** DNS-only for `smpl-ai.com` (no customer app/data hosted there)? | **YES** / **NO** / **TBD** | Expected **YES** |
| **Q9** | Confirm exact **Vercel / Railway / Resend / Stripe / Anthropic / Sanity / GitHub** hosting or processing **regions** (or “provider multi-region / unknown”) | Fill per vendor or leave **TBD** | Do **not** invent — leave TBD until console-confirmed |
| **Q10** | Any other production vendor processing customer or auth data that is missing from [02_subprocessors.md](./02_subprocessors.md)? | **YES** (name) / **NO** / **TBD** | — |

---

## Diagram pointer

Keep an **internal named** architecture diagram aligned with this list. External IT diagram may abstract hosts. Related: `docs/SMPL_IT_Technical_Diagram.pdf`, `docs/Architecture_Master.md` (update named hosts as needed).

---

## Change log

| Date | Change | Owner |
|------|--------|-------|
| 2026-07-22 | Draft populated from known stack; multi-tenant / no-write-back / AI notes added | Kickoff |
| 2026-07-28 | Production boundary locked from deploy reality; hostnames + Neon project; Matt YES/NO/TBD pack; Sanity/OpenAI/staging left TBD | Agent (Week 2 boundary) |
