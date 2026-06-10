# SMPL.ai — Reporting Architecture & AI Integration Context

**Prepared by:** Finance & Product  
**As of:** June 2026  
**Purpose:** Technical handoff for the reporting pipeline, close automation, and Claude API integration.

**Related docs:** `docs/DEPLOYMENT.md`, `docs/VERCEL_AUTH_DEPLOY.md`, `docs/CUSTOMER_ACCESS.md`, `docs/VISUAL_DESIGN_WORKFLOW.md`  
**Go-live checklist (live):** `/progress` — source: `frontend/lib/go-live-progress.ts`

---

## 1. What SMPL's Reporting Layer Does

SMPL delivers a CFO operating system for SaaS finance teams. The reporting layer has three surfaces:

| Surface | Audience | Status |
|---|---|---|
| `/board` — Static HTML dashboard | Prospects, board members | Live on Vercel |
| MDA Package (Excel) | CFO / Finance team | Generated each close |
| Board Deck (PowerPoint) | Board, investors | Generated each close |

All three are driven by the same underlying CSV data — actuals from the data warehouse and forecast/budget files from the FP&A model. The goal is that **changing one config value rolls everything forward.**

The authenticated `/app` dashboards are a fourth surface (live API + Postgres). They share the same warehouse data but are not generated from the static HTML close roller.

---

## 2. The Monthly Close Roller (`smpl_close_roller.py`)

### What it is

A Python script that rolls all three reporting surfaces forward to a new close month by reading actual CSV files and writing values into the correct cells and JS data arrays.

### Location

**Planned:** `scripts/smpl_close_roller.py` (not yet in repo — build when CSV schema stabilizes).

Output files land in `frontend/public/board/` and `frontend/public/board/exports/` for Vercel deploy.

### Usage (planned)

```bash
python scripts/smpl_close_roller.py \
  --close-month 2026-07 \
  --actuals-dir  ./actuals/july \
  --forecast-dir ./forecast \
  --budget-dir   ./budget \
  --output-dir   ./output
```

Then run `npm run copy:board-all` or `npm run update:board-june` to copy patched HTML + exports into `public/board/`.

### What it updates automatically

| Component | What changes |
|---|---|
| `SMPL_Board_Platform_<month>.html` | `CLOSE_MONTH` constant + all data arrays (`ARR_ACT`, `REV_ACT`, `CASH_ACT`, etc.) |
| `SMPL_MDA_Package_<month>.xlsx` | Close month column → actuals; subtotals recalculated; sheet titles updated |
| `SMPL_Board_Review_<quarter>.pptx` | Metric values, chart data, slide narratives |

### The single line that drives everything in the HTML dashboard

```javascript
const CLOSE_MONTH = '2026-07';  // <-- UPDATE THIS EACH CLOSE
```

Every chart boundary, KPI label, actual/forecast color split, period badge, and scenario label derives from this constant automatically. See `frontend/public/board/index.html` (June 2026) for the full derivation chain.

### Critical ARR subtotal logic (do not break)

ARR is **not additive** across months. The correct logic is:

- **Beginning ARR** = first period's `beginning_arr` (point-in-time, not sum)
- **Components** (New Business, Expansion, Reactivation, Contraction, Churn) = **sum** across the period
- **Ending ARR** = last period's `ending_arr` (point-in-time, not sum)
- **Net New ARR** = sum of monthly `net_new_arr` values
- Contraction and Churn are always displayed as **positive absolute values** in the waterfall rows

### Cash flow chaining rule (do not break)

When rolling from actuals to forecast:

- July `beginning_cash` = June actual `ending_cash` (from `Actual_cash_flow_bridge.csv`)
- Do **not** use the forecast model's opening cash — it was built on a different basis
- Each forecast month chains: `ending_cash = beginning_cash + net_change`
- Balance sheet `cash` = `ending_cash` for that period

### Year-end rollover

When `--close-month` is `YYYY-01`:

