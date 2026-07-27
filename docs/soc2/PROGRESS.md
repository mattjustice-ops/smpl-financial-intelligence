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
| **Week 2 (now)** | ~2026-07-29 → 2026-08-05 | **P01–P12 Approved 2026-07-27** (Matt Justice) — approval ≠ SOC 2 certified; open evidence remains. Next: platform decision (explicit Vanta wait date **or** signup); DPA legal path; P15 draft next |
| **Week 3–4** | ~2026-08-05 → 2026-08-19 | Access review #1 signed; backup restore test evidence; IR tabletop notes; vendor SOC report collection started; DPA draft → legal path |
| **Month 2** | ~2026-08-19 → 2026-09-19 | Controls habitually running; secrets spot-check; tenant isolation test evidence; AI/LLM subprocessor write-up finalized; security one-pager published for sales |
| **Month 3–4** | ~2026-09-19 → 2026-11-19 | Engage CPA / Type I fieldwork **TARGET** (adjustable — not a commitment) |
| **After Type I** | Report in hand + 3–12 months | Type II observation window, then Type II report |

**Next guided item for Matt:** Week 2 — policies **Approved**. Choose compliance platform **or** write “wait until ____” in the decision log; start consolidated **Customer DPA / MSA** legal path ([P10](./policies/P10_risk_assessment.md) R16); prioritize **P15** AI/LLM draft next. Reminder: approving ≠ SOC 2 certified.

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
| `[!]` | Compliance platform choice **or** “wait until ____” | Matt | Week 2 | ← **start here**; no auto-signup |
| `[!]` | Confirm boundary matches production | Matt | Week 2–3 | Resolve TBDs in boundary doc |
| `[!]` | Confirm vendor regions / unused vendors; OpenAI if live | Matt | Week 2–3 | |
| `[ ]` | First quarterly-style access review sign-off | Matt | Week 3–4 | After MFA verified + inventory stable |
| `[ ]` | Neon backup **restore test** evidence | Matt | Week 3–4 | Required before Type I |
| `[ ]` | IR tabletop notes (operable IR) | Matt | Week 3–4 | Plan draft exists; exercise + notes |
| `[ ]` | Vendor SOC / ISO reports folder (under NDA) — collection started | Matt | Week 3–4 | Vercel, Railway, Neon, Stripe, Anthropic, Resend, … |
| `[!]` | Customer DPA / MSA — **single legal workstream** (privacy, retention, subprocessors) | Matt | Week 3–4 | Canonical item — also [P10](./policies/P10_risk_assessment.md) R16; P07/P08/P09 cross-ref only |
| `[ ]` | Secrets only in env stores (spot-check) | Matt | Month 2 | |
| `[ ]` | Tenant isolation evidence (Org A ≠ Org B) | Matt | Month 2 | Test plan + results |
| `[!]` | **P15 draft next** — AI/LLM Data Handling + Anthropic write-up | Matt | Month 2 (draft sooner OK) | Prioritized next policy draft; referenced from P02/P06/P10 |
| `[ ]` | Security one-pager **published** for sales | Matt | Month 2 | Draft exists; publish / share under NDA |
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
| Tracking gaps so Matt can engage an auditor | Signing up for Vanta/Drata unless Matt decides |

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
| 1. Kickoff | [~] In progress | Scope **APPROVED** + owners named; scoreboard live — **platform / target month / CPA still open** |
| 2. Controls live | [~] In progress | Policies **approved** 2026-07-27; MFA + access inventory; change/deploy path; IR approved (tabletop open); restore test / vendor reports / tenant isolation still open |
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
| `[!]` | Compliance platform choice **or** explicit “wait until ____” | **TBD — Matt to decide** (Week 2 target). Do **not** buy until MFA started; **do not sign up for Vanta in this wave** |
| `[!]` | Target Type I month | Even approximate YYYY-MM — **TARGET**, not commitment |
| `[!]` | Audit firm shortlist / engagement | Independent CPA; platform partner network OK later |

### B. System boundary & vendors (documentation)

| Status | Item | Notes |
|--------|------|-------|
| `[x]` | System boundary draft from known stack | [01_system_boundary.md](./01_system_boundary.md) — Vercel, Railway, Neon, Auth.js, Resend, Anthropic, Stripe, GitHub, Sanity |
| `[~]` | Boundary TBDs assigned | Sanity in/out, staging projects, hostnames, OpenAI fallback, privileged ops list |
| `[!]` | Confirm boundary matches production | Matt — resolve TBDs |
| `[x]` | Subprocessors named list draft | [02_subprocessors.md](./02_subprocessors.md) |
| `[!]` | Confirm regions / unused vendors; mark OpenAI if live | Matt |
| `[ ]` | Vendor SOC / ISO reports folder (under NDA) | Collect Vercel, Railway, Neon, Stripe, Anthropic, Resend, etc. |
| `[!]` | Customer DPA / MSA — **single legal workstream** | Sales unblocker; counsel as needed — also P10 R16 (covers privacy/retention/subprocessors formerly flagged in P07–P09) |
| `[x]` | Security one-pager (draft) | [SECURITY_ONE_PAGER.md](./SECURITY_ONE_PAGER.md) — honest “pursuing SOC 2”; not certified. Publish for sales = Month 2 |

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
| `[ ]` | First quarterly-style access review sign-off | After inventory stable — Week 3–4 |

