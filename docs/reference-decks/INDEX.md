# Reference deck index

**Folder:** `docs/reference-decks/`  
**Company:** **SMPL** — *We make finance simple* (not “ClarityFP”; that label was only used on early reference filenames.)

**Inventory (May 2026):** SMPL board/MD&A reference `.pptx` + `.xlsx`, 20 `Slide*.PNG`, 38 `IMG_*.jpg`, waterfall/GTM Excel examples.

Ask the agent: **`@docs/reference-decks/INDEX.md`** plus attach native Office files in chat — binary files may not appear in workspace search but are readable on disk.

---

## SMPL reference templates (primary dynamic targets)

Filenames may still say `ClarityFP_` from prior exports; treat them as **SMPL layout references only**.

| File | Size | Role |
|------|------|------|
| `ClarityFP_Board_Review_May2026_v5.pptx` | ~151 KB | **Target board deck** — layout + commentary patterns → `board_slides.py` / `pptx_builder.py` |
| `Copy of ClarityFP_MDA_Package_May2026_v4.xlsx` | ~57 KB | **Target MD&A workbook** — variance phrasing → `excel_workbook.py` / `commentary_engine.py` |
| `GTM Metrics Example.xlsx` | ~103 KB | GTM funnel / efficiency table patterns → `marketing_channels`, `gtm_performance` |
| `Waterfall Example Actual - Forecast - Budget 2026_05.xlsx` | ~234 KB | Actual + Forecast + Budget period columns → `board_period_ytd.py`, `reporting_period_engine.py` |

**Agent inventory script (run locally after adding files):**  
`backend/scripts/inventory_reference_decks.py` → writes `docs/reference-decks/_inventory.txt`

---

## PNG slide exports (CARET / Iterable-style — layout DNA)

Use `Slide*.PNG` for pixel-perfect hierarchy (agent can read these via full path).

---

## Deck A — CARET board / 3+9 forecast (`Slide1.PNG`–`Slide20.PNG`)

Polished **export targets** — use these for PPTX layout and narrative structure.

| Slide | Title / topic | Pattern to emulate |
|-------|----------------|-------------------|
| 1 | Section: **3+9 Forecast · GTM** | Dark green divider |
| 2 | Section: **Pipeline, Bookings, Revenue** | Light divider |
| 3 | Pipeline → bookings (FY26 3+9F) | 2×2 funnel actuals + **vs budget** (bps on rates) |
| 4 | **Q1 Actual** funnel | Same as 3, quarterly actual label |
| 5 | **Total Bookings — quarterly** | **Commentary left**, wide period table right (FY25A, FY26F, FY26B, vs 26B, Y/Y) |
| 6 | **ARR roll forward** | Entity columns; waterfall + retention / % of BoP |
| 7 | Section: **Pipeline and Bookings by Channel** | Divider |
| 8 | Channel: pipeline $, close rates, bookings, lost | Stacked blocks by channel |
| 9 | Channel: opps created, win rate, wins, losses | Four metric tables; red boxes on FY focus cols |
| 10 | Channel: deal size, licenses, PPU | Deep-dive appendix style |
| 11 | **Marketing performance metrics** (rollup) | Spend → funnel → efficiency; FY25A vs FY26F highlighted |
| 12 | Section: **Marketing Metrics by Source** | Divider |
| 13–20 | Marketing by source (Paid, Direct, Referral, …) | **~65% table + ~35% orange commentary** |

**Design system:** Green section labels, navy headers, zebra rows, `$k`, parentheses for negatives, **vs budget** and **Y/Y** columns, orange narrative headers.

---

## Deck B — Photos (`IMG_8022.jpg`–`IMG_8070.jpg`)

Use for **data semantics, tie-outs, and BOD slide patterns** — not as pixel-perfect PPTX templates (many are Excel or photo glare).

### B1 — Excel / working models (dense grids → simplify for board)

| Files (representative) | Content | Platform use |
|------------------------|---------|----------------|
| 8022, 8024–8026 | GC forecast model: pipeline, Fcst vs BOD, ARR/GAAP/EBITDA waterfalls | Cash bridge, ARR waterfall, validation tie-outs |
| 8027 | ProServ consolidated P&L by month | Department spend / GL export tabs |
| 8028–8031, 8033–8034, 8036–8037 | Revenue, hiring ROI, NDR analysis tabs | Headcount ROI commentary; retention metrics |
| 8064, 8067–8070 | Airship 3-statement model (IS-BS-CF, AR rollforward, accruals) | Balance sheet, deferred revenue, cash continuity checks |

