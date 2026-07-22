# Week 1 checklist — SOC 2 Type I kickoff

Immediate founder/ops work. Check boxes as you go. Details: [../SOC2_TYPE1_KICKOFF.md](../SOC2_TYPE1_KICKOFF.md) · Living scoreboard: [PROGRESS.md](./PROGRESS.md).

**Sales reminder:** say “pursuing SOC 2” / “readiness in progress” only — never “certified” until a report is issued.

**Legend:** `[x]` done · `[ ]` open · `[~]` in progress · `[!]` needs Matt

---

## Decisions & ownership

- [x] Read [SMPL_SOC2_Readiness_Reference_v2.md](../SMPL_SOC2_Readiness_Reference_v2.md) (§1 scope, §6 sales language) — kickoff artifacts align with it
- [~] Fill [00_decision_log.md](./00_decision_log.md): Sec + Avail + Conf; PI deferred — **proposed defaults drafted; [!] Matt confirm/sign**
- [!] Name executive sponsor — proposed Matt Justice
- [!] Name security owner — proposed Matt Justice
- [!] Name engineering owner
- [!] Name ops / CS privileged-access owner (may be same person)
- [!] Choose platform path: create Vanta/Drata/Secureframe account **or** write “wait until ____” in decision log (do not stall MFA either way; **do not auto-sign up for Vanta in this kickoff**)
- [!] Set target Type I month (even if approximate)

---

## Access hardening (do this before or while buying a platform)

- [!] MFA on GitHub org admins / owners
- [!] MFA on Vercel team
- [!] MFA on Railway
- [!] MFA on Neon
- [!] MFA on corporate email / IdP
- [!] MFA on Stripe
- [!] MFA on Sanity (if admin access exists)
- [!] MFA on Resend / Anthropic consoles
- [!] First pass of [03_access_inventory_template.md](./03_access_inventory_template.md) — template ready; people rows need Matt
- [!] Confirm no shared passwords for prod systems

---

## Boundary & vendors

- [x] Draft [01_system_boundary.md](./01_system_boundary.md) from known stack
- [!] Review boundary; resolve or assign TBDs
- [x] Draft [02_subprocessors.md](./02_subprocessors.md) named list
- [!] Review subprocessors; mark any unused vendors / confirm OpenAI
- [ ] Start folder for vendor SOC reports (under NDA) — Vercel, Railway, Neon, Stripe, Anthropic, Resend, etc.

---

## Engineering hygiene (start Week 1, finish into Week 2)

- [!] Branch protection on `main` + required PR review
- [ ] Confirm secrets are not in git; production secrets only in Vercel/Railway (etc.)
- [!] Note who can deploy frontend (Vercel) vs API (Railway)
- [!] Calendar a Neon backup restore test

---

## Policies & sales unblockers (start drafting)

- [x] Open [04_policy_index.md](./04_policy_index.md); P01–P05 stubbed as **Draft** in [policies/](./policies/)
- [!] Kick off customer DPA (counsel or template) — legal review
- [ ] Kick off security one-pager (encryption, tenant isolation, no GL write-back, auth model, AI keys on API)
- [x] Align external language with “pursuing” only — documented in kickoff + PROGRESS

---

## End of Week 1 — definition of done

- [!] Decision log has owners + scope + platform choice or explicit wait — **confirm proposed defaults**
- [!] MFA on admin cloud accounts
- [!] Access inventory first pass exists
- [x] Subprocessors list ready to attach to questionnaires (draft; confirm TBDs)
- [x] At least four policy drafts started (five stubs: P01–P05) — still need approval
