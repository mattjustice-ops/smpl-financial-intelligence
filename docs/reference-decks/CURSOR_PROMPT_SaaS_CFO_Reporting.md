# SMPL — SaaS CFO Board Reporting Platform

**Company:** SMPL — *We make finance simple*  
**Note:** Some reference filenames still use the legacy prefix `ClarityFP_`; branding in generated outputs must always say **SMPL**.
## Master Cursor Prompt: Month-End Close Intelligence Engine

> **How to use this file:** Paste the relevant section(s) into Cursor's system prompt or chat. Each section is self-contained. For full builds, use ALL sections. For targeted updates, use only the relevant module.

---

## SECTION 0 — WHAT THIS SYSTEM DOES

You are building an automated SaaS CFO reporting engine. Every month, a set of CSV data files is dropped into a folder. The system reads those CSVs, performs budget vs. actual vs. forecast analysis, generates executive commentary, and produces two output files:

1. **Board PowerPoint** — 20 slides, board-ready, clean white design, varied layouts
2. **MD&A Excel Workbook** — 16+ tabs, formatted, with commentary sections and embedded charts

This is NOT a generic dashboard or BI tool. The outputs must feel like they were prepared by a seasoned SaaS CFO and their team. Every number tells a story. Every slide has one job. Every commentary block explains the "so what," not just the "what."

---

## SECTION 1 — DATA ARCHITECTURE

### 1.1 Source CSV Files & Field Definitions

All source files live in `/data/` and follow consistent naming:
```
{version}_{dataset}.csv
```
Where `version` is one of: `Actual`, `Forecast`, `Budget`

#### ARR / MRR Movement
**Files:** `Actual_MRR_Waterfall.csv`, `Forecast_mrr_waterfall.csv`, `Budget_MRR_Waterfall.csv`

| Field | Type | Description |
|---|---|---|
| `period` | YYYY-MM | Reporting month |
| `beginning_arr` | float | Opening ARR ($) |
| `new_business_arr` | float | New logo ARR added |
| `expansion_arr` | float | Upsell/seat expansion from existing customers |
| `contraction_arr` | float | Downgrades from existing customers (negative) |
| `churn_arr` | float | Full customer losses (negative) |
| `reactivation_arr` | float | Reactivated churned customers |
| `net_new_arr` | float | Sum of all movement (excl. beginning/ending) |
| `ending_arr` | float | Closing ARR ($) |
| `net_dollar_retention_rate` | float | NRR as decimal (e.g., 1.002 = 100.2%) |
| `gross_retention_rate` | float | GRR as decimal |

**Critical rules:**
- Renewals do NOT appear as a separate line — they are embedded in the retention rate
- Contraction and Churn are always negative values in source data
- NRR = (Expansion + Contraction + Churn) / Beginning ARR + 1
- Net New ARR = New Business + Expansion + Contraction + Churn + Reactivation

#### Income Statement
**Files:** `Actual_income_statement.csv`, `Forecast_income_statement.csv`, `Budget_income_statement.csv`

| Field | Type | Description |
|---|---|---|
| `period` | YYYY-MM | Reporting month |
| `revenue` | float | Total GAAP revenue |
| `cost_of_revenue` | float | COGS |
| `gross_profit` | float | Revenue - COGS |
| `gross_margin_percent` | float | As decimal (e.g., 0.77) |
| `sales_and_marketing` | float | S&M OpEx |
| `research_and_development` | float | R&D OpEx |
| `general_and_administrative` | float | G&A OpEx |
| `total_opex` | float | Sum of OpEx lines |
| `ebitda` | float | Operating income before D&A |
| `depreciation_amortization` | float | D&A add-back |
| `operating_income` | float | EBITDA - D&A |

#### Cash Flow Bridge
**Files:** `Actual_cash_flow_bridge.csv`, `Forecast_cash_flow_bridge.csv`, `Budget_cash_flow_bridge.csv`

| Field | Type | Description |
|---|---|---|
| `period` | YYYY-MM | Reporting month |
| `beginning_cash` | float | Opening cash balance |
| `collections` | float | Cash collected from customers |
| `payroll_cash_out` | float | Payroll disbursements (positive = outflow) |
| `commission_cash_out` | float | Commission payments |
| `vendor_cash_out_n30` | float | Vendor/AP payments |
| `tax_cash_out` | float | Tax payments |
| `interest_cash_out` | float | Interest expense paid |
| `other_operating_cash_out` | float | Miscellaneous operating outflows |
| `capex` | float | Capital expenditures |
| `financing_to_maintain_cash_floor` | float | Financing draws (only if floor breached) |
| `ending_cash` | float | Closing cash balance |
| `cash_floor` | float | Minimum operating cash requirement |

#### GTM / Marketing Pipeline
**Files:** `Actual_marketing_pipeline.csv`, `Forecast_marketing_pipeline.csv`, `Budget_marketing_pipeline.csv`

| Field | Type | Description |
|---|---|---|
| `period` | YYYY-MM | Reporting month |
| `marketing_channel` | string | Channel name |
| `marketing_spend` | float | Spend ($) |
| `mqls` | int | Marketing Qualified Leads |
| `sqls` | int | Sales Qualified Leads |
| `sals` | int | Sales Accepted Leads |
| `opportunities_created` | int | Opportunities opened |
| `pipeline_arr_created` | float | ARR value of pipeline created |
| `closed_won_arr` | float | ARR from closed-won deals |
| `closed_lost_arr` | float | ARR from closed-lost deals |
| `cost_per_mql` | float | Spend / MQLs |

**Derived fields to compute:**
```python
pipeline_efficiency = pipeline_arr_created / marketing_spend  # Pipeline per $1 spend
win_rate_dollar = closed_won_arr / (closed_won_arr + closed_lost_arr)
win_rate_count = closed_won_count / (closed_won_count + closed_lost_count)
```

#### Pipeline Waterfall
**Files:** `Actual_pipeline_waterfall.csv`, `Forecast_pipeline_waterfall.csv`, `Budget_pipeline_waterfall.csv`

| Field | Type | Description |
|---|---|---|
| `period` | YYYY-MM | Reporting month |
| `beginning_pipeline` | float | Opening pipeline balance |
| `pipeline_created` | float | New pipeline created |
| `closed_won` | float | Pipeline converted to ARR |
| `closed_lost` | float | Pipeline lost |
| `slipped_pipeline` | float | Deals pushed to future periods |
| `ending_pipeline` | float | Closing pipeline balance |
| `weighted_pipeline` | float | Probability-weighted pipeline |
| `pipeline_coverage_ratio` | float | Pipeline / ARR target |

#### Opportunity Movements (CRM Detail)
**File:** `Actual_opportunity_movements.csv` (also Forecast, Budget variants)

