# MD&A Deck — GTM, Headcount & Marketing Slide Plan

Short design plan from Matt’s feedback on `mda_deck_2026-06 (18).pptx` and attached reference slides.  
Reference images live in [`docs/partners/mda-design-refs/`](../partners/mda-design-refs/).

**Status:** **Shipped** (Prompt 5 payload + system prompt + reference deck — Aug 2026). Layout/bug fixes from dafd8c0 remain in place.

---

## 1. GTM performance slide (priority redesign) — **Shipped**

**Problem:** Current GTM slide under-uses space and reads as a thin funnel stub rather than a board-grade GTM operating review.

**Shipped composition:**
- Payload: `gtm_channel_metrics` (wide table), `gtm_channel_drilldown`, `gtm_funnel`, `gtm_performance` (existing pipeline waterfall on slide 7).
- Layout picker: `deck_slide_order.gtm_slide_6.primary_layout` → `channel_metrics_table` (preferred) | `funnel_tables` | `channel_drilldown_cards`.
- Slide 6: 4 KPI cards + **one dense primary visual** + **full-width Key Takeaways below** (no cramped right-rail KT).
- Code: `prompt5_mda_slides.py`, `prompt5_v3.py`, `generate_deck_reference.js`.

**Not in v1 build:** Marketing Roadmap / Lead-gen strategy templates (`lead-gen-funnel-strategy.png`) — kept as Department Updates inspiration (below).

---

## 2. Projected Headcount slide — **Shipped (optional slide)**

**Matt likes the idea** (`projected-headcount-mock.png`): stacked headcount by department (actual solid / goal dashed) + tenure / length-of-employment lines.

**Shipped:**
1. Payload block `projected_headcount` from `ReportingBundle.headcount` (same SoT as platform `headcount_totals` / `fy_outlook.headcount`).
2. Optional slide 10 when `projected_headcount.include_slide` is true (department stacked bars, monthly totals, KPIs, full-width KT).
3. Graceful skip when no headcount rows or all zero — deck becomes 13 slides; `deck_slide_order` drives numbering.

**Gap (open):** Tenure / length-of-employment requires `workforce_employees` in export bundle — payload exposes `tenure.available: false` until workforce roster is wired into ReportingBundle.

---

## 3. Marketing / Department Updates — **Shipped**

**Shipped as slides 12–13** (14-slide deck with headcount; 13 without):
- **Slide 12 — Funnel & Efficiency:** `department_updates.funnel_efficiency` — CAC proxy, CAC payback, channel efficiency table, full-width KT.
- **Slide 13 — Big Efforts & Milestones:** `department_updates.big_efforts_milestones` — 4 milestone cards + optional channel table; Claude authors from freeze/evidence.

Section nav: cyan **DEPARTMENT UPDATES** label per `deck_slide_order.section_nav`.

---

## 4. Commentary — **Shipped (prompt nudge)**

Improving; keep regenerating with craft criteria. Prompt 5 craft criteria already expand KT panel height when vertical room exists — no soft-strip regression.

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

---

## Deck order (Prompt 5 — 14 slides with headcount)

| # | Slide | Payload | Skip if |
|---|-------|---------|---------|
| 1 | Title | `period_context` | — |
| 2 | Executive Dashboard | `period_matrix` | — |
| 3 | ARR Analysis | `arr_analysis` | — |
| 4 | P&L Review | `pl_detail` | — |
| 5 | Cash & Liquidity | `cash_liquidity` | — |
| 6 | **GTM Performance** | `gtm_channel_metrics`, `gtm_funnel`, `gtm_performance` | — |
| 7 | Pipeline Waterfall | `gtm_performance.pipeline_waterfall_chart` | — |
| 8 | Risks & Opportunities | `risks_and_opportunities` | — |
| 9 | Financial Outlook | `fy_outlook`, `monthly_trends` | — |
| 10 | **Projected Headcount** | `projected_headcount` | `include_slide` false |
| 11 | Board Actions | `board_actions` | — |
| 12 | **Dept — Funnel & Efficiency** | `department_updates.funnel_efficiency` | — |
| 13 | **Dept — Big Efforts** | `department_updates.big_efforts_milestones` | — |
| 14 | Appendix CFS | `appendix.ytd_cash_flow_statement` | — |

**Regenerate:** Prompt 5 deck export after backend deploy. Verify payload via `build_prompt5_payload()` → check `deck_slide_order`, `gtm_channel_metrics.available`, `projected_headcount.include_slide`.

**Tests:** `backend/tests/test_prompt5_mda_slides.py`
