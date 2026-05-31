# SaaS Board Package — Handoff Brief for ChatGPT / External Assistants

**Company:** **SMPL** — *We make finance simple*  
**Project:** SaaS Financial Intelligence (board + MD&A export platform)  
**Repo path:** `C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence`  
**Last updated:** May 2026 (presentation engine + semantic layer pass)

Reference filenames in `docs/reference-decks/` may still use the legacy prefix `ClarityFP_`; generated decks and commentary must brand **SMPL**, not ClarityFP.

Copy this entire file into ChatGPT or attach it as context. Do not rebuild from generic PowerPoint tutorials.

---

## 1. What we are building (not what we are NOT building)

We are **not** building:
- BI dashboard exports
- Power BI / CSV screenshot decks
- “Show all data” slide generators
- Generic AI slide layouts with random charts per slide

We **are** building:
- A **SaaS operational finance intelligence** board package
- A **CFO / CRO / board-ready** narrative: GTM → Funnel → Pipeline → Opportunities → ARR → Revenue → Cash → Financials
- Output: **PowerPoint** via FastAPI export (`GET /api/v1/export/board-package`)

**Quality bar:** SaaS CFO board deck, CRO operating review, investor operating review, executive MD&A — **not** auto-generated filler.

---

## 2. Non-negotiable slide rules

Every slide must pass an **executive 10–15 second test:**
- What changed?
- Why it changed?
- Why it matters?
- What action is needed?

**Layout (one executive view per slide):**
| Zone | ~Share | Content |
|------|--------|---------|
| TOP | 15–20% | Title, subtitle, **max 4 KPI cards** (uniform size) |
| MIDDLE | 55–65% | **ONE primary visual** (chart OR table, not both stacked) |
| BOTTOM | 20–25% | **Max 3 bullets**, 1 takeaway, max 2 risk/action callouts |

**Do NOT:**
- Stack chart + table + long commentary on same slide
- Use beginning/ending pipeline balances as the hero metric
- Mix MQL counts with ARR dollars in one chart
- Export blank, placeholder, or zero-data charts
- Use more than one major chart per slide
- Write paragraph-style commentary

**Period framing (all major metrics):**
- Current Month, QTD, YTD, FY Outlook
- **Actual** for closed months ≤ `as_of_period`
- **Forecast** for open months in fiscal year
- Default narrative = **trajectory**, not isolated monthly snapshots

---

## 3. Local development

```powershell
# Terminal 1 — Postgres
cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence
docker compose up -d

# Terminal 2 — API (use project venv)
cd backend
.\start-api.ps1
# uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3 — Frontend
cd frontend
npm.cmd run dev
# Default port: http://localhost:3002  (NOT 3000)

# First-time DB migrations
cd backend
.\.venv\Scripts\Activate.ps1
python -m alembic upgrade head
```

**URLs:**
| Service | URL |
|---------|-----|
| App | http://localhost:3002 |
| API | http://127.0.0.1:8000 |
| Health | http://127.0.0.1:8000/health |
| API docs | http://127.0.0.1:8000/docs |

**Frontend env:** `frontend/.env.local`  
`NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`  
(Use `127.0.0.1`, not `localhost`, on Windows to avoid IPv6 timeouts.)

**One-shot script:**  
`powershell -ExecutionPolicy Bypass -File .\scripts\start-local-dev.ps1`  
(Starts docker, opens backend + frontend terminals. Use ASCII-only in script — no Unicode em dashes.)

**Probe API:**  
`powershell -ExecutionPolicy Bypass -File .\scripts\check-backend.ps1`

**Test org (example):** `8571e520-0687-4516-bdee-379f37c58c1f`

---

## 4. Architecture & data flow

```
collect_reporting_bundle()  →  ReportingBundle
       ↓
build_board_package_from_bundle()  →  BoardPackage (slides JSON)
       ↓
filter_board_slides()  →  drop weak / prune visuals
       ↓
render_pptx_bytes()  →  .pptx binary
```

**Source-of-truth (do not violate):**
| Metric | Source |
|--------|--------|
| ARR / MRR | `actual_mrr_waterfall`, `forecast_mrr_waterfall`, `budget_mrr_waterfall` |
| Pipeline | **Pipeline waterfall** (NOT `marketing_pipeline` for ARR validation) |
| Opportunity drilldown | `opportunity_movements` |
| Deferred revenue | Deferred revenue waterfall |
| Cash | Cash flow bridge |
| GTM / marketing | `marketing_pipeline` (GTM slides only) |

---

## 5. Key code modules (where to edit)

