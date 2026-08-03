# Type I month + CPA shortlist — founder decision pack

**Purpose:** Help Matt pick a **target Type I month** and **2–3 CPA firms to contact** when outreach is unblocked.  
**Status:** Readiness decision pack only — **not** SOC 2 certified / not an engagement.  
**Outreach:** **Intentionally held (funding)** as of 2026-08-03 — do **not** send CPA inquiries until Matt lifts the hold.  
**Owner:** Matt Justice  
**Related:** [PROGRESS.md](./PROGRESS.md) · [00_decision_log.md](./00_decision_log.md) · [evidence/vendor-soc/TRACKER.md](./evidence/vendor-soc/TRACKER.md) · [evidence/dpa-counsel-chase-checklist-2026-07-29.md](./evidence/dpa-counsel-chase-checklist-2026-07-29.md)

---

## Honest readiness snapshot (as of 2026-08-03 sync)

| Area | State |
|------|--------|
| Policies P01–P12 + P15 | **Approved** (approval ≠ certified) |
| MFA, branch protection, Dependabot/secret scanning | **Done** |
| Access review, restore test, IR tabletop | **Done** (evidence filed) |
| Secrets spot-check + tenant isolation | **Pass** |
| Security one-pager | **Published for sales under NDA** |
| Customer DPA / MSA (R16) | **Open** — pack sent 2026-07-29; counsel firm **not selected**; awaiting redline / customer-ready draft |
| Vendor SOC / ISO Type II pack | **Partial** — Railway / Neon / Stripe / Anthropic / Resend Type II **received + reviewed** (Matt skim 2026-08-03); **Vercel** waiting/requested; GitHub P1 **deferred** until Type I audit engagement |
| CPA outreach | **Held (funding)** — pack ready; no inquiries until hold lifts |
| Other vendor regions | **TBD** (Neon us-east-1 locked) |

**Bottom line:** Control design + core evidence are strong for a solo founder. **Do not** book fieldwork until DPA is customer-offerable (or explicitly deferred in writing with auditor awareness) **and** remaining P0 vendor Type II (Vercel) is reviewed. **Do not** start CPA inquiry outreach while the funding hold is active.

---

## 1. Recommended target window options

Windows are **TARGETS**, not commitments. Type I “done” = CPA report in hand.

| Option | Window | Pros (solo founder) | Cons / risks |
|--------|--------|---------------------|--------------|
| **A — Aggressive** | **2026-10** (fieldwork target) | Keeps momentum after Week 1–Month 2 closeouts; report could land before year-end sales cycle; aligns with early Month 3–4 calendar | DPA redline + P0 vendor Type II are still open — October fieldwork is only realistic if both are green by ~mid-September; little buffer if counsel or Trust Centers lag; Q4 calendar congestion at popular firms |
| **B — Balanced (recommended default)** | **2026-11** | Matches existing Month 3–4 band (~2026-09-19 → 2026-11-19); ~6–8 weeks after this pack to close DPA + vendor downloads; still a clean Type I before deep holiday freeze | Still depends on counsel turnaround and Matt portal time; some firms slow in late November / Thanksgiving week — book kickoff early in month |
| **C — Buffer / Q4 band** | **2026-Q4** (pick exact YYYY-MM after quotes: Oct **or** Nov **or** early Dec) | Maximum honesty with open legal/vendor work; lets quotes drive the month; early Dec only if pre-engagement checklist is green | Vague until narrowed; Dec fieldwork often slips into January; sales may ask “when?” without a pinned month — pin after first two firm replies |

**Guidance:** Prefer **B (2026-11)** unless a live enterprise deal forces earlier. Use **C** only as the holding label until quotes return, then write a concrete `YYYY-MM` into [PROGRESS.md](./PROGRESS.md).

---

## 2. CPA / SOC 2 Type I shortlist (early SaaS–suitable)

Licensed CPA (or CPA-affiliated assessor firm that issues SOC 2 under AICPA AT-C) required for a real report. **No pricing below** — ask each firm for a scoped Type I quote (Security + Availability + Confidentiality; solo founder; cloud SaaS; DIY evidence folder, no Vanta/Drata yet).

