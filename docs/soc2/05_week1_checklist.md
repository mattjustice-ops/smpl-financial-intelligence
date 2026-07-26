# Week 1 checklist — SOC 2 Type I kickoff

Immediate founder/ops work. Check boxes as you go. Details: [../SOC2_TYPE1_KICKOFF.md](../SOC2_TYPE1_KICKOFF.md) · Living scoreboard: [PROGRESS.md](./PROGRESS.md).

**Sales reminder:** say “pursuing SOC 2” / “readiness in progress” only — never “certified” until a report is issued.

**Legend:** `[x]` done · `[ ]` open · `[~]` in progress · `[!]` needs Matt

---

## Decisions & ownership

- [x] Read [SMPL_SOC2_Readiness_Reference_v2.md](../SMPL_SOC2_Readiness_Reference_v2.md) (§1 scope, §6 sales language) — kickoff artifacts align with it
- [x] Fill [00_decision_log.md](./00_decision_log.md): Sec + Avail + Conf; PI deferred — **confirmed 2026-07-22**; all owners Matt Justice
- [x] Name executive sponsor — Matt Justice
- [x] Name security owner — Matt Justice
- [x] Name engineering owner — Matt Justice
- [x] Name ops / CS privileged-access owner — Matt Justice
- [!] Choose platform path: create Vanta/Drata/Secureframe account **or** write “wait until ____” in decision log (do not stall MFA either way; **do not auto-sign up for Vanta in this kickoff**)
- [!] Set target Type I month (even if approximate)

---

## Access hardening (do this before or while buying a platform)

- [x] MFA on GitHub org admins / owners — **2026-07-26**
- [x] MFA on Vercel team — **2026-07-26**
- [x] MFA on Railway — **2026-07-26**
- [x] MFA on Neon — **2026-07-26**
- [x] MFA on corporate email / IdP — **2026-07-26**
- [x] MFA on Stripe — **2026-07-26**
- [x] MFA on Sanity (if admin access exists) — **2026-07-26** (IdP MFA via Google login; not Sanity-native)
- [x] MFA on Resend — **2026-07-26**
- [!] MFA on Anthropic console — still open
- [!] MFA on DNS / domain admin (if separate from IdP) — not confirmed
- [~] First pass of [03_access_inventory_template.md](./03_access_inventory_template.md) — Matt on all known systems; most MFA verified 2026-07-26; Anthropic + DNS/ops still open
- [x] Confirm no shared passwords for prod systems — **2026-07-26**

---

## Boundary & vendors

- [x] Draft [01_system_boundary.md](./01_system_boundary.md) from known stack
- [!] Review boundary; resolve or assign TBDs
- [x] Draft [02_subprocessors.md](./02_subprocessors.md) named list
- [!] Review subprocessors; mark any unused vendors / confirm OpenAI
- [ ] Start folder for vendor SOC reports (under NDA) — Vercel, Railway, Neon, Stripe, Anthropic, Resend, etc.
- [x] Security one-pager draft — [SECURITY_ONE_PAGER.md](./SECURITY_ONE_PAGER.md)

---

## Engineering hygiene (start Week 1, finish into Week 2)

- [!] Branch protection on `main` + required PR review
- [ ] Confirm secrets are not in git; production secrets only in Vercel/Railway (etc.)
- [x] Document deploy path + who can deploy — [CHANGE_MANAGEMENT.md](./CHANGE_MANAGEMENT.md) (Matt); GitHub/Vercel/Railway MFA done 2026-07-26; branch protection still `[!]`
- [!] Calendar a Neon backup restore test

---

## Policies & sales unblockers (start drafting)

- [x] Open [04_policy_index.md](./04_policy_index.md); P01–P05 expanded; P06/P08/P09/P11/P12 drafted as **Draft** in [policies/](./policies/)
- [!] Kick off customer DPA (counsel or template) — legal review
- [x] Security one-pager drafted (encryption, tenant isolation, no GL write-back, auth model, AI keys on API)
- [!] **Approve** core policy drafts — Matt
- [x] Align external language with “pursuing” only — documented in kickoff + PROGRESS + one-pager

---

## End of Week 1 — definition of done

- [~] Decision log has owners + scope — **done**; platform choice or explicit wait — **[!]** Matt
- [~] MFA on admin cloud accounts — most done 2026-07-26; Anthropic (+ DNS if separate) still open
- [~] Access inventory first pass exists (owners filled; most MFA verified; Anthropic/DNS pending)
- [x] Subprocessors list ready to attach to questionnaires (draft; confirm TBDs)
- [x] Core policy drafts started (P01–P06, P08–P09, P11–P12) — still need approval
