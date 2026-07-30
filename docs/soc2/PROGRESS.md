# SOC 2 Type I — Progress scoreboard

**Living checklist.** Update statuses as work completes. Parent plan: [../SOC2_TYPE1_KICKOFF.md](../SOC2_TYPE1_KICKOFF.md) · Scope: [../SMPL_SOC2_Readiness_Reference_v2.md](../SMPL_SOC2_Readiness_Reference_v2.md) · Decision log: [00_decision_log.md](./00_decision_log.md)

**Public progress UI:** [https://www.smpl-ai.com/compliance](https://www.smpl-ai.com/compliance) (marketing route `/compliance`)

**Scope locked (2026-07-22):** Security + Availability + Confidentiality **IN**; Processing Integrity + Privacy **DEFERRED**. All roles: **Matt Justice**. See [00_decision_log.md](./00_decision_log.md).

---

## Remaining checklist + target timeline

> **Read this first.** Solo-founder calendar — realistic, not fantasy. Windows are **targets**, not commitments. Owner of every open item: **Matt Justice**.
>
> **Type I is “compliant” / “done” only when an independent CPA Type I report is in hand.** Completing rows below is readiness, not certification.

### Target calendar (solo founder)

| Window | Target (not commitment) | Focus |
|--------|-------------------------|--------|
| **Week 1** | ~2026-07-22 → 2026-07-29 | **COMPLETE 2026-07-26** — MFA on admin consoles; access inventory first pass; protect `main` + required PR (GitHub ruleset; solo-friendly, approvals may be 0); break-glass = Neon/Railway MFA (no separate login) |
| **Week 2 (now)** | ~2026-07-29 → 2026-08-05 | **P01–P12 Approved 2026-07-27**; platform **deferred DIY** 2026-07-27; **P15 Approved v1.1 2026-07-28**; **DPA/MSA sent to counsel 2026-07-29** (awaiting redline). **Boundary/vendor Q1–Q10 locked 2026-07-28** (other vendor regions TBD). Approval ≠ SOC 2 certified |
| **Week 3–4** | ~2026-08-05 → 2026-08-19 | Access review #1 **signed 2026-07-29** (OK/Allow); **backup restore test Pass 2026-07-27**; IR tabletop notes; vendor SOC report collection started; DPA counsel redline / customer-ready draft (pack sent 2026-07-29) |
| **Month 2** | ~2026-08-19 → 2026-09-19 | Controls habitually running; secrets spot-check **Pass 2026-07-29**; tenant isolation **Pass 2026-07-29**; AI/LLM write-up (**P15 Approved 2026-07-28**); security one-pager published for sales |
| **Month 3–4** | ~2026-09-19 → 2026-11-19 | Engage CPA / Type I fieldwork **TARGET** (adjustable — not a commitment) |
| **After Type I** | Report in hand + 3–12 months | Type II observation window, then Type II report |

**Next guided item for Matt:** (1) Await DPA/MSA counsel redline / customer-ready draft (**R16 open** — pack **sent 2026-07-29**; chase checklist [evidence/dpa-counsel-chase-checklist-2026-07-29.md](./evidence/dpa-counsel-chase-checklist-2026-07-29.md)). (2) Vendor SOC **Matt-only portal downloads** — [evidence/vendor-soc/TRACKER.md](./evidence/vendor-soc/TRACKER.md) (public research done 2026-07-29; **no Type II received**). Security one-pager **published for sales under NDA 2026-07-29** (optional: attach PDF when a prospect asks). Secrets spot-check + tenant isolation **Pass 2026-07-29**. Reminder: readiness ≠ SOC 2 certified.

### Remaining `[!]` and `[ ]` items

| Status | Item | Owner | Target window | Notes |
|--------|------|-------|---------------|-------|
| `[x]` | MFA — GitHub org admins | Matt | Week 1 | Done 2026-07-26 |
| `[x]` | MFA — Vercel | Matt | Week 1 | Done 2026-07-26 |
| `[x]` | MFA — Railway | Matt | Week 1 | Done 2026-07-26 |
| `[x]` | MFA — Neon | Matt | Week 1 | Done 2026-07-26 |
| `[x]` | MFA — corporate email / IdP | Matt | Week 1 | Done 2026-07-26 |
| `[x]` | MFA — Stripe | Matt | Week 1 | Done 2026-07-26 |
| `[x]` | MFA — Sanity (if admin) | Matt | Week 1 | Done 2026-07-26 — IdP MFA via Google login (not Sanity-native toggle) |
| `[x]` | MFA — Resend | Matt | Week 1 | Done 2026-07-26 |
| `[x]` | MFA — Anthropic console | Matt | Week 1 | Done 2026-07-26 — IdP MFA via Google login (not Anthropic-native TOTP) |
| `[x]` | MFA — DNS / domain admin (Squarespace) | Matt | Week 1 | Done 2026-07-26 — Squarespace MFA for smpl-ai.com |
| `[x]` | Confirm no shared prod passwords | Matt | Week 1 | Confirmed 2026-07-26 — no shared prod passwords |
| `[x]` | Protect `main` + required PR review | Matt | Week 1 | Done 2026-07-26 — GitHub branch ruleset; required PR before merge; solo-friendly (approvals may be 0) |
| `[x]` | Leadership approve core policies (P01–P12 / core set) | Matt | Week 2 | **Approved 2026-07-27** by Matt Justice — approval ≠ SOC 2 certified |
| `[x]` | Compliance platform choice **or** “wait until ____” | Matt | Week 2 | **Deferred DIY 2026-07-27** — docs/soc2 + `/app/compliance`; revisit on enterprise GRC requirement **or** CPA Type I engagement (whichever first) |
| `[x]` | Confirm boundary matches production | Matt | Week 2–3 | **Locked 2026-07-28** — Matt Q1–Q10 answered; [01_system_boundary.md](./01_system_boundary.md) |
| `[x]` | Confirm vendor regions / unused vendors; OpenAI if live | Matt | Week 2–3 | **Locked 2026-07-28** — OpenAI/APM unused; Sanity/HubSpot off product DPA; Neon **us-east-1**; **other vendor regions TBD** — [02_subprocessors.md](./02_subprocessors.md) |
| `[x]` | Dependabot + GitHub secret scanning enabled | Matt | Week 2–3 | **Confirmed 2026-07-28** — PR #19 merged; alerts, security updates, Secret Protection, push protection — [evidence/dependabot-enabled-2026-07-28.md](./evidence/dependabot-enabled-2026-07-28.md) |
| `[x]` | First quarterly-style access review sign-off | Matt | Week 3–4 | **Signed 2026-07-29** — OK/Allow; Matt Justice (security owner + exec sponsor); corporate email mattjustice@smpl-ai.com; items 1–12 OK — [evidence/access-review-2026-Q3.md](./evidence/access-review-2026-Q3.md); readiness only — not SOC 2 certified |
| `[x]` | Neon backup **restore test** evidence | Matt | Week 3–4 | **Pass 2026-07-27** — PITR throwaway `restore-test-2026-07-27`; Railway URL unchanged — [evidence/neon-restore-test-2026-07-27.md](./evidence/neon-restore-test-2026-07-27.md) |
| `[x]` | IR tabletop notes (operable IR) | Matt | Week 3–4 | **Complete 2026-07-28** — Scenarios A + B; async/chat-facilitated — [evidence/ir-tabletop-2026-07-28.md](./evidence/ir-tabletop-2026-07-28.md); readiness evidence only — not SOC 2 certified |
| `[~]` | Vendor SOC / ISO reports folder (under NDA) — collection **in progress** | Matt | Week 3–4 | **Public research 2026-07-29** — [evidence/vendor-soc/TRACKER.md](./evidence/vendor-soc/TRACKER.md) + [PUBLIC_RESEARCH_2026-07-29.md](./evidence/vendor-soc/PUBLIC_RESEARCH_2026-07-29.md). P0 + GitHub → `researched` / Stripe `public summary available` (SOC 3 only). **No Type II received.** PDFs outside git / gitignored. |
| `[~]` | Customer DPA / MSA — **single legal workstream** (privacy, retention, subprocessors) | Matt | Week 3–4 | **Sent to counsel 2026-07-29** — awaiting redline / customer-ready draft; R16 **not** closed. Firm: unspecified. Chase checklist [evidence/dpa-counsel-chase-checklist-2026-07-29.md](./evidence/dpa-counsel-chase-checklist-2026-07-29.md); send attestation [evidence/dpa-counsel-sent-2026-07-29.md](./evidence/dpa-counsel-sent-2026-07-29.md); also [P10](./policies/P10_risk_assessment.md) R16; P07/P08/P09 cross-ref only |
| `[x]` | Secrets only in env stores (spot-check) | Matt | Month 2 | **Pass 2026-07-29** — git hygiene + Vercel/Railway/Neon consoles; Matt confirmed console checks + Org-B-only T1/T2 2026-07-29 via chat — [evidence/secrets-env-store-spotcheck-2026-07-29.md](./evidence/secrets-env-store-spotcheck-2026-07-29.md); readiness only — not SOC 2 certified |
| `[x]` | Tenant isolation evidence (Org A ≠ Org B) | Matt | Month 2 | **Pass 2026-07-29** — unit/SQL/unauth + Matt confirmed Org-B-only authenticated T1/T2 via chat — [evidence/tenant-isolation-2026-07-29.md](./evidence/tenant-isolation-2026-07-29.md); readiness only — not SOC 2 certified |
| `[x]` | **P15** AI/LLM Data Handling — Approved | Matt | Week 2 | **Approved 2026-07-28** v1.1 (machine-primary grounding) — [P15](./policies/P15_ai_llm_data_handling.md); approval ≠ SOC 2 certified |
| `[x]` | Security one-pager **published** for sales | Matt | Month 2 | **Published for sales under NDA 2026-07-29** — [SECURITY_ONE_PAGER.md](./SECURITY_ONE_PAGER.md) + [SMPL_Security_One_Pager_2026-07.pdf](./SMPL_Security_One_Pager_2026-07.pdf); evidence [evidence/security-one-pager-published-2026-07-29.md](./evidence/security-one-pager-published-2026-07-29.md); no public `/security` page; readiness only — not SOC 2 certified |
| `[!]` | Target Type I month (YYYY-MM) | Matt | Month 2–3 | Even approximate; mark TARGET |
| `[!]` | Audit firm shortlist / engagement | Matt | Month 3–4 | Independent CPA — **TARGET** fieldwork |
| `[!]` | Engage CPA; schedule Type I fieldwork | Matt | Month 3–4 | **TARGET**, not commitment |
| `[ ]` | **Type I report issued** | Matt + CPA | When report in hand | **Only then** Type I is “done” / shareable as Type I |
| `[ ]` | Type II observation (3–12 months) + Type II report | Matt + CPA | After Type I | Keep controls operating |

---

## How to update the public `/compliance` page

This markdown file is the **working scoreboard** for the team. The live site reads statuses from a TypeScript module that mirrors the phases/items below:

| Layer | Path |
|-------|------|
| Internal checklist (you are here) | `docs/soc2/PROGRESS.md` |
| Public page data | `frontend/lib/compliance/progress.ts` |
| UI | `frontend/components/compliance/ComplianceProgressDashboard.tsx` |

**When a status changes:**

1. Update the mark in this file (`[x]` / `[~]` / `[ ]` / `[!]`).
2. Update the matching item in `frontend/lib/compliance/progress.ts` (`done` / `in_progress` / `open` / `needs_owner`).
3. Bump `lastUpdated` (YYYY-MM-DD) in that TS module.
4. Deploy the frontend (Vercel) so [smpl-ai.com/compliance](https://www.smpl-ai.com/compliance) reflects the change.

Do **not** mark Type I complete on the public page until a CPA report is in hand.

---

## Critical honesty (read first)

SMPL is **not** “SOC 2 compliant” and is **not** “SOC 2 certified” until an **independent CPA firm** issues a SOC 2 report.

| What we are doing | What we are not doing |
|-------------------|------------------------|
| Readiness: design controls, write policies, gather evidence | Claiming compliance or certification |
| Preparing for a Type I engagement | Issuing or “passing” an audit ourselves |
| Tracking gaps so Matt can engage an auditor | Buying Vanta/Drata now (deferred DIY until enterprise GRC req or CPA engagement) |

**Sales language until a report exists:** “We are pursuing SOC 2” / “SOC 2 readiness in progress.” Never “we are SOC 2 certified.”

---

## Definition of done — Type I

**Done = an independent CPA firm has issued a SOC 2 Type I report** covering the Trust Services Criteria we scoped (**Security + Availability + Confidentiality**), and that report is in hand (typically shared with customers under NDA).

Everything before that is **readiness + evidence**. A completed checklist in this repo is necessary prep; it is **not** compliance.

Type II comes later: after Type I, controls operate over an observation window (often 3–12 months), then the firm issues a Type II report.

---

## Phase map

| Phase | Status | Exit criteria |
|-------|--------|---------------|
| 1. Kickoff | [~] In progress | Scope **APPROVED** + owners named; platform **deferred DIY**; **target month / CPA still open** |
| 2. Controls live | [~] In progress | Policies **approved** (P01–P12 2026-07-27; P15 v1.1 2026-07-28); MFA + access inventory; change/deploy path + Dependabot/secret scanning **confirmed 2026-07-28**; IR approved + **tabletop complete 2026-07-28**; access review **signed 2026-07-29**; secrets + tenant isolation **Pass 2026-07-29**; vendor reports still open |
| 3. Type I audit | [ ] Open | CPA firm engaged; fieldwork complete; **Type I report issued** |
| 4. Type II observation | [ ] Open | Controls operate cleanly over window; Type II report issued |

---

## Status legend

| Mark | Meaning |
|------|---------|
| `[x]` | Done |
| `[~]` | In progress |
| `[ ]` | Open |
| `[!]` | Needs Matt (cannot finish from repo alone) |

---

## Checklist

### A. Kickoff & governance

| Status | Item | Notes |
|--------|------|-------|
| `[x]` | Kickoff plan published | [../SOC2_TYPE1_KICKOFF.md](../SOC2_TYPE1_KICKOFF.md) |
| `[x]` | Readiness reference (scope + criteria) | [../SMPL_SOC2_Readiness_Reference_v2.md](../SMPL_SOC2_Readiness_Reference_v2.md) |
| `[x]` | Working folder `docs/soc2/` seeded | Decision log, boundary, subprocessors, access template, policy index, week1 checklist |
| `[x]` | This scoreboard created | You are here |
| `[x]` | Decision log — scope + owners **APPROVED** | [00_decision_log.md](./00_decision_log.md) — Sec+Avail+Conf **IN**; PI + Privacy **DEFERRED**; all owners Matt Justice (**2026-07-22 APPROVED**) |
| `[x]` | Freeze Type I criteria: Sec + Avail + Conf; PI deferred; Privacy skip | **APPROVED** 2026-07-22 |
| `[x]` | Name executive sponsor | Matt Justice |
| `[x]` | Name security owner | Matt Justice |
| `[x]` | Name engineering owner | Matt Justice (all roles for now) |
| `[x]` | Name ops / CS privileged-access owner | Matt Justice (all roles for now) |
| `[x]` | Compliance platform choice **or** explicit “wait until ____” | **Deferred DIY 2026-07-27** — [00_decision_log.md](./00_decision_log.md). Use docs/soc2 + `/app/compliance`. Triggers (whichever first): paying enterprise requires formal GRC platform **or** CPA Type I engagement |
| `[!]` | Target Type I month | Even approximate YYYY-MM — **TARGET**, not commitment |
| `[!]` | Audit firm shortlist / engagement | Independent CPA; platform partner network OK later |

### B. System boundary & vendors (documentation)

| Status | Item | Notes |
|--------|------|-------|
| `[x]` | System boundary draft from known stack | [01_system_boundary.md](./01_system_boundary.md) — Vercel, Railway, Neon, Auth.js, Resend, Anthropic, Stripe, GitHub; prod hosts named; Sanity out of Type I (marketing) |
| `[x]` | Boundary TBDs assigned | **Q1–Q10 locked 2026-07-28** — remaining honest TBD = other vendor regions only |
| `[x]` | Confirm boundary matches production | **Locked 2026-07-28** by Matt Justice — [01_system_boundary.md](./01_system_boundary.md) |
| `[x]` | Subprocessors named list draft | [02_subprocessors.md](./02_subprocessors.md) — product DPA list; Neon us-east-1; other regions TBD |
| `[x]` | Confirm regions / unused vendors; mark OpenAI if live | **Locked 2026-07-28** — OpenAI **NO**; Neon us-east-1; other regions **TBD** |
| `[~]` | Vendor SOC / ISO reports folder (under NDA) | **Public research 2026-07-29** — [evidence/vendor-soc/TRACKER.md](./evidence/vendor-soc/TRACKER.md); **no Type II received** (Stripe public SOC 3 only) — Matt portal downloads next |
| `[~]` | Customer DPA / MSA — **single legal workstream** | **Sent to counsel 2026-07-29** — awaiting redline / customer-ready draft; R16 **not** closed. Firm: unspecified. Chase [evidence/dpa-counsel-chase-checklist-2026-07-29.md](./evidence/dpa-counsel-chase-checklist-2026-07-29.md); send [evidence/dpa-counsel-sent-2026-07-29.md](./evidence/dpa-counsel-sent-2026-07-29.md). Also P10 R16 (covers privacy/retention/subprocessors formerly flagged in P07–P09) |
| `[x]` | Security one-pager (draft → published for sales) | [SECURITY_ONE_PAGER.md](./SECURITY_ONE_PAGER.md) + PDF [SMPL_Security_One_Pager_2026-07.pdf](./SMPL_Security_One_Pager_2026-07.pdf) — honest “pursuing SOC 2”; **published for sales under NDA 2026-07-29** — [evidence/security-one-pager-published-2026-07-29.md](./evidence/security-one-pager-published-2026-07-29.md); not certified |

### C. Access hardening (Matt / ops)

| Status | Item | Notes |
|--------|------|-------|
| `[x]` | MFA — GitHub org admins | Done 2026-07-26 |
| `[x]` | MFA — Vercel | Done 2026-07-26 |
| `[x]` | MFA — Railway | Done 2026-07-26 |
| `[x]` | MFA — Neon | Done 2026-07-26 |
| `[x]` | MFA — corporate email / IdP | Done 2026-07-26 |
| `[x]` | MFA — Stripe | Done 2026-07-26 |
| `[x]` | MFA — Sanity (if admin) | Done 2026-07-26 — IdP MFA via Google login (provider-level, not Sanity-native) |
| `[x]` | MFA — Resend | Done 2026-07-26 |
| `[x]` | MFA — Anthropic console | Done 2026-07-26 — IdP MFA via Google login (not Anthropic-native TOTP) |
| `[x]` | MFA — DNS / domain admin (Squarespace) | Done 2026-07-26 — Squarespace MFA for smpl-ai.com |
| `[x]` | Access inventory — people + roles filled | [03_access_inventory_template.md](./03_access_inventory_template.md) — first pass complete 2026-07-26; ops/break-glass = same MFA as Neon/Railway (solo; no separate login) |
| `[x]` | Confirm no shared prod passwords | Confirmed 2026-07-26 |
| `[x]` | First quarterly-style access review sign-off | **Signed 2026-07-29** — OK/Allow; [evidence/access-review-2026-Q3.md](./evidence/access-review-2026-Q3.md); readiness only — not SOC 2 certified |

### D. Policies

| Status | Item | Notes |
|--------|------|-------|
| `[x]` | Policy index | [04_policy_index.md](./04_policy_index.md) |
| `[x]` | Draft stubs expanded: ISP, Acceptable Use, Access Control, IR, Change Mgmt | [policies/](./policies/) P01–P05 |
| `[x]` | Core policies P01–P12 drafted (approval-ready) | P06–P12 expanded; P07 + P10 created 2026-07-26 |
| `[x]` | Leadership approve core policies | **Approved 2026-07-27** by Matt Justice — [04_policy_index.md](./04_policy_index.md). Approval ≠ SOC 2 certified; evidence items remain |
| `[x]` | **P15** AI / LLM Data Handling — Approved | **Approved 2026-07-28** by Matt Justice — [policies/P15_ai_llm_data_handling.md](./policies/P15_ai_llm_data_handling.md); approval ≠ SOC 2 certified |

### E. Engineering hygiene

| Status | Item | Notes |
|--------|------|-------|
| `[x]` | Protect `main` + required PR review | Done 2026-07-26 — GitHub branch ruleset; required PR before merge; solo-friendly (approvals may be 0) |
| `[x]` | Document deploy path (Vercel FE, Railway API) + who can promote | [CHANGE_MANAGEMENT.md](./CHANGE_MANAGEMENT.md) — Matt can promote; GitHub/Vercel/Railway MFA done; branch protection live 2026-07-26 |
| `[x]` | Dependabot + GitHub secret scanning enabled | **Confirmed 2026-07-28** — PR #19; Matt confirmed 4 Code security toggles — [evidence/dependabot-enabled-2026-07-28.md](./evidence/dependabot-enabled-2026-07-28.md) |
| `[x]` | Secrets only in env stores (not git) | **Pass 2026-07-29** — git + consoles; Matt confirmed via chat — [evidence/secrets-env-store-spotcheck-2026-07-29.md](./evidence/secrets-env-store-spotcheck-2026-07-29.md); readiness only — not SOC 2 certified |
| `[x]` | Calendar or complete Neon backup **restore test** | **Pass 2026-07-27** — PITR throwaway validated; [evidence/neon-restore-test-2026-07-27.md](./evidence/neon-restore-test-2026-07-27.md) |
| `[x]` | Tenant isolation evidence (Org A ≠ Org B) | **Pass 2026-07-29** — unit/SQL/unauth + Matt confirmed Org-B-only T1/T2 via chat — [evidence/tenant-isolation-2026-07-29.md](./evidence/tenant-isolation-2026-07-29.md); readiness only — not SOC 2 certified |
| `[x]` | **P15** + AI/LLM / Anthropic write-up | **Approved 2026-07-28** — [policies/P15_ai_llm_data_handling.md](./policies/P15_ai_llm_data_handling.md) |

### F. Pre–Type I readiness bar (from readiness v2)

Book the auditor only when these are **live**, not merely drafted:

| Status | Control area |
|--------|----------------|
| `[x]` | MFA on admin/cloud accounts | Cloud + DNS (Squarespace) done 2026-07-26 (Anthropic via Google IdP); ops/break-glass covered by Neon/Railway MFA (solo; no separate login) |
| `[x]` | Written policies **approved** by leadership | P01–P12 Approved 2026-07-27; **P15 Approved 2026-07-28**; approval ≠ certified |
| `[x]` | Access inventory + first review artifact | Inventory first pass done; Q3 review **signed 2026-07-29** — [evidence/access-review-2026-Q3.md](./evidence/access-review-2026-Q3.md); readiness only — not SOC 2 certified |
| `[x]` | Documented change/deploy path + PR review on `main` | Path documented; GitHub ruleset protecting `main` live 2026-07-26; Dependabot + secret scanning confirmed 2026-07-28 |
| `[x]` | Incident response plan (approved + operable) | **Approved** 2026-07-27; tabletop **complete 2026-07-28** ([runbooks/ir-tabletop.md](./runbooks/ir-tabletop.md); [evidence/ir-tabletop-2026-07-28.md](./evidence/ir-tabletop-2026-07-28.md)) |
| `[x]` | Backup restore test evidence | **Pass 2026-07-27** — PITR throwaway; [evidence/neon-restore-test-2026-07-27.md](./evidence/neon-restore-test-2026-07-27.md) |
| `[~]` | Subprocessor inventory + vendor reports collected | Inventory **locked** 2026-07-28; public research **2026-07-29** ([evidence/vendor-soc/](./evidence/vendor-soc/)); Type II reports **not** received/reviewed |
| `[x]` | Tenant isolation evidence | Month 2 — **Pass 2026-07-29**; Matt confirmed Org-B-only T1/T2 via chat — [evidence/tenant-isolation-2026-07-29.md](./evidence/tenant-isolation-2026-07-29.md); readiness only — not SOC 2 certified |
| `[x]` | **P15** + AI/subprocessor write-up for Anthropic | **Approved 2026-07-28** |

### G. Type I → Type II

| Status | Item |
|--------|------|
| `[!]` | Engage CPA firm; schedule fieldwork | **TARGET** Month 3–4 |
| `[ ]` | Type I report issued → **this is when Type I is “done”** |
| `[ ]` | Keep controls operating; start Type II observation clock |
| `[ ]` | Type II report issued |

---

## What we checked off this wave (2026-07-22) — documentation only

Not compliance. No Vanta signup. Not certified.

1. Decision log: scope Sec+Avail+Conf **APPROVED** by Matt; PI + Privacy deferred; **all owners = Matt Justice**; platform later deferred DIY (2026-07-27)
2. Remaining checklist + solo-founder target timeline published (this section)
3. P01–P05 expanded; P06 / P08 / P09 / P11 / P12 drafted
4. Customer-facing [SECURITY_ONE_PAGER.md](./SECURITY_ONE_PAGER.md) (honest pursuing language)
5. [CHANGE_MANAGEMENT.md](./CHANGE_MANAGEMENT.md) — GitHub → Vercel/Railway
6. Access inventory rows filled (owner Matt)
7. Scoreboard + `/compliance` data synced

## What we checked off 2026-07-26 — access hygiene (Matt)

Not SOC 2 certified. Readiness evidence only.

1. MFA enabled: GitHub, Vercel, Railway, Neon, corporate email/IdP, Stripe, Resend, Domain DNS / Squarespace (smpl-ai.com)
2. Sanity: MFA via Google IdP login (provider-level; not a Sanity-native MFA toggle)
3. Anthropic: MFA via Google IdP login (same pattern; not Anthropic-native TOTP)
4. Confirmed: **no shared prod passwords**
5. Ops/break-glass: **N/A as separate login** — solo founder; privileged DB/ops access is via MFA’d Neon/Railway consoles already inventoried
6. GitHub branch ruleset: protect `main` + required PR before merge (solo-friendly; approvals may be 0)
7. **Week 1 marked COMPLETE** (readiness only — not SOC 2 certified)

---

## Top `[!]` for Matt (do next)

1. **[~]** Customer DPA / MSA — **Sent to counsel 2026-07-29** — awaiting redline / customer-ready draft; R16 **not** closed ([evidence/dpa-counsel-sent-2026-07-29.md](./evidence/dpa-counsel-sent-2026-07-29.md); chase [evidence/dpa-counsel-chase-checklist-2026-07-29.md](./evidence/dpa-counsel-chase-checklist-2026-07-29.md); pack [legal/COUNSEL_SEND_PACKAGE.md](./legal/COUNSEL_SEND_PACKAGE.md))
2. **[~]** Vendor SOC / ISO — **Matt-only Trust Center / Documents downloads** ([evidence/vendor-soc/TRACKER.md](./evidence/vendor-soc/TRACKER.md)). Public research done 2026-07-29; **no Type II received**
3. **[!]** Target Type I month + audit-firm shortlist (**TARGET**, not commitment)
4. Open evidence (keep honest): Staging **exists, no Customer Data** (Q3 locked). Other vendor **regions TBD**. Access review **signed 2026-07-29**. Restore test **Pass** 2026-07-27 (P12). **IR tabletop complete** 2026-07-28 (P04). **Dependabot + secret scanning confirmed** 2026-07-28 (P05). **P15 Approved v1.1** 2026-07-28
5. Platform purchase **deferred DIY** (decided 2026-07-27) — revisit on enterprise GRC requirement or CPA Type I engagement

---

## What we checked off 2026-07-26 — P01–P12 drafts ready for approval

Not approved at the time. Not SOC 2 certified. Readiness documentation only.

1. Created **P07** (Customer Data / Confidentiality Procedures) and **P10** (Risk Assessment + initial register)
2. Expanded P06, P08, P09, P11, P12 to approval-ready drafts (same structure as P01–P05)
3. P01 control-theme table now links P07/P10; policy index + policies README updated
4. Scoreboard + `/compliance` data: drafts **ready for approval**; leadership approval remains **[!]**

## What we checked off 2026-07-27 — P01–P12 Approved (Matt review + sign-off)

**Not SOC 2 certified.** Approving policies ≠ CPA Type I report. Open evidence items remain.

1. Matt review fixes before approval: immutability vs retention clarity (P08/P01); P10 **R15** Railway in-flight export interrupt (`ThreadPoolExecutor` + durable Postgres metadata); **R16** consolidated Customer DPA/MSA legal workstream; **P15** tracked as draft-next
2. **P01–P12 Approved** 2026-07-27 by Matt Justice — approval tables + [04_policy_index.md](./04_policy_index.md)
3. Incomplete flags left honest: restore test not run; IR tabletop not scheduled; staging / Dependabot not confirmed (P05)
4. Scoreboard + `/compliance` data synced

## What we checked off 2026-07-27 — Platform deferral + P15 draft

**Not SOC 2 certified.** Drafting P15 ≠ approved policy ≠ CPA Type I report.

1. **Compliance platform deferred DIY** — Matt decided not to buy Vanta/Drata/etc. now; continue with [docs/soc2/](./) + `/app/compliance`. Revisit when **either**: first paying enterprise requires a formal GRC/compliance platform, **or** CPA engagement for Type I (whichever first). Logged in [00_decision_log.md](./00_decision_log.md)
2. **P15** AI / LLM Data Handling drafted (approval-ready, **not approved**) — [policies/P15_ai_llm_data_handling.md](./policies/P15_ai_llm_data_handling.md)
3. Policy index, P02/P06/P10 cross-refs, scoreboard + `/compliance` data synced

## What we checked off 2026-07-27 — Neon restore test runbook (execution blocked)

**Not SOC 2 certified.** Runbook ≠ completed restore evidence.

1. Clarified scope: Neon already provides PITR/backups; test is throwaway-branch validation only — never change Railway `DATABASE_URL`
2. Added [runbooks/neon-restore-test.md](./runbooks/neon-restore-test.md) (Console clicks + API `parent_timestamp` PITR path + validation SQL)
3. Evidence stub [evidence/neon-restore-test-2026-07-27.md](./evidence/neon-restore-test-2026-07-27.md) — initially **Blocked** (no `NEON_API_KEY`)
4. P12 calendar checkbox + sign-off row updated; P10 R06 notes; scoreboard → in progress / blocked

## What we checked off 2026-07-27 — Neon restore test **Pass** (OAuth retry)

**Not SOC 2 certified.** Restore fire drill ≠ CPA Type I report.

1. Matt approved `neonctl` browser OAuth promptly
2. Created PITR throwaway branch `restore-test-2026-07-27` on `smpl-auth-prod` from `production` (`parent_timestamp` resolved `2026-07-27T19:38:21Z`)
3. Validated SQL on throwaway host only — core + warehouse tables; Demo Co present; sanitized counts filed
4. Railway / Vercel production URLs **unchanged**; branch left named for Matt to delete
5. Evidence + P12 sign-off + P10 R06 + scoreboard / `/compliance` data synced to **Pass**

## What we checked off 2026-07-28 — P15 Approved (redline + companion edits)

**Not SOC 2 certified.** Approving P15 ≠ CPA Type I report.

1. Applied Matt redline: expanded hallucination / "don't know" §4.7; Confidential AI prompt/debug log retention ≤ 30 days (§5)
2. Companion: P04 incident type + Sev2 + containment row for AI hallucination reaching a customer; P08 retention row for AI prompt/debug logs
3. **P15 Approved** 2026-07-28 by Matt Justice — approval table + [04_policy_index.md](./04_policy_index.md)
4. Cross-refs (P01/P02/P06/P09/P10), scoreboard + `/compliance` data synced

## What we checked off 2026-07-28 — Customer DPA / MSA outline (R16 started)

**Not SOC 2 certified.** Outline ≠ signed DPA ≠ legal advice. R16 remains open until counsel-ready / customer-offerable agreement.

1. Drafted counsel-ready outline — [legal/DPA_MSA_OUTLINE.md](./legal/DPA_MSA_OUTLINE.md) (parties/roles, processing, subprocessors, TOMs, breach, retention/immutability distinction, AI no-training, MSA pointers, exhibits)
2. Pulled from P07/P08/P09/P15, subprocessors list, security one-pager, Trust & Security positioning; no invented certifications
3. Scoreboard + `/compliance` data: DPA workstream → **in progress** (awaiting counsel); R16 **not** closed
4. Decision log note + P10 R16 treatment note updated

## What we packaged 2026-07-29 — DPA/MSA counsel send package (R16 still open)

**Not SOC 2 certified.** Send package ≠ email sent ≠ counsel engaged ≠ signed DPA. Agents do **not** email counsel — Matt must send.

1. Added [legal/COUNSEL_SEND_PACKAGE.md](./legal/COUNSEL_SEND_PACKAGE.md) — attach list, product/data flows, subprocessors, P15 fail-closed AI posture, Sanity/HubSpot outside product DPA, Neon us-east-1, open questions
2. Added [legal/DRAFT_EMAIL_TO_COUNSEL.md](./legal/DRAFT_EMAIL_TO_COUNSEL.md) — paste-ready short email for Matt
3. Updated outline status pointer; scoreboard + `/compliance` data: still **[~] in progress** — awaiting **Matt send**; R16 **not** closed
4. Decision log + P10 R16 treatment note refreshed

## What we logged 2026-07-29 — DPA/MSA **sent to counsel** (R16 still open)

**Not SOC 2 certified.** Send ≠ counsel redline ≠ customer-ready draft ≠ signed DPA. R16 **not** closed.

1. Matt replied **send** (treated as **sent**) 2026-07-29 via chat — counsel firm **unspecified**; agent did **not** email counsel
2. Evidence note — [evidence/dpa-counsel-sent-2026-07-29.md](./evidence/dpa-counsel-sent-2026-07-29.md)
3. Scoreboard + `/compliance` data: still **[~] / in_progress** — **Sent to counsel 2026-07-29** — awaiting redline / customer-ready draft; R16 **not** closed
4. Legal pack status lines + P10 R16 + decision log updated

## What we checked off 2026-07-28 — Production boundary + vendor confirmation pack

**Not SOC 2 certified.** Documenting the boundary ≠ Matt confirmation ≠ CPA Type I report.

1. Updated [01_system_boundary.md](./01_system_boundary.md): Type I system = **production**; named hosts (`www.smpl-ai.com`, Vercel project, `sfi-api-production`, Neon `smpl-auth-prod`); Squarespace DNS; Matt **Q1–Q10** YES/NO/TBD pack
2. Updated [02_subprocessors.md](./02_subprocessors.md): Neon **AWS us-east-1** from restore evidence; other vendor regions left **TBD**; OpenAI/HubSpot/APM/staging conditional; unused OpenAI not listed externally until confirmed live
3. Scoreboard + `/compliance` data: boundary/vendor items → **in progress** (awaiting Matt answers) — not marked done

## What we checked off 2026-07-28 — Boundary/vendor Q1–Q10 **LOCKED**

**Not SOC 2 certified.** Matt answers ≠ CPA Type I report. Other vendor regions remain **TBD**.

1. Matt locked Q1–Q10: Sanity **NO** (marketing only); OpenAI **NO**; staging exists / **no Customer Data**; hostnames **YES**; Neon **us-east-1 YES**; APM **NO**; HubSpot **NO** (sales CRM); Squarespace DNS-only **YES**; other regions **TBD**; no other Customer Data vendors **NO**
2. Updated [01_system_boundary.md](./01_system_boundary.md), [02_subprocessors.md](./02_subprocessors.md), [00_decision_log.md](./00_decision_log.md)
3. Closed scoreboard items: confirm boundary matches production; confirm unused vendors / OpenAI / Neon region (other regions stay TBD in subprocessors table)
4. Scoreboard + `/compliance` data synced

## What we checked off 2026-07-28 — Dependabot + GitHub secret scanning

**Not SOC 2 certified.** Enabling Dependabot and secret scanning = readiness evidence only — not CPA Type I report.

1. `.github/dependabot.yml` merged on `main` via PR **#19** (npm `/frontend`, pip `/backend`, weekly Monday)
2. Matt confirmed GitHub Code security toggles enabled: Dependabot alerts, Dependabot security updates, Secret Protection (secret scanning), push protection
3. Filed evidence — [evidence/dependabot-enabled-2026-07-28.md](./evidence/dependabot-enabled-2026-07-28.md)
4. P05 §6, [CHANGE_MANAGEMENT.md](./CHANGE_MANAGEMENT.md), IR tabletop follow-up #1, scoreboard + `/compliance` synced

## What we checked off 2026-07-28 — IR tabletop complete

**Not SOC 2 certified.** Tabletop evidence = operable-IR readiness only — not CPA Type I report.

1. Completed async/chat-facilitated tabletop (~55 min) — Scenarios A (credential leak, Sev2+) + B (AI hallucination → customer, Sev2)
2. Filed dated evidence — [evidence/ir-tabletop-2026-07-28.md](./evidence/ir-tabletop-2026-07-28.md) (removed WIP file)
3. Scenario B root cause = grounding/validation gate **fail-open** (not human-review skip); residual risk documented honestly per [controls/](./controls/README.md)
4. P04 §7 + runbook updated; scoreboard IR item → **[x]**; `/compliance` synced
5. Includes P15 v1.1 + Scenario B **Allow** from branch `soc2/p15-v11-scenario-b-allow` (merged via this PR if not yet on main)

## What we checked off 2026-07-28 — IR tabletop pack (awaiting run)

**Not SOC 2 certified.** Runbook ≠ completed tabletop evidence. Do **not** mark IR tabletop `[x]` until Matt runs the exercise and files dated notes.

1. Added solo-founder tabletop runbook — [runbooks/ir-tabletop.md](./runbooks/ir-tabletop.md) (~45–60 min; scenarios A credential leak, B AI hallucination → customer / P15+P04 Sev2)
2. Added blank evidence template — [evidence/ir-tabletop-TEMPLATE.md](./evidence/ir-tabletop-TEMPLATE.md) (copy → `ir-tabletop-YYYY-MM-DD.md` when run)
3. P04 §7 points at runbook; scoreboard IR item → **[~] pack ready / awaiting run** (not complete)

## What we Allowed 2026-07-28 — P15 v1.1 + Scenario B

**Not SOC 2 certified.** Allow / approval ≠ completed tabletop evidence. Do **not** mark IR tabletop complete until the full exercise is run.

1. **P15 v1.1 Approved** — machine-primary grounding (evidence binding, fail-closed, freeze-ID); human review before send not primary — [policies/P15_ai_llm_data_handling.md](./policies/P15_ai_llm_data_handling.md)
2. **IR Scenario B Allowed** (chat) — root cause = grounding/validation fail-open; +18% / EMEA vs freeze ~4% — [runbooks/ir-tabletop.md](./runbooks/ir-tabletop.md)
3. WIP evidence updated — [evidence/ir-tabletop-2026-07-28-WIP.md](./evidence/ir-tabletop-2026-07-28-WIP.md); **full 45–60 min run still pending**
4. Normative controls pack unchanged — [controls/](./controls/README.md)
5. P04 companion note — P15 v1.1 Approved

## What we drafted 2026-07-28 — P15 v1.1 + Scenario B (prior to Allow)

**Not SOC 2 certified.** Draft amendment ≠ Allowed. Do **not** forge Matt Allow. Do **not** mark IR tabletop complete.

1. **P15 v1.1 draft** — machine-primary grounding (evidence binding, fail-closed, freeze-ID); human review before send not primary — [policies/P15_ai_llm_data_handling.md](./policies/P15_ai_llm_data_handling.md)
2. **IR Scenario B rewrite** — root cause = grounding/validation fail-open; +18% / EMEA vs freeze ~4% — [runbooks/ir-tabletop.md](./runbooks/ir-tabletop.md)
3. P04 containment companion + WIP evidence — [evidence/ir-tabletop-2026-07-28-WIP.md](./evidence/ir-tabletop-2026-07-28-WIP.md)
4. **Normative controls pack** — [controls/](./controls/README.md) (`data_integrity_framework.md`, `data_sources_tieout_prompt.md`); Part 6 human sign-off adapted → periodic testing; honest implemented-vs-roadmap labels
5. **P15 §4.8 + Scenario B eradicate/prevent** — cite `_sources`, evidence-only Claude, freeze-ID, tie-out/second-pass as gates; residual = gates failed open; large commentary-vs-engine variance = unacceptable control failure

---

## What we prepared 2026-07-29 — Month 2 readiness pack (later closed same day)

**Not SOC 2 certified.** Prep pack items later closed same day where noted.

1. **Secrets env-store spot-check** — runnable runbook + evidence template — [runbooks/secrets-env-store-spotcheck.md](./runbooks/secrets-env-store-spotcheck.md) → **Pass** same day
2. **Tenant isolation (Org A ≠ Org B)** — test plan; Org A = SMPL Demo Co `8571e520-0687-4516-bdee-379f37c58c1f` — [runbooks/tenant-isolation-test.md](./runbooks/tenant-isolation-test.md) → **Pass** same day
3. **Security one-pager** — near-publish draft → **published for sales under NDA** same day — [runbooks/security-one-pager-publish.md](./runbooks/security-one-pager-publish.md)
4. Demo dashboard financials **unchanged**

---

## What we closed 2026-07-29 — Month 2 secrets + tenant isolation (Pass)

**Not SOC 2 certified.** Pass = readiness evidence only. Matt confirmed console checks + Org-B-only T1/T2 2026-07-29 via chat (same pattern as access-review Allow). Agent did **not** invent authenticated API logs.

1. **Secrets** — git hygiene **Pass** (agent) + Vercel/Railway/Neon A1–A5, B1–B5, C1 **Pass** (Matt chat). Evidence: [evidence/secrets-env-store-spotcheck-2026-07-29.md](./evidence/secrets-env-store-spotcheck-2026-07-29.md)
2. **Tenant isolation** — Org B = **Customer Corp** `cfa7c116-3a89-4dd1-91df-80d4ece5c59d`; unit membership **403** Pass; prod unauth **401** Pass; SQL tenants distinct; Matt confirmed Org-B-only user + authenticated T1/T2 **Pass**. Evidence: [evidence/tenant-isolation-2026-07-29.md](./evidence/tenant-isolation-2026-07-29.md)
3. Scoreboard + `/compliance`: both items `[x]` / `done`
4. Demo Co financial seed / Board / FE **unchanged**

---

## What we closed 2026-07-29 — Security one-pager published for sales (NDA)

**Not SOC 2 certified.** Published for sales = NDA-ready pack + scoreboard link — not a public `/security` page and not a CPA report.

1. Pre-publish checks complete — [runbooks/security-one-pager-publish.md](./runbooks/security-one-pager-publish.md)
2. Canonical markdown — [SECURITY_ONE_PAGER.md](./SECURITY_ONE_PAGER.md) (honest pursuing language; isolation Pass noted; share under NDA)
3. PDF export — [SMPL_Security_One_Pager_2026-07.pdf](./SMPL_Security_One_Pager_2026-07.pdf)
4. Evidence — [evidence/security-one-pager-published-2026-07-29.md](./evidence/security-one-pager-published-2026-07-29.md)
5. Scoreboard + `/compliance`: item `[x]` / `done`
6. Optional Matt step when a prospect asks: attach PDF under NDA

---

## What we executed 2026-07-29 — Month 2 secrets + tenant isolation (partial → later Pass)

**Superseded same day** by Pass closeout above. Earlier agent session: git Pass; consoles Blocked; authenticated T1/T2 Blocked pending Org-B-only invite. Matt completed remaining rows via chat attestation.

---

## What we checked off 2026-07-29 — Vendor SOC / ISO collection scaffold

**Not SOC 2 certified.** Scaffold ≠ reports collected ≠ CPA Type I. Do **not** mark vendor reports complete until P0 PDFs are reviewed under NDA.

1. Added [evidence/vendor-soc/](./evidence/vendor-soc/) — README (storage rules: PDFs outside git / gitignored `private/`), [TRACKER.md](./evidence/vendor-soc/TRACKER.md) with Trust Center / portal links, [REQUEST_TEMPLATES.md](./evidence/vendor-soc/REQUEST_TEMPLATES.md)
2. Vendors tracked: P0 Vercel, Railway, Neon, Stripe, Anthropic, Resend; P1 GitHub; P2 Sanity, Squarespace, Google IdP — all status **not started**
3. Scoreboard + `/compliance` data: vendor SOC → **[~] in progress / scaffold ready**; reports **not** received
4. Cross-refs: [02_subprocessors.md](./02_subprocessors.md), P09 evidence row, evidence README, `.gitignore` for vendor PDFs

---

## What we researched 2026-07-29 — Vendor SOC public Trust Centers (no Matt console)

**Not SOC 2 certified.** Public research ≠ Type II received. Scoreboard stays **[~]**.

1. Researched P0 + GitHub public docs / Trust Centers without Matt login or Allow — [evidence/vendor-soc/PUBLIC_RESEARCH_2026-07-29.md](./evidence/vendor-soc/PUBLIC_RESEARCH_2026-07-29.md)
2. Updated [TRACKER.md](./evidence/vendor-soc/TRACKER.md): P0 → `researched`; Stripe → `public summary available` (SOC 3 period 2024-10 → 2025-09); **no Type II `received`**
3. Saved public Stripe SOC 3 only under gitignored `private/` — not committed
4. DPA: added counsel chase checklist only — [evidence/dpa-counsel-chase-checklist-2026-07-29.md](./evidence/dpa-counsel-chase-checklist-2026-07-29.md); R16 **still open**; no invented customer-ready DPA
5. Scoreboard + `/compliance`: vendor SOC + DPA remain **[~] / in_progress**

---

## What we shipped 2026-07-30 — P15 claim-verify fail-closed (incremental)

**Not SOC 2 certified.** Product integrity gate — not a CPA report.

1. Reusable helper `backend/app/services/commentary/claim_verify.py` — extract material numeric claims; verify vs evidence package; TOL_ACTUALS **$1.00**; fail-closed omit / don't-know
2. **Live on** `/api/v1/commentary/generate` — evidence package in prompt + post-LLM verify + strip unsupported sections
3. **Live on** MD&A Prompt 2 package path — matrix mismatch hard-blocks emit; post-LLM strip of unverifiable commentary cells; all-unverifiable variance sheet blocks emit
4. **Live on** Prompt 5 deck — evidence in prompt; post-LLM hard-block on invented $/% in PPTX string literals
5. **Live on** board slide regenerate — per-bullet soft strip / don't-know
6. **Copilot** — structured evidence/attribution packages from bundle/TS/cash (+ freeze `sections`); blob supplement; **`_sources` tags** on evidence values (catalog + ENGINE_PATH) with warehouse `org_id` / `loaded_at` / `is_final` (honest nulls)
7. **Attribution v1:** `attribution_verify.py` — allowlist causal/driver claims; live on commentary generate, MD&A Prompt 2, Prompt 5 (soft-strip + hard-block-when-fully-wiped), board regenerate (per-bullet), Copilot structured packages; **deal-count / named-logo / magnitude dominance** + **multi-driver AND** — [controls/ai_attribution_verify.md](./controls/ai_attribution_verify.md)
8. **Citation verify:** post-LLM material money/%/Nx must cite `_sources` token on commentary generate, MD&A Prompt 2, Copilot — [controls/ai_claim_verify.md](./controls/ai_claim_verify.md)
9. **Production FE↔Board single-source** confirmed (shared outlook API/builder) + TS↔SRC $1 regression + **hydrate residue fix** (full row replace + prune closed Actuals) — [controls/fe_board_single_source.md](./controls/fe_board_single_source.md)
10. **DOM `data-source` overlay** + audit hotkey on Board/FE KPIs; **partial client `runTieOut`** (Rule C/A) gates live MD&A export + FINAL forecast promote — [controls/fe_board_single_source.md](./controls/fe_board_single_source.md)
11. Founder coverage checklist: [controls/ai_claim_verify.md](./controls/ai_claim_verify.md)
12. Demo Board/FE seed financials **unchanged** (no reseed)
13. Guarantee 4 corrected to machine-primary
---

## How you’ll know Type I is complete

**You hold a SOC 2 Type I report issued by an independent CPA firm** covering Security + Availability + Confidentiality (as scoped). Until then: readiness only.

---

## Document control

| Field | Value |
|-------|--------|
| Title | SMPL.ai SOC 2 Type I Progress Scoreboard |
| Status | Internal living draft |
| Last updated | 2026-07-30 (P15 citation/tags/AND + DOM overlay/runTieOut; vendor SOC public research — no Type II; DPA/MSA awaiting redline) |
| Related | [../SOC2_TYPE1_KICKOFF.md](../SOC2_TYPE1_KICKOFF.md), [00_decision_log.md](./00_decision_log.md) |