| Field | Type | Description |
|---|---|---|
| `opportunity_id` | string | Unique deal identifier |
| `customer_name` | string | Account name |
| `opportunity_type` | string | New Business / Expansion / Renewal |
| `stage` | string | CRM stage |
| `close_status` | string | Closed Won / Closed Lost / Contraction / Churn |
| `arr_impact` | float | ARR value of this opportunity |
| `region` | string | Geographic region |
| `customer_segment` | string | Enterprise / Mid-Market / SMB |
| `billing_cadence` | string | Annual / Quarterly / Monthly |
| `contract_term_months` | int | Contract length |

#### Deferred Revenue
**File:** `Actual_deferred_revenue_waterfall.csv`

| Field | Description |
|---|---|
| `beginning_deferred` | Opening deferred revenue balance |
| `billings` | New invoices issued |
| `revenue_recognized` | GAAP revenue recognized |
| `ending_deferred` | Closing deferred balance |

#### Headcount Plan
**File:** `headcount_plan.csv`

| Field | Description |
|---|---|
| `department` | Department name |
| `role` | Job title/level |
| `period` | Month of hire or measurement |
| `headcount_beginning` | Opening HC |
| `new_hires` | Hires in period |
| `attrition` | Departures in period |
| `headcount_ending` | Closing HC |
| `quota_capacity` | Sales quota capacity ($) |

#### GL Detail
**File:** `gl_detail.csv`

| Field | Description |
|---|---|
| `period` | Reporting month |
| `department` | Department |
| `sub_department` | Sub-department |
| `account_group` | Expense category (e.g., Salaries, Software) |
| `expense_type` | Specific line item |
| `actual_amount` | Actual spend |
| `budget_amount` | Budget |
| `variance` | Actual - Budget |

---

### 1.2 Period Logic — ALWAYS follow these rules

```python
# Determine which periods are actuals vs. forecast
ACTUAL_PERIODS = all periods where version == 'Actual'
FORECAST_PERIODS = all periods where version == 'Forecast'
BUDGET_PERIODS = full 12-month plan for the fiscal year

# Period aggregation logic
def get_period_data(df, period_type, start_month, end_month):
    """
    QTD = sum of months within current quarter up to latest actual
    YTD = sum of Jan through latest actual month
    H1/H2 = respective half-year aggregation
    FY = Actual months + Forecast months for open periods
    """
    pass

# ALWAYS default to: Actual closed periods + Forecast open periods
FULL_YEAR_VIEW = actual_months + forecast_months  # Never budget-only for "full year"

# Quarter mapping
Q1 = ['01','02','03']  # Jan, Feb, Mar
Q2 = ['04','05','06']  # Apr, May, Jun
Q3 = ['07','08','09']  # Jul, Aug, Sep
Q4 = ['10','11','12']  # Oct, Nov, Dec
```

---

### 1.3 Variance Calculation Rules

```python
# Standard variance = Actual - Budget (or Forecast - Budget)
variance_dollar = actual - budget

# Good/bad interpretation depends on the line:
FAVORABLE_WHEN_POSITIVE = ['revenue', 'arr', 'gross_profit', 'ebitda', 'cash',
                            'nrr', 'grr', 'collections', 'pipeline_created',
                            'closed_won_arr', 'mqls', 'sqls']

FAVORABLE_WHEN_NEGATIVE = ['cost_of_revenue', 'total_opex', 'sales_and_marketing',
                            'research_and_development', 'general_and_administrative',
                            'payroll_cash_out', 'vendor_cash_out', 'capex',
                            'churn_arr', 'contraction_arr', 'closed_lost_arr']

def variance_color(field, variance_value):
    if field in FAVORABLE_WHEN_POSITIVE:
        return GREEN if variance_value > 0 else RED
    elif field in FAVORABLE_WHEN_NEGATIVE:
        return GREEN if variance_value < 0 else RED  # Less spend = good
    return NEUTRAL

# Percentage variance
variance_pct = variance_dollar / abs(budget_value)  # Always divide by absolute budget
```

---

## SECTION 2 — BOARD POWERPOINT SPECIFICATION

### 2.1 Design System

```
PALETTE:
  Navy:    #1a2e44   (titles, headers, dark backgrounds)
  Teal:    #0d9488   (primary accent, positive indicators, section labels)
  Green:   #15803d   (favorable variance)
  Red:     #dc2626   (unfavorable variance)
  Amber:   #d97706   (watch/neutral, moderate risk)
  Gray:    #64748b   (secondary text, captions)
  DkGray:  #334155   (body text)
  LGray:   #e2e8f0   (borders, dividers)
  White:   #ffffff   (slide background)
  OffWht:  #f8fafc   (panel backgrounds, alternating rows)
  DkText:  #0f172a   (primary body text)

TYPOGRAPHY:
  All text: Calibri (universally available in PowerPoint)
  Title:    28–32pt, bold, Navy
  Section:  8pt, Teal, ALL CAPS, letter-spacing 2.5
  Subtitle: 10pt, Gray, regular
  Body:     9–10pt, DkGray, regular
  Data:     8.5–9pt in tables
  Caption:  8.5pt, Gray, italic
  KPI val:  18–26pt, bold, Navy
  KPI lbl:  8pt, Gray

SLIDE DIMENSIONS: 10" × 5.625" (16:9)

MARGINS:
  Left/Right: 0.45"
  Top (content starts): 1.28" (below header)
  Bottom (content ends): 5.42" (above footer)
  Content area height: 4.14"

HEADER STRUCTURE (every content slide):
  - Navy bar: x=0, y=0, w=10, h=0.055
  - Section label: x=0.45, y=0.12, 8pt Teal bold, ALL CAPS, charSpacing=2.5
  - Title: x=0.45, y=0.34, 28pt Navy bold
  - Subtitle: x=0.45, y=0.98, 10pt Gray (optional)

FOOTER STRUCTURE (every content slide):
  - Horizontal rule: y=5.44, LGray 0.8pt
  - Left text: "SMPL · Board Operating Review · [Month Year] · CONFIDENTIAL"
  - Right: "N / TOTAL" page number
```

### 2.2 Layout Rules — THE MOST IMPORTANT SECTION

**The cardinal rule: ONE BIG IDEA PER SLIDE.**

Every slide should be immediately legible from 10 feet away. An executive should be able to understand the point of a slide in under 5 seconds.

#### Layout Types — Use variety. Never repeat the same layout twice in a row.

**TYPE A: Large Chart + Key Takeaways**
```
[CHART — 65% width, full content height]  [KEY TAKEAWAYS — 33% width]
                                            Key Takeaways (bold navy)
                                            ─────────────────────────
                                            • Bullet 1 (specific, data-backed)
                                            • Bullet 2
                                            • Bullet 3
                                            • Bullet 4
                                            • Bullet 5
[caption italic gray]
```
Use for: ARR trend, Revenue trend, cash trend, bookings trends

**TYPE B: Two Charts Side by Side**
```
[CHART LEFT — 45% width]        [CHART RIGHT — 45% width]
[caption]                        [caption]
• Bullet 1                       • Bullet 1
• Bullet 2                       • Bullet 2
```
Use for: Cash (balance + collections), GTM (two channels), Pipeline (created + coverage)

