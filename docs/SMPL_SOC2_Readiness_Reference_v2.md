# SMPL.ai SOC 2 Readiness Reference (v2)

Internal working document. Covers: which Trust Services Criteria apply to SMPL, a Type I readiness checklist mapped to our current stack, sales language rules, and first moves. Target path: **Type I first** (design of controls at a point in time), then **Type II** (operating effectiveness over an observation window).

This is orientation, not legal or audit advice. The auditor is an independent CPA firm; a compliance-automation platform (Vanta, Drata, Secureframe, or similar) will do most of the evidence collection. Refine the map below with whichever partner you choose.

**v2 changes vs v1:** Softened Processing Integrity expectations; added SMPL current-state gaps, system boundary, roles, sales-now artifacts, AI/white-glove notes, timeline/cost realism, and a clearer evidence bar.

---

## 1. Which Trust Services Criteria apply to us

SOC 2 has five criteria categories. Only **Security** is mandatory; the rest are opt-in based on what you operate and what you promise customers. Broader scope means more cost and evidence — scope deliberately.

### Security (Common Criteria, CC1–CC9) — REQUIRED

Every SOC 2 report includes this. It covers protecting systems and data from unauthorized access, disclosure, and damage. Themes include control environment, communication, risk assessment, monitoring, control activities, logical/physical access, system operations, change management, and risk mitigation. This is the bulk of the work.

### Availability — RECOMMENDED for SMPL

Covers whether the system is available as committed. Natural fit for SaaS that finance teams use during close and board cycles. Include if you make (or imply) uptime commitments. Expect monitoring, incident response, and backup/recovery evidence.

### Confidentiality — RECOMMENDED for SMPL

Covers protection of information designated confidential. SMPL ingests customer financial data (GL, ARR, pipeline, headcount, etc.). Buyer security teams will expect this for a B2B finance platform.

### Processing Integrity — DEFER by default (strategic later option)

Covers whether system processing is complete, valid, accurate, timely, and authorized **as controlled** — e.g. change controls, error handling, authorized jobs — **not** an independent certification that SMPL’s FP&A methodology, ARR waterfalls, or Financial Intelligence Engine produce correct accounting answers.

Most SaaS companies skip PI. SMPL’s brand (deterministic, reproducible calculation) makes it *tempting*, but marketing PI as “a third party attested our numbers/engine” would overclaim. **Do not include PI in the first Type I** unless an auditor and counsel agree on narrow, honest language. Revisit after Security + Availability + Confidentiality are solid.

### Privacy — SKIP for now

Heaviest criterion set; aimed at personal information against a privacy notice. SMPL primarily handles company financial data. Revisit if you process meaningful consumer/employee PII at scale or a customer contractually requires it.

### Target starting scope

**Security + Availability + Confidentiality.**

Decision log (fill in when decided):

| Decision | Choice | Date | Owner |
|----------|--------|------|-------|
| Type I criteria | Sec + Avail + Conf (default) | | |
| Processing Integrity | Deferred / Include (circle one) | | |
| Compliance platform | Vanta / Drata / Secureframe / other | | |
| Audit firm | | | |
| Target Type I date | | | |

---

## 2. In-scope system boundary (draft)

Auditors need a clear “what is the system.” Draft for refinement:

**In scope (production financial intelligence platform)**
- Customer-facing app and auth (e.g. Vercel + Auth.js / magic link)
- API services (e.g. Railway FastAPI)
- Primary datastore (e.g. Neon Postgres — warehouse + auth-related tables)
- Ops paths that can touch tenant data (Ops console, white-glove load tooling, privileged DB access)
- Production secrets and CI/CD that deploy the above
- Subprocessors that process or store customer data in the course of delivery (see §7)

**Typically out of scope or separately controlled**
- Pure marketing site content (still covered by org policies where it shares infra)
- Local developer laptops (covered by acceptable use / endpoint policy, not as “the product system”)
- Customer’s own source systems (NetSuite, Salesforce, etc.)

