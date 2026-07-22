# SMPL.ai — SOC 2 Type I Kickoff Plan

Founder-executable plan to start **SOC 2 Type I** readiness. Not legal or audit advice. Do **not** claim SOC 2 certified until an independent CPA firm issues a report.

**Living scoreboard (what’s checked off / what’s open):** [soc2/PROGRESS.md](./soc2/PROGRESS.md)

**Remaining checklist + target timeline (solo-founder calendar):** [soc2/PROGRESS.md § Remaining checklist + target timeline](./soc2/PROGRESS.md#remaining-checklist--target-timeline) — also on `/compliance` under **Remaining & targets**.

**Public progress page:** [https://www.smpl-ai.com/compliance](https://www.smpl-ai.com/compliance) — statuses are edited in `frontend/lib/compliance/progress.ts` (keep in sync with [soc2/PROGRESS.md](./soc2/PROGRESS.md); see that file’s “How to update” section).

**Source of truth (scope + criteria):** [SMPL_SOC2_Readiness_Reference_v2.md](./SMPL_SOC2_Readiness_Reference_v2.md)

**Working artifacts:** [docs/soc2/](./soc2/)

**Scope locked (APPROVED 2026-07-22 by Matt Justice):** Security + Availability + Confidentiality **IN**. Processing Integrity + Privacy **DEFERRED**. All named owners: Matt Justice. See [soc2/00_decision_log.md](./soc2/00_decision_log.md).

---

## How we know we’re Type I “done”

**Definition of done:** an independent CPA firm issues a SOC 2 Type I report covering Security + Availability + Confidentiality, and that report is in hand. Until then this program is **readiness + evidence only** — not compliance. Track progress on [soc2/PROGRESS.md](./soc2/PROGRESS.md).

---

## Sales language (read before talking to buyers)

| Stage | Say | Never say |
|-------|-----|-----------|
| Now / Week 1–2 | “We are pursuing SOC 2” / “SOC 2 readiness in progress” | “We are SOC 2 certified” |
| After Type I issued | “SOC 2 Type I complete; Type II in progress” (criteria as on report) | Naming criteria not on the report |
| After Type II issued | “SOC 2 Type II” — share report under NDA | Implying the report validates ARR math / FP&A methodology |

Until a report exists, prefer the security one-pager + DPA + subprocessors list over loud SOC 2 claims.

---

## Week 1–2 actions

### Week 1 — Decide, name owners, harden access

| # | Action | Owner | Done when |
|---|--------|-------|-----------|
| 1 | Fill [00_decision_log.md](./soc2/00_decision_log.md): freeze Sec+Avail+Conf; PI deferred | Executive sponsor | **Done — APPROVED 2026-07-22** |
| 2 | Name people in decision log / readiness §3 (sponsor, security, engineering, ops/CS) — one person can wear multiple hats | Executive sponsor | **Done — all roles Matt Justice** |
| 3 | Choose compliance platform **or** explicitly defer 1–2 weeks: Vanta / Drata / Secureframe (or other). Do **not** buy until you own MFA + access inventory | Security owner | Choice or “wait until ____” in decision log |
| 4 | MFA on every admin account: GitHub, Vercel, Railway, Neon, email/Google Workspace (or IdP), Sanity, Stripe | Security owner | Screenshots or platform evidence |
| 5 | Start [03_access_inventory_template.md](./soc2/03_access_inventory_template.md) — who has prod / billing / DB | Security owner | First pass complete |
| 6 | Confirm [01_system_boundary.md](./soc2/01_system_boundary.md) + [02_subprocessors.md](./soc2/02_subprocessors.md) match production | Engineering owner | TBDs resolved or marked with owner |

### Week 2 — Policies draft + sales unblockers + platform connect

| # | Action | Owner | Done when |
|---|--------|-------|-----------|
| 7 | Draft core policies from [04_policy_index.md](./soc2/04_policy_index.md) (start with ISP, Acceptable Use, Access Control, Incident Response) | Security owner | Drafts in [soc2/policies/](./soc2/policies/) (**P01–P05 stubs exist — still need approval**) |
| 8 | Ship sales unblockers in parallel: DPA, security one-pager, named subprocessors list | Executive / counsel as needed | Shareable under NDA |
| 9 | If platform chosen: create account, connect GitHub + Vercel/Railway/Neon as available; treat auto gap list as backlog | Security owner | Integrations connected |
| 10 | Protect `main`: required PR review; document deploy path (Vercel frontend, Railway API) | Engineering owner | Branch rules + short deploy note |
| 11 | Schedule backup **restore test** on Neon (or document who runs it in Week 3) | Engineering owner | Date on calendar or completed |
| 12 | Pick audit-firm shortlist (platform partner network OK); set **target Type I month** in decision log | Executive sponsor | Target date filled |

Use the checkbox list: [05_week1_checklist.md](./soc2/05_week1_checklist.md). Prefer updating statuses on [PROGRESS.md](./soc2/PROGRESS.md) as the single scoreboard.

---

## Decision log template

Copy into [00_decision_log.md](./soc2/00_decision_log.md) (already seeded with **proposed** defaults). Minimum fields:

| Decision | Choice | Date | Owner |
|----------|--------|------|-------|
| Type I criteria | Security + Availability + Confidentiality | | |
| Processing Integrity | Deferred | | |
| Compliance platform | Vanta / Drata / Secureframe / other / wait | | |
| Audit firm | TBD | | |
| Target Type I date | YYYY-MM | | |
| Security owner | Name | | |
| Engineering owner | Name | | |

---

## Policies to draft first (Week 1–2)

Priority order — full list in [04_policy_index.md](./soc2/04_policy_index.md):

1. Information Security Policy (umbrella) — **DRAFT stub:** [soc2/policies/P01_information_security_policy.md](./soc2/policies/P01_information_security_policy.md)
2. Acceptable Use — **DRAFT stub:** [soc2/policies/P02_acceptable_use_policy.md](./soc2/policies/P02_acceptable_use_policy.md)
3. Access Control (incl. MFA, offboarding same-day) — **DRAFT stub:** [soc2/policies/P03_access_control_policy.md](./soc2/policies/P03_access_control_policy.md)
4. Incident Response — **DRAFT stub:** [soc2/policies/P04_incident_response_plan.md](./soc2/policies/P04_incident_response_plan.md)
5. Change Management / SDLC — **DRAFT stub:** [soc2/policies/P05_change_management_policy.md](./soc2/policies/P05_change_management_policy.md)
6. Data Classification & Confidentiality Handling
7. Vendor / Subprocessor Management
8. Business Continuity / Backup & Recovery
9. AI / LLM Data Handling (Anthropic prompts; keys on API only)

Templates from the compliance platform are fine later; customize for SMPL (multi-tenant financial warehouse, white-glove loads, no GL write-back).

---

## Access inventory (systems to cover)

At minimum: GitHub, Vercel, Railway, Neon, Sanity, Stripe, Resend, Anthropic console, email/IdP, Ops/privileged DB paths. Template: [03_access_inventory_template.md](./soc2/03_access_inventory_template.md).

---

## What “good” looks like before booking Type I

From readiness v2 — book the audit only when controls are **live**, not merely drafted:

- MFA on admin/cloud accounts
- Written policies approved by leadership
- Access inventory + first quarterly-style review artifact
- Documented change/deploy path + PR review on `main`
- Incident response plan
- Backup restore test evidence
- Subprocessor inventory + vendor SOC reports collected under NDA where available
- Tenant isolation evidence (Org A cannot read Org B)
- AI/subprocessor write-up for Anthropic

---

## Document control

| Field | Value |
|-------|--------|
| Title | SMPL.ai SOC 2 Type I Kickoff |
| Status | Internal working draft |
| Related | [soc2/PROGRESS.md](./soc2/PROGRESS.md), [SMPL_SOC2_Readiness_Reference_v2.md](./SMPL_SOC2_Readiness_Reference_v2.md), [docs/soc2/](./soc2/) |