### D. Policies

| Status | Item | Notes |
|--------|------|-------|
| `[x]` | Policy index | [04_policy_index.md](./04_policy_index.md) |
| `[x]` | Draft stubs expanded: ISP, Acceptable Use, Access Control, IR, Change Mgmt | [policies/](./policies/) P01–P05 |
| `[x]` | Core policies P01–P12 drafted (approval-ready) | P06–P12 expanded; P07 + P10 created 2026-07-26 |
| `[x]` | Leadership approve core policies | **Approved 2026-07-27** by Matt Justice — [04_policy_index.md](./04_policy_index.md). Approval ≠ SOC 2 certified; evidence items remain |
| `[!]` | **P15 draft next** (AI / LLM Data Handling) | Prioritized; not a blocker for P01–P12 approval |

### E. Engineering hygiene

| Status | Item | Notes |
|--------|------|-------|
| `[x]` | Protect `main` + required PR review | Done 2026-07-26 — GitHub branch ruleset; required PR before merge; solo-friendly (approvals may be 0) |
| `[x]` | Document deploy path (Vercel FE, Railway API) + who can promote | [CHANGE_MANAGEMENT.md](./CHANGE_MANAGEMENT.md) — Matt can promote; GitHub/Vercel/Railway MFA done; branch protection live 2026-07-26 |
| `[ ]` | Secrets only in env stores (not git) | Spot-check / confirm — Month 2 |
| `[ ]` | Calendar or complete Neon backup **restore test** | Evidence required before Type I — Week 3–4 |
| `[ ]` | Tenant isolation evidence (Org A ≠ Org B) | Test plan + results — Month 2 |
| `[!]` | **P15 draft next** + AI/LLM / Anthropic write-up | Prioritized next policy draft — Month 2 (sooner OK) |

### F. Pre–Type I readiness bar (from readiness v2)

Book the auditor only when these are **live**, not merely drafted:

| Status | Control area |
|--------|----------------|
| `[x]` | MFA on admin/cloud accounts | Cloud + DNS (Squarespace) done 2026-07-26 (Anthropic via Google IdP); ops/break-glass covered by Neon/Railway MFA (solo; no separate login) |
| `[x]` | Written policies **approved** by leadership | P01–P12 Approved 2026-07-27; approval ≠ certified |
| `[~]` | Access inventory + first review artifact | Inventory first pass done; quarterly sign-off still open (Week 3–4) |
| `[x]` | Documented change/deploy path + PR review on `main` | Path documented; GitHub ruleset protecting `main` live 2026-07-26 |
| `[~]` | Incident response plan (approved + operable) | **Approved** 2026-07-27; tabletop **not scheduled** — still open |
| `[ ]` | Backup restore test evidence | **Not run** as of 2026-07-27 |
| `[ ]` | Subprocessor inventory + vendor reports collected | Inventory draft; reports not collected |
| `[ ]` | Tenant isolation evidence |
| `[!]` | **P15 draft next** + AI/subprocessor write-up for Anthropic |

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

1. Decision log: scope Sec+Avail+Conf **APPROVED** by Matt; PI + Privacy deferred; **all owners = Matt Justice**; platform TBD
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

1. **[!]** Platform: choose Vanta/Drata/etc. **or** write “wait until ____” in decision log ← **Week 2 start here**
2. **[!]** Customer DPA / MSA — **single legal workstream** (privacy, retention, subprocessors) — P10 R16
3. **[!]** **P15 draft next** — AI / LLM Data Handling (prioritized; not Type I blocker for approved P01–P12)
4. **[!]** Target Type I month + audit-firm shortlist (**TARGET**, not commitment)
5. **[!]** Resolve boundary TBDs / vendor regions
6. Open evidence (keep honest): restore test **not run** (P12); IR tabletop **not scheduled** (P04); staging / Dependabot **not confirmed** (P05)

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

---

## How you’ll know Type I is complete

**You hold a SOC 2 Type I report issued by an independent CPA firm** covering Security + Availability + Confidentiality (as scoped). Until then: readiness only.

---

## Document control

| Field | Value |
|-------|--------|
| Title | SMPL.ai SOC 2 Type I Progress Scoreboard |
| Status | Internal living draft |
| Last updated | 2026-07-27 |
| Related | [../SOC2_TYPE1_KICKOFF.md](../SOC2_TYPE1_KICKOFF.md), [00_decision_log.md](./00_decision_log.md) |