Update this boundary with the auditor; keep it consistent with the **named** internal architecture diagram (§8).

---

## 3. Roles (even if one person wears several hats)

| Role | Responsibility | Named owner |
|------|----------------|-------------|
| Executive sponsor | Approves policies, accepts residual risk | |
| Security owner | Policies, access reviews, IR, vendor risk | |
| Engineering owner | Change management, SDLC, logging, env separation | |
| Ops / CS privileged access owner | White-glove loads, tenant support access | |

---

## 4. Type I readiness checklist

Type I attests that controls are **designed** appropriately at a point in time. Goal: real controls + documentation so an auditor can confirm they exist and are sound. Type II later confirms they **operated** over a window — that clock only starts once controls are live.

This is a readiness map, not the auditor’s exact test list.

### 4.1 SMPL current state vs gap (snapshot)

Honest working view — update as you close gaps.

| Area | Already rough-ready | Likely gap for Type I |
|------|---------------------|------------------------|
| Encryption in transit / at rest | TLS on edge/API; managed Postgres at rest | Written control + evidence (provider docs + config) |
| Environments | Production vs sandbox/staging | Formal change/promotion policy |
| Version control | Git | Protected `main`, required PR review |
| Deploy path | Vercel + Railway | Documented deploy process + who can promote |
| Product auth | Magic-link login, org invites/seats | MFA on **admin/cloud** accounts; customer SSO is backlog, not Type I blocker if scoped honestly |
| Tenant isolation | `organization_id` multi-tenant design | Documented enforcement + cross-tenant negative tests |
| Ops / white-glove | Read-oriented ingest playbooks | Privileged access logging, approval, revocation |
| AI | Keys on API only; narrative grounded in engine outputs | Subprocessor + data-handling policy (what may be sent to LLM) |
| Monitoring | Partial / evolving | Central alerts, on-call/IR ownership, retain logs |
| Policies | Thin / informal | Written ISMS set, acknowledged by team |

### 4.2 Governance and people (CC1, CC2)

- [ ] Written information security policy, reviewed and approved by leadership.
- [ ] Acceptable use / code of conduct; employees and contractors acknowledge at onboarding.
- [ ] Defined security ownership (table in §3).
- [ ] How security issues are reported internally (and, when relevant, to customers) — communication.
- [ ] Background checks for roles with access to customer data (as applicable by role/region).
- [ ] Security awareness training at onboarding and periodically after.

### 4.3 Access control (CC6)

- [ ] Unique user accounts; no shared logins for systems touching customer data.
- [ ] MFA enforced on critical systems: cloud host(s), GitHub, database consoles, email/IdP, compliance platform.
- [ ] Least privilege; inventory of who has access to what and why (prod, staging, Neon, Railway, Vercel, Ops).
- [ ] Access grant and revoke process (offboarding: revoke same day).
- [ ] Periodic access reviews (quarterly typical) with **evidence** (dated review artifact).
- [ ] Encryption in transit (TLS) and at rest — document provider controls + our configuration.
- [ ] Secrets management: no secrets in git; rotation process; env/secret store only.
- [ ] Privileged / break-glass access to tenant data documented (ops support, white-glove).

### 4.4 Change management (CC8)

- [ ] Version control for all production code (Git).
- [ ] Documented path: develop → review → deploy to production.
- [ ] Peer review / approval before production (PR review enforced).
- [ ] Separation of development, staging/sandbox, and production.
- [ ] Dependency / secret scanning in CI (baseline vulnerability hygiene).

### 4.5 System operations and monitoring (CC7)

- [ ] Logging of systems and security-relevant access (including privileged ops actions where feasible).
- [ ] Alerting on security- and availability-relevant events.
- [ ] Documented incident-response plan (roles, severity, customer notification triggers).
- [ ] Vulnerability management process (how findings are triaged and fixed).
- [ ] Asset inventory: systems that store or process customer data.

