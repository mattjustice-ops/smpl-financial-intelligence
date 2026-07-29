# Quarterly access review — 2026-Q3

> **Readiness evidence only.** Completing this review ≠ SOC 2 certification — Type I requires an independent CPA report.  
> **Agent limitation:** Cursor agent **cannot** log into GitHub / Vercel / Railway / Neon / Stripe / etc. for Matt. Console verification and sign-off must come from Matt.

## Status: IN PROGRESS — awaiting Matt console verification + sign-off

| Field | Value |
|-------|--------|
| Review period | **2026-Q3** (first quarterly-style review after Week 1 inventory) |
| Review opened | 2026-07-29 |
| Security owner / reviewer | Matt Justice |
| Related policy | [P03 Access Control](../policies/P03_access_control_policy.md) §3.6 (periodic review) |
| Living inventory | [03_access_inventory_template.md](../03_access_inventory_template.md) |
| Prior inventory first pass | **2026-07-26** (MFA verified on primary consoles; owner = Matt on all rows) |
| Sign-off | **Not signed** — do not mark PROGRESS `[x]` until Matt replies OK / notes changes |

---

## Baseline inventory (pre-filled from 2026-07-26 first pass)

Solo founder posture: **one person × all systems**. No other humans on admin consoles known at first pass. Do **not** invent additional members.

| Person | System | Role / permission | Prod? | MFA (first pass) | Business justification | Last reviewed (inventory) |
|--------|--------|-------------------|-------|------------------|------------------------|---------------------------|
| Matt Justice | GitHub (org / repo) | Owner / admin | Y | **Y** 2026-07-26 | Source control, PRs, deploy triggers | 2026-07-26 |
| Matt Justice | Vercel (team / project) | Team admin | Y | **Y** 2026-07-26 | Frontend production deploys + env | 2026-07-26 |
| Matt Justice | Railway (project / service) | Project admin | Y | **Y** 2026-07-26 | API production deploys + env | 2026-07-26 |
| Matt Justice | Neon (org / project / DB) | Org / project admin | Y | **Y** 2026-07-26 | Postgres warehouse + auth data | 2026-07-26 |
| Matt Justice | Sanity (project) | Project admin | Y | **Y** 2026-07-26 (Google IdP MFA) | Marketing CMS / studio | 2026-07-26 |
| Matt Justice | Stripe (account) | Account admin | Y | **Y** 2026-07-26 | Billing / subscriptions | 2026-07-26 |
| Matt Justice | Resend (account) | Account admin | Y | **Y** 2026-07-26 | Transactional email / magic links | 2026-07-26 |
| Matt Justice | Anthropic (console / API keys) | Account / key owner | Y | **Y** 2026-07-26 (Google IdP MFA) | LLM API (keys on Railway) | 2026-07-26 |
| Matt Justice | Corporate email / IdP | Admin / primary mailbox | Y | **Y** 2026-07-26 | Identity + magic-link delivery | 2026-07-26 |
| Matt Justice | Compliance platform | Admin (future) | N/A | N/A | Platform TBD — deferred DIY | 2026-07-22 |
| Matt Justice | Ops / white-glove | Privileged operator | Y | **Y** via Neon/Railway MFA | Tenant support & POC data loads | 2026-07-26 |
| Matt Justice | Direct DB / break-glass | Privileged DB | Y | **Y / N/A separate** (same as Neon/Railway; solo) | Emergency / migration access | 2026-07-26 |
| Matt Justice | Domain DNS / Squarespace | Domain admin | Y | **Y** 2026-07-26 | smpl-ai.com DNS / domain | 2026-07-26 |

**Shared passwords:** Confirmed **none** for prod — Matt 2026-07-26.

---

## `[!]` items still needing Matt (from inventory template)

