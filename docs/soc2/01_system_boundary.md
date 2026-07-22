# System boundary (draft for Type I)

What auditors mean by “the system.” Refine with the compliance platform and audit firm. Keep this **named** (internal). Customer-facing diagrams may stay abstracted.

Parent: [../SOC2_TYPE1_KICKOFF.md](../SOC2_TYPE1_KICKOFF.md) · Scoreboard: [PROGRESS.md](./PROGRESS.md) · Readiness: [../SMPL_SOC2_Readiness_Reference_v2.md](../SMPL_SOC2_Readiness_Reference_v2.md)

**Status:** Draft from known SMPL stack (readiness v2 + prior kickoff artifacts). **[!]** Matt / engineering must confirm against production and resolve TBDs below. Not auditor-final.

---

## Product in one line

SMPL.ai — B2B SaaS financial intelligence (FP&A / ARR / close / board export). Reads and reconciles customer finance data; **does not** write back to customer GL/ERP.

---

## In scope (production financial intelligence platform)

| Component | Provider / tech | Role | Status |
|-----------|-----------------|------|--------|
| Customer-facing web app | **Vercel** (Next.js) | UI, Auth.js session edge | Confirmed stack |
| Authentication | **Auth.js** magic link (email) | Login, org invites/seats | Confirmed; SSO = backlog |
| API services | **Railway** (FastAPI / Python) | REST, exports, privileged ops paths | Confirmed stack |
| Primary datastore | **Neon** (Postgres) | Multi-tenant warehouse + auth-related tables | Confirmed stack |
| Transactional email | **Resend** | Magic links, product email | Confirmed stack |
| LLM / AI commentary | **Anthropic** (API keys on backend only) | Narrative drafts from engine outputs; not system of record for numbers | Confirmed; OpenAI fallback if used → TBD |
| Billing | **Stripe** | Subscriptions / checkout | Confirmed stack |
| Source control & CI | **GitHub** | Code, PRs, deploy triggers | Confirmed |
| CMS (marketing content) | **Sanity** | Blog / glossary / studio | Confirmed present; boundary TBD below |
| Secrets / env | Vercel + Railway env / secret stores | Production secrets | Document locations TBD |
| Ops / white-glove | Ops console, direct data load tooling, privileged DB access | Tenant support & POC loads | Document named operators TBD |
| Production CI/CD that deploys the above | GitHub → Vercel / Railway | Promote to prod | Document who can promote TBD |

### Data categories (flows to name on diagrams)

- Auth identifiers (email, session, org membership)
- Financial warehouse facts (GL-derived, ARR, pipeline, headcount, etc.)
- Export artifacts (Excel close packs, board decks)
- Prompt context to LLM (prefer aggregated / freeze context; minimize raw PII)

---

## Typically out of scope (or separately controlled)

| Item | Notes |
|------|-------|
| Customer source systems (NetSuite, Salesforce, HubSpot, etc.) | Customer-controlled; SMPL reads via upload/share |
| Pure marketing site content | Still covered by org policies where infra is shared |
| Local developer laptops | Acceptable use / endpoint policy — not “the product system” |
| Processing Integrity of FP&A methodology | **Deferred** — not in first Type I |

---

## Multi-tenant & product constraints (known)

| Fact | Source / note |
|------|----------------|
| Tenant isolation model | `organization_id` multi-tenant design (readiness v2) — **evidence still required** (Org A cannot read Org B) |
| Auth | Auth.js magic link; org invites/seats; customer SSO = backlog |
| No GL write-back | Product reads/reconciles customer finance data; does not write back to customer GL/ERP |
| AI | Anthropic API keys on backend only; narrative from engine outputs; not system of record for numbers |

---

## Boundary decisions still TBD — [!] Matt / eng

- [ ] Is **Sanity** in the SOC 2 system description, or only org-policy / marketing? (Recommend: document as subprocessor if it can hold customer-named content; else note marketing-only.)
- [ ] Staging / sandbox accounts: same providers? Separate Neon/Railway projects?
- [ ] Exact production hostnames / project names (internal only)
- [ ] Whether OpenAI (or other LLM) is live as fallback
- [ ] List of privileged Ops roles that can see tenant data
- [ ] Secrets locations confirmed (Vercel + Railway env / secret stores)

---

## Diagram pointer

Keep an **internal named** architecture diagram aligned with this list. External IT diagram may abstract hosts. Related: `docs/SMPL_IT_Technical_Diagram.pdf`, `docs/Architecture_Master.md` (update named hosts as needed).

---

## Change log

| Date | Change | Owner |
|------|--------|-------|
| 2026-07-22 | Draft populated from known stack; multi-tenant / no-write-back / AI notes added | Kickoff |