### B2 — Airship BOD / Google Slides (photo → **strong board layouts**)

| Files (representative) | Content | Map to our slide |
|------------------------|---------|------------------|
| 8039 | **Q2 consolidated dashboard** — KPI table (TY, Plan, % var, LY) + **Key Takeaways** bullets | **Executive Summary** (scorecard + wins/risks narrative) |
| 8045 | **Q2 Headcount** — stacked bar by dept + hiring commentary | **Headcount & Hiring** |
| 8050 | **Financial outlook H2** — strategy bullets (ARR target, hiring, covenant) | **Risks & Opportunities** / MD&A |
| 8055 | **Cash forecast post refinance** — line chart vs covenant + assumptions | **Cash Forecast** |
| 8058+ (if similar) | Likely revenue/bookings/NDR slides — treat like 8039/8055 | GTM / finance sections |

### B3 — Analysis workbooks (appendix / CFO pack)

| Files | Content |
|-------|---------|
| 8032 | TAM hiring ROI scenarios (Low/Mid/High) — incremental ARR, retention uplift, ROI |
| Others | NDR by region/uplift, pipeline detail — drilldown support in Excel export, not full board slides |

---

## Priority mapping → platform board export

| Our export slide | Primary reference | Secondary |
|------------------|-----------------|-----------|
| Executive Summary | **IMG 8039** (KPI + takeaways) | Slide 5 (commentary + table) |
| SaaS MD&A Summary | IMG 8050 (strategy narrative) | Slide 5 left column |
| GTM Performance | Slide 8, 11 | Slide 9 |
| Marketing Channels | Slide 13, 15, 20 | Slide 11 rollup |
| Funnel Conversion | Slide 3, 4 | — |
| Pipeline Health / Movement | Slide 8, 9 | — |
| ARR Waterfall | Slide 6 | Excel 8022 waterfalls |
| Cash Forecast | **IMG 8055** | Excel cash bridge |
| Headcount | **IMG 8045** | 8032 hiring ROI |
| Department Spend | IMG 8027 ProServ P&L | Variance heatmap (simplified) |
| Risks & Opportunities | IMG 8050 | Executive callouts |

---

## What NOT to copy onto board slides

- Full-screen Excel grids (8022, 8067, etc.) — keep in **Excel close package** only.
- Red highlight boxes from manual decks — replace with **conditional tone** (favorable / unfavorable / watch) in generated KPIs.
- Cohort-level marketing tables on one slide without commentary column.

---

## File naming tips for future drops

- `SlideNN.PNG` — finished deck slides (layout reference).
- `IMG_####.jpg` — working sessions, Excel, or other companies’ BOD decks.
- Optional: prefix by company, e.g. `CARET_Slide5.PNG`, `AIRSHIP_8039.jpg`.

---

## Agent workflow

1. Read `Slide5`, `Slide6`, `Slide13`, `IMG_8039`, `IMG_8055`, `IMG_8045` first for layout DNA.
2. Applied in code (May 2026): `board_visuals.py`, `board_period_ytd.py`, `board_story_chain.py`, `board_slides.py`, `pptx_builder.py`.
3. Keep source-of-truth rules in `reporting_semantic_mappings.py` — decks inform **presentation**, not data logic.
4. **Deterministic templates:** `backend/app/presentation/` + `docs/design-language/` — AI fills slots only; layouts are fixed archetypes.

### Implemented layout mapping

| Layout id | Reference | Used on |
|-----------|-----------|---------|
| `executive_ytd` | IMG 8039 + YTD scorecard | Executive Summary (CM/QTD/YTD/FY + ARR trajectory) |
| `mda_narrative` | Slide 5 commentary | SaaS MD&A (What/Why/Impact/Risks/Actions) |
| `story_slide` | Slide 5/6 single-chart | GTM, Funnel, Pipeline, ARR, Revenue, Headcount |
| `marketing_source` | Slide 13 | Department spend |
| `cash_trend` | IMG 8055 | Cash Forecast |
| `spotlight` | — | Opportunity drilldown |
| `risk_matrix` | — | Risks & opportunities |
| `section_divider` | Slide 1–2 | Before GTM and ARR sections (full board) |

**Story chain:** Every slide subtitle follows GTM → Funnel → Pipeline → ARR → Revenue → Cash → Financials (`board_story_chain.py`).