**TYPE C: Large Chart + Compact Table**
```
[CHART — 60% width]    [TABLE HEADER]
                        [row 1]
                        [row 2]
                        [row 3]
[caption]               [KEY TAKEAWAYS — 2 bullets]
```
Use for: ARR waterfall + bridge table, P&L + variance table

**TYPE D: Full-Width Table**
```
[SECTION LABEL]
[TABLE — full width, all columns]
──────────────────────────────────────────
Key finding: [bold label] [narrative sentence]
Board action: [bold label] [action sentence]
```
Use for: GTM channel efficiency (all channels in one view), Department variance

**TYPE E: Pure Narrative (Text-Dominant)**
```
[Section 1 title]
[3–4 sentences of body text]
───────────────────────────
[Section 2 title]
[3–4 sentences]
───────────────────────────
[Section 3 title]
[3–4 sentences]
───────────────────────────
[Section 4 title]
[3–4 sentences]
```
Use for: Financial Outlook, Strategic context, MD&A narrative — maximum ONE of these per deck

**TYPE F: Executive Dashboard (Cover-style Summary)**
```
[TITLE]
[subtitle]
[COMPARISON TABLE — left 60%]     [KEY TAKEAWAYS — right 38%]
 This Period | Budget | % Var |
 Last Period | % Var  |       |
```
Use for: Slide 2 executive dashboard only

**TYPE G: Action Cards**
```
[01][FOR APPROVAL] Action Title                    Owner  Due Date
     Description body text
─────────────────────────────────────────────────────────────────
[02][FOR APPROVAL] Action Title                    Owner  Due Date
     Description body text
```
Use for: Board approvals slide — always the last slide

#### WHAT NEVER TO DO:
- ❌ Never put a KPI strip AND a chart AND a table AND driver boxes on the same slide
- ❌ Never repeat Type A layout more than once in a row
- ❌ Never use more than 5 bullet points in a Key Takeaways column
- ❌ Never put text below 8pt anywhere in the deck
- ❌ Never crowd the slide — if it feels busy, remove something
- ❌ Never use a legend that takes more than 10% of chart area
- ❌ Never use 3D charts, shadows, or gradients on data
- ❌ Never use pie charts — use bars or tables instead
- ❌ Never leave a slide without a caption below each chart

### 2.3 Chart Specifications

#### Colors in Charts
```python
CHART_COLORS = {
    'actual':      '0d9488',  # Teal — primary data series
    'budget':      'd1d5db',  # Light gray — budget/plan
    'forecast':    'f59e0b',  # Amber — forecast periods
    'prior_year':  '9ca3af',  # Medium gray — prior year
    'favorable':   '15803d',  # Green — positive variance
    'unfavorable': 'dc2626',  # Red — negative variance
    'gross_profit':'d1fae5',  # Light green — GP bars
    'highlight':   '1d4ed8',  # Blue — callout or emphasis
}
```

#### Chart Axis Rules
```
- All $ values: abbreviate as $XM (millions) or $XK (thousands)
- All % values: show as XX.X% — always one decimal place
- Never show more than 6 tick marks on any axis
- Y-axis: start from 0 unless the range is very tight (then start from 80% of min)
- X-axis for monthly: show month abbreviations (Jan, Feb, Mar...)
- Grid lines: light gray (#e2e8f0), 0.5pt — horizontal only, no vertical
- Font size on axes: 9–10pt, Gray
- Show data labels on bar charts when <= 6 bars
- Never show data labels on line charts (too cluttered)
```

#### Required Chart → Slide Mappings

| Slide | Primary Chart | Chart Type | Data Source |
|---|---|---|---|
| Executive Summary | ARR trend actual vs budget | Line (2 series) | ARR Waterfall |
| ARR Waterfall | Monthly net new ARR act vs bud | Grouped bar | ARR Waterfall |
| ARR Retention | NRR trend monthly | Line | ARR Waterfall |
| Revenue & P&L | Revenue + Gross Profit combo | Bar (GP) + Line (Rev) | Income Statement |
| EBITDA Bridge | Waterfall: Rev → GP → OpEx → EBITDA | Waterfall bar | Income Statement |
| Cash Forecast | Cash balance trend | Line (2 series) | Cash Flow Bridge |
| Collections | Monthly collections bar | Bar (single) | Cash Flow Bridge |
| Pipeline Health | Pipeline created vs coverage | Bar + Line combo | Pipeline Waterfall |
| GTM Efficiency | Pipeline per $1 spend | Horizontal bar or table | Marketing Pipeline |
| ARR by Segment | New Business by segment | Stacked bar | Opportunity Movements |
| Headcount | HC bridge beginning + hires - attrition | Waterfall bar | Headcount Plan |
| Department Spend | Variance by dept | Horizontal bar | GL Detail |

### 2.4 The 20-Slide Board Deck Structure

```
SECTION 1: EXECUTIVE LAYER (Slides 1–3)
├── Slide 1: Cover
│     Layout: LEFT panel (navy) | RIGHT panel (5 KPIs with lines)
│     KPIs: ARR, Revenue, Cash, NRR, FY Forecast
│
├── Slide 2: Executive Dashboard
│     Layout: TYPE F — ARR trend chart + Metrics table + Key Takeaways
│     Data: All primary KPIs, current vs budget vs prior period
│
└── Slide 3: MD&A Summary (text-dominant)
      Layout: TYPE E — 4 narrative paragraphs
      Content: ARR story, Revenue story, Cash story, Outlook
      This is the CFO's spoken narrative on one slide

SECTION 2: ARR & RETENTION (Slides 4–6)
├── Slide 4: ARR Waterfall
│     Layout: TYPE C — Net new ARR bars + FY bridge table
│     Data: ARR Waterfall CSVs (actual, forecast, budget)
│
├── Slide 5: ARR Retention
│     Layout: TYPE A — NRR trend line chart + Key Takeaways
│     Data: NRR and GRR monthly trend, SMB vs enterprise breakdown
│
└── Slide 6: ARR by Segment / Motion
      Layout: TYPE B — New Business by segment | Expansion by type
      Data: Opportunity Movements CSV

SECTION 3: REVENUE & P&L (Slides 7–8)
├── Slide 7: Revenue & Gross Margin
│     Layout: TYPE A — Combo chart (GP bars + revenue lines) + Key Takeaways
│     Data: Income Statement
│
└── Slide 8: EBITDA & OpEx
      Layout: TYPE C — EBITDA bridge waterfall + OpEx variance table
      Data: Income Statement

SECTION 4: GTM & PIPELINE (Slides 9–12)
├── Slide 9: GTM Channel Efficiency
│     Layout: TYPE D — Full-width channel table sorted by efficiency
│     Data: Marketing Pipeline (all channels, YTD)
│
├── Slide 10: Pipeline Health
│     Layout: TYPE B — Pipeline created trend | Coverage ratio trend
│     Data: Pipeline Waterfall
│
├── Slide 11: Funnel Conversion
│     Layout: TYPE C — Funnel visualization + Conversion rate table
│     Data: Marketing Pipeline (MQL → SQL → SAL → Opp → Won)
│
└── Slide 12: Pipeline Detail (optional: move to appendix)
      Layout: TYPE D — Opportunity spotlight table
      Data: Opportunity Movements (top 10 by ARR impact)

SECTION 5: CASH & LIQUIDITY (Slides 13–14)
├── Slide 13: Cash Forecast
│     Layout: TYPE B — Cash balance trend | Monthly collections
│     Data: Cash Flow Bridge
│
└── Slide 14: Deferred Revenue & Billings
      Layout: TYPE C — Deferred rev bridge chart + Collections analysis
      Data: Deferred Revenue Waterfall

SECTION 6: OPERATIONAL (Slides 15–16)
├── Slide 15: Headcount & Productivity
│     Layout: TYPE B — HC bridge waterfall | ARR per employee trend
│     Data: Headcount Plan
│
└── Slide 16: Department Spend
      Layout: TYPE A — Variance heatmap by dept | Key Takeaways
      Data: GL Detail

SECTION 7: STRATEGY & DECISIONS (Slides 17–20)
├── Slide 17: Risks & Opportunities
│     Layout: 8-card grid (4 risks, 4 opps), 2 columns × 4 rows
│
├── Slide 18: Financial Outlook
│     Layout: TYPE E — Pure narrative, H2 strategy, forecast update
│
├── Slide 19: Key Metrics Dashboard
│     Layout: Full-width metrics grid — current, budget, prior year, FY forecast
│     This is the "one-pager" all data in one place
│
└── Slide 20: Board Approvals & Next Steps
      Layout: TYPE G — 4–6 numbered action cards with owner and due date
```