- Reset all actuals arrays to just January
- Replace `TS_DATA.Forecast` and `TS_DATA.Budget` with new year CSV files
- Reset headcount bridge BOP to new January opening
- **Gate:** Do not allow year rollover until a new Budget file is present — the script will error if `--budget-dir` is missing or contains only prior-year data

### Version safety (TO BUILD)

Before any rollover, the script should:

1. Copy the prior month's output files to `./archive/<prior-month>/`
2. Write a manifest (`close_manifest.json`) with timestamp, period, file hashes
3. Expose a `--dry-run` flag that validates all CSV inputs without writing output files

This protects against data corruption and allows rollback if a close is incorrect.

---

## 3. Data File Conventions

### Actuals (from data warehouse export)

All files follow the pattern `Actual_<dataset>.csv` with a `period` column in `YYYY-MM` format.

| File | Used for |
|---|---|
| `Actual_income_statement.csv` | Revenue, GP, S&M, R&D, G&A, EBITDA, Net Income |
| `Actual_cash_flow_statement.csv` | GAAP indirect CFS |
| `Actual_cash_flow_bridge.csv` | Cash bridge (collections, payroll, etc.) — **use this for beginning/ending cash, not CFS** |
| `Actual_balance_sheet.csv` | AR, AP, Deferred Revenue, Cash, Equity |
| `Actual_MRR_Waterfall.csv` | ARR movements — NB, Expansion, Reactivation, Contraction, Churn |
| `Actual_Headcount_Plan.csv` | Monthly HC by department (Jan–May, point-in-time at start of month) |
| `Forecast_Headcount_Plan.csv` | Forecast HC including June endings (use this for close month HC) |
| `Actual_marketing_spend_by_channel.csv` | GTM channel efficiency |
| `Actual_Sales_Quotas.csv` | Rep-level quota attainment |
| `Actual_opportunities.csv` | Pipeline by channel and type |
| `Actual_Employees.csv` | Point-in-time June snapshot (132 employees excl. overhead like CFO/VPs) |

### Known data gaps (as of June 2026)

- `Actual_Headcount_Plan.csv` reflects headcount at month **start** not month end — use `Forecast_Headcount_Plan.csv` June row for June ending HC
- `Actual_Employees.csv` excludes certain overhead roles (CFO, VPs) — June ending is **137** per `Forecast_Headcount_Plan.csv`, not 132
- Forecast CSV opening cash does not match actual — always chain from `Actual_cash_flow_bridge.csv` ending cash
- No separate Budget ARR file — use `Forecast_MRR_Waterfall.csv` as budget proxy for subtotals
- `Forecast_MRR_Waterfall.csv` was built with a stale June BOP ($83.44M) — override with actual June EOP ($86.10M) and use CSV EOP values for Jul–Dec directly

### Forecast files

- `Forecast_MRR_Waterfall_V<timestamp>.csv` — versioned; use latest
- `Forecast_cash_flow_statement_V<timestamp>.csv` — versioned; use latest
- `Forecast_income_statement.csv`
- `Forecast_Headcount_Plan.csv`

---

## 4. The HTML Dashboard (`frontend/public/board/index.html`)

### Architecture

Single-file self-contained HTML. No build step, no dependencies beyond CDN Chart.js. Served at `/board` via `frontend/app/board/route.ts`. Deployable on Vercel from `public/board/`.

Copy/patch workflow: `frontend/scripts/copy-board-html.mjs`, `patch-board-exports.mjs`, `npm run update:board-june`.

### Tab structure (11 tabs)

Executive Summary → ARR Waterfall → Revenue & ARR → Cash Forecast → 3-Statement → Management P&L → GTM/Marketing → Sales → Workforce → Risks & Opps → **SMPL Copilot**

### CLOSE_MONTH derivation chain

Everything downstream of `CLOSE_MONTH`:

```javascript
const CLOSE_MONTH     = '2026-06';  // UPDATE THIS
const CLOSE_LABEL     = 'Jun 2026';
const CLOSE_MO        = 'Jun';
const CLOSE_MO_IDX    = parseInt(CLOSE_MONTH.slice(5)) - 1;  // 5 for Jun
const ACT_MONTHS_COUNT= CLOSE_MO_IDX + 1;                    // 6
const FC_MO_LABELS    = MO12.slice(CLOSE_MO_IDX + 1);        // ['Jul'…'Dec']
```

