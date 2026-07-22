# Week 1 checklist — SOC 2 Type I kickoff

Immediate founder/ops work. Check boxes as you go. Details: [../SOC2_TYPE1_KICKOFF.md](../SOC2_TYPE1_KICKOFF.md).

**Sales reminder:** say “pursuing SOC 2” / “readiness in progress” only — never “certified” until a report is issued.

---

## Decisions & ownership

- [ ] Read [SMPL_SOC2_Readiness_Reference_v2.md](../SMPL_SOC2_Readiness_Reference_v2.md) (§1 scope, §6 sales language)
- [ ] Fill [00_decision_log.md](./00_decision_log.md): Sec + Avail + Conf; PI deferred
- [ ] Name executive sponsor
- [ ] Name security owner
- [ ] Name engineering owner
- [ ] Name ops / CS privileged-access owner (may be same person)
- [ ] Choose platform path: create Vanta/Drata/Secureframe account **or** write “wait until ____” in decision log (do not stall MFA either way)
- [ ] Set target Type I month (even if approximate)

---

## Access hardening (do this before or while buying a platform)

- [ ] MFA on GitHub org admins / owners
- [ ] MFA on Vercel team
- [ ] MFA on Railway
- [ ] MFA on Neon
- [ ] MFA on corporate email / IdP
- [ ] MFA on Stripe
- [ ] MFA on Sanity (if admin access exists)
- [ ] MFA on Resend / Anthropic consoles
- [ ] First pass of [03_access_inventory_template.md](./03_access_inventory_template.md)
- [ ] Confirm no shared passwords for prod systems

---

## Boundary & vendors

- [ ] Review [01_system_boundary.md](./01_system_boundary.md); resolve or assign TBDs
- [ ] Review [02_subprocessors.md](./02_subprocessors.md); mark any unused vendors
- [ ] Start folder for vendor SOC reports (under NDA) — Vercel, Railway, Neon, Stripe, Anthropic, Resend, etc.

---

## Engineering hygiene (start Week 1, finish into Week 2)

- [ ] Branch protection on `main` + required PR review
- [ ] Confirm secrets are not in git; production secrets only in Vercel/Railway (etc.)
- [ ] Note who can deploy frontend (Vercel) vs API (Railway)
- [ ] Calendar a Neon backup restore test

---

## Policies & sales unblockers (start drafting)

- [ ] Open [04_policy_index.md](./04_policy_index.md); pick P01–P04 to draft first
- [ ] Kick off customer DPA (counsel or template)
- [ ] Kick off security one-pager (encryption, tenant isolation, no GL write-back, auth model, AI keys on API)
- [ ] Align external language with “pursuing” only

---

## End of Week 1 — definition of done

- [ ] Decision log has owners + scope + platform choice or explicit wait
- [ ] MFA on admin cloud accounts
- [ ] Access inventory first pass exists
- [ ] Subprocessors list ready to attach to questionnaires
- [ ] At least four policy drafts started (or platform templates assigned)