---

## SECTION 3 — COMMENTARY ENGINE

### 3.1 Commentary Quality Standard

**The test:** Would a seasoned SaaS CFO be comfortable reading this verbatim in a board meeting?

```
BAD COMMENTARY (never do this):
"Revenue increased by $0.08M compared to budget."

GOOD COMMENTARY (always do this):
"Subscription revenue outperformed budget in all five periods — ARR momentum
is translating into GAAP revenue ahead of plan while gross margin held at 77.0%,
demonstrating COGS discipline as the subscription base scales."
```

**Commentary must:**
1. Lead with the key insight, not the metric
2. Explain the operational driver (WHY, not just WHAT)
3. Quantify specifically (never "significant" — always "$X.XM" or "X%")
4. Flag forward-looking implications (risks or opportunities)
5. End with an action or recommendation where applicable

### 3.2 Commentary Template by Category

#### ARR Waterfall Commentary
```python
ARR_COMMENTARY_TEMPLATE = """
{month} ARR of {ending_arr} {exceeded|trailed} the {budget_arr} budget by {variance}.
{new_biz_narrative} {expansion_narrative} {churn_narrative}
{forward_looking}: {implication}. {action_if_any}.
"""

# Example outputs:
"""
May ARR of $83.45M exceeded the $83.33M budget by $0.12M.
New business of $1.80M outperformed the $1.73M plan on improved enterprise
close rates in the West region. Expansion ARR of $0.91M beat the $0.85M budget —
Customer Success penetration of mid-market accounts is driving seat expansion.
Churn at $0.49M remained within the $0.50M budget ceiling, though SMB cohort
concentration (78% of gross churn) represents a material H2 risk if the Q3
renewal cycle underperforms. Recommend activating targeted SMB retention
intervention before August.
"""
```

#### Revenue Commentary
```python
REVENUE_COMMENTARY_TEMPLATE = """
{month} GAAP revenue of {actual_rev} {exceeded|trailed} the {budget_rev} budget
by {variance} ({variance_pct}). {driver_explanation}. Gross margin {held at|
improved to|declined to} {gm_pct} {vs_budget_note}. {ebitda_note}. {forward_note}.
"""
```

#### Cash Commentary
```python
CASH_COMMENTARY_TEMPLATE = """
Ending cash of {ending_cash} {exceeded|trailed} the {budget_cash} budget by
{variance}. {primary_driver}. {secondary_driver}. {h2_outlook}. {action}.
"""
```

#### GTM Commentary
```python
GTM_COMMENTARY_TEMPLATE = """
{top_channel} continues to deliver the highest pipeline efficiency at {top_eff}x
pipeline per $1 of spend, with a {top_wr}% closed-won rate — while receiving only
{top_pct_budget}% of total GTM budget. In contrast, {bottom_channels} absorb
{bottom_pct_budget}% of budget at {bottom_eff}x efficiency and {bottom_wr}% win
rate. {reallocation_opportunity}. {recommended_action}.
"""
```

### 3.3 Commentary Generation Rules

```python
# Rule 1: Variance thresholds for commentary emphasis
HIGHLIGHT_THRESHOLD = 0.05   # 5% variance → mention in commentary
MATERIAL_THRESHOLD  = 0.10   # 10% variance → lead with this in commentary
CRITICAL_THRESHOLD  = 0.20   # 20% variance → board-level flag

# Rule 2: Always contextualize against trend
# Don't just say "May was $X". Say "May was $X, the 3rd consecutive month of..."

# Rule 3: Always state the root cause
ROOT_CAUSES = {
    'arr_outperformance': ['enterprise close rate', 'deal size expansion',
                           'renewal timing', 'CS-led expansion'],
    'churn_risk':         ['SMB segment pressure', 'product gaps', 'pricing',
                           'competitive displacement', 'renewal timing'],
    'cash_variance':      ['billing timing', 'annual contract concentration',
                           'collections velocity', 'vendor payment timing'],
    'gtm_inefficiency':   ['channel mix', 'lead quality', 'cycle time',
                           'AE productivity', 'win rate deterioration'],
    'margin_compression': ['COGS scaling', 'infrastructure costs',
                           'hosting/compute', 'professional services mix'],
}

# Rule 4: Include forward-looking language
FORWARD_PHRASES = [
    "Heading into H2...",
    "This creates a [risk/opportunity] for...",
    "If this trajectory holds...",
    "The Q3 [renewal cycle/pipeline] will be the key test...",
    "We expect this to [continue/normalize/reverse] because...",
]
```

---

## SECTION 4 — EXCEL MD&A WORKBOOK SPECIFICATION

### 4.1 Workbook Architecture

```
REQUIRED TABS (in order):
01. Executive Summary      — KPIs, metrics table, written MD&A narrative
02. ARR Waterfall          — Monthly bridge with act/bud/var columns + embedded chart
03. ARR Waterfall Detail   — FY forecast vs budget component bridge
04. Income Statement       — Full P&L with act/bud/var across all 12 months
05. Cash Forecast          — Cash bridge monthly with act/bud/var
06. Cash Flow Statement    — GAAP indirect method, act vs budget
07. Deferred Revenue       — Billings, recognition, deferred balance waterfall
08. GTM Review             — Channel performance table + efficiency metrics
09. Pipeline Health        — Pipeline waterfall act/bud/var monthly
10. Funnel Conversion      — MQL → SQL → SAL → Opp → Won conversion
11. Headcount              — HC bridge by department + productivity metrics
12. Department Spend       — GL variance by department and account group
13. Variance Commentary    — Written commentary for all material variances
14. Risks & Opportunities  — Structured risk/opp matrix
15. Assumptions & Legend   — Color coding, data sources, period logic
16. Appendix — Opp Detail  — Top opportunities from CRM data
```

