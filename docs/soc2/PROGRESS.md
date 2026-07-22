# SOC 2 Type I — Progress scoreboard

**Living checklist.** Update statuses as work completes. Parent plan: [../SOC2_TYPE1_KICKOFF.md](../SOC2_TYPE1_KICKOFF.md) · Scope: [../SMPL_SOC2_Readiness_Reference_v2.md](../SMPL_SOC2_Readiness_Reference_v2.md)

**Public progress UI:** [https://www.smpl-ai.com/compliance](https://www.smpl-ai.com/compliance) (marketing route `/compliance`)

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
| 1. Kickoff | [~] In progress | Scope frozen in decision log; owners named; scoreboard + artifacts started |
| 2. Controls live | [ ] Open | Policies approved; MFA + access inventory; change/deploy path; IR; restore test; vendor evidence; tenant isolation evidence |
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
| `[~]` | Decision log — proposed defaults drafted | [00_decision_log.md](./00_decision_log.md) — **Matt must confirm/sign** |
| `[!]` | Freeze Type I criteria: Sec + Avail + Conf; PI deferred; Privacy skip | Proposed in decision log; confirm date + owner |
| `[!]` | Name executive sponsor | Proposed: Matt Justice — confirm |
| `[!]` | Name security owner | Proposed: Matt Justice — confirm |
| `[!]` | Name engineering owner | TBD — Matt names |
| `[!]` | Name ops / CS privileged-access owner | TBD — Matt names (may be same person) |
| `[!]` | Compliance platform choice **or** explicit “wait until ____” | Do **not** buy until MFA + access inventory started; **do not sign up for Vanta in this kickoff** |
| `[!]` | Target Type I month | Even approximate YYYY-MM |
| `[!]` | Audit firm shortlist / engagement | Independent CPA; platform partner network OK later |

### B. System boundary & vendors (documentation)

| Status | Item | Notes |
|--------|------|-------|
| `[x]` | System boundary draft from known stack | [01_system_boundary.md](./01_system_boundary.md) — Vercel, Railway, Neon, Auth.js, Resend, Anthropic, Stripe, GitHub, Sanity |
| `[~]` | Boundary TBDs assigned | Sanity in/out, staging projects, hostnames, OpenAI fallback, privileged ops list |
| `[!]` | Confirm boundary matches production | Engineering / Matt — resolve TBDs |
| `[x]` | Subprocessors named list draft | [02_subprocessors.md](./02_subprocessors.md) |
| `[!]` | Confirm regions / unused vendors; mark OpenAI if live | Matt / eng |
| `[ ]` | Vendor SOC / ISO reports folder (under NDA) | Collect Vercel, Railway, Neon, Stripe, Anthropic, Resend, etc. |
| `[!]` | Customer DPA — legal review / ship | Sales unblocker; counsel as needed |
| `[ ]` | Security one-pager | Encryption, tenant isolation, no GL write-back, auth, AI keys on API |

### C. Access hardening (Matt / ops)

| Status | Item | Notes |
|--------|------|-------|
| `[!]` | MFA — GitHub org admins | Evidence: screenshot or platform |
| `[!]` | MFA — Vercel | |
| `[!]` | MFA — Railway | |
| `[!]` | MFA — Neon | |
| `[!]` | MFA — corporate email / IdP | |
| `[!]` | MFA — Stripe | |
| `[!]` | MFA — Sanity (if admin) | |
| `[!]` | MFA — Resend / Anthropic consoles | |
| `[!]` | Access inventory — people + roles filled | Template ready: [03_access_inventory_template.md](./03_access_inventory_template.md) |
| `[!]` | Confirm no shared prod passwords | |
| `[ ]` | First quarterly-style access review sign-off | After inventory exists |

### D. Policies

| Status | Item | Notes |
|--------|------|-------|
| `[x]` | Policy index | [04_policy_index.md](./04_policy_index.md) |
| `[x]` | Draft stubs: ISP, Acceptable Use, Access Control, IR, Change Mgmt | [policies/](./policies/) — **DRAFT / not approved** |
| `[~]` | Remaining core policies (P06–P17) | Not started or later |
| `[!]` | Leadership approve core policies | Draft ≠ approved; auditor wants approved docs |

### E. Engineering hygiene

| Status | Item | Notes |
|--------|------|-------|
| `[ ]` / `[!]` | Protect `main` + required PR review | Confirm in GitHub settings |
| `[ ]` | Document deploy path (Vercel FE, Railway API) + who can promote | |
| `[ ]` | Secrets only in env stores (not git) | Spot-check / confirm |
| `[ ]` | Calendar or complete Neon backup **restore test** | Evidence required before Type I |
| `[ ]` | Tenant isolation evidence (Org A ≠ Org B) | Test plan + results |
| `[ ]` | AI/LLM data-handling write-up aligned with P15 | Keys on API; narrative from engine outputs |

### F. Pre–Type I readiness bar (from readiness v2)

Book the auditor only when these are **live**, not merely drafted:

| Status | Control area |
|--------|----------------|
| `[ ]` | MFA on admin/cloud accounts |
| `[ ]` | Written policies **approved** by leadership |
| `[ ]` | Access inventory + first review artifact |
| `[ ]` | Documented change/deploy path + PR review on `main` |
| `[ ]` | Incident response plan (approved + operable) |
| `[ ]` | Backup restore test evidence |
| `[ ]` | Subprocessor inventory + vendor reports collected |
| `[ ]` | Tenant isolation evidence |
| `[ ]` | AI/subprocessor write-up for Anthropic |

### G. Type I → Type II

| Status | Item |
|--------|------|
| `[!]` | Engage CPA firm; schedule fieldwork |
| `[ ]` | Type I report issued → **this is when Type I is “done”** |
| `[ ]` | Keep controls operating; start Type II observation clock |
| `[ ]` | Type II report issued |

---

## What we checked off from repo knowledge (this kickoff)

Documentation and scaffolding only — **not** compliance:

1. Scoreboard + honest definition of done
2. System boundary draft (known production stack)
3. Subprocessors draft (named vendors)
4. Decision log proposed defaults for Matt to confirm
5. Policy index + five DRAFT policy stubs
6. Week 1 checklist linked; documentation items marked where drafts exist

---

## Top `[!]` for Matt (do next)

1. Confirm decision log (Sec+Avail+Conf, PI deferred, owners — propose Matt Justice as security / sponsor)
2. MFA on every admin cloud account (GitHub, Vercel, Railway, Neon, email, Stripe, …)
3. Fill access inventory with real people
4. Platform: write “wait until ____” **or** choose later — do not stall MFA; do not auto-sign up for Vanta here
5. DPA legal path + audit-firm shortlist / target Type I month

---

## How you’ll know Type I is complete

**You hold a SOC 2 Type I report issued by an independent CPA firm** covering Security + Availability + Confidentiality (as scoped). Until then: readiness only.

---

## Document control

| Field | Value |
|-------|--------|
| Title | SMPL.ai SOC 2 Type I Progress Scoreboard |
| Status | Internal living draft |
| Last updated | 2026-07-22 |
| Related | [../SOC2_TYPE1_KICKOFF.md](../SOC2_TYPE1_KICKOFF.md), [00_decision_log.md](./00_decision_log.md) |
