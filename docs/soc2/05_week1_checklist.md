# Week 1 checklist — SOC 2 Type I kickoff

Immediate founder/ops work. Check boxes as you go. Details: [../SOC2_TYPE1_KICKOFF.md](../SOC2_TYPE1_KICKOFF.md) · Living scoreboard: [PROGRESS.md](./PROGRESS.md).

**Sales reminder:** say “pursuing SOC 2” / “readiness in progress” only — never “certified” until a report is issued.

**Legend:** `[x]` done · `[ ]` open · `[~]` in progress · `[!]` needs Matt

**Week 1 status:** **COMPLETE 2026-07-26** (readiness only — not SOC 2 certified). Platform choice, policy approval, boundary TBDs, DPA, and restore-test calendar roll into **Week 2+** per [PROGRESS.md](./PROGRESS.md).

---

## Decisions & ownership

- [x] Read [SMPL_SOC2_Readiness_Reference_v2.md](../SMPL_SOC2_Readiness_Reference_v2.md) (§1 scope, §6 sales language) — kickoff artifacts align with it
- [x] Fill [00_decision_log.md](./00_decision_log.md): Sec + Avail + Conf; PI deferred — **confirmed 2026-07-22**; all owners Matt Justice
- [x] Name executive sponsor — Matt Justice
- [x] Name security owner — Matt Justice
- [x] Name engineering owner — Matt Justice
- [x] Name ops / CS privileged-access owner — Matt Justice
- [x] Choose platform path: create Vanta/Drata/Secureframe account **or** write “wait until ____” in decision log — **Deferred DIY 2026-07-27** (docs/soc2 + `/app/compliance`; revisit on enterprise GRC requirement **or** CPA Type I engagement)
- [!] Set target Type I month (even if approximate) — **Week 2+ / Month 2–3** target window

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
- [x] MFA on Anthropic console — **2026-07-26** (IdP MFA via Google login; not Anthropic-native TOTP)
- [x] MFA on DNS / domain admin (Squarespace for smpl-ai.com) — **2026-07-26**
- [x] First pass of [03_access_inventory_template.md](./03_access_inventory_template.md) — Matt on all known systems; cloud + DNS MFA verified; ops/break-glass = same MFA as Neon/Railway (solo; no separate login) — **2026-07-26**
- [x] Confirm no shared passwords for prod systems — **2026-07-26**

---

## Boundary & vendors

- [x] Draft [01_system_boundary.md](./01_system_boundary.md) from known stack
- [!] Review boundary; resolve or assign TBDs — **Week 2–3**
- [x] Draft [02_subprocessors.md](./02_subprocessors.md) named list
- [!] Review subprocessors; mark any unused vendors / confirm OpenAI — **Week 2–3**
- [ ] Start folder for vendor SOC reports (under NDA) — Vercel, Railway, Neon, Stripe, Anthropic, Resend, etc. — **Week 3–4**
- [x] Security one-pager draft — [SECURITY_ONE_PAGER.md](./SECURITY_ONE_PAGER.md)

---

## Engineering hygiene (start Week 1, finish into Week 2)

- [x] Branch protection on `main` + required PR review — **2026-07-26** (GitHub branch ruleset; solo-friendly; approvals may be 0)
- [ ] Confirm secrets are not in git; production secrets only in Vercel/Railway (etc.) — **Month 2** spot-check
- [x] Document deploy path + who can deploy — [CHANGE_MANAGEMENT.md](./CHANGE_MANAGEMENT.md) (Matt); MFA + branch protection live 2026-07-26
- [!] Calendar a Neon backup restore test — **Week 2 / Week 3–4**

---

## Policies & sales unblockers (start drafting)

- [x] Open [04_policy_index.md](./04_policy_index.md); **P01–P12 Approved 2026-07-27** by Matt Justice in [policies/](./policies/)
- [!] Kick off Customer DPA / MSA — **single legal workstream** (privacy, retention, subprocessors) — counsel — **Week 3–4** (also P10 R16)
  - **[~]** Outline drafted 2026-07-28 — [legal/DPA_MSA_OUTLINE.md](./legal/DPA_MSA_OUTLINE.md); awaiting counsel (R16 not closed)
- [x] Security one-pager drafted (encryption, tenant isolation, no GL write-back, auth model, AI keys on API)
- [x] **Approve** core policy drafts (P01–P12) — Matt — **Approved 2026-07-27** (approval ≠ SOC 2 certified)
- [x] Align external language with “pursuing” only — documented in kickoff + PROGRESS + one-pager
- [x] **P15** AI / LLM Data Handling — **Approved 2026-07-28** ([policies/P15_ai_llm_data_handling.md](./policies/P15_ai_llm_data_handling.md))

---

## End of Week 1 — definition of done

- [x] Decision log has owners + scope — **done**; platform deferred DIY — **done** 2026-07-27
- [x] MFA on admin cloud accounts — cloud + DNS (Squarespace) done 2026-07-26 (Anthropic via Google IdP); ops/break-glass = Neon/Railway MFA (solo; no separate login)
- [x] Access inventory first pass exists (owners filled; MFA columns verified; break-glass noted as same-as-Neon/Railway)
- [x] Subprocessors list ready to attach to questionnaires (draft; confirm TBDs in Week 2–3)
- [x] Core policies P01–P12 **Approved 2026-07-27** by Matt Justice (approval ≠ SOC 2 certified; evidence items remain)
- [x] Protect `main` + required PR review — GitHub ruleset live 2026-07-26

**Week 1 COMPLETE 2026-07-26.** Not SOC 2 certified — readiness tracking only.
