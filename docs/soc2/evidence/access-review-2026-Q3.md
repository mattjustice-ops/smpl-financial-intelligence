# Quarterly access review — 2026-Q3

> **Readiness evidence only.** Completing this review ≠ SOC 2 certification — Type I requires an independent CPA report.  
> **Agent limitation:** Cursor agent **cannot** log into GitHub / Vercel / Railway / Neon / Stripe / etc. for Matt. Console verification and sign-off came from Matt (chat attestation 2026-07-29).

## Status: COMPLETE — signed 2026-07-29

| Field | Value |
|-------|--------|
| Review period | **2026-Q3** (first quarterly-style review after Week 1 inventory) |
| Review opened | 2026-07-29 |
| Last reviewed / sign-off date | **2026-07-29** |
| Security owner / reviewer | Matt Justice |
| Executive sponsor (sign-off) | Matt Justice |
| Corporate email (inventory) | **mattjustice@smpl-ai.com** |
| Related policy | [P03 Access Control](../policies/P03_access_control_policy.md) §3.6 (periodic review) |
| Living inventory | [03_access_inventory_template.md](../03_access_inventory_template.md) |
| Prior inventory first pass | **2026-07-26** (MFA verified on primary consoles; owner = Matt on all rows) |
| Result | **OK / Allow** — items 1–12 OK; no CHANGEs stated |
| Sign-off | **Signed** — Matt Justice 2026-07-29 (security owner + exec sponsor) |

---

## Baseline inventory (pre-filled from 2026-07-26 first pass; emails + Last reviewed updated on close)

Solo founder posture: **one person × all systems**. No other humans on admin consoles known. Do **not** invent additional members.

| Person | Email | System | Role / permission | Prod? | MFA (first pass) | Business justification | Last reviewed |
|--------|-------|--------|-------------------|-------|------------------|------------------------|---------------|
| Matt Justice | mattjustice@smpl-ai.com | GitHub (org / repo) | Owner / admin | Y | **Y** 2026-07-26 | Source control, PRs, deploy triggers | 2026-07-29 |
| Matt Justice | mattjustice@smpl-ai.com | Vercel (team / project) | Team admin | Y | **Y** 2026-07-26 | Frontend production deploys + env | 2026-07-29 |
| Matt Justice | mattjustice@smpl-ai.com | Railway (project / service) | Project admin | Y | **Y** 2026-07-26 | API production deploys + env | 2026-07-29 |
| Matt Justice | mattjustice@smpl-ai.com | Neon (org / project / DB) | Org / project admin | Y | **Y** 2026-07-26 | Postgres warehouse + auth data | 2026-07-29 |
| Matt Justice | mattjustice@smpl-ai.com | Sanity (project) | Project admin | Y | **Y** 2026-07-26 (Google IdP MFA) | Marketing CMS / studio | 2026-07-29 |
| Matt Justice | mattjustice@smpl-ai.com | Stripe (account) | Account admin | Y | **Y** 2026-07-26 | Billing / subscriptions | 2026-07-29 |
| Matt Justice | mattjustice@smpl-ai.com | Resend (account) | Account admin | Y | **Y** 2026-07-26 | Transactional email / magic links | 2026-07-29 |
| Matt Justice | mattjustice@smpl-ai.com | Anthropic (console / API keys) | Account / key owner | Y | **Y** 2026-07-26 (Google IdP MFA) | LLM API (keys on Railway) | 2026-07-29 |
| Matt Justice | mattjustice@smpl-ai.com | Corporate email / IdP | Admin / primary mailbox | Y | **Y** 2026-07-26 | Identity + magic-link delivery | 2026-07-29 |
| Matt Justice | mattjustice@smpl-ai.com | Compliance platform | Admin (future) | N/A | N/A | Platform TBD — deferred DIY | 2026-07-29 |
| Matt Justice | mattjustice@smpl-ai.com | Ops / white-glove | Privileged operator | Y | **Y** via Neon/Railway MFA | Tenant support & POC data loads | 2026-07-29 |
| Matt Justice | mattjustice@smpl-ai.com | Direct DB / break-glass | Privileged DB | Y | **Y / N/A separate** (same as Neon/Railway; solo) | Emergency / migration access | 2026-07-29 |
| Matt Justice | mattjustice@smpl-ai.com | Domain DNS / Squarespace | Domain admin | Y | **Y** 2026-07-26 | smpl-ai.com DNS / domain | 2026-07-29 |