### Slide content & narrative
| File | Role |
|------|------|
| `backend/app/services/reporting/export/board_slides.py` | Builds 17 slides + section transitions; calls viability filter |
| `backend/app/services/reporting/export/board_visuals.py` | Charts, tables, KPIs per slide |
| `backend/app/services/reporting/export/board_slide_templates.py` | `assemble_slide()` — caps bullets/KPIs |
| `backend/app/services/reporting/export/board_commentary_service.py` | Per-slide executive commentary |
| `backend/app/services/reporting/export/board_story_chain.py` | Story subtitles + section transition copy |
| `backend/app/services/reporting/export/board_semantic_mappings.py` | Slide order, package modes, section anchors |

### Semantic / YTD layer
| File | Role |
|------|------|
| `backend/app/services/reporting/export/reporting_period_engine.py` | CM/QTD/YTD/FY; **`is_closed_period(p, as_of, has_actual_rows=...)`** required |
| `backend/app/services/reporting/export/board_period_ytd.py` | Period rollups for executive table & trends |
| `backend/app/services/reporting/export/saas_semantic_reporting.py` | Movement attribution, channels, revenue lineage, aging |
| `backend/app/services/reporting/export/board_slide_viability.py` | **Drop blank slides; prune chart+table** |

### Charts & density
| File | Role |
|------|------|
| `backend/app/services/reporting/export/board_chart_service.py` | Chart/KPI builders |
| `backend/app/services/reporting/export/board_chart_density.py` | Thin categories, $K/$M scale, max 7 points |

### PPTX rendering (presentation engine)
| File | Role |
|------|------|
| `backend/app/services/board_package/pptx_builder.py` | Renders slides to PowerPoint |
| `backend/app/services/board_package/pptx_layout_engine.py` | **Strict zones**, no overlap |
| `backend/app/services/board_package/schemas.py` | `SlideContent`, layouts, `ChartSpec` |

### Export API
| File | Role |
|------|------|
| `backend/app/services/reporting/export/board_export_service.py` | Orchestrates package + PPTX |
| `backend/app/api/export_routes.py` | HTTP export endpoints |

### Reference decks (visual only)
| Path | Use |
|------|-----|
| `docs/reference-decks/` | Slide*.PNG, IMG_*.jpg — hierarchy, whitespace, pacing |
| `docs/reference-decks/INDEX.md` | Maps references to layouts |

---

## 6. Slide order (full_board package)

1. executive_summary — `executive_ytd` layout; KPIs + ARR trajectory; YTD in KPI subtexts  
2. mda_summary — `mda_narrative`; What/Why/Impact/Risks/Actions  
3. **[section]** GTM transition — title, narrative quote, coverage KPI  
4. gtm_performance — pipeline created trend; top KPIs (spend, pipe, closed won)  
5. marketing_channels — ranked channels; top 5 + bottom 3 + Other  
6. funnel_conversion — funnel counts chart; conversion table if no chart  
7. pipeline_health — movement (created/won/lost/deferred); not ending balance  
8. pipeline_movement — **movement lineage buckets** (new / advanced / prior won / deferred)  
9. opportunity_drilldown — spotlight cards (top deals)  
10. **[section]** ARR transition  
11. arr_waterfall — ARR waterfall chart; rollforward table only if no chart  
12. retention_churn — dropped if weak duplicate of ARR slide  
13. gaap_revenue — revenue lineage (ARR → billings → deferred → revenue → cash)  
14. deferred_revenue — merged/dropped if weak vs gaap_revenue  
15. cash_forecast — cash line chart  
16. headcount — headcount bridge  
17. department_spend — dept variance table  
18. risks_opportunities — risk matrix callouts  
19. validation — appendix validation table (optional)

**Viability filter** may remove slides with no data. Slide count is **not fixed at 19**.

---

## 7. Executive reporting governance

**Policy doc:** `docs/EXECUTIVE_REPORTING_GOVERNANCE.md`  
**Code:** `backend/app/services/reporting/export/executive_reporting_governance.py`  
**Master prompt:** `docs/reference-decks/CURSOR_PROMPT_SaaS_CFO_Reporting.md`

Covers: source-of-truth hierarchy, movement lineage, density limits, appendix escalation, chart selection, visual QA, story arc, dashboard visual spec.

---

## 8. Presentation engine (May 2026 pass)

**Pipeline before PPTX:**
```
filter_board_slides() → enforce_executive_layout() → inject_appendix_slides() → render_pptx_bytes() → audit_presentation()
```

