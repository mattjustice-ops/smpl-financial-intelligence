# Reporting Export Layer

Month-end close, management review, and board reporting exports pull **only** from API/database services (no hardcoded metrics).

## Prerequisites

1. PostgreSQL running with uploaded CSVs (`scripts/load_versioned_csvs.py`).
2. Backend: `cd backend && uvicorn app.main:app --reload --port 8000`
3. Frontend: `cd frontend && npm run dev` (port **3002**)
4. Optional AI commentary: set `OPENAI_API_KEY` in `backend/.env`

Install export dependency if needed:

```bash
pip install xlsxwriter==3.2.9
```

## API Endpoints

All endpoints use the same query parameters as the executive dashboard:

| Parameter | Description |
|-----------|-------------|
| `organization_id` | Tenant UUID |
| `scenario` | `Combined`, `Actual`, `Budget`, or `Forecast` |
| `start_period` / `end_period` | `YYYY-MM` |
| `as_of_period` | Defaults to `end_period` (MTD / QTD / YTD anchor) |
| `include_ai_commentary` | `true` to draft narrative when OpenAI is configured |
| `block_on_failure` | `true` to return HTTP 409 if validation checks fail |

| Endpoint | Output |
|----------|--------|
| `GET /api/v1/export/validation` | JSON validation pre-check |
| `GET /api/v1/export/preview` | Full reporting bundle JSON |
| `GET /api/v1/export/month-end-close.xlsx` | 17-tab SaaS MD&A close workbook |
| `GET /api/v1/export/management-review.xlsx` | Executive subset workbook |
| `GET /api/v1/export/variance-commentary.xlsx` | Commentary + validation tabs |
| `GET /api/v1/export/board-presentation.pptx` | 12-slide board MD&A deck |

### Example (curl)

```bash
ORG=8571e520-0687-4516-bdee-379f37c58c1f
curl -o close.xlsx "http://127.0.0.1:8000/api/v1/export/month-end-close.xlsx?organization_id=$ORG&scenario=Combined&start_period=2026-01&end_period=2026-12&as_of_period=2026-05"
```

## Excel Workbook Tabs (Month-End Close)

1. Executive Summary  
2. KPI Scorecard  
3. Income Statement  
4. Balance Sheet  
5. Cash Flow Statement  
6. Cash Flow Bridge  
7. MRR / ARR Waterfall  
8. Pipeline Waterfall  
9. Opportunity Drilldown  
10. Marketing Performance  
11. Revenue Forecast  
12. Bookings Forecast  
13. Deferred Revenue Waterfall  
14. Headcount & Hiring  
15. GL Detail by Department  
16. Department Spend / P&L (semantic GL roll-up)  
17. Variance Commentary (data-driven MD&A fields)  
18. Data Sources & Gaps  
19. Validation Checks  

Formatting: frozen headers, currency formats, variance conditional coloring, CM/MoM/QTD/YTD summary columns, blank cells (not zeros) when data is missing, commentary/owner columns.

### Period logic (May 2026 close example)

- **Actual:** Jan–May (posted months)  
- **Forecast outlook:** Jun–Dec (open months)  
- **Budget:** full-year static plan  
- Closed months never show misleading **$0 Forecast**; close month may include Actual vs Forecast when both exist.

### Source-of-truth rules

| Domain | Source |
|--------|--------|
| ARR movement | MRR waterfall |
| Pipeline movement | Pipeline waterfall (not `marketing_pipeline` for validation) |
| Pipeline drilldown | Opportunity movements |
| Billings / revenue recognition | Deferred revenue waterfall |
| Cash forecast | Cash flow bridge (ending cash ties to balance sheet) |

## Data Sources

Exports always pull **Actual, Budget, and Forecast** separately, then lay out **months across the top**:

- **Closed months:** `Actual | Budget | Var $ | Var %` (+ `Forecast` / `Act vs Fcst` on the close month when forecast exists).
- **Open months:** `Budget | Outlook` (forecast; no zero-placeholder forecast on closed months).
- **Summary columns:** CM Actual, CM Budget, CM Var, MoM Δ, QTD, YTD.

| Section | Service / table |
|---------|-------------------|
| Waterfalls | `waterfall_response()` × 3 scenarios — MRR waterfall is ARR source of truth |
| Cash bridge | `cash_flow` waterfall × 3 scenarios |
| Financial statements | `summary()` × 3 scenarios (`actual_*`, `budget_*`, `forecast_*` tables) |
| Marketing | `marketing.actual_budget_forecast` |
| Opportunities | `pipeline_drilldown()` per movement type |
| GL | `gl_actuals` (`version` = Actual / Budget) |
| Headcount | `workforce_period_summary` (preferred), legacy `headcount_plan` / `forecast_headcount_plan` |
| Commentary metrics | Auto-filled in **Metric Context** column from A/B/F comparison |
| Missing data | **Data Sources & Gaps** tab lists required CSVs and actions |

If Budget or Forecast columns are zero for a period, open **Data Sources & Gaps** — it names the CSV/table to upload (e.g. `Budget_MRR_Waterfall.csv`, `Budget_income_statement.csv`).

## Frontend

The **Reporting exports** panel on the Executive Flow dashboard runs validation pre-check and downloads each artifact using the current org/scenario/period filters.

## Tests

```bash
cd backend
python -m pytest tests/test_reporting_export.py tests/test_workforce_integration.py tests/test_workforce_validation.py tests/test_management_pl_workforce.py tests/test_forecast_cash_workforce_payroll.py -q
```
