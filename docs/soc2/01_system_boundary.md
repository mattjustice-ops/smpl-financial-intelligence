# System boundary (production = Type I system)

What auditors mean by “the system.” Refine with the audit firm. Keep this **named** (internal). Customer-facing diagrams may stay abstracted.

Parent: [../SOC2_TYPE1_KICKOFF.md](../SOC2_TYPE1_KICKOFF.md) · Scoreboard: [PROGRESS.md](./PROGRESS.md) · Subprocessors: [02_subprocessors.md](./02_subprocessors.md) · Readiness: [../SMPL_SOC2_Readiness_Reference_v2.md](../SMPL_SOC2_Readiness_Reference_v2.md)

**Status:** Production Type I boundary **locked** by Matt Justice **2026-07-28** (Q1–Q10 answered). Neon region **AWS us-east-1** confirmed; other vendor regions remain **TBD**. **Not** auditor-final. **Not** a claim of SOC 2 certification.

---

## Product in one line

SMPL.ai — B2B SaaS financial intelligence (FP&A / ARR / close / board export). Reads and reconciles customer finance data; **does not** write back to customer GL/ERP.

---

## Type I system = production

For SOC 2 Type I readiness, **the in-scope system is the production financial intelligence platform** that serves real customers and demo tenants on live hosts below. Local developer laptops, throwaway restore-test branches, staging/preview (no Customer Data), marketing CMS (Sanity), and non-prod experiments are **out of the product system** (still covered by org policies where people/process apply).

| Surface | Production identity (confirmed 2026-07-28) | Source |
|---------|----------------------------------|--------|
| Canonical web | `https://www.smpl-ai.com` (apex `smpl-ai.com` → www) | `frontend/lib/site.ts`, GO_LIVE / domain setup; Matt Q4 **YES** |
| Vercel project hostname | `https://smpl-financial-intelligence.vercel.app` | [CHANGE_MANAGEMENT.md](./CHANGE_MANAGEMENT.md), [GO_LIVE_PROD_DEPLOY.md](../GO_LIVE_PROD_DEPLOY.md); Matt Q4 **YES** |
| API | `https://sfi-api-production.up.railway.app` (`sfi-api-production`) | GO_LIVE, Railway scripts; Matt Q4 **YES** |
| Datastore | Neon project **`smpl-auth-prod`** · branch **`production`** · **AWS us-east-1** | [evidence/neon-restore-test-2026-07-27.md](./evidence/neon-restore-test-2026-07-27.md); Matt Q5 **YES** |
| DNS / registrar | **Squarespace** for `smpl-ai.com` — **DNS-only** | Access inventory; MFA 2026-07-26; Matt Q8 **YES** |

---

## In scope (production financial intelligence platform)

| Component | Provider / tech | Role | Status |
|-----------|-----------------|------|--------|
| Customer-facing web app | **Vercel** (Next.js) | UI, Auth.js session edge, marketing + `/app` | Confirmed production |
| Authentication | **Auth.js** magic link (email) | Login, org invites/seats — library on Vercel, not a separate host | Confirmed; SSO = backlog |
| API services | **Railway** FastAPI (`sfi-api-production`) | REST, exports, commentary, privileged ops paths | Confirmed production |
| Primary datastore | **Neon** Postgres (`smpl-auth-prod` / `production`) | Multi-tenant warehouse + auth/org tables | Confirmed; region **AWS us-east-1** (Matt Q5) |
| Transactional email | **Resend** | Magic links, product email | Confirmed stack; region **TBD** |
| LLM / AI commentary | **Anthropic** (API keys on Railway only) | Narrative drafts from engine outputs; not system of record for numbers | Confirmed primary; **OpenAI not live** on prod Railway (Matt Q2 **NO**) |
| Billing | **Stripe** | Subscriptions / checkout | Confirmed stack; region **TBD** |
| Source control & CI | **GitHub** | Code, PRs, deploy triggers → Vercel / Railway | Confirmed; region **TBD** / multi-region |
| DNS | **Squarespace** | Domain DNS for `smpl-ai.com` (not app host) | Confirmed DNS-only (Matt Q8); not a Customer Data processor |
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

## Out of Type I product boundary (org / marketing / non-prod)