### 4.2 Column Structure — All Financial Tabs

**The new layout (established and working — maintain exactly):**
```
COLUMN GROUPS (left to right):
A:        Row label
B–G:      ACTUALS — one column per actual closed month (Jan, Feb, Mar, Apr, May, Jun*)
H:        [Jun placeholder if not closed — yellow background, user input]
I–N:      FORECAST — Jul through Dec
O:        Q1 Actual subtotal
P:        Q2 Actual subtotal (Apr + May + Jun when closed)
Q:        H1 Actual subtotal
R:        FY Act + Forecast (Jan-May actual + Jun-Dec forecast)
S:        Q1 Budget
T:        Q2 Budget
U:        H1 Budget
V:        FY Budget
W:        Q1 Variance $
X:        Q2 Variance $
Y:        H1 Variance $
Z:        FY Variance $
AA:       Q1 Variance %
AB:       Q2 Variance %
AC:       H1 Variance %
AD:       FY Variance %
```

**Group header colors:**
```python
COLUMN_GROUP_COLORS = {
    'actuals':          ('1B4F72', 'EFF6FF'),  # Blue header, light blue bg
    'june_placeholder': ('92400E', 'FFF9C4'),  # Amber header, yellow bg
    'forecast':         ('92400E', 'FFFBEB'),  # Amber header, light amber bg
    'actual_subtotals': ('1B4F72', 'DBEAFE'),  # Blue header, blue tint bg
    'budget_subtotals': ('0F6E56', 'DCFCE7'),  # Green header, green tint bg
    'variance_dollar':  ('374151', 'F1F5F9'),  # Gray header, light bg
    'variance_pct':     ('374151', 'F1F5F9'),  # Gray header, light bg
}
```

### 4.3 Row Formatting Rules

```python
# Section dividers
SECTION_DIVIDER = {
    'background': TEAL_COLOR,
    'font_color': WHITE,
    'font_size': 9,
    'height': 16,
    'text': '  SECTION NAME (ALL CAPS)',
    'merge_all_columns': True,
}

# Subtotal rows (e.g., Gross Profit, Total OpEx, EBITDA)
SUBTOTAL_ROW = {
    'background': 'EEF9F7',
    'font_bold': True,
    'border_top': 'medium',
}

# Data rows
DATA_ROW_ODD  = {'background': 'F8FAFC'}  # Off-white
DATA_ROW_EVEN = {'background': 'FFFFFF'}  # White

# Input cells (hardcoded source data)
INPUT_CELL_COLOR = '0000FF'  # Blue text — industry convention

# Formula cells
FORMULA_CELL_COLOR = '1E293B'  # Dark text — computed

# Variance coloring
POSITIVE_VARIANCE_COLOR = '16A34A'  # Green — favorable
NEGATIVE_VARIANCE_COLOR = 'C0392B'  # Red — unfavorable
NEUTRAL_COLOR           = '64748B'  # Gray — no variance
```

### 4.4 Number Formatting

```python
NUMBER_FORMATS = {
    'dollar_millions':    '$#,##0.0;($#,##0.0);"-"',      # $12.3M style
    'dollar_millions_2':  '$#,##0.00;($#,##0.00);"-"',    # $12.34M style
    'dollar_thousands':   '$#,##0;($#,##0);"-"',           # $12,345 style
    'variance_dollar':    '+$#,##0.0;($#,##0.0);"-"',     # +$1.2M / ($1.2M)
    'variance_pct':       '+0.0%;(0.0%);"-"',              # +5.2% / (5.2%)
    'percentage':         '0.0%;(0.0%);"-"',               # 77.0%
    'percentage_2':       '0.00%;(0.00%);"-"',             # 77.00%
    'headcount':          '#,##0',                          # 142
    'multiplier':         '0.0x',                           # 3.3x
    'bps':               '+0"bps";-0"bps";"-"',            # +20bps
}
```

### 4.5 Commentary Section Structure (ALL financial tabs)

Every financial tab (ARR Waterfall, Income Statement, Cash Forecast, Cash Flow Statement) must include a Commentary section below the data. Structure:

```
[5px spacer row]
[SECTION HEADER: "EXECUTIVE COMMENTARY & VARIANCE ANALYSIS" — Forest green]
[Column headers row — navy background]:
  Period/Topic | Category | Variance Driver | Narrative & Analysis | Impact | Action Required

[Data rows — alternating offwhite/white]:
  Each row = one commentary item
  Row height = 52px (wrapping text)
  Column widths: 14 | 16 | 20 | 65 | 16 | 30
```

**Minimum commentary rows per tab:**
```
ARR Waterfall:      5 rows (New Biz, Expansion, Churn, NRR, FY Forecast)
Income Statement:   5 rows (Revenue, Gross Margin, S&M, EBITDA, Leverage)
Cash Forecast:      5 rows (Collections, Floor coverage, Payroll, H2 outlook, Opportunity)
Cash Flow Stmt:     5 rows (CFO, Deferred Rev, CFI, CFF, Net Change)
GTM Review:         1 row per channel + 1 summary row
Pipeline Health:    3 rows (Pipeline created, Coverage, Conversion)
```

### 4.6 Embedded Charts in Excel

**ARR Waterfall tab** — embed a clustered bar chart:
```python
# Chart: Monthly Net New ARR — Actual vs Budget
chart = BarChart()
chart.type = 'col'
chart.grouping = 'clustered'
chart.title = 'Net New ARR — Actual vs Budget'
chart.series[0].graphicalProperties.solidFill = '0D9488'  # Teal = actual
chart.series[1].graphicalProperties.solidFill = 'D1D5DB'  # Gray = budget
chart.width = 20; chart.height = 12
# Place: anchor at column F, 2 rows below last data row
```

**Income Statement tab** — embed revenue + gross profit combo:
```python
# Bar chart for gross profit, line chart overlay for revenue
# Gross profit bars: light green (#D1FAE5)
# Revenue actual line: teal (#0D9488)
# Revenue budget line: light gray (#9CA3AF)
```

**Cash Forecast tab** — embed line chart:
```python
# Two-line chart: Actual cash balance vs Budget cash balance
# Actual: teal (#0D9488), lineWidth=2.5
# Budget: gray (#D1D5DB), lineWidth=1.5
```

---

## SECTION 5 — EXECUTION INSTRUCTIONS FOR CURSOR

### 5.1 File Structure to Create