**Shared passwords:** Confirmed **none** for prod — Matt 2026-07-26; reconfirmed OK 2026-07-29 (item 12).

---

## Items closed this review

| Item | Status | Resolution |
|------|--------|------------|
| Corporate email address on every inventory row | **Closed** | **mattjustice@smpl-ai.com** filled on all inventory rows |
| Compliance platform | **N/A** | Deferred DIY until enterprise GRC or CPA engagement — no change this quarter |
| Console member/admin verification (items 1–12) | **OK** | Matt: “This looks good to me. Just finished reviewing.” — no CHANGEs stated |

---

## Matt console verification checklist (2026-Q3)

For each system: open the members/admins (or account settings) page and confirm **only Matt** (or note any unexpected account). Spot-check MFA still on.

| # | System | Where to look (typical) | Expected | Matt result |
|---|--------|-------------------------|----------|-------------|
| 1 | **GitHub** | Org → People / Members; repo Settings → Collaborators & teams; org Owners | Only Matt as owner/admin; no unexpected outside collaborators with write/admin | **OK** |
| 2 | **Vercel** | Team → Members / Settings | Only Matt as team admin | **OK** |
| 3 | **Railway** | Project → Settings / Members (or account access) | Only Matt as project admin | **OK** |
| 4 | **Neon** | Org → Members / project access | Only Matt as org/project admin | **OK** |
| 5 | **Sanity** | Project → Members / manage members | Only Matt as project admin | **OK** |
| 6 | **Stripe** | Settings → Team / users | Only Matt as account admin | **OK** |
| 7 | **Resend** | Account / team members | Only Matt as account admin | **OK** |
| 8 | **Anthropic** | Console account / org members (if any) | Only Matt; keys not shared | **OK** |
| 9 | **Email / IdP** | Google Workspace / Microsoft 365 admin (or personal Google account security) | MFA still on; mailbox is the magic-link identity path | **OK** |
| 10 | **Ops / DB / break-glass** | Neon + Railway only (no separate break-glass login) | Still solo; no new shared DB users/roles beyond Matt | **OK** |
| 11 | **DNS / Squarespace** | Squarespace account / domain permissions for smpl-ai.com | Only Matt; MFA still on | **OK** |
| 12 | **Shared passwords** | Mental check + password manager | Still **no** shared prod passwords | **OK** |

Optional evidence (sanitized): screenshots stay local or in a private vault — **do not commit secrets**. No MFA failures or extra accounts invented.

---

## Review conclusions

| Question | Answer |
|----------|--------|
| Any unexpected admins / collaborators? | **No** (Matt review OK; no CHANGEs) |
| Any access revoked this quarter? | **None stated** |
| Any new people granted access? | **None** (solo founder baseline) |
| MFA still verified on admin paths? | **Yes** — first pass Y 2026-07-26; reconfirmed OK 2026-07-29 |
| Break-glass still = Neon/Railway MFA only? | **Yes** |
| Corporate email recorded on inventory? | **Yes** — mattjustice@smpl-ai.com |

---

## Sign-off

| Review period | Reviewer (security owner) | Executive sponsor | Date | Result | Notes |
|---------------|---------------------------|-------------------|------|--------|-------|
| 2026-Q3 | Matt Justice | Matt Justice | **2026-07-29** | **OK / Allow** | First quarterly-style review after Week 1 inventory. Chat attestation: review complete; corporate email mattjustice@smpl-ai.com; items 1–12 OK; no CHANGEs. Readiness evidence only — not SOC 2 certified. |

Related: [P03](../policies/P03_access_control_policy.md) · [P02](../policies/P02_acceptable_use_policy.md) · [inventory](../03_access_inventory_template.md) · [PROGRESS](../PROGRESS.md)

_End of 2026-Q3 access review evidence — signed 2026-07-29_
