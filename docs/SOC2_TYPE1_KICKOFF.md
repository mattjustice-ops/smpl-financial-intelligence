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

### Week 1 — Decide, name owners, harden access — **COMPLETE 2026-07-26**

Readiness only — **not** SOC 2 certified.

| # | Action | Owner | Done when |
|---|--------|-------|-----------|
| 1 | Fill [00_decision_log.md](./soc2/00_decision_log.md): freeze Sec+Avail+Conf; PI deferred | Executive sponsor | **Done — APPROVED 2026-07-22** |
| 2 | Name people in decision log / readiness §3 (sponsor, security, engineering, ops/CS) — one person can wear multiple hats | Executive sponsor | **Done — all roles Matt Justice** |
| 3 | Choose compliance platform **or** explicitly defer: Vanta / Drata / Secureframe (or other). Do **not** buy until you own MFA + access inventory | Security owner | **Done 2026-07-27 — Deferred DIY** — docs/soc2 + `/app/compliance`; revisit on enterprise GRC requirement **or** CPA Type I engagement ([soc2/00_decision_log.md](./soc2/00_decision_log.md)) |
| 4 | MFA on every admin account: GitHub, Vercel, Railway, Neon, email/Google Workspace (or IdP), Sanity, Stripe, Resend, Anthropic, Domain DNS / Squarespace | Security owner | **Done 2026-07-26** (GitHub, Vercel, Railway, Neon, email/IdP, Stripe, Sanity via Google IdP, Resend, Anthropic via Google IdP — not Anthropic-native TOTP; Squarespace MFA for smpl-ai.com; no shared prod passwords). Ops/break-glass = same MFA as Neon/Railway (solo; no separate login) |
| 5 | Start [03_access_inventory_template.md](./soc2/03_access_inventory_template.md) — who has prod / billing / DB | Security owner | **Done — first pass complete 2026-07-26** |
| 6 | Confirm [01_system_boundary.md](./soc2/01_system_boundary.md) + [02_subprocessors.md](./soc2/02_subprocessors.md) match production | Engineering owner | Drafts exist; TBDs → **Week 2–3** |
| 10 | Protect `main`: required PR before merge; document deploy path (Vercel frontend, Railway API) | Engineering owner | **Done 2026-07-26** — GitHub branch ruleset (solo-friendly; approvals may be 0) + [CHANGE_MANAGEMENT.md](./soc2/CHANGE_MANAGEMENT.md) |

### Week 2 — Policies + platform decision + sales unblockers ← **now**

| # | Action | Owner | Done when |
|---|--------|-------|-----------|
| 7 | Draft core policies from [04_policy_index.md](./soc2/04_policy_index.md) (start with ISP, Acceptable Use, Access Control, Incident Response) | Security owner | **Done** — P01–P12 **Approved 2026-07-27** by Matt Justice ([soc2/policies/](./soc2/policies/)). Approval ≠ SOC 2 certified |
| 3b | **Approve** core policies + choose platform **or** write “wait until ____” | Security / Executive | Policies **Approved** 2026-07-27; platform **deferred DIY** 2026-07-27 |
| 8 | Ship sales unblockers in parallel: DPA, security one-pager, named subprocessors list | Executive / counsel as needed | One-pager + subprocessors drafted; **Customer DPA/MSA = single legal workstream** still open (P10 R16) |
| 9 | If platform chosen: create account, connect GitHub + Vercel/Railway/Neon as available; treat auto gap list as backlog | Security owner | Integrations connected |
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

1. Information Security Policy (umbrella) — **Approved 2026-07-27:** [soc2/policies/P01_information_security_policy.md](./soc2/policies/P01_information_security_policy.md)
2. Acceptable Use — **Approved 2026-07-27:** [soc2/policies/P02_acceptable_use_policy.md](./soc2/policies/P02_acceptable_use_policy.md)
3. Access Control (incl. MFA, offboarding same-day) — **Approved 2026-07-27:** [soc2/policies/P03_access_control_policy.md](./soc2/policies/P03_access_control_policy.md)
4. Incident Response — **Approved 2026-07-27:** [soc2/policies/P04_incident_response_plan.md](./soc2/policies/P04_incident_response_plan.md)
5. Change Management / SDLC — **Approved 2026-07-27:** [soc2/policies/P05_change_management_policy.md](./soc2/policies/P05_change_management_policy.md)
6. Data Classification & Handling — **Approved 2026-07-27:** [soc2/policies/P06_data_classification_and_handling.md](./soc2/policies/P06_data_classification_and_handling.md)
7. Customer Data / Confidentiality Procedures — **Approved 2026-07-27:** [soc2/policies/P07_customer_data_confidentiality_procedures.md](./soc2/policies/P07_customer_data_confidentiality_procedures.md)
8. Retention & Deletion — **Approved 2026-07-27:** [soc2/policies/P08_retention_and_deletion.md](./soc2/policies/P08_retention_and_deletion.md)
9. Vendor / Subprocessor Management — **Approved 2026-07-27:** [soc2/policies/P09_vendor_subprocessor_management.md](./soc2/policies/P09_vendor_subprocessor_management.md)
10. Risk Assessment — **Approved 2026-07-27:** [soc2/policies/P10_risk_assessment.md](./soc2/policies/P10_risk_assessment.md)
11. Business Continuity / DR — **Approved 2026-07-27:** [soc2/policies/P11_business_continuity_disaster_recovery.md](./soc2/policies/P11_business_continuity_disaster_recovery.md)
12. Backup & Restore — **Approved 2026-07-27:** [soc2/policies/P12_backup_and_restore.md](./soc2/policies/P12_backup_and_restore.md)

**Next policy action:** **Approve P15** AI / LLM Data Handling draft — [soc2/policies/P15_ai_llm_data_handling.md](./soc2/policies/P15_ai_llm_data_handling.md) (draft ready; **not** auto-approved).

Still open later: P15 approval, plus P13–P14, P16–P17.

Compliance platform templates are fine later if/when a GRC tool is purchased; customize for SMPL (multi-tenant financial warehouse, white-glove loads, no GL write-back).

---

## Access inventory (systems to cover)

At minimum: GitHub, Vercel, Railway, Neon, Sanity, Stripe, Resend, Anthropic console, email/IdP, Ops/privileged DB paths. Template: [03_access_inventory_template.md](./soc2/03_access_inventory_template.md).

---

## What “good” looks like before booking Type I

From readiness v2 — book the audit only when controls are **live**, not merely drafted:

- MFA on admin/cloud accounts (**[x]** cloud + DNS/Squarespace live 2026-07-26 incl. Anthropic via Google IdP; ops/break-glass = Neon/Railway MFA)
- Written policies approved by leadership — **done 2026-07-27** (approval ≠ SOC 2 certified)
- Access inventory + first quarterly-style review artifact (inventory first pass done; quarterly sign-off still open)
- Documented change/deploy path + PR review on `main` (**[x]** path + GitHub ruleset live 2026-07-26)

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
