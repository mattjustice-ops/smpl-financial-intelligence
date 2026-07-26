# Access inventory

Who can touch production systems or customer data, and why. Complete Week 1; review quarterly thereafter (dated sign-off = audit evidence).

Parent: [../SOC2_TYPE1_KICKOFF.md](../SOC2_TYPE1_KICKOFF.md) · Scoreboard: [PROGRESS.md](./PROGRESS.md)

**Status (2026-07-26):** Known systems inventoried with **owner = Matt Justice** for all rows.  
MFA verified for primary cloud consoles (GitHub, Vercel, Railway, Neon, email/IdP, Stripe, Sanity via Google IdP, Resend, Anthropic via Google IdP).  
**[!]** DNS/ops/break-glass rows still need confirmation if credentials are separate from IdP.  
Do **not** invent MFA completion.

**Rules of thumb:** unique accounts (no shared logins); MFA on admin; least privilege; revoke same day on offboarding.

---

## Instructions

1. Export members/admins from each console (or screenshot role lists).
2. Keep one row per person × system (add people as the team grows).
3. Security owner reviews; executive sponsor signs quarterly review block at bottom.
4. When MFA is confirmed for a row, change `MFA verified?` from `[!]` / `N — needs Matt` to `Y` and date it.

---

## Inventory

| Person | Email | System | Role / permission | Prod access? | MFA verified? | Business justification | Last reviewed |
|--------|-------|--------|-------------------|--------------|---------------|------------------------|---------------|
| Matt Justice | _[! confirm corporate email]_ | GitHub (org / repo) | Owner / admin | Y | **Y** — 2026-07-26 | Source control, PRs, deploy triggers | 2026-07-26 |
| Matt Justice | _[!]_ | Vercel (team / project) | Team admin | Y | **Y** — 2026-07-26 | Frontend production deploys + env | 2026-07-26 |
| Matt Justice | _[!]_ | Railway (project / service) | Project admin | Y | **Y** — 2026-07-26 | API production deploys + env | 2026-07-26 |
| Matt Justice | _[!]_ | Neon (org / project / DB) | Org / project admin | Y | **Y** — 2026-07-26 | Postgres warehouse + auth data | 2026-07-26 |
| Matt Justice | _[!]_ | Sanity (project) | Project admin | Y | **Y** — 2026-07-26 (IdP MFA via Google login; not Sanity-native toggle) | Marketing CMS / studio | 2026-07-26 |
| Matt Justice | _[!]_ | Stripe (account) | Account admin | Y | **Y** — 2026-07-26 | Billing / subscriptions | 2026-07-26 |
| Matt Justice | _[!]_ | Resend (account) | Account admin | Y | **Y** — 2026-07-26 | Transactional email / magic links | 2026-07-26 |
| Matt Justice | _[!]_ | Anthropic (console / API keys) | Account / key owner | Y | **Y** — 2026-07-26 (IdP MFA via Google login; not Anthropic-native TOTP) | LLM API for commentary (keys on Railway) | 2026-07-26 |
| Matt Justice | _[!]_ | Corporate email / IdP (Google / Microsoft / other) | Admin / primary mailbox | Y | **Y** — 2026-07-26 | Identity + magic-link delivery | 2026-07-26 |
| Matt Justice | _[!]_ | Compliance platform (when chosen) | Admin (future) | N/A yet | N/A | Platform TBD — Matt to decide | 2026-07-22 |
| Matt Justice | _[!]_ | Ops console / white-glove tooling | Privileged operator | Y | **[!]** N — confirm if separate credentials | Tenant support & POC data loads | 2026-07-22 |
| Matt Justice | _[!]_ | Direct DB / break-glass | Privileged DB access | Y | **[!]** N — confirm if separate credentials | Emergency / migration access | 2026-07-22 |
| Matt Justice | _[!]_ | Domain DNS / Squarespace / registrar | Domain admin | Y | **[!]** N — needs Matt if login ≠ IdP | smpl-ai.com DNS / domain | 2026-07-22 |

Add rows as needed when additional people receive access. Duplicate systems for staging if separate from prod.

---

## Systems checklist (have we inventoried owners?)

- [x] GitHub — owner row filled (MFA **Y** 2026-07-26)
- [x] Vercel — owner row filled (MFA **Y** 2026-07-26)
- [x] Railway — owner row filled (MFA **Y** 2026-07-26)
- [x] Neon — owner row filled (MFA **Y** 2026-07-26)
- [x] Sanity — owner row filled (MFA **Y** 2026-07-26 via Google IdP)
- [x] Stripe — owner row filled (MFA **Y** 2026-07-26)
- [x] Resend — owner row filled (MFA **Y** 2026-07-26)
- [x] Anthropic — owner row filled (MFA **Y** 2026-07-26 via Google IdP)
- [x] Email / IdP — owner row filled (MFA **Y** 2026-07-26)
- [x] DNS / domain admin — owner row filled (MFA **[!]** )
- [x] Ops / privileged tenant access — owner row filled (MFA **[!]** confirm)
- [ ] Compliance platform (when live) — N/A until Matt chooses platform

---

## Privileged / white-glove operators

| Person | What they can access | Approval path | Revocation trigger |
|--------|----------------------|---------------|--------------------|
| Matt Justice | Tenant data via ops / DB / load tooling; all cloud admin consoles | Self as exec/security owner (document when team grows) | End of POC / ticket close / offboarding / role change |

---

## Shared passwords

| Check | Status |
|-------|--------|
| Confirm no shared prod passwords | **Y** — confirmed by Matt 2026-07-26 (no shared prod passwords) |

---

## Quarterly access review sign-off

| Review period | Reviewer | Date | Result (OK / changes made) | Notes |
|---------------|----------|------|----------------------------|-------|
| YYYY-QX | Matt Justice | | | First review after remaining MFA (DNS / ops if separate) verified |

Attach exports or links to evidence folder (do not commit secrets or customer dumps to git).
