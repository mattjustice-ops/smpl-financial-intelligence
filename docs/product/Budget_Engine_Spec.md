# Budget Engine — product spec

> **Status:** Phase 1 — ARR + GTM + HC + IS live; BS/CF stubs next  
> **Org:** Demo Co `8571e520-0687-4516-bdee-379f37c58c1f`  
> **Close month:** `2026-06` (rolls forward as monthly Actuals land)  
> **Budget plan year:** FY2027 (`2027-01` → `2027-12`)  
> **Demo gates:** Advisor dry-run **Fri 2026-09-05** · Partner meeting **Tue 2026-09-09**

## Decisions (locked)

| Topic | Decision |
|-------|----------|
| Historical context | Read-only **FY26 quarterly** columns (Q1–Q2 Actual, Q3–Q4 Fcst) |
| ARR driver | **YoY ending ARR growth** → compound monthly → net new → component mix |
| Jan 2027 BOP | Locked to **Dec 2026 Forecast** ending ARR **$90,291,801.85** |
| GTM direction | **Top-down from ARR new business** → opps → ~3× pipeline → MQLs → marketing spend → implied S&M |
| Tab compute order | **ARR → GTM → Sales → HC → IS → BS → CF last** |
| Notes | Per-row notes on every tab (assumption register seed) |
| Dept GL / P&L by group | **Back pocket** — after overall product feels right |

## Demo readiness path (hit every gap)

```
Wed–Thu  Budget tabs: HC → IS → Overview tie-outs → light BS/CF stubs
Thu–Fri  Period-scoped Actual loader + Jul close pack smoke
Fri      Advisor demo: Budget Engine story + live Board/FE + one close roll
Sat–Mon  Jul–Dec packs, forecast rebase, Budget CSV export / “submit”
Mon–Tue  Company brief + LLM narrative; PPI/predictive skim; partner dry-run
Tue      Partner meeting
```

### Must-hit gaps (baked into path)

| Gap | When | Demo proof |
|-----|------|------------|
| **HC → payroll into IS** | Wed–Thu | Change hires → IS opex moves |
| **Overview tie-outs** | Thu | ARR↔GTM↔HC↔IS checks green/amber |
| **Period-scoped Actual upsert + close_month roll** | Thu–Fri | Load Jul without wiping Jan–Jun |
| **Forecast rebase after close** | Fri+ | Jul Actual → H2 Fcst / FY27 BOP refresh story |
| **Versioned submit** | Mon | Export `Budget_*` pack / named plan version |
| **Variance as first-class** | Fri+ | Act vs Bud vs Fcst on Board (existing) + Budget notes |
| **Assumption register** | Ongoing | Notes columns → brief “drivers” strip on Overview |
| **Company brief (thin)** | Mon | 1–2p who/ICP/market/2027 goals for LLM |
| **PPI / predictive** | Mon–Tue | 3–5 feasibility questions on submitted plan |
| **Synthetic data labeling** | Always | Demo close / not audited |

### Advisor Friday (minimum lovable)

1. Sign-in → `/app/board` + `/forecast-engine` show **Live** warehouse (not Demo 502)  
2. `/budget-engine`: ARR → GTM → HC → IS chain with YoY / coverage / hire levers  
3. Overview KPIs + at least ARR↔GTM and GTM/HC→IS narrative  
4. Walk: “change growth → GTM spend moves → HC sales capacity → IS”

### Partner Tuesday (fuller)

Friday set **plus** Jul close load (or cumulative), forecast rebase story, submitted budget pack, company brief → Copilot/board commentary with market/goals color, light predictive “is this plan feasible?”

## Tab specs

### ARR (live)

- Sidebar: YoY ending ARR growth; Dec target; Jan BOP lock  
- Mix % per plan month; waterfall $; FY totals; notes  

### GTM (live)

- Demand from ARR **new business**  
- Editable: ACV, opp→close %, MQL→opp %, CPL; coverage × slider  
- Derived: logos, opps to close, pipeline $, MQLs, marketing spend, implied S&M  

### Sales (live)

- Dimensions: **region × group (NB | CS) × role**; FY25 high-watermark quota seed  
- FY26 context = prior annual / 4; FY27 months = incremental quota run-rate  
- **NB demand** = ARR new business; **CS demand** = max(expansion, FY26 churn+cont × coverage) — CS owns customers ≥1yr  
- Existing bench covers adjustable share of company growth via **YoY quota lift**; remainder filled by **NB/CS hires** through the year  
- Editable: growth goal %, bench share (quota YoY), attainment %, CS churn-cover ×, monthly hire overrides  
- Output: NB AE + CS headcount → HC → IS (CS payroll in S&M)  

### HC (live)

- **Sales (NB) + Customer Success:** read-only from Sales tab  
- **Other depts:** starting HC + monthly incremental hires + avg fully loaded cost  
- Merit / benefits load toggles  
- Output: monthly HC by dept + payroll $ → IS  

### IS (live)

- Subscription ≈ ending ARR/12; services % of sub  
- COGS % of revenue (sidebar)  
- S&M = GTM marketing program + Sales + CS + Marketing payroll  
- R&D / G&A = HC payroll for those depts  
- EBITDA → NI with D&A / interest / tax stubs  

### BS / CF (stub → derived)

- CF last; BS from cash + WC drivers; enough for partner narrative, not full GL  

### Overview

- Dec ARR, FY net new, FY marketing, FY payroll, FY EBITDA (when IS live)  
- Tie-out strip: NB/CS coverage vs required; growth split; GTM vs IS S&M  

## Data / platform follow-ups

- Period-scoped Actual load/delete (blocker for true monthly close demo)  
- Jul–Dec monthly close packs (±$2M vs Forecast)  
- FY2027 `Budget_*` CSV export after assumptions stabilize  
- Extend FY26 Actuals as closes land; BOP re-lock when FY26 completes  

## Route

`/budget-engine` — Enterprise module (reuses `forecast_engine` entitlement for demo)