Declaration order is critical: `MO` → `MO12` → `ALL12` → `CLOSE_MONTH` → `CLOSE_MO_IDX` → `ACT_MONTHS_COUNT` → ... → `FC_MO_LABELS`

### Monthly rollover checklist (manual steps beyond the script)

1. Change `CLOSE_MONTH`, `CLOSE_LABEL`, `CLOSE_MO`
2. Extend actuals arrays: `ARR_ACT`, `NN_ACT`, `REV_ACT`, `GP_ACT`, `SM_ACT`, `RD_ACT`, `GA_ACT`, `EBITDA_ACT`, `CASH_ACT`, `COLL`
3. Add to `SD.monthly` (sales quota attainment)
4. Add to `SD.pipeline` (pipeline by month)
5. Add to `TS_DATA.Actual` — `.is`, `.cfs`, `.bs` for the new period
6. Update `WF_HC_ALL` with actual HC counts
7. Remove filled `WF_REQS` entries (start month ≤ `CLOSE_MONTH`)
8. Shift `WF_SC_PAY` / `WF_SC_HC` scenario arrays (drop first element, add Dec value)
9. Update `AI_CTX` and commentary-text divs with new actuals
10. Update `CP_DATA` in the Copilot tab

### TS_DATA structure

```javascript
TS_DATA = {
  Actual:   { periods: [...], is: {period: {...}}, cfs: {period: {...}}, bs: {period: {...}} },
  Forecast: { periods: [...], is: {period: {...}}, cfs: {period: {...}}, bs: {period: {...}} },
  Budget:   { periods: [...], is: {period: {...}}, cfs: {period: {...}}, bs: {period: {...}} }
}
```

- **Actual**: Jan–Jun (from actuals CSVs)
- **Forecast**: Jul–Dec (from forecast CSVs, with cash chained from actual ending)
- **Budget**: Full year Jan–Dec (from budget CSVs)

---

## 5. SMPL Copilot — AI Integration via Claude API

### What it is

A chat interface embedded in the dashboard's 11th tab. Answers questions about ARR, revenue, cash, headcount, GTM performance, and variances — grounded in reconciled financial data, not generic AI responses.

### Current state (as of June 2026)

- UI is built and deployed in the HTML dashboard
- `CP_DATA` object contains June actuals summary embedded in the page
- System prompt structured for three-part responses:
  1. Primary driver + variance context
  2. Financial and operational root cause
  3. Recommended action + board summary
- **API key is not yet wired** — `cpSend()` and `aiComm()` call `https://api.anthropic.com/v1/messages` without auth headers

### What Cursor needs to do to activate Copilot (demo `/board` only)

For the **public board demo**, options include:

- Short-term: backend-less proxy route or server-injected key at HTML serve time (still avoid exposing key in committed HTML)
- Never commit `sk-ant-...` into `index.html`

Model: `claude-sonnet-4-20250514`  
Max tokens: `1000`

Headers required:

```javascript
headers: {
  'Content-Type': 'application/json',
  'x-api-key': '<from server env — not client bundle>',
  'anthropic-version': '2023-06-01'
}
```

### Important: static HTML vs authenticated app

| Surface | API key handling |
|---|---|
| `/board` (public demo) | Acceptable to proxy via Next.js route with server env; do not embed key in static HTML |
| `/app` (production) | **Must** proxy through FastAPI with session + org checks — never client-side key |

### Production architecture (Phase C and beyond)

```
Browser → Next.js /api/copilot route (authenticated) → FastAPI /api/v1/copilot → Claude API
```

The FastAPI backend should:

1. Validate the user session and organization membership
2. Fetch the relevant financial data for that org from Postgres
3. Build the `CP_DATA` context dynamically from live data (not hardcoded)
4. Call Claude API with the org's data as context
5. Return the structured three-part response