### 4.6 Risk and vendors (CC3, CC9)

- [ ] Documented risk assessment (threats, likelihood, mitigation).
- [ ] Subprocessor / vendor inventory with compliance posture (collect their SOC 2 / ISO reports under NDA).
- [ ] Vendor review cadence for material processors (hosting, DB, email, LLM, billing).
- [ ] Business continuity / disaster recovery plan.
- [ ] Physical security: largely **inherited** from cloud providers — document reliance on their controls rather than inventing a data-center program.

### 4.7 Availability-specific (in scope)

- [ ] Documented uptime monitoring and any customer-facing availability commitments (be precise; don’t invent SLAs you won’t meet).
- [ ] Backups configured; **restore tested** (evidence of a successful restore test, not only “backups enabled”).

### 4.8 Confidentiality-specific (in scope)

- [ ] Data classification (what is confidential; how handled).
- [ ] Customer data handling procedures (ingest, storage, support access).
- [ ] Retention and deletion on contract end / customer request.
- [ ] White-glove path: read-only where possible, documented access method, revocation after engagement.

### 4.9 Secure SDLC extras (strongly recommended)

- [ ] Branch protection + required reviews on production branches.
- [ ] Dependency vulnerability scanning (e.g. GitHub Dependabot / equivalent).
- [ ] Periodic penetration test or external vulnerability assessment (annual is a common buyer expectation; confirm with auditor/platform).

### 4.10 Enabling moves

- [ ] Select compliance-automation platform early (integrates with GitHub/cloud, maps controls, continuous evidence).
- [ ] Select independent CPA / audit firm (platform partner networks are fine).
- [ ] Book Type I only once core controls are **live**, not merely drafted.

---

## 5. Evidence: what “done” looks like

Auditors need artifacts, not intent. Examples:

| Control | Example evidence |
|---------|------------------|
| Access review | Dated spreadsheet/export of GitHub + cloud + DB admins, reviewer sign-off |
| MFA | IdP/cloud screenshots or platform integration status |
| Change management | PR links + deploy history for a sample period |
| Backup restore | Ticket/notes + screenshot from restore test date |
| IR plan | Approved doc + tabletop exercise notes |
| Vendor review | Folder of subprocessor SOC reports + review checklist |
| Tenant isolation | Test plan + results showing Org A cannot read Org B |
| Offboarding | Checklist completed for a departed user (or dry-run) |

---

## 6. How SOC 2 maps to what we tell customers

**It removes a hard blocker more than it wins deals outright.** For mid-market and enterprise, “Do you have SOC 2?” is often a gate. Type I gives something to show while Type II runs; many buyers accept “Type I complete, Type II in observation” from an earlier-stage vendor.

**It reinforces trust — carefully.** SOC 2 attests that **we operate security/availability/confidentiality controls** as described. It does **not** by itself prove board numbers or ARR math are correct. Keep product claims (traceability, determinism, freeze packs) separate from compliance claims.

**Processing Integrity is not a shortcut to “certified calculations.”** If ever in scope later, describe it as attestation over **processing controls**, never as validation of financial methodology.

**Honesty with legal teeth.** Until a report is issued, say “pursuing” / “in progress,” never imply you hold SOC 2. Same discipline as the rest of SMPL external language.

### What we can say, and when

| Stage | Allowed language |
|-------|------------------|
| Before kickoff | Prefer security one-pager + DPA; avoid loud “SOC 2” claims |
| Platform + real control work started | “We are pursuing SOC 2” / “SOC 2 readiness in progress” |
| After Type I issued | “SOC 2 Type I complete; Type II in progress” (criteria as on report) |
| After Type II issued | “SOC 2 Type II” — report under NDA |
| Never | Implying a completed report early, or naming criteria not on the issued report |