```
/project
├── /data                          ← Drop CSVs here every month-end
│   ├── Actual_MRR_Waterfall.csv
│   ├── Forecast_mrr_waterfall.csv
│   ├── Budget_MRR_Waterfall.csv
│   ├── Actual_income_statement.csv
│   ├── Forecast_income_statement.csv
│   ├── Budget_income_statement.csv
│   ├── Actual_cash_flow_bridge.csv
│   ├── Forecast_cash_flow_bridge.csv
│   ├── Budget_cash_flow_bridge.csv
│   ├── Actual_marketing_pipeline.csv
│   ├── Forecast_marketing_pipeline.csv
│   ├── Budget_marketing_pipeline.csv
│   ├── Actual_pipeline_waterfall.csv
│   ├── headcount_plan.csv
│   └── gl_detail.csv
│
├── /templates                     ← Reference files (do not modify)
│   ├── ClarityFP_Board_Review_May2026_v5.pptx   (layout reference)
│   └── ClarityFP_MDA_Package_May2026_v4.xlsx    (structure reference)
│
├── /output                        ← Generated files land here
│   ├── Board_Review_{YYYYMM}.pptx
│   ├── Board_Review_{YYYYMM}.pdf
│   └── MDA_Package_{YYYYMM}.xlsx
│
├── /src
│   ├── data_loader.py             ← CSV ingestion + validation
│   ├── analytics.py               ← All calculations + variances
│   ├── commentary.py              ← AI commentary generation
│   ├── build_pptx.py              ← PowerPoint generator
│   ├── build_excel.py             ← Excel workbook generator
│   └── main.py                    ← Orchestrator: run everything
│
└── config.yaml                    ← Reporting period, company info, thresholds
```

### 5.2 config.yaml Structure

```yaml
company:
  name: "SMPL"
  tagline: "We make finance simple"
  fiscal_year_start: "01"  # January
  currency: "USD"
  scale: "millions"        # Display scale

reporting:
  period: "2026-05"        # CHANGE THIS EACH MONTH
  actuals_through: "2026-05"
  company_arr_floor: 10000000  # $10M cash floor

thresholds:
  material_variance_pct: 0.05    # 5% = highlight in commentary
  critical_variance_pct: 0.10    # 10% = board-level flag

ai_commentary:
  model: "claude-sonnet-4-20250514"  # or openai model
  enabled: true
  tone: "CFO"  # Options: CFO, analytical, brief

board_deck:
  slide_count: 20
  include_appendix: true
  appendix_starts_at_slide: 18

excel:
  tab_count: 16
  embed_charts: true
  commentary_rows_per_tab: 5
```

### 5.3 Python Implementation Patterns

#### Data Loader Pattern
```python
# data_loader.py
import pandas as pd
import yaml
from pathlib import Path

class DataLoader:
    def __init__(self, data_dir: str, config: dict):
        self.data_dir = Path(data_dir)
        self.config = config
        self.period = config['reporting']['period']

    def load_arr(self) -> dict:
        """Load and merge actual + forecast + budget ARR data."""
        actual   = pd.read_csv(self.data_dir / 'Actual_MRR_Waterfall.csv')
        forecast = pd.read_csv(self.data_dir / 'Forecast_mrr_waterfall.csv')
        budget   = pd.read_csv(self.data_dir / 'Budget_MRR_Waterfall.csv')

        # Tag each source
        actual['version']   = 'Actual'
        forecast['version'] = 'Forecast'
        budget['version']   = 'Budget'

        # Filter actuals to closed periods only
        actual = actual[actual['period'] <= self.period]

        return {'actual': actual, 'forecast': forecast, 'budget': budget}

    def load_all(self) -> dict:
        """Load all data sources. Called once at startup."""
        return {
            'arr':      self.load_arr(),
            'income':   self.load_income_statement(),
            'cash':     self.load_cash_flow(),
            'gtm':      self.load_marketing_pipeline(),
            'pipeline': self.load_pipeline_waterfall(),
            'headcount':self.load_headcount(),
            'gl':       self.load_gl_detail(),
        }
```

#### Analytics Pattern
```python
# analytics.py
class Metrics:
    def __init__(self, data: dict, config: dict):
        self.data = data
        self.config = config

    def arr_summary(self) -> dict:
        """Compute all ARR metrics for the reporting period."""
        act = self.data['arr']['actual']
        bud = self.data['arr']['budget']

        latest_period = act['period'].max()
        latest_act = act[act['period'] == latest_period].iloc[0]
        latest_bud = bud[bud['period'] == latest_period].iloc[0]

        # YTD aggregation
        ytd_act = act.groupby('period').sum()  # sum monthly movements
        ytd_bud = bud[bud['period'] <= latest_period]

        return {
            'ending_arr':     latest_act['ending_arr'],
            'ending_arr_bud': latest_bud['ending_arr'],
            'arr_var':        latest_act['ending_arr'] - latest_bud['ending_arr'],
            'arr_var_pct':    (latest_act['ending_arr'] - latest_bud['ending_arr'])
                              / latest_bud['ending_arr'],
            'net_new_arr':    latest_act['net_new_arr'],
            'net_new_bud':    latest_bud['net_new_arr'],
            'nrr':            latest_act['net_dollar_retention_rate'],
            'grr':            latest_act['gross_retention_rate'],
            # ... etc
        }

    def gtm_channel_efficiency(self) -> pd.DataFrame:
        """Rank all GTM channels by pipeline efficiency."""
        act = self.data['gtm']['actual']
        bud = self.data['gtm']['budget']

        # Aggregate YTD
        act_ytd = act[act['period'] <= self.config['reporting']['period']]
        act_agg = act_ytd.groupby('marketing_channel').agg({
            'marketing_spend': 'sum',
            'mqls': 'sum',
            'sqls': 'sum',
            'pipeline_arr_created': 'sum',
            'closed_won_arr': 'sum',
            'closed_lost_arr': 'sum',
        }).reset_index()

        act_agg['efficiency'] = (act_agg['pipeline_arr_created']
                                  / act_agg['marketing_spend'].clip(lower=1))
        act_agg['win_rate']   = (act_agg['closed_won_arr']
                                  / (act_agg['closed_won_arr']
                                   + act_agg['closed_lost_arr']).clip(lower=1))

        return act_agg.sort_values('efficiency', ascending=False)
```

#### Commentary Generation Pattern
```python
# commentary.py
import anthropic

class CommentaryEngine:
    def __init__(self, config: dict):
        self.client = anthropic.Anthropic()
        self.config = config

    def generate(self, slide_name: str, metrics: dict) -> str:
        """
        Generate CFO-quality commentary for any slide/section.
        Always provide specific numbers in the context.
        """
        context = self._build_context(slide_name, metrics)
        prompt = f"""You are the CFO preparing a board presentation.
Write 2-3 sentences of executive commentary for the {slide_name} section.

Rules:
- Lead with the key insight, not the metric
- Quantify specifically — always use exact dollar amounts and percentages
- Explain the operational driver (WHY something happened)
- Include one forward-looking implication
- Sound like a seasoned CFO, not a report generator
- Do NOT start with "The data shows" or "Revenue increased"

Financial context:
{context}

Write ONLY the commentary. No labels, no bullets."""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def _build_context(self, slide_name: str, metrics: dict) -> str:
        """Convert metrics dict to readable context string."""
        lines = []
        for key, val in metrics.items():
            if isinstance(val, float):
                lines.append(f"{key}: {val:,.2f}")
            else:
                lines.append(f"{key}: {val}")
        return "\n".join(lines)
```

