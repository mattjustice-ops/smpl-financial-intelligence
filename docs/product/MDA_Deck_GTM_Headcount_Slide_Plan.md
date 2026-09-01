# MD&A Deck — GTM, Headcount & Marketing Slide Plan

Short design plan from Matt’s feedback on `mda_deck_2026-06 (18).pptx` and attached reference slides.  
Reference images live in [`docs/partners/mda-design-refs/`](../partners/mda-design-refs/).

**Status:** Plan only (except layout/bug fixes already shipped in Prompt 5). Full new slides are optional / later.

---

## 1. GTM performance slide (priority redesign)

**Problem:** Current GTM slide under-uses space and reads as a thin funnel stub rather than a board-grade GTM operating review.

**Recommended composition (pick one primary layout per regenerate; don’t cram all):**

| Pattern | Inspiration (ref file) | Use when |
|---|---|---|
| **Funnel tables (New Logo / Migration)** | `pipeline-bookings-funnel-tables.png` | Need volume → conversion → $ outcome + vs budget in one view. 2×2: Actual/Fcst top, vs Budget bottom; segment by size (new logo) vs product (migration). |
| **Channel metrics (time × source)** | `performance-by-channel-metrics.png` | Multi-quarter pipeline / close rates / bookings / lost by Marketing, Partner, BDR, Sales, Referral + FY + vs budget. |
| **Channel metrics (wide efficiency table)** | `channel-metrics-table.png` | Single-period deep dive: Spend → MQL → SQL → Opps → Pipeline ARR → Closed Won → CAC → Win Rate by channel. |
| **Channel drilldown cards** | `channel-drilldowns-cards.png`, `channel-drilldowns-cards-grid.png` | At-a-glance Actual vs Budget cards (Spend / Pipeline / Closed Won / Efficiency) — good second visual or appendix. |
| **CAC / payback charts** | `funnel-and-efficiency-cac.png` | Efficiency story: CAC trend + CAC payback months; pair with Key Takeaways bar. |
| **Source detail + commentary** | `marketing-performance-by-source-referral-detail.png`, `marketing-performance-referral.png` | One channel deep-dive (e.g. Referral) with forecast/budget columns and a right-rail narrative. |

**Layout craft for MD&A Prompt 5:**
- Fill ≥75% of usable area; avoid a sparse funnel strip + empty band.
- Prefer **one dense primary visual** (funnel 2×2 or channel table) + **full-width Key Takeaways** under it (same packing rule as ARR/pipeline waterfalls).
- Optional second beat: CAC/payback dual cards *or* a compact channel-card strip — not both plus a third table.
- Wire to existing payload: `gtm_funnel`, `gtm_performance.channels`, pipeline waterfall / closed-lost / coverage fields already in evidence packages.

**Not in v1 build:** Marketing Roadmap / Lead-gen strategy templates (`lead-gen-funnel-strategy.png`) — keep as Department Updates inspiration (below).

---

## 2. Projected Headcount slide

**Matt likes the idea** (`projected-headcount-mock.png`): stacked headcount by department (actual solid / goal dashed) + tenure / length-of-employment lines.

**Platform today:** Strong headcount bridge already exists in the board / workforce experience (`headcount` on the reporting bundle; FY outlook already exposes HC actual / budget / forecast via `headcount_totals`).

**MD&A plan (don’t build full slide unless trivial):**
1. Add a **payload block** `headcount_bridge` / `projected_headcount` from the same SoT as the platform bridge (by department, CM + forward months, actual vs plan).
2. New optional slide (or swap into appendix): left stacked bars (actual + goal), right tenure or bridge table; Key Takeaways under.
3. Until then: keep the appendix CFS headcount warning honest; don’t invent HC charts from empty tables.

---

## 3. Marketing / Department Updates (future section)

Refs for a later **Department Updates** chapter (not core Financials MD&A):
- `big-efforts-milestones-dept.png` — priorities / milestones card strip.
- `lead-gen-funnel-strategy.png` — strategy funnel (lead gen vs demand creation).
- Source performance + roadmap-style slides (see GTM table above).

Treat as a second deck section or optional slides after Board Actions — same visual language (serif title, takeaways bar, footer section nav) as the mocks.

---

## 4. Commentary

Improving; keep regenerating with craft criteria. Light nudge only: when visuals leave vertical room, **expand Key Takeaways panel height** (still 3–5 bullets, no overlap with charts/footer). Already reflected in Prompt 5 narrative layout locks.

---

## 5. Parked — FY25 actuals for historical commentary / PPI

Future thought only: enrich historical commentary and any PPI / multi-year compares with **FY25 actuals** (not just FY26 YTD + budget). No work in this pass.

---

## 6. Bug fixes shipped with this plan (Prompt 5)

Concrete fixes for Matt’s (18) review (see chat summary):
1. Slide 2 — remove KPI sparklines under Ending ARR / Revenue / Ending Cash.
2. Slide 2 — Ending Cash **YTD Variance** reinjected from `period_matrix` (pos/neg).
3. Slide 5 — YTD Cash Summary packed below cash bridge (no overlap); YTD ending-cash budget uses `budget_ytd` not FY EoY.
4. Slide 11 — CFS variances reinjected from payload; Source note packed below Ending Cash.

**Redeploy:** Backend Prompt 5 / board metrics changes require a backend deploy before the next regenerate picks them up.