### Data grounding (critical for accuracy)

Claude's answers are only as good as the context it receives. The `CP_SYSTEM` prompt and `CP_DATA` object must be updated each close month. In production `/app`, `CP_DATA` should be generated dynamically from the org's warehouse data.

The full CSV dataset (40+ files) is too large for a single prompt; recommended architecture for full fidelity is **RAG or tool-use**:

```
User question → FastAPI → SQL query against Postgres warehouse →
structured result → Claude API (with result as context) → structured response
```

### Three-part response format (enforced by system prompt)

Every Copilot response must follow:

1. **PRIMARY DRIVER + VARIANCE CONTEXT** — single most important metric with exact $ or % variance
2. **FINANCIAL AND OPERATIONAL ROOT CAUSE** — connect operational metric to financial outcome
3. **RECOMMENDED ACTION + BOARD SUMMARY** — one actionable recommendation + one board-ready sentence

---

## 6. Export Buttons — File Hosting

### Current state (June 2026 — done in repo)

Top bar has **two** links (footer export row removed):

| Button | File | URL |
|---|---|---|
| **MD&A Deck** | `SMPL_Board_Review_Q2_2026.pptx` | `/board/exports/SMPL_Board_Review_Q2_2026.pptx` |
| **Variance Commentary** | `SMPL_MDA_Package_June2026.xlsx` | `/board/exports/SMPL_MDA_Package_June2026.xlsx` |

Implemented via `openMdaDeck()` / `openVarianceCommentary()` in `index.html`, patched on copy by `frontend/scripts/patch-board-exports.mjs`.

Files live in `frontend/public/board/exports/` and must be committed for Vercel.

### Each close month

1. Replace exports in `public/board/exports/` (or copy from close roller output)
2. Run `npm run copy:board` with new HTML from Downloads
3. Commit + deploy

### Future state (authenticated `/app`)

Generate MDA and board deck on-demand via FastAPI and stream downloads — not static files.

---

## 7. AI Commentary Regeneration (`aiComm()`)

Per-tab "Regenerate AI commentary" buttons call `aiComm(slideKey, targetId)` with context from `AI_CTX`. Same API/proxy requirements as Copilot.

`AI_CTX` keys: `exec`, `arr`, `revenue`, `gtm`, `cash`, `headcount`, `risks`. Update each close month via close roller or Claude handoff.

---

## 8. Summary — What Cursor Owns vs What Claude Owns

| Task | Owner | Status |
|---|---|---|
| Wire Anthropic API via server proxy (not client HTML) | Cursor | Pending |
| `/board` export paths + Vercel static hosting | Cursor | **Done** |
| Build `smpl_close_roller.py` | Cursor (when schema stable) | Not started |
| Run close roller each month | Finance (+ Claude content) | Manual today |
| Update `CP_DATA` and `AI_CTX` each close | Claude (via close roller output) | Monthly |
| Generate MDA package + board deck content | Claude (via close roller) | Monthly |
| Build `/api/v1/copilot` in FastAPI (Phase C) | Cursor | Pending |
| RAG / SQL tool-use for full CSV fidelity | Cursor + Claude | Phase C |
| Neon auth + hosted API + PR2 org wiring | Cursor | **Next go-live track** — see `/progress` |

---

## 9. Files to Keep in Sync

| File | Updated by | Frequency |
|---|---|---|
| `frontend/public/board/index.html` | close roller + `copy:board` | Monthly |
| `frontend/public/board/exports/*.xlsx` | close roller | Monthly |
| `frontend/public/board/exports/*.pptx` | close roller | Quarterly |
| `scripts/smpl_close_roller.py` | Cursor | As needed |
| `AI_CTX` in HTML | close roller / Claude | Monthly |
| `CP_DATA` in HTML | close roller / Claude | Monthly |
| `TS_DATA` in HTML | close roller | Monthly |
| `CLOSE_MONTH` in HTML | close roller | Monthly |

---

*Last updated: June 2026*
