# Stakeholder week brief — SOC 2 readiness (week of 2026-08-03)

**Audience:** Matt Justice (founder) before primary stakeholder meetings this week.  
**Honesty:** SMPL is **not** SOC 2 certified and **not** SOC 2 compliant until an independent CPA issues a Type I report. This pack is **readiness status**, not a certification claim.  
**Living scoreboard:** [PROGRESS.md](./PROGRESS.md) · Public mirror: [smpl-ai.com/compliance](https://www.smpl-ai.com/compliance)

---

## A. Meeting-ready talking points (say aloud)

1. **We are pursuing SOC 2 Type I** (Security + Availability + Confidentiality). Processing Integrity and Privacy are **deferred** by design — not forgotten.
2. **We are not certified.** “Done” for Type I means a CPA report in hand. Until then: readiness + evidence only.
3. **Control design is largely closed for a solo founder:** policies P01–P12 + P15 **Approved**; MFA on admin consoles; `main` protected; Dependabot + secret scanning on.
4. **Core operational evidence has Pass / signed artifacts** (readiness, not audit opinions): access review signed; Neon restore test **Pass**; IR tabletop complete; secrets-in-env **Pass**; tenant isolation **Pass**.
5. **Customer-facing pack exists under NDA:** security one-pager (markdown + PDF) — language is “pursuing / readiness,” never “certified.”
6. **Two readiness streams still open:** (a) customer **DPA/MSA** sent to counsel 2026-07-29 — awaiting redline (R16 open; firm unspecified); (b) **vendor SOC Type II** — public research done; **no Type II received**; Matt portal downloads remain.
7. **CPA path is packaged, not engaged:** target month + 2–3 firms still Matt decisions — pack at [TYPE1_CPA_SHORTLIST.md](./TYPE1_CPA_SHORTLIST.md). Recommended default fieldwork target: **2026-11** (TARGET, not commitment).
8. **Platform automation (Vanta/Drata) is deferred DIY** until an enterprise GRC requirement or CPA engagement — we are not blocked on a GRC purchase.
9. **What stakeholders can see this week with confidence:** scope lock, approved policies, Pass/signed evidence index, NDA security one-pager, honest open items + next clicks. **What they cannot see:** a Type I report, a customer-ready signed DPA, or a reviewed vendor Type II folder.
10. **Ask of stakeholders (optional):** patience on certification language; support for counsel turnaround and Type I window once DPA + P0 vendor reports are green.

---

## B. Done vs open (snapshot 2026-08-03)

| Bucket | What’s in it |
|--------|----------------|
| **Done (readiness)** | Scope + owners APPROVED; boundary Q1–Q10 locked (other vendor regions TBD); P01–P12 + P15 Approved; MFA; branch protection; Dependabot/secret scanning; access review signed; restore **Pass**; IR tabletop; secrets **Pass**; tenant isolation **Pass**; security one-pager published for sales under NDA; compliance platform deferred DIY; CPA decision pack drafted |
| **In progress `[~]`** | Vendor SOC collection (researched; **no Type II received**); Customer DPA/MSA (sent; awaiting counsel redline; R16 open) |
| **Waiting on Matt `[!]`** | Vendor Trust Center / Documents downloads; DPA counsel chase (firm name + ping); pick Type I month; pick 2–3 CPA firms and send inquiries |
| **Waiting on external** | Counsel redline / customer-ready DPA draft; vendor portal approvals (e.g. Neon ~2 BD); CPA quotes / engagement / Type I report |
| **Not done / not claimable** | Type I report issued; Type II observation; “SOC 2 certified/compliant” |

Evidence index: [evidence/README.md](./evidence/README.md) · Vendor tracker: [evidence/vendor-soc/TRACKER.md](./evidence/vendor-soc/TRACKER.md)

---

## C. What to show in the meeting (pack)

| Asset | Use | Path |
|-------|-----|------|
| Public progress UI | Honest dashboard (not certification) | https://www.smpl-ai.com/compliance |
| This brief | Talking points + open queue | `docs/soc2/STAKEHOLDER_WEEK_BRIEF.md` |
| DPA counsel chase pack | Copy-paste chase email + cadence | [DPA_COUNSEL_CHASE_PACK.md](./DPA_COUNSEL_CHASE_PACK.md) |
| Security one-pager | Share under NDA if asked | [SECURITY_ONE_PAGER.md](./SECURITY_ONE_PAGER.md) + [SMPL_Security_One_Pager_2026-07.pdf](./SMPL_Security_One_Pager_2026-07.pdf) |
| Scoreboard | Detail on Pass vs open | [PROGRESS.md](./PROGRESS.md) |
| CPA decision pack | Month + firm shortlist | [TYPE1_CPA_SHORTLIST.md](./TYPE1_CPA_SHORTLIST.md) |
| Vendor session kit | Post-meeting execution | [evidence/vendor-soc/SESSION_CHECKLIST_2026-07-31.md](./evidence/vendor-soc/SESSION_CHECKLIST_2026-07-31.md) |

**Do not show as complete:** invented Type II PDFs, a signed DPA, or any “certified” badge.

---

## D. Ordered work queue — this week

Agent-completable items (docs/sync) are first; Matt/external next.

| # | Item | Owner | Status |
|---|------|-------|--------|
| 1 | Stakeholder brief + scoreboard/`/compliance` sync for CPA pack + this week | Agent | **This branch** |
| 2 | **Vendor SOC session** (~45–90 min) — P0 downloads per session checklist; update TRACKER only when files exist | Matt | Open — Matt login |
| 3 | **DPA chase** — confirm counsel firm; if no ack by ~2026-08-05 (~5 BD after 2026-07-29 send), polite ETA ping — pack [DPA_COUNSEL_CHASE_PACK.md](./DPA_COUNSEL_CHASE_PACK.md) | Matt → counsel | Open — chase due this week |
| 4 | **CPA month + 2–3 firms** — decide boxes in TYPE1_CPA_SHORTLIST; send draft outreach (inquiry OK while DPA/vendor still `[~]`) | Matt | Open — Matt decide |
| 5 | Book Type I fieldwork only when pre-engagement checklist green (P0 Type II reviewed + DPA customer-ready or written deferral) | Matt + CPA | Later — not this week’s close |
| 6 | Warehouse-gate product integrity (Phase 1–2) | Eng / Matt | Parallel product track — **not** Type I certification; see [controls/WAREHOUSE_GATE_NEAR_TERM_PLAN.md](./controls/WAREHOUSE_GATE_NEAR_TERM_PLAN.md) |

---

## E. Agent vs Matt this session

| Can close in-repo / agent | Needs Matt (stop and ask) |
|---------------------------|---------------------------|
| Stakeholder brief, chase calendar note, scoreboard + `progress.ts` sync, evidence index pointers | Vendor portal NDA/downloads; counsel email/ping; firm name; Type I month pick; CPA firm contact; signatures; Type II PDF receipt |

**Matt: which Matt-only track first after this pack?**  
1) Vendor SOC session · 2) CPA month/firm outreach · 3) DPA counsel chase · 4) Evidence polish only

---

## Document control

| Field | Value |
|-------|--------|
| Title | Stakeholder week brief — SOC 2 readiness |
| Status | Internal — readiness only; not SOC 2 certified |
| As of | 2026-08-03 |
| Related | [PROGRESS.md](./PROGRESS.md), [TYPE1_CPA_SHORTLIST.md](./TYPE1_CPA_SHORTLIST.md) |