### Sales unblockers **now** (before Type I)

Do not wait for the audit to answer questionnaires:

- [ ] Customer DPA (and privacy/security exhibits as needed)
- [ ] Subprocessors list (named vendors that touch customer data)
- [ ] Short security one-pager (encryption, tenant isolation, no GL write-back, auth model, AI key handling)
- [ ] Architecture / data-flow summary suitable for NDA review
- [ ] Honest roadmap line: SSO, richer audit logs, SOC 2 Type I target date (once set)

---

## 7. AI / LLM and white-glove appendices

### 7.1 AI / LLM

- Treat the LLM provider (e.g. Anthropic; OpenAI fallback if used) as a **subprocessor** when prompts may include customer-derived context.
- Document: keys only on the API, not in static board HTML or the browser.
- Document: AI drafts narrative from engine outputs; it is not the system of record for numbers.
- Capture contractual posture on training / retention where available from the vendor.
- Minimize sensitive raw PII in prompts; prefer aggregated metrics and governed freeze context.

### 7.2 White-glove / direct data access

- Prefer read-only shares / IAM; no write-back to customer GL/ERP.
- Document access method, scope, staging location, load procedure, and **revocation** after POC or on request.
- Privileged SMPL operators who can see tenant data: named, least privilege, reviewed.

---

## 8. Named vs abstracted architecture (compliance artifact)

External IT diagrams may abstract hosts (“managed edge / API / Postgres / LLM”) for durability and reduced attack-surface chatter.

SOC 2 needs the opposite for vendor and data-flow evidence:

- Keep an **internal named** diagram and subprocessors list (e.g. Vercel, Railway, Neon, Resend, Anthropic, Stripe, etc. — update as reality changes).
- Include **data categories** on flows: auth identifiers, financial warehouse facts, export artifacts, prompt context to LLM.
- External abstracted diagram stays customer-facing; named version is a compliance artifact.

---

## 9. Timeline and cost realism (order of magnitude)

| Milestone | Calendar (focused small team) | Notes |
|-----------|-------------------------------|--------|
| Platform kickoff + gap list | 1–3 weeks | Policies templates + integrations |
| Controls live enough for Type I | ~4–10 weeks | Depends on access reviews, logging, IR, restore test |
| Type I report | Often ~2–4 months from serious kickoff | Firm scheduling varies |
| Type II observation | Typically **3–12 months** of clean operation | Clock starts when controls are operating |
| Type II report | After observation + audit fieldwork | What most enterprises ultimately want |

**Cost ballpark (startup B2B SaaS):** compliance platform roughly low–mid five figures per year; auditor often mid–high five figures depending on scope and firm; plus meaningful engineering/ops time. Get current quotes — numbers move.

---

## 10. Suggested first moves

1. **Freeze Type I scope:** Security + Availability + Confidentiality; record PI as deferred in the decision log.
2. **Ship sales unblockers:** DPA, subprocessors list, security one-pager (parallel to audit prep).
3. **Select compliance platform** and connect GitHub + cloud accounts; accept the auto gap list as backlog.
4. **Name owners** (§3) and approve the core policy set.
5. **Close SMPL-specific gaps first:** MFA on admin systems, access reviews, privileged ops logging, backup restore test, tenant isolation evidence, AI/subprocessor write-up.
6. **Book Type I** once controls are live; then keep operating so the Type II window accumulates.
7. **Only then** revisit Processing Integrity as a deliberate positioning + audit-cost decision — with non-overclaiming language.

---

## Document control

| Field | Value |
|-------|--------|
| Title | SMPL.ai SOC 2 Readiness Reference |
| Version | 2 |
| Status | Internal working draft |
| Supersedes | v1 (`SMPL_SOC2_Readiness_Reference.md`) |
| Related | IT Technical Diagram; Technical White Paper v3; customer DPA / security one-pager (to be maintained alongside) |
