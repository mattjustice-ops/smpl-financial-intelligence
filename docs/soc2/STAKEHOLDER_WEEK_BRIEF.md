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
6. **Two readiness streams still open:** (a) customer **DPA/MSA** — pack sent 2026-07-29; R16 **open**; counsel firm **not selected** (finder notes [legal/COUNSEL_FINDER_NOTES.md](./legal/COUNSEL_FINDER_NOTES.md)); (b) **vendor SOC Type II** — Railway / Neon / Stripe / Anthropic / Resend **received + reviewed** (Matt skim 2026-08-03); **Vercel** still waiting/requested; GitHub P1 **deferred** until Type I audit engagement.
7. **CPA path is packaged, outreach intentionally held (funding):** decision pack at [TYPE1_CPA_SHORTLIST.md](./TYPE1_CPA_SHORTLIST.md). Recommended default fieldwork target when unblocked: **2026-11** (TARGET, not commitment). Do **not** send CPA inquiries until funding hold lifts.
8. **Platform automation (Vanta/Drata) is deferred DIY** until an enterprise GRC requirement or CPA engagement — we are not blocked on a GRC purchase.
9. **What stakeholders can see this week with confidence:** scope lock, approved policies, Pass/signed evidence index, NDA security one-pager, five P0 vendor Type II **reviewed** (private store), honest open items. **What they cannot see:** a Type I report, a customer-ready signed DPA, or a **Vercel** Type II on file.
10. **Ask of stakeholders (optional):** patience on certification language; support for counsel selection / turnaround and Type I window once DPA + remaining vendor report are green and funding allows CPA outreach.

---

## B. Done vs open (snapshot 2026-08-03)

| Bucket | What’s in it |
|--------|----------------|
| **Done (readiness)** | Scope + owners APPROVED; boundary Q1–Q10 locked (other vendor regions TBD); P01–P12 + P15 Approved; MFA; branch protection; Dependabot/secret scanning; access review signed; restore **Pass**; IR tabletop; secrets **Pass**; tenant isolation **Pass**; security one-pager published for sales under NDA; compliance platform deferred DIY; CPA decision pack drafted; five P0 vendor Type II **reviewed** (Railway/Neon/Stripe/Anthropic/Resend) |
| **In progress `[~]`** | Vendor SOC — **Vercel** waiting/requested (five P0 reviewed); Customer DPA/MSA (sent; counsel firm not selected; R16 open) |
| **Waiting on Matt `[!]`** | Vercel Trust Center approval / download when granted; select DPA counsel (or chase if firm already engaged offline); CPA month/firm — **held (funding)** |
| **Waiting on external** | Counsel redline / customer-ready DPA draft (after firm selected); Vercel portal approval; CPA quotes / engagement / Type I report (when funding hold lifts) |
| **Not done / not claimable** | Type I report issued; Type II observation; “SOC 2 certified/compliant” |

Evidence index: [evidence/README.md](./evidence/README.md) · Vendor tracker: [evidence/vendor-soc/TRACKER.md](./evidence/vendor-soc/TRACKER.md)

---

## C. What to show in the meeting (pack)

| Asset | Use | Path |
|-------|-----|------|
| Public progress UI | Honest dashboard (not certification) | https://www.smpl-ai.com/compliance |
| This brief | Talking points + open queue | `docs/soc2/STAKEHOLDER_WEEK_BRIEF.md` |
| DPA counsel chase pack | Copy-paste chase email + cadence + R16 ladder | [DPA_COUNSEL_CHASE_PACK.md](./DPA_COUNSEL_CHASE_PACK.md) |
| Counsel finder notes | Where to look + what to ask (no firm shortlist) | [legal/COUNSEL_FINDER_NOTES.md](./legal/COUNSEL_FINDER_NOTES.md) |
| Security one-pager | Share under NDA if asked | [SECURITY_ONE_PAGER.md](./SECURITY_ONE_PAGER.md) + [SMPL_Security_One_Pager_2026-07.pdf](./SMPL_Security_One_Pager_2026-07.pdf) |
| Scoreboard | Detail on Pass vs open | [PROGRESS.md](./PROGRESS.md) |
| CPA decision pack | Month + firm shortlist — outreach **held (funding)** | [TYPE1_CPA_SHORTLIST.md](./TYPE1_CPA_SHORTLIST.md) |
| Vendor SOC working pack | Status board + remaining Vercel path | [evidence/vendor-soc/WORKING_PACK_2026-08.md](./evidence/vendor-soc/WORKING_PACK_2026-08.md) |
| Vendor session kit | Ordered portal clicks (Vercel remaining) | [evidence/vendor-soc/SESSION_CHECKLIST_2026-07-31.md](./evidence/vendor-soc/SESSION_CHECKLIST_2026-07-31.md) |

**Do not show as complete:** invented Vercel Type II, a signed DPA, or any “certified” badge.

---

## D. Ordered work queue — this week

Agent-completable items (docs/sync) are first; Matt/external next.

| # | Item | Owner | Status |
|---|------|-------|--------|
| 1 | Stakeholder brief + scoreboard/`/compliance` sync (vendor reviewed + CPA held) | Agent | **This branch** |
| 2 | **Vercel Type II** — wait for SafeBase / Trust Center approval → download → skim → `reviewed` | Matt | Open — waiting/requested |
| 3 | **DPA / counsel** — select firm (finder notes) or fill **[MATT FILL]** if already engaged; chase ~2026-08-05 only if firm known and no ack — [DPA_COUNSEL_CHASE_PACK.md](./DPA_COUNSEL_CHASE_PACK.md) | Matt → counsel | Open — firm not selected; R16 open |
| 4 | **CPA month + 2–3 firms** — pack ready; **outreach intentionally held (funding)** | Matt | **Held** — do not inquire yet |
| 5 | Book Type I fieldwork only when funding + pre-engagement checklist green (P0 Type II reviewed including Vercel + DPA customer-ready or written deferral) | Matt + CPA | Later |
| 6 | Warehouse-gate product integrity (Phase 1–2) | Eng / Matt | Parallel product track — **not** Type I certification; see [controls/WAREHOUSE_GATE_NEAR_TERM_PLAN.md](./controls/WAREHOUSE_GATE_NEAR_TERM_PLAN.md) |

---

## E. Agent vs Matt this session

| Can close in-repo / agent | Needs Matt (stop and ask) |
|---------------------------|---------------------------|
| Stakeholder brief, scoreboard + `progress.ts` sync, counsel finder notes, evidence index pointers | Vercel portal approval/download; counsel firm selection / email; Type I month pick; CPA outreach (after funding); signatures |

**Matt: which Matt-only track first after this pack?**  
1) Vercel Type II when approved · 2) DPA counsel select/chase · 3) CPA outreach after funding · 4) Evidence polish only

---

## Document control

| Field | Value |
|-------|--------|
| Title | Stakeholder week brief — SOC 2 readiness |
| Status | Internal — readiness only; not SOC 2 certified |
| As of | 2026-08-03 (sync: five P0 reviewed; Vercel waiting; CPA held) |
| Related | [PROGRESS.md](./PROGRESS.md), [TYPE1_CPA_SHORTLIST.md](./TYPE1_CPA_SHORTLIST.md), [legal/COUNSEL_FINDER_NOTES.md](./legal/COUNSEL_FINDER_NOTES.md) |