| Item | Notes | Matt (2026-07-28) |
|------|-------|-------------------|
| **Sanity** (marketing CMS) | Blog / glossary / studio — marketing/website only; **not** a Customer Data subprocessor for product DPA. May note separately as marketing/website vendor | Q1 **NO** |
| **HubSpot** (SMPL sales CRM) | Request-quote / prospect CRM — sales org tool only; **not** on customer product DPA exhibit | Q7 **NO** |
| **OpenAI** | Code supports fallback if key set; **not live** on production Railway | Q2 **NO** |
| **Error / APM / product analytics** | No Sentry/PostHog/etc. with request/user context in prod app | Q6 **NO** |
| **Staging / Preview** | Staging/preview stack **exists**; holds **no Customer Data**. Out of Type I production system; still under change/access policy | Q3 — exists; no Customer Data |
| Customer source systems (NetSuite, Salesforce, customer HubSpot CRM, etc.) | Customer-controlled; SMPL reads via upload/share | — |
| Local developer laptops | Acceptable use / endpoint policy — not “the product system” | — |
| Neon throwaway restore-test branches | Evidence only; must not change Railway `DATABASE_URL` | — |
| Processing Integrity of FP&A methodology | **Deferred** — not in first Type I | — |
| Privacy Trust Services criteria | **Deferred** for Type I scope | — |

---

## Multi-tenant & product constraints (known)

| Fact | Source / note |
|------|----------------|
| Tenant isolation model | `organization_id` multi-tenant design — **evidence still required** (Org A cannot read Org B) |
| Auth | Auth.js magic link; org invites/seats; customer SSO = backlog |
| No GL write-back | Product reads/reconciles; does not write back to customer GL/ERP |
| AI | Anthropic API keys on **Railway only**; narrative from engine outputs; not system of record for numbers ([P15](./policies/P15_ai_llm_data_handling.md)). OpenAI **not** live in prod |
| Privileged ops | Solo founder: Matt Justice via MFA’d Neon / Railway / ops emails |

---

## Matt confirmation pack — Q1–Q10 **LOCKED 2026-07-28**

Answered by **Matt Justice** on **2026-07-28**. Closes PROGRESS items “Confirm boundary matches production” and “Confirm vendor regions / unused vendors” (other vendor **regions** remain honest **TBD**).

| # | Question | Answer | Notes |
|---|----------|--------|-------|
| **Q1** | Include **Sanity** in the Type I system / customer subprocessors exhibit? | **NO** | Marketing CMS only; outside Type I product boundary. May note as marketing/website vendor; **not** Customer Data subprocessor for product DPA |
| **Q2** | Is **OpenAI** (or any non-Anthropic LLM) **live** on production Railway today? | **NO** | Code-only fallback; omit from external Customer Data list |
| **Q3** | Does a **staging / sandbox** stack exist that can hold Customer Data? | Staging/preview **exists**; **no Customer Data** | Out of Type I production system |
| **Q4** | Confirm production hostnames (`www.smpl-ai.com`, Vercel project host, `sfi-api-production`, Neon `smpl-auth-prod`) | **YES** | Accurate as of 2026-07-28 |
| **Q5** | Confirm **Neon** production region is **AWS us-east-1** | **YES** | Matches restore evidence endpoint |
| **Q6** | Any **error/APM/analytics** vendor live in production with request/user context? | **NO** | None in prod app |
| **Q7** | List **HubSpot** on customer-facing product subprocessors? | **NO** | Sales CRM only; not customer product DPA exhibit |
| **Q8** | Is **Squarespace** DNS-only for `smpl-ai.com`? | **YES** | No customer app/data hosted there |
| **Q9** | Confirm exact **Vercel / Railway / Resend / Stripe / Anthropic / GitHub** (etc.) regions | **Neon us-east-1**; **other vendor regions TBD** | Do not invent geography |
| **Q10** | Any other production vendor processing Customer Data missing from [02_subprocessors.md](./02_subprocessors.md)? | **NO** | Known stack is complete for Customer Data |

---

## Diagram pointer

Keep an **internal named** architecture diagram aligned with this list. External IT diagram may abstract hosts. Related: `docs/SMPL_IT_Technical_Diagram.pdf`, `docs/Architecture_Master.md` (update named hosts as needed).

---

## Change log

| Date | Change | Owner |
|------|--------|-------|
| 2026-07-22 | Draft populated from known stack; multi-tenant / no-write-back / AI notes added | Kickoff |
| 2026-07-28 | Production boundary locked from deploy reality; hostnames + Neon project; Matt YES/NO/TBD pack; Sanity/OpenAI/staging left TBD | Agent (Week 2 boundary) |
| 2026-07-28 | **Matt Q1–Q10 locked** — Sanity/HubSpot out of product DPA; OpenAI/APM unused; staging exists (no Customer Data); hostnames + Neon us-east-1 confirmed; other regions TBD | Matt Justice (answers); Agent (docs) |