| # | Firm | Typical focus | How to inquire | Notes for SMPL |
|---|------|---------------|----------------|----------------|
| 1 | **Johanson Group LLP** | Boutique SOC / ISO / HIPAA for startups & early SaaS; common on GRC marketplaces | [johansonllp.com](https://johansonllp.com/) contact form · support@johansonllp.com · (719) 434-0750 | Often shortlisted for first Type I; right-sized scope; ask how they handle DIY evidence (no Vanta) and AI/LLM subprocessor (Anthropic + P15) |
| 2 | **BARR Advisory** | Cloud-native / AWS-heavy SaaS; SOC + ISO; approachable mid-market | [barradvisory.com](https://barradvisory.com/) → Contact / free consultation | Strong fit for fully cloud stacks (Vercel/Railway/Neon); clarify attest vs advisory walls; ask Type I timeline for ~1-person ops |
| 3 | **Sensiba** (Sensiba LLP / tech attest practice) | California CPA firm; tech & life sciences; fixed-fee messaging in market; partners with common GRC tools | [sensiba.com](https://www.sensiba.com/) contact / assurance inquiry | Good “real CPA firm” letterhead without Big Four process; confirm they will engage a DIY readiness shop (platform deferred) |
| 4 | **A-LIGN** | High-volume SOC / multi-framework (ISO, FedRAMP, etc.); platformized delivery (A-SCEND) | [a-lign.com/contact](https://www.a-lign.com/contact) · +1 888.702.5446 | Brand recognition helps enterprise vendor reviews later; may feel heavier for solo Type I — ask explicitly for startup / Type I scoping |
| 5 | **Schellman & Company** | Specialist assessor; large SOC practice; often named in competitive RFPs | [schellman.com/contact](https://www.schellman.com/contact) · RFP path on site | Excellent letterhead; expect more structured process; useful if a named prospect already knows Schellman |
| 6 | **Prescient Assurance** | Startup / seed–Series A SOC 2; marketplace-friendly | [prescientassurance.com](https://prescientassurance.com/) contact / request proposal | Common early-SaaS alternative if boutique speed is the priority; verify CPA issuance and Type I vs Type II packaging |

**Suggested contact set (pick 2–3):**  
- **Speed + fit:** Johanson + BARR + Prescient  
- **Letterhead for enterprise:** A-LIGN + Schellman + Sensiba  

Do **not** engage the same firm for paid readiness remediation and the attest if they cannot show independence.

---

## 3. Pre-engagement checklist (green before fieldwork)

Book kickoff / fieldwork only when these are green. Inquiry emails can go out while `[~]` items finish.

| # | Must be green | Status pointer |
|---|---------------|----------------|
| 1 | Scope still locked: Security + Availability + Confidentiality; PI + Privacy deferred | [00_decision_log.md](./00_decision_log.md) |
| 2 | System boundary + production hosts match live prod | [01_system_boundary.md](./01_system_boundary.md) |
| 3 | Subprocessor list current; unused vendors out | [02_subprocessors.md](./02_subprocessors.md) |
| 4 | Policies Approved (P01–P12, P15) | [04_policy_index.md](./04_policy_index.md) |
| 5 | MFA + access inventory + signed access review | [PROGRESS.md](./PROGRESS.md) §C |
| 6 | Change/deploy path + `main` protection + Dependabot/secret scanning evidence | [CHANGE_MANAGEMENT.md](./CHANGE_MANAGEMENT.md) |
| 7 | IR plan operable + tabletop evidence | [evidence/ir-tabletop-2026-07-28.md](./evidence/ir-tabletop-2026-07-28.md) |
| 8 | Backup restore test Pass | [evidence/neon-restore-test-2026-07-27.md](./evidence/neon-restore-test-2026-07-27.md) |
| 9 | Secrets-in-env + tenant isolation Pass | Month 2 evidence files |
| 10 | **P0 vendor SOC Type II** received/reviewed under NDA (Vercel, Railway, Neon, Stripe, Anthropic, Resend; GitHub as available) | [evidence/vendor-soc/TRACKER.md](./evidence/vendor-soc/TRACKER.md) — five P0 **reviewed**; **Vercel** still open; GitHub deferred |
| 11 | **Customer DPA/MSA** customer-ready (or written deferral + auditor informed) | R16 — **not green yet** (counsel firm not selected) |
| 12 | Evidence index ready to share (policies, runbooks, dated Pass notes; PDFs outside git) | [evidence/README.md](./evidence/README.md) |
| 13 | Honest sales language still in force | “Pursuing SOC 2” / readiness — never “certified” until report in hand |

---

## 4. Draft outreach email (Matt sends)

Subject: SOC 2 Type I inquiry — early SaaS (Security + Availability + Confidentiality)

```
Hi —

I'm Matt Justice, founder of SMPL.ai (financial intelligence SaaS for operators).
We're pursuing SOC 2 Type I readiness (not certified yet) and looking for an
independent CPA firm for a Type I examination.

Scope (locked):
- Trust Services Criteria: Security, Availability, Confidentiality
- Processing Integrity and Privacy: deferred
- Stack: Vercel (FE), Railway (API), Neon (Postgres, AWS us-east-1), Auth.js,
  Stripe, Resend, Anthropic (LLM), GitHub; solo founder / all control owners = me
- Evidence: DIY folder (docs/soc2 + dated Pass artifacts); no Vanta/Drata yet

Target fieldwork window (TARGET, not commitment): [2026-10 / 2026-11 / 2026-Q4 — pick one]

Ask:
1) Are you taking new Type I engagements in that window?
2) Rough timeline from kickoff → draft report for a cloud SaaS of this size?
3) What do you need from us before fieldwork (evidence index, vendor SOC pack, DPA)?
4) Quote for Type I only; optional note on Type II observation later

Happy to share our system boundary, subprocessors list, and security one-pager
under NDA. We are not claiming SOC 2 compliance today.

Thanks,
Matt Justice
Founder, SMPL.ai
mattjustice@smpl-ai.com
https://www.smpl-ai.com
```

---

## 5. Decision boxes (Matt)

### Pick target month

- [ ] **2026-10** (aggressive)
- [ ] **2026-11** (balanced default)
- [ ] **2026-Q4** then pin YYYY-MM after quotes: ________
- [ ] Other: ________

**Decision:** ________  **Date:** ________

### Pick 2–3 firms to contact this week

- [ ] Johanson Group LLP
- [ ] BARR Advisory
- [ ] Sensiba
- [ ] A-LIGN
- [ ] Schellman & Company
- [ ] Prescient Assurance

**Contact order:** 1) ________  2) ________  3) ________  
**Emails sent (date):** ________

### After replies

- [ ] Chosen firm: ________
- [ ] Engagement letter / SOW date: ________
- [ ] Fieldwork start TARGET: ________
- [ ] Update [PROGRESS.md](./PROGRESS.md) `[!]` rows + `/compliance` data when month + firm are decided

---

## Document control

| Field | Value |
|-------|--------|
| Title | Type I month + CPA shortlist — founder decision pack |
| Status | Internal — awaiting Matt decisions |
| Created | 2026-07-31 |
| Honesty | Readiness only — not SOC 2 certified |
