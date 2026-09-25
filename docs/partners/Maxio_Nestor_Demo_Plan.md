# SMPL × Maxio — Live Demo Plan for Partner Integrations

**Audience:** Nestor (Senior PM, integrations) · Nick may forward / join  
**Job of the demo:** Prove the extension layer is real, that Maxio stays the foundation, and earn a **45-minute working session** (customer profile + data path together).  
**Companion materials:** Deck blueprint v2 · `Maxio_Sept8_Partnership_Path.md` · `SMPL_Maxio_Week_Prep_One_Pager.md` · `Maxio_Technical_Readiness_QA.md`  
**As of:** 2026-09-14  

**Recommendation:** Use this plan as the script source of truth. Do not ask ChatGPT to invent the demo from scratch — it will invent features and soften the honesty rules. If you want polish, paste *only* the talk-track lines into ChatGPT and ask for tighter spoken phrasing, keeping every product claim unchanged.

---

## What you are trying to get across (partnership items)

Land these five. Everything on screen serves one of them.

| # | Partnership item | How the demo proves it |
|---|---|---|
| 1 | **Complementary jobs, same customer** | Board opens on close actuals that look like Maxio-governed ARR / cash / pipeline — then you say we *consume* that record, we don't replace billing |
| 2 | **Maxio is the trusted anchor; SMPL is read-only** | Say it once, early: no writeback to Maxio / ERP / GL. Point at validation / as-of, not Neon |
| 3 | **We fill the gap after recurring-revenue reporting** | Board (what happened) → Forecast (what's in motion) → Budget / Plan Assurance (can the plan deliver) |
| 4 | **We do the implementation** | Closing beat: stack as-is, Maxio intact, customer validates and decides — not "they stand up FP&A" |
| 5 | **Integration status is honest** | No production Maxio connector today. Path A / white-glove load is how the demo is populated. MCP / REST / exports are the technical-session agenda |

**Single ask to earn:** one 45-minute working session covering **customer lane + data path** in the same meeting.

---

## What you have that is demoable today

| Surface | URL / entry | Show for | Do not claim |
|---|---|---|---|
| **Board Platform** | `/app/board` | Close narrative, ARR / cash / pipeline, MD&A export if time, clickable trust (pipeline cell → deals where available) | Native Maxio sync; universal GL drill everywhere |
| **Forecast Engine** | `/app/forecast-engine` | What's in motion vs plan; promote / outlook framing | Calibrated forecast accuracy |
| **Budget Engine + Plan Assurance** | `/app/budget-engine` → Analytics / Plan Assurance | Drivers → computed budget; 15 checks; named stress; Monte Carlo monthly cash band | Calibrated Probability of Attainment; shocks resampled monthly; preferred partner status |
| **MD&A deck** | Board export | Only if regenerating is already warm / you have a clean recent file | Live generation mid-demo (too slow / timeout risk) |

**Strongest single beat:** Plan Assurance monthly cash corridor — P10–P90 by month vs floor, tightest month, **P(any month below floor) vs P(December below floor)**. That is a question Maxio reporting does not ask.

---

## Recommended structure (best of both worlds)

| Block | Time | Where |
|---|---|---|
| Frame (Maxio-first) | 2 min | Deck slides 1–4 *or* spoken only if deck already sent |
| Live product | **6–8 min** | Board → Forecast (light) → Budget / Plan Assurance |
| Partnership close | 2–3 min | Implementation + honesty + ask |
| Q&A buffer | rest | Integrations questions |

Total live product: keep under **10 minutes**. Integrations PMs punish long tours.

If the deck is already in their hands: **skip slides 5–9 on screen** and go straight from slide 4 into the demo, then close verbally with the ask.

---

## Timed run-of-show

### 0:00–0:02 — Open (spoken)

**Say:**

> "This isn't a pitch to replace anything in Maxio. You own the recurring-revenue foundation. We extend that into planning, cash risk, and board reporting for the same growth-stage finance team — usually two to four people who can't stand up a full FP&A platform themselves. I'll show the product for about seven minutes, then I want one clear next step."

**Do:** Maxio on the left of every sentence. No Abacum. No "picks up where you leave off."

---

### 0:02–0:04 — Board: what happened (trusted close)

**Open:** `/app/board` on a clean June (or current) close.

**Show:**
1. Executive operating summary / verdict (live KPIs, not stale prose)
2. One ARR waterfall or cash view with validation / as-of visible
3. Optional: Pipeline cell → opportunity drill (Executive Flow if that's where drill is strong) — one click that proves "numbers have parents"

**Say:**

> "This is the board close package. The recurring-revenue actuals are treated as governed inputs — in a Maxio customer, that layer is yours. We reconcile across GL, CRM, and workforce around it, and every figure is meant to be explainable, not just pretty."

**Partnership item:** #1 and #2.

**Don't:** Open Neon. Don't start an MD&A regen. Don't apologize about demo data — frame as Path A / representative close.

---

### 0:04–0:05 — Forecast: what's in motion (light touch)

**Open:** Forecast Engine briefly *or* stay on Board forecast/outlook tab if cleaner.

**Show:** One forward view that is clearly not "re-report Maxio metrics" — pipeline / outlook / promote framing.

**Say:**

> "Maxio tells you what the book is. This layer is what finance needs next: what's still in motion against the plan."

**Keep to ~60 seconds.** Integrations buyers care more about Plan Assurance and data path than forecast UI chrome.

---

### 0:05–0:10 — Budget Engine + Plan Assurance (the money)

**Open:** Budget Engine → Overview briefly, then **Analytics / Plan Assurance**.

**Show in order:**
1. **Drivers → computed budget** — "This isn't a budget CSV we uploaded. Months are calculated through a closed formula graph."
2. **Feasibility / 15-check strip** — named constraints, green/amber/red
3. **One named stress case** (e.g. softer sales / pricier leads) — cash impact visible on the corridor
4. **Monte Carlo cash through the year** — P10–P90 band, floor, tightest month  
   **Line that lands:** "A plan can finish December fine and still need financing in July. That's the difference between year-end cash and path risk."

**Say (naming discipline):**

> "This is stress frequency under stated priors — not a calibrated probability of attainment. Same formula graph that built the plan; the model doesn't invent dollars in the narrative."

**Partnership item:** #3 (gap after Maxio reporting) and why Maxio customers specifically benefit (governed ARR in → plan tested on top).

**Don't:** Call it PoA. Don't claim three full years of loaded actuals if asked (historical context is partial / backcast — answer honestly per Tech Q&A).

---

### 0:10–0:12 — Implementation + integration honesty

**Screen:** Can stay on Plan Assurance or go blank / back to slide 8–9.

**Say:**

> "Two practical points. First: we perform the implementation. The customer's Maxio configuration stays intact; they validate mappings and decide — they don't redesign billing or stand up a planning stack. Second: we do not have a production Maxio connector today. What you're seeing is Path A — white-glove load into our warehouse. For partners, the open question is which data path fits which job: REST, governed MCP, or standardized exports. That's exactly what I'd like to sort in a working session with your team."

**Partnership item:** #4 and #5.

**If they ask connector timeline:** "Scaffold exists; we won't fake GA. Design-partner + agreed export/API shape is how we'd harden it."

---

### 0:12–0:15 — Close / ask

**Say:**

> "If this lane is real in your base — lean finance teams that want planning and board support without administering an FP&A platform — the right next step is one 45-minute session covering customer profile and data path together. Same room, not two cycles."

**Leave with (priority order):**
1. Confirm the **customer lane**
2. Book the **45-minute working session** (partnerships + SC + integrations)
3. Soft: sample export / AB site+key / MCP partner scope — **not** the unlock for the conversation
4. Verbal: partner certification track (costs them nothing)

**Abacum one-liner (only if raised):**

> "Abacum is your FP&A partner and we're not asking you to revisit that. We think there's a different lane — teams that want this without running a platform themselves. We'd like to test that with one joint customer."

---

## Nestor-specific concerns (pre-empt or answer short)

| Concern | Answer |
|---|---|
| Are you competitive with Maxio? | No — adjacent job; Maxio = system of record for recurring revenue; we consume it |
| Are you criticizing our data? | Opposite — governed Maxio actuals are why the extension is feasible |
| Do you already integrate? | Not in production. Scaffold + Path A. Honest on purpose |
| How much work for my team? | Low if Path A / export; co-design of connector only if we earn a design partner |
| Writeback / risk? | Read-only. No posts to Maxio, ERP, or GL |
| Security | Browser-based; magic-link today; SOC 2 readiness in progress — **not certified**; no SSO claim |

---

## Pre-flight checklist (day of)

- [ ] Logged into `/app` on production (or staging that mirrors prod demo org), not localhost
- [ ] Board close period correct; exec verdict not stale
- [ ] Plan Assurance corridor loads; stress chips respond; cash labels readable
- [ ] No MD&A job in flight / no deploy mid-demo
- [ ] Tab order bookmarked: Board → Budget Engine Analytics
- [ ] One backup: recent MD&A pptx on Desktop if they ask "board package" — do not regenerate live
- [ ] Deck: Maxio-first blueprint; no Abacum / no competitor quadrant / no "seamless integration"
- [ ] Mentally rehearse: PoA wording, connector honesty, implementation line

---

## What not to show / not to say

- Live Maxio API pull or implying connector is live  
- Neon SQL as the trust proof  
- Calibrated Probability of Attainment / "we know you'll hit the plan"  
- Preferred / successor framing vs Abacum  
- SOC 2 certified / SSO  
- Fixed implementation price as a published SKU  
- Curriculum gap as an accusation — only as a question if it comes up  
- Long Forecast Engine tour, workforce deep-dive, or regenerating MD&A  

---

## Optional ChatGPT use (safe)

Paste **only** the "Say:" blocks from this file and ask:

> "Tighten for spoken delivery. Do not add product claims, integrations, certifications, or competitive framing. Keep Maxio as the foundation and SMPL as the extension."

Do not give ChatGPT a blank "write me a Maxio demo script" prompt.