| Item | Status | What Matt should do |
|------|--------|---------------------|
| Corporate email address on every inventory row | **Open** — template still has `_[! confirm corporate email]_` / `_[!]_` | Reply with the **corporate email** used for admin logins (or confirm “same on all systems: ____@____”) so rows can be filled |
| Compliance platform | **N/A** — deferred DIY until enterprise GRC or CPA engagement | No action this quarter unless Matt chose a platform since 2026-07-27 |
| Console member/admin exports | **Open for this review** | Spot-check each console below; optional sanitized screenshot description in notes — **do not** paste secrets or customer dumps into git |

---

## Matt console verification checklist (2026-Q3)

For each system: open the members/admins (or account settings) page and confirm **only Matt** (or note any unexpected account). Spot-check MFA still on. Reply **OK** or **CHANGE: …** per line.

| # | System | Where to look (typical) | Expected | Matt result (fill on close) |
|---|--------|-------------------------|----------|-----------------------------|
| 1 | **GitHub** | Org → People / Members; repo Settings → Collaborators & teams; org Owners | Only Matt as owner/admin; no unexpected outside collaborators with write/admin | ☐ pending |
| 2 | **Vercel** | Team → Members / Settings | Only Matt as team admin | ☐ pending |
| 3 | **Railway** | Project → Settings / Members (or account access) | Only Matt as project admin | ☐ pending |
| 4 | **Neon** | Org → Members / project access | Only Matt as org/project admin | ☐ pending |
| 5 | **Sanity** | Project → Members / manage members | Only Matt as project admin | ☐ pending |
| 6 | **Stripe** | Settings → Team / users | Only Matt as account admin | ☐ pending |
| 7 | **Resend** | Account / team members | Only Matt as account admin | ☐ pending |
| 8 | **Anthropic** | Console account / org members (if any) | Only Matt; keys not shared | ☐ pending |
| 9 | **Email / IdP** | Google Workspace / Microsoft 365 admin (or personal Google account security) | MFA still on; mailbox is the magic-link identity path | ☐ pending |
| 10 | **Ops / DB / break-glass** | Neon + Railway only (no separate break-glass login) | Still solo; no new shared DB users/roles beyond Matt | ☐ pending |
| 11 | **DNS / Squarespace** | Squarespace account / domain permissions for smpl-ai.com | Only Matt; MFA still on | ☐ pending |
| 12 | **Shared passwords** | Mental check + password manager | Still **no** shared prod passwords | ☐ pending |

Optional evidence (sanitized): one-line description per console of what you saw (e.g. “GitHub org Members: 1 owner”). Screenshots stay local or in a private vault — **do not commit secrets**.

---

## Review conclusions (fill after Matt replies)

| Question | Answer (pending) |
|----------|------------------|
| Any unexpected admins / collaborators? | _Awaiting Matt_ |
| Any access revoked this quarter? | _Awaiting Matt_ |
| Any new people granted access? | _Awaiting Matt_ (baseline expects **none**) |
| MFA still verified on admin paths? | _Awaiting Matt_ (first pass was Y 2026-07-26) |
| Break-glass still = Neon/Railway MFA only? | _Awaiting Matt_ |
| Corporate email recorded on inventory? | _Awaiting Matt `[!]`_ |

---

## Sign-off (do not forge)

| Review period | Reviewer | Date | Result | Notes |
|---------------|----------|------|--------|-------|
| 2026-Q3 | Matt Justice | _pending_ | _pending — OK / changes made_ | First quarterly-style review; WIP opened 2026-07-29 |

**Closeout rule:** Mark complete only when Matt confirms in chat (or equivalent dated attestation). Then:

1. Set this file **Status: COMPLETE**.
2. Update Last reviewed → **2026-07-29** (or sign-off date) on [03_access_inventory_template.md](../03_access_inventory_template.md).
3. Fill quarterly sign-off row + corporate email `[!]` if provided.
4. Mark [PROGRESS.md](../PROGRESS.md) + `frontend/lib/compliance/progress.ts` access-review items **done** with evidence link.

---

Related: [P03](../policies/P03_access_control_policy.md) · [P02](../policies/P02_acceptable_use_policy.md) · [inventory](../03_access_inventory_template.md) · [PROGRESS](../PROGRESS.md)

_End of WIP evidence — not signed off_