| Module | Role |
|--------|------|
| `pptx_presentation_orchestrator.py` | Forces `story_slide` / `executive_ytd`; runs QA remediate |
| `pptx_visual_qa.py` | Pre-render remediate; post-render overlap/clipping audit |
| `pptx_chart_archetypes.py` | 13 executive chart archetypes (axis, legend, density) |
| `board_appendix_engine.py` | Overflow tables/charts → `appendix_*` slides |
| `pptx_layout_engine.py` | Strict KPI / visual / footer zones (no overlap) |
| `board_chart_density.py` | $K/$M/%, top-N+Other, quarterly thinning |

**Render entry:** `render_pptx_bytes()` calls `prepare_package_for_render()` automatically.

---

## 9. Layout IDs (pptx_builder)

| Layout | Use |
|--------|-----|
| `executive_ytd` | Executive summary — KPI row + single YTD chart |
| `story_slide` | Most content slides — one visual, footer commentary |
| `mda_narrative` | MD&A cards |
| `section_transition` | Rich section divider |
| `cash_trend` | Cash forecast line |
| `spotlight` | Opportunity drilldown |
| `risk_matrix` | Risks & opportunities |
| `marketing_source` | Dept spend (table left, commentary right) |
| `compact_table` | Validation appendix |

---

## 10. Bugs fixed in this effort (do not reintroduce)

| Issue | Fix |
|-------|-----|
| Frontend timeout to API | `127.0.0.1:8000`, uvicorn `--host 0.0.0.0` |
| PowerShell script parse error | Remove Unicode em dashes from `.ps1` files |
| Circular import on API start | Empty `reporting/export/__init__.py`; slim `board_package/__init__.py`; lazy imports |
| `is_closed_period()` missing `has_actual_rows` | `reporting_period_engine._actual_presence_by_period()` |
| `ZONE_VISUAL_TOP` not defined | Import in `pptx_builder.py` |
| Overlapping chart + commentary | Zone enforcement; footer-only commentary on story slides |
| Blank / sparse slides in deck | `board_slide_viability.filter_board_slides()` |
| `TableSpec` has no attribute `table` | `_table_has_rows(table)` accepts `TableSpec` |
| `visual_zone` not defined | Added to `pptx_layout_engine.py` |

---

## 11. What is still weak / incomplete

### Presentation engine
- Visual QA on **real customer data** PPTX still needed (tune legend/axis on dense decks).
- Section transitions skipped if commentary &lt; 20 chars.
- `chart_primary` / `dual_metric` legacy paths still exist for non-story slides — prefer `story_slide`.

### Semantic layer (needs richer CSV / DB)
- Opportunity movement: heuristics on `created_period`, stage — needs CRM columns in `opportunity_movements`.
- Pipeline aging: defaults if `days_in_stage` missing.
- Channel **scatter** (spend vs pipeline bubble) — ranked table only.
- Department **variance heatmap** — table only.
- Cohort retention chart — partial.
- Headcount quota capacity — needs headcount plan data.

### Commentary
- Improves with loaded data + `company_context.py`; avoid generic “ARR increased” text.

---

## 12. Instructions for ChatGPT (paste as system context)

```
You are extending an existing FastAPI + Next.js SaaS board export in:
saas-financial-intelligence/backend/app/services/reporting/export/
and board_package/pptx_builder.py

RULES:
1. One primary visual per slide; max 4 KPIs; max 3 bullets; max 5 table rows.
2. chart OR table in middle zone — never both stacked (see board_slide_viability.prune_slide_content).
3. YTD: Actual closed months + Forecast open months (reporting_period_engine, board_period_ytd).
4. is_closed_period(period, as_of, has_actual_rows=bool) — ALWAYS pass has_actual_rows.
5. No circular imports: do not import pptx_builder from reporting/export/__init__.py.
6. Pipeline slides: movement (created/converted/lost/deferred/aging/coverage) — NOT beginning/ending balance hero metrics.
7. Movement buckets: saas_semantic_reporting.build_movement_attribution() — not raw waterfall keys alone.
8. Drop slides with score < 58 in board_slide_viability unless ALWAYS_KEEP.
9. Match reference-decks for whitespace and hierarchy — do not copy their content.
10. Extend existing modules — do not create parallel PPTX generators.

PRIORITY ORDER:
1. Fix overlap / overflow in pptx_layout_engine + pptx_builder (real PPTX QA).
2. Wire real data into charts (empty bundle = dropped slides — expected).
3. Improve opportunity_movements column mapping for movement lineage.
4. Revenue lineage when deferred revenue + billings waterfalls populated.
5. Appendix overflow — `board_appendix_engine.inject_appendix_slides()` (extend for GL/opps).
6. Chart archetypes — `pptx_chart_archetypes.py` (wire remaining slide_ids).
7. Do NOT add decorative extra charts or second charts per slide.

WHEN TESTING:
pytest backend/tests/test_board_export_slides.py
pytest backend/tests/test_board_slide_viability.py
pytest backend/tests/test_saas_semantic_reporting.py
User verifies: http://127.0.0.1:8000/health and board-package export in UI.
```