#### PowerPoint Builder Pattern
```python
# build_pptx.py
from pptxgen import Presentation  # or use python-pptx

class BoardDeckBuilder:
    """
    Builds the 20-slide board deck.
    Each slide method is independent and self-contained.
    Layout types are enforced — no slide should have the same
    visual structure as the one before it.
    """

    LAYOUT_SEQUENCE = [
        'cover',      # Slide 1
        'type_f',     # Slide 2: Dashboard
        'type_e',     # Slide 3: MD&A narrative
        'type_c',     # Slide 4: ARR Waterfall
        'type_a',     # Slide 5: Retention
        'type_b',     # Slide 6: ARR by segment
        'type_a',     # Slide 7: Revenue
        'type_c',     # Slide 8: EBITDA
        'type_d',     # Slide 9: GTM channels
        'type_b',     # Slide 10: Pipeline
        'type_c',     # Slide 11: Funnel
        'type_d',     # Slide 12: Pipeline detail
        'type_b',     # Slide 13: Cash
        'type_c',     # Slide 14: Deferred revenue
        'type_b',     # Slide 15: Headcount
        'type_a',     # Slide 16: Department spend
        'risk_grid',  # Slide 17: Risks & Opps
        'type_e',     # Slide 18: Outlook
        'metrics',    # Slide 19: Full metrics
        'type_g',     # Slide 20: Board actions
    ]

    def slide_header(self, slide, section: str, title: str, subtitle: str = None):
        """Standard header — called on every content slide."""
        # Navy bar: x=0, y=0, w=10, h=0.055
        # Section label: 8pt Teal bold, charSpacing 2.5
        # Title: 28pt Navy bold
        # Subtitle: 10pt Gray (if provided)
        pass

    def slide_footer(self, slide, page_num: int):
        """Standard footer — called on every content slide."""
        # Rule at y=5.44
        # Company/CONFIDENTIAL text left
        # Page number right
        pass

    def chart_line(self, slide, x, y, w, h, data: dict, colors: list):
        """Standardized line chart with our palette and axis rules."""
        pass

    def chart_bar(self, slide, x, y, w, h, data: dict, colors: list,
                  show_values=True, grouped=True):
        """Standardized bar chart."""
        pass

    def key_takeaways(self, slide, x, y, w, h, bullets: list):
        """Standard Key Takeaways panel."""
        # OffWhite background, LGray border
        # "Key Takeaways" label in Navy bold
        # Divider line
        # Bullets with teal dots, DkGray text
        pass
```

---

## SECTION 6 — SLIDE-BY-SLIDE CONTENT RULES

### Slide 1: Cover
- Left panel (40%): Navy background. SMPL in Teal. Tagline optional: "We make finance simple". Title "Board Operating Review". Month year. Prepared for line.
- Right panel (60%): White. 5 KPIs stacked vertically with separator lines. Each KPI: label (9pt Gray) + value (26pt Navy bold) + delta (9pt Teal/Green).
- NO footer on cover slide.

### Slide 2: Executive Dashboard
- Show ARR trend chart (actual vs budget) for the period — this is the primary visual
- Compact metrics table below the chart: This Period / Budget / Var $ / Last Period / Var %
- Key Takeaways column: 5 bullets max. Each references a specific number.
- The chart should take ~60% of slide height and ~65% of slide width.

### Slide 3: MD&A Narrative
- Pure text slide. No chart. No table. Just 4 narrative paragraphs.
- Structure: ARR & ARR drivers | Revenue & Margin | Cash & Liquidity | Outlook & Decisions
- Each paragraph: 3–4 sentences. Bold the opening phrase.
- Left margin: 0.65". Content line width: 8.5". Generous leading (1.4x).

### Slide 4: ARR Waterfall
- PRIMARY VISUAL: Grouped bar chart (net new ARR monthly, actual vs budget). Teal vs light gray. Show values.
- RIGHT COLUMN: FY bridge table (BOP → components → EOP) with Forecast/Budget/Var columns.
- BELOW TABLE: 2 key takeaway bullets.
- Caption below chart: "Net New ARR ($M) · Actual vs Budget · [Period]"

### Slide 5: ARR Retention
- PRIMARY VISUAL: NRR monthly trend line chart. Show 12 months where possible (actuals + forecast).
- Include GRR as second line.
- RIGHT: Key Takeaways. 4 bullets. Include SMB vs enterprise commentary if segment data available.

### Slide 9: GTM Channel Efficiency
- Full-width table. Sorted by pipeline efficiency (high to low).
- Columns: Channel | Act Spend | Bud Spend | Spend Var | Act Pipeline | Eff (x) | Win Rate | Commentary
- Color-code Eff column: Green ≥5x, Amber 2–5x, Red <2x
- Color-code Win Rate: Green ≥30%, Amber 10–30%, Red <10%
- Two sentences below: "Key finding:" and "Board action:" in formatted text.

### Slide 13: Cash Forecast
- TWO CHARTS side by side:
  - LEFT: Cash balance trend (actual vs budget line chart)
  - RIGHT: Monthly collections bar chart
- Captions below each chart (italic gray)
- 2 bullet points below each chart — total 4 bullets
- NO table. NO driver boxes. Just the two charts and 4 bullets.

### Slide 18: Financial Outlook
- PURE TEXT. No chart. No table.
- 4 sections separated by horizontal rules:
  1. ARR Forecast update (with specific $ figure)
  2. GTM decision (specific reallocation proposal)
  3. Retention action (specific intervention)
  4. Cash / contract strategy
- Each section: bold title + 2–3 sentences. Left color bar accent.

### Slide 20: Board Approvals
- 4–6 action cards
- Each card: numbered badge + status pill (FOR APPROVAL / FOR DISCUSSION) + title + description + owner + due date
- Status pill: blue for approval, amber for discussion
- Description: 2 sentences max. Specific and actionable.

---

## SECTION 7 — QUALITY CHECKLIST

Run this checklist before delivering any output:

