# SOC 2 Type I — Decision log

Fill as decisions are made. Do not claim certification until a CPA firm issues a report.

Parent plan: [../SOC2_TYPE1_KICKOFF.md](../SOC2_TYPE1_KICKOFF.md) · Scoreboard: [PROGRESS.md](./PROGRESS.md) · Scope detail: [../SMPL_SOC2_Readiness_Reference_v2.md](../SMPL_SOC2_Readiness_Reference_v2.md)

**Scope status:** **APPROVED** by Matt Justice on **2026-07-22**. Trust Services Criteria and named owners below are frozen. Audit firm and Type I fieldwork month remain open for Matt.

**Remaining work + calendar:** [PROGRESS.md — Remaining checklist + target timeline](./PROGRESS.md#remaining-checklist--target-timeline)

---

## Scope & platform

| Decision | Choice | Date | Owner | Notes |
|----------|--------|------|-------|-------|
| Engagement type | Type I first, then Type II | 2026-07-22 | Matt Justice | **APPROVED** |
| Type I Trust Services Criteria | **Security + Availability + Confidentiality** | 2026-07-22 | Matt Justice | **APPROVED** — frozen for Type I |
| Processing Integrity | **Deferred** | 2026-07-22 | Matt Justice | **APPROVED deferral** — revisit only with auditor + counsel; not “certified ARR math” |
| Privacy | **Deferred / skip for now** | 2026-07-22 | Matt Justice | **APPROVED deferral** — revisit if consumer/employee PII at scale or contract requires |
| Compliance automation platform | **Deferred — DIY for now** (no Vanta / Drata / Secureframe purchase) | 2026-07-27 | Matt Justice | **DECIDED** — continue with existing [docs/soc2/](./) + `/app/compliance` scoreboard. Revisit purchase when **either** trigger fires (whichever comes first): (1) first paying enterprise that **requires** a formal GRC/compliance platform, **or** (2) CPA engagement for Type I. Document both triggers; do not auto-signup. |
| Audit firm (CPA) | TBD | | **[!]** Matt Justice | Independent CPA; platform partner network OK later |
| Target Type I fieldwork / report month | YYYY-MM | | **[!]** Matt Justice | Book only when controls are live — see PROGRESS timeline (**TARGET**, not commitment) |

---

## Named owners

| Role | Name | Date named | Notes |
|------|------|------------|-------|
| Executive sponsor | **Matt Justice** | 2026-07-22 | **APPROVED** — Approves policies; accepts residual risk. Owns all roles for now. |
| Security owner | **Matt Justice** | 2026-07-22 | **APPROVED** — Policies, access reviews, IR, vendor risk |
| Engineering owner | **Matt Justice** | 2026-07-22 | **APPROVED** — Change management, SDLC, logging, env separation |
| Ops / CS privileged access owner | **Matt Justice** | 2026-07-22 | **APPROVED** — White-glove loads, tenant support access |

One person may hold multiple roles; still write the names so accountability is clear. Roles may be split later without changing Type I scope.

---

## Confirmation block (Matt)

| Field | Value |
|-------|--------|
| Confirmed by | **Matt Justice** |
| Date | **2026-07-22** (scope/owners); platform deferral **2026-07-27**; boundary/vendors Q1–Q10 **2026-07-28** |
| Status | **APPROVED** — Type I scope (Security + Availability + Confidentiality); Processing Integrity deferred; Privacy deferred; all named owners = Matt Justice; production boundary/vendors locked (other regions TBD) |
| Exceptions / still open | Compliance platform **deferred DIY** (triggers documented 2026-07-27); audit firm TBD; Type I fieldwork month TBD (TARGET on scoreboard); other vendor **regions** TBD (Neon us-east-1 locked) |

---

## Production boundary & vendors (Matt Q1–Q10)

| Decision | Choice | Date | Owner | Notes |
|----------|--------|------|-------|-------|
| Sanity in Type I / product DPA Customer Data exhibit | **NO** — marketing CMS only | 2026-07-28 | Matt Justice | Outside product boundary; may note as marketing/website vendor |
| OpenAI live on prod Railway | **NO** | 2026-07-28 | Matt Justice | Omit from external Customer Data list |
| Staging / preview | **Exists; no Customer Data** | 2026-07-28 | Matt Justice | Out of Type I production system |
| Production hostnames accurate | **YES** | 2026-07-28 | Matt Justice | www.smpl-ai.com, Vercel project, sfi-api-production, Neon smpl-auth-prod |
| Neon region | **AWS us-east-1** | 2026-07-28 | Matt Justice | Matches restore evidence |
| APM / analytics with user context in prod | **NO** | 2026-07-28 | Matt Justice | None |
| HubSpot on product DPA exhibit | **NO** — sales CRM only | 2026-07-28 | Matt Justice | Not Customer Data subprocessor for product |
| Squarespace | **DNS-only** | 2026-07-28 | Matt Justice | |
| Other vendor regions (Vercel, Railway, Resend, Stripe, Anthropic, GitHub, …) | **TBD** | 2026-07-28 | Matt Justice | Do not invent; Neon only confirmed |
| Other prod Customer Data vendors beyond known stack | **NO** | 2026-07-28 | Matt Justice | |

Detail: [01_system_boundary.md](./01_system_boundary.md) · [02_subprocessors.md](./02_subprocessors.md)

---

## Change history

| Date | What changed | Who |
|------|--------------|-----|
| 2026-07-22 | Initial log created | Kickoff |
| 2026-07-22 | Proposed defaults: Sec+Avail+Conf; PI deferred; Privacy skip; platform TBD/wait; security/sponsor Matt Justice TBD confirm | Agent (readiness kickoff) |
| 2026-07-22 | Confirmed scope Sec+Avail+Conf; PI deferred; Privacy skip; all named owners → Matt Justice; platform left TBD (Matt to decide) | Agent (compliance checklist wave) |
| 2026-07-22 | **Scope frozen APPROVED** by Matt Justice; owners all Matt; platform/CPA/target month still open | Agent (Matt-approved scope lock) |
| 2026-07-27 | **Platform deferred DIY** — no Vanta/Drata/etc. now; use docs/soc2 + `/app/compliance`; revisit on first paying enterprise requiring formal GRC platform **or** CPA Type I engagement (whichever first) | Matt Justice (decision); Agent (log) |
| 2026-07-28 | **DPA/MSA outline drafted** — [legal/DPA_MSA_OUTLINE.md](./legal/DPA_MSA_OUTLINE.md) for counsel review. P10 R16 remains **open** (outline ≠ signed DPA). Not legal advice; not SOC 2 certified. | Agent (Week 2 #1); Matt next: counsel |
| 2026-07-29 | **DPA/MSA counsel send package ready** — [legal/COUNSEL_SEND_PACKAGE.md](./legal/COUNSEL_SEND_PACKAGE.md) + [legal/DRAFT_EMAIL_TO_COUNSEL.md](./legal/DRAFT_EMAIL_TO_COUNSEL.md). Matt must send; agent did **not** email counsel. P10 R16 remains **open**. Not legal advice; not SOC 2 certified. | Agent (counsel readiness); Matt next: send |
| 2026-07-29 | **DPA/MSA sent to counsel** — Matt attested send via chat (“send”); counsel firm **unspecified**; agent did **not** email. Evidence [evidence/dpa-counsel-sent-2026-07-29.md](./evidence/dpa-counsel-sent-2026-07-29.md). P10 R16 remains **open** (awaiting redline / customer-ready draft). Not legal advice; not SOC 2 certified. | Matt Justice (send attestation); Agent (log) |
| 2026-07-29 | **Vendor SOC public research (no Matt console)** — P0 + GitHub Trust Centers/docs researched; Stripe public SOC 3 only; **no Type II received**. Tracker + [evidence/vendor-soc/PUBLIC_RESEARCH_2026-07-29.md](./evidence/vendor-soc/PUBLIC_RESEARCH_2026-07-29.md). DPA chase checklist only; R16 still open. Not SOC 2 certified. | Agent (autonomous research); Matt next: portal downloads + counsel redline |
| 2026-08-03 | **Stakeholder week brief** — [STAKEHOLDER_WEEK_BRIEF.md](./STAKEHOLDER_WEEK_BRIEF.md) for primary meetings; DPA chase ~**2026-08-05**; CPA month/firm still `[!]`; vendor Type II still not received. Not SOC 2 certified. | Agent (docs); Matt next: vendor session / DPA chase / CPA picks |
| 2026-07-28 | **Production boundary + vendor pack** — [01_system_boundary.md](./01_system_boundary.md) / [02_subprocessors.md](./02_subprocessors.md) updated from deploy reality (www.smpl-ai.com, Railway `sfi-api-production`, Neon `smpl-auth-prod` us-east-1 evidence). Matt Q1–Q10 still open; no invented regions; not SOC 2 certified. | Agent (Week 2 boundary/vendors) |
| 2026-07-28 | **Boundary/vendor Q1–Q10 LOCKED** — Sanity/HubSpot out of product DPA; OpenAI/APM unused; staging exists (no Customer Data); hostnames + Neon us-east-1 YES; other regions TBD; no other Customer Data vendors. Checklist items closed; not SOC 2 certified. | Matt Justice (answers); Agent (docs) |