---

## 11. Original 17-slide content spec (summary)

**Slide 1 — Executive Summary:** KPI scorecard, ARR/revenue/EBITDA/cash trends, CM/QTD/YTD/FY, wins/risks/actions.

**Slide 2 — MD&A:** What changed / Why / Impact / Risks / Actions (interpret, don’t restate).

**Slide 3 — GTM:** Marketing spend, pipeline created, closed won ARR, pipe/spend — separate funnel counts from dollars.

**Slide 4 — Channels:** Efficiency ranking or scatter; dimensions: Paid Search, Social, Organic, Webinar, Events, Partner, Direct, Referral, Outbound.

**Slide 5 — Funnel:** MQL → SQL → SAL → Opp → Closed Won; conversion %; ARR separate.

**Slide 6 — Pipeline health:** Created, converted, lost, deferred, active pipe, aging, coverage — NOT ending pipeline balance.

**Slide 7 — Pipeline movement:** New created vs advanced vs prior-period closed vs deferred — CRM lineage.

**Slide 8 — Opportunity drilldown:** Top won/lost/deferred/forecast spots — not giant tables.

**Slide 9 — ARR waterfall:** New, expansion, contraction, churn, reactivation; NRR/GRR KPIs; renewals NOT additive growth visually.

**Slide 10 — Retention/churn:** Churn vs expansion trends; segment if possible.

**Slide 11 — GAAP revenue:** ARR → billings → deferred → GAAP revenue bridge.

**Slide 12 — Deferred revenue:** Billings, recognized revenue, ending deferred.

**Slide 13 — Cash:** Collections, payroll, vendor, commissions, capex, financing, ending cash.

**Slide 14 — Headcount:** Hires, attrition, rev/employee, ARR/employee, quota capacity.

**Slide 15 — Dept spend:** Variance by department; heatmap ideal.

**Slide 16 — Risks & opportunities:** Matrix with impact, owner, mitigation.

**Slide 17 — Validation:** Waterfall ties, cash ties, BS, collections alignment.

---

## 12. Package modes (API query param `package_mode`)

| Mode | Slides |
|------|--------|
| `full_board` | All narrative + section transitions + validation |
| `executive_summary` | Executive, MD&A, ARR, cash, risks |
| `gtm_deep_dive` | GTM + funnel + pipeline + opportunities |
| `finance_deep_dive` | ARR, revenue, deferred, cash, headcount, dept, validation |
| `variance_commentary` | Executive, MD&A, dept, cash, risks |

---

## 13. Export API (for testing)

```
GET /api/v1/export/board-package
  ?organization_id=<uuid>
  &as_of_period=2026-05
  &package_mode=full_board
  &include_commentary=true
```

Alias: `board-presentation.pptx`

---

## 14. Attachments that help ChatGPT most

1. This file (`docs/BOARD_DECK_HANDOFF.md`).
2. User’s full slide-by-slide spec (if longer than section 11).
3. Sample **export error** JSON (`detail` field) if any.
4. One **good** and one **bad** exported PPTX (or screenshots).
5. CSV column headers for: `opportunity_movements`, MRR waterfall, pipeline waterfall.
6. `as_of_period` and `organization_id` used in export.

---

## 15. What NOT to ask ChatGPT to redo from zero

- New generic python-pptx tutorial project  
- Replacing `ReportingBundle` with raw CSV reads in the renderer  
- Dashboard-style multi-chart slides  
- Re-adding `reporting/export/__init__.py` imports that pull in `pptx_report_builder` at load time  
- Beginning/ending pipeline balance as primary GTM chart  

**Extend** `board_visuals`, `saas_semantic_reporting`, `pptx_layout_engine`, `board_slide_viability` with real data first.

---

## 16. Conversation arc (for continuity)

1. Built 17-slide board package from reference decks (CARET / Airship patterns).  
2. User required GTM→Cash story, YTD framing, executive layouts.  
3. Presentation overlapped — added `pptx_layout_engine` + `board_chart_density`.  
4. Semantic layer: `reporting_period_engine`, `saas_semantic_reporting`.  
5. Local dev: docker, API, frontend port 3002, IPv6 localhost fix.  
6. API crashes: circular import, `has_actual_rows`, missing `ZONE_VISUAL_TOP`.  
7. Latest pass: **viability filter**, **section transitions**, **strict single-visual zones**.

---

*End of handoff brief.*