### PowerPoint Checklist
- [ ] No two consecutive slides have the same layout type
- [ ] Every chart has an italic gray caption below it
- [ ] Every slide (except cover) has the standard header and footer
- [ ] No slide has more than 5 bullet points in any takeaway column
- [ ] No text is smaller than 8pt
- [ ] Every variance is color-coded (green favorable, red unfavorable)
- [ ] All dollar values use $XM or $XK format (never raw numbers like 83450000)
- [ ] All percentage variances show one decimal place (e.g., +0.1%, not +0.12348%)
- [ ] Slide 3 is text-only (no chart)
- [ ] Slide 18 is text-only (no chart)
- [ ] The two text-only slides have generous whitespace and large type
- [ ] Page numbers are correct on all slides
- [ ] Charts use teal (#0d9488) for actual and gray (#d1d5db) for budget

### Excel Checklist
- [ ] All financial tabs have the 4-group column structure (Actuals | Forecast | Actual Subtotals | Budget Subtotals | Variance)
- [ ] June placeholder column is yellow background
- [ ] Input cells (hardcoded data) have blue text
- [ ] All financial tabs have commentary sections at the bottom
- [ ] Each commentary row has: Period | Category | Driver | Narrative | Impact | Action
- [ ] ARR Waterfall tab has an embedded bar chart
- [ ] Income Statement tab has an embedded combo chart
- [ ] Cash Forecast tab has an embedded line chart
- [ ] Variance colors: green for favorable, red for unfavorable (accounting for line type)
- [ ] All tabs have freeze panes at B4 (first data column, first data row)
- [ ] Column widths are set explicitly (never auto-fit)
- [ ] Sheet is set to showGridLines=False on all tabs

### Commentary Checklist
- [ ] No commentary starts with "The data shows" or generic phrasing
- [ ] Every commentary mentions specific dollar amounts and percentages
- [ ] Every commentary includes a forward-looking statement or recommendation
- [ ] Variances above 10% are flagged explicitly in commentary
- [ ] Commentary explains WHY, not just WHAT

---

## SECTION 8 — MONTHLY RUN INSTRUCTIONS

Each month-end, the process is:

```bash
# 1. Drop new CSV files into /data/ folder

# 2. Update config.yaml
reporting:
  period: "2026-06"           # ← Change this to new month
  actuals_through: "2026-06"  # ← Change this to new month

# 3. Run the generator
python src/main.py

# 4. Outputs appear in /output/:
#    Board_Review_202606.pptx
#    Board_Review_202606.pdf
#    MDA_Package_202606.xlsx

# 5. Review commentary for AI-generated sections
#    (All commentary blocks are labeled with their source)

# 6. Distribute
```

**What updates automatically:**
- All charts update to include the new month's data
- All variance calculations update
- All commentary regenerates for any metric with >5% variance
- Page numbers stay correct
- The "actuals" column block grows by one column each month

**What to review manually each month:**
- AI commentary for accuracy and tone
- Any new material variance (>10%) that needs CFO attention before distribution
- Risks & Opportunities slide — update manually for new strategic items
- Board Approvals slide — update status of prior-month items

---

## APPENDIX A — REFERENCE VALUES

### Palette (copy-paste ready)
```
Navy:    #1a2e44  /  rgb(26,46,68)
Teal:    #0d9488  /  rgb(13,148,136)
Green:   #15803d  /  rgb(21,128,61)
Red:     #dc2626  /  rgb(220,38,38)
Amber:   #d97706  /  rgb(217,119,6)
Gray:    #64748b  /  rgb(100,116,139)
DkGray:  #334155  /  rgb(51,65,85)
LGray:   #e2e8f0  /  rgb(226,232,240)
White:   #ffffff  /  rgb(255,255,255)
OffWht:  #f8fafc  /  rgb(248,250,252)
DkText:  #0f172a  /  rgb(15,23,42)
Forest:  #0D3D2A  (for Excel section headers)
```

### pptxgenjs Chart Format (proven working)
```javascript
// Simple line chart
slide.addChart(pres.charts.LINE, [
  {name: 'Actual', labels: months, values: actValues},
  {name: 'Budget', labels: months, values: budValues},
], {
  x: 0.45, y: 1.28, w: 5.8, h: 2.65,
  lineSize: 2.5,
  chartColors: ['0d9488', 'd1d5db'],
  catAxisLabelColor: '64748b',
  valAxisLabelColor: '64748b',
  catAxisLabelFontSize: 10,
  valAxisLabelFontSize: 10,
  valGridLine: {color: 'e2e8f0', size: 0.5},
  catGridLine: {style: 'none'},
  showLegend: true,
  legendPos: 'b',
  legendFontSize: 9,
  chartArea: {fill: {color: 'ffffff'}},
});

// Combo chart (bars + lines) — IMPORTANT: wrap in array, NO lineDash
slide.addChart(
  [{type: pres.charts.BAR,
    data: [{name: 'Gross Profit', labels: months, values: gpValues}],
    options: {chartColors: ['d1fae5']}},
   {type: pres.charts.LINE,
    data: [{name: 'Revenue Act', labels: months, values: revActValues},
           {name: 'Revenue Bud', labels: months, values: revBudValues}],
    options: {lineSize: 2.5, chartColors: ['0d9488', '9ca3af']}}],
  {x: 0.45, y: 1.28, w: 6.4, h: 3.55,   // ← options object (NOT array)
   catAxisLabelColor: '64748b',
   valAxisLabelColor: '64748b',
   catAxisLabelFontSize: 10,
   valAxisLabelFontSize: 10,
   valGridLine: {color: 'e2e8f0', size: 0.5},
   catGridLine: {style: 'none'},
   showLegend: true,
   legendPos: 'b',
   legendFontSize: 9,
   chartArea: {fill: {color: 'ffffff'}}}
);
// ⚠️ CRITICAL: In combo charts, all colors in options.chartColors MUST be
// hex strings (e.g., '0d9488'), never JavaScript variable references.
// ⚠️ CRITICAL: The third argument to addChart() for combo charts must be
// a plain object {}, NOT an array [{}].
```

### openpyxl Chart Format (proven working)
```python
from openpyxl.chart import BarChart, LineChart, Reference

chart = BarChart()
chart.type = 'col'
chart.grouping = 'clustered'
chart.title = 'Net New ARR — Actual vs Budget'
chart.y_axis.title = 'ARR ($M)'
chart.legend = None
chart.width = 20
chart.height = 12
chart.style = 2

# Data reference
data = Reference(ws, min_col=2, max_col=3,
                 min_row=header_row, max_row=last_data_row)
cats = Reference(ws, min_col=1,
                 min_row=header_row+1, max_row=last_data_row)
chart.add_data(data, titles_from_data=True)
chart.set_categories(cats)

# Apply colors
chart.series[0].graphicalProperties.solidFill = '0D9488'  # Teal
chart.series[0].graphicalProperties.line.solidFill = '0D9488'
chart.series[1].graphicalProperties.solidFill = 'D1D5DB'  # Gray
chart.series[1].graphicalProperties.line.solidFill = 'D1D5DB'

# Anchor: place chart starting at col F, 2 rows after last data row
ws.add_chart(chart, f'F{last_data_row + 2}')
```

---

*This prompt was derived from a complete end-to-end SaaS CFO board reporting build, including 47 historical board slide references, real CSV data from a B2B SaaS platform, and iterative refinement of both PowerPoint and Excel outputs. The patterns, palette, layout rules, and code snippets are all proven working.*

*Last updated: May 2026*
