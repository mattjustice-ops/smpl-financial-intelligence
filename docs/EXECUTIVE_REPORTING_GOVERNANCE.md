# Executive reporting governance

**Company:** SMPL — *We make finance simple*

Codified platform rules layered on semantic reporting + board export. Implemented in:

`backend/app/services/reporting/export/executive_reporting_governance.py`

**Presentation templates (deterministic layouts):** `docs/EXECUTIVE_PRESENTATION_SYSTEM.md` and `backend/app/presentation/` — AI fills metrics/commentary only; slide geometry is fixed.

Master prompt reference: `docs/reference-decks/CURSOR_PROMPT_SaaS_CFO_Reporting.md`

## Philosophy

Optimize for **executive consumption**, not slide generation. Every slide answers: *What should leadership focus on next?*

## Semantic source-of-truth hierarchy

| Domain | Primary sources (never substitute) |
|--------|-----------------------------------|
| ARR movement | MRR/ARR waterfall Actual / Forecast / Budget |
| Pipeline movement | Pipeline waterfall (not marketing_pipeline alone) |
| Opportunity attribution | Opportunity movements |
| GTM efficiency | Marketing pipeline |
| Revenue | Deferred revenue waterfall + income statement |
| Cash | Cash flow bridge |
| GL / departments | gl_detail |

**Never:** derive ARR from revenue; cash from EBITDA; collections from revenue; pipeline totals from opportunities when waterfall exists.

## Movement lineage

Pipeline movement ≠ ARR movement. Distinguish: creation, advancement, prior-period close, slip/defer, expansion, renewal, churn. Closed won in period ≠ created in period.

## Slide density (executive)

| Element | Max |
|---------|-----|
| Primary visual | 1 |
| Secondary visual | 1 |
| Bullets | 5 (footer typically 3) |
| Table rows (on slide) | 5 |
| Chart categories | 7 |
| Chart series | 2 |
| Visible table columns | 12 |

## Appendix escalation

Move detail to appendix when: table rows > 8, categories > 7, opportunities > 10, GL rows > 12, bullets > 5, or chart unreadable.

## Chart selection

| Situation | Preferred |
|-----------|-------------|
| Trend over time | Line |
| Few categories | Grouped column |
| Many categories | Horizontal bar |
| Movement | Waterfall / bridge |
| Stages | Funnel |
| Relationship | Scatter |
| Distribution | Heatmap |

**Avoid:** pie, radar, 3D, donut, gauges.

## Visual QA (pre/post render)

`pptx_visual_qa.py` — overlap, clipping, sparse slides, stacked chart+table.

`render_pptx_bytes()` runs `prepare_package_for_render()` then `audit_presentation()`.

## Story arc

GTM → Funnel → Pipeline → Opportunities → ARR → Revenue → Cash → Financials → Risks

Section transitions: title + one KPI + one takeaway (not blank filler).

## Dashboard compatibility

`DashboardVisualSpec` in governance module — chart type, axes, grouping, filters, drilldowns, KPI ids, commentary zone. Same bundle powers PPTX, Excel, commentary, future widgets.
