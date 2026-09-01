# Reporting Logic

> Definitions, calculations, tie-out rules, and export behavior for all customer-facing reports.

## Principles

1. **One logic path** — Dashboards and Excel/PPTX exports call the same backend services.
2. **Waterfalls win** — When metrics conflict, canonical waterfalls override summary KPIs or statement lines.
3. **Explicit scenarios** — Actual, Budget, Forecast, and Combined are never silently blended except in Combined mode per cutover rules.
4. **Validation is part of the report** — Every close package includes a Validation tab fed by `ValidationCheck` records.

---

## Source-of-truth matrix

| Business question | Source of truth | Must tie to |
|-------------------|-----------------|-------------|
| How did ARR change? | **MRR/ARR waterfall** | Pipeline `closed_won` (new business), opportunity drilldown |
| How did pipeline change? | **Pipeline waterfall** | Opportunity movements by `waterfall_type` |
| Billings vs recognized revenue? | **Deferred revenue waterfall** | P&L revenue (GAAP), invoice timing |
| How much cash will we have? | **Cash flow bridge** | Balance sheet cash, cash flow statement |
| What is GAAP revenue next quarter? | Revenue schedule + deferred waterfall | Not MRR alone |
| Marketing efficiency? | Marketing mart (`actual_budget_forecast`) | Pipeline creation movements (optional) |

---

## Scenario: Combined

Used for executive and board views spanning closed and open months.

```
For each period P in [start_period, end_period]:
  if P <= as_of_period and Actual exists for P:
    use Actual
  else if Forecast exists for P:
    use Forecast
  else:
    use Budget (fallback)
```

Close month (`P = as_of_period`) may show **Actual + Budget + Forecast** columns side by side in Excel (see period column layout in export layer).

---

## Report catalog

### Executive & KPI

| Report | API / service | Primary inputs |
|--------|---------------|----------------|
| Executive Flow Dashboard | `GET /api/v1/dashboard/executive-flow` | All waterfalls + KPIs + validation |
| KPI scorecard | Embedded in executive flow / export | Derived from waterfalls + statements |

### Waterfalls

| Report | Endpoint | `waterfall_type` examples |
|--------|----------|---------------------------|
| MRR / ARR | `/api/v1/waterfalls/arr` | `beginning_arr`, `new_arr`, `expansion`, `contraction`, `churn`, `ending_arr` |
| Pipeline | `/api/v1/waterfalls/pipeline` | `new`, `progression`, `closed_won`, `closed_lost`, `slipped` |
| Deferred revenue | `/api/v1/waterfalls/deferred-revenue` | `beginning_balance`, `billings`, `recognized`, `ending_balance` |
| Cash flow bridge | `/api/v1/waterfalls/cash-flow` | Operating adjustments, `ending_cash` |

Attribution drilldown: `/api/v1/waterfalls/{type}/attribution` and opportunity drilldown per movement.

### Financial statements

| Report | Endpoint |
|--------|----------|
| Income statement (P&L) | `/api/v1/financial-statements/income-statement` |
| Balance sheet | `/api/v1/financial-statements/balance-sheet` |
| Cash flow statement | `/api/v1/financial-statements/cash-flow` |
| Summary + validation | `/api/v1/financial-statements/summary`, `/validation` |

### RevOps & marketing

| Report | Endpoint |
|--------|----------|
| Opportunity stage summary | `/api/v1/opportunities/stage-summary` |
| Closed by month | `/api/v1/opportunities/closed-by-month` |
| Remaining pipeline | `/api/v1/opportunities/remaining-pipeline` |
| Marketing performance | `/api/v1/marketing/*` |

### Forecasting

| Report | Endpoint / service |
|--------|-------------------|
| GAAP revenue forecast | `gaap_revenue_forecast_service` |
| Driver-based forecast | `/api/v1/forecast/*`, `forecast_driver_assumptions` |

### Commentary & export

| Output | Endpoint |
|--------|----------|
| Validation pre-check | `/api/v1/export/validation` |
| Month-end close Excel | `/api/v1/export/month-end-close.xlsx` |
| Management review Excel | `/api/v1/export/management-review.xlsx` |
| Variance commentary Excel | `/api/v1/export/variance-commentary.xlsx` |
| Board PowerPoint | `/api/v1/export/board-presentation.pptx` |

Implementation detail: [../backend/docs/REPORTING_EXPORT.md](../backend/docs/REPORTING_EXPORT.md).

---

## MRR / ARR waterfall logic

### Roll-forward

```
ending_arr(P) = beginning_arr(P)
              + new_arr(P)
              + expansion(P)
              - contraction(P)
              - churn(P)
              + reactivation(P)   # if modeled
```

MRR is ARR ÷ 12 (unless org policy uses ACV-based ARR — document in tenant settings).

### New business tie to pipeline

```
pipeline.closed_won(P) ≈ mrr_waterfall.new_arr(P)
```

Tolerance: default **$1.00** (`validation_service.compare_values`). Status `fail` if outside tolerance.

### Cross-system tie-out patterns (CRM ↔ billing ↔ ERP)

When a customer runs a **billing sub-ledger** (Maxio, Stripe Billing, Chargebee) plus CRM and ERP:

| Layer | Role in SMPL | Tie-out |
|-------|--------------|---------|
| **CRM** | Pipeline waterfall, opportunity drilldown, **forecast** bookings | `closed_won` ↔ MRR `new_arr` (bookings date policy must match tenant) |
| **Billing sub-ledger** | Subscription MRR/ARR, contract metadata, rev-rec schedules | Billing-export new/churn/expansion ↔ MRR waterfall; deferred billings ↔ deferred waterfall |
| **ERP / GL** | Audited P&L, balance sheet, cash, deferred balance | GL revenue ↔ deferred `recognized`; GL deferred ↔ waterfall ending |

**Maxio-shaped stack (common mid-market SaaS):** CRM feeds contracts into Maxio; Maxio posts rev-rec to NetSuite/QBO/Rillet/Intacct. SMPL reads all three — CRM for pipeline/forecast, Maxio (or export) for **actual** ARR/rev-rec, ERP for GL. Do not treat CRM closed-won as SoT for *actual* new ARR when Maxio is the billing system of record; reconcile both and fail on `$1` gaps. See [product/SMPL_Agent_and_Predictive_Analytics_Checklist.md](./product/SMPL_Agent_and_Predictive_Analytics_Checklist.md) §3.

**Stand by the numbers:** prose and AI commentary never override a failed validation check. Export with `block_on_failure=true` returns HTTP 409 until ties pass or exceptions are documented in variance commentary.

**Closed actuals severity labels** (do not call multi-thousand gaps “rounding”):

| |Δ| | Label |
|---|---|
| `≤ $0.01` | `rounding` (cents) |
| `$0.01 < \|Δ\| ≤ $1.00` | `investigate` |
| `> $1.00` | `significant_miss` / `data_mismatch` — product **fail** |

FE↔Board demo seed gaps: [soc2/controls/reconcile_financial_statements.md](./soc2/controls/reconcile_financial_statements.md). Bank timing soft checks (~$1k) are separate from statement tie-out.

**Customer / production GL construction** (RE rolling from `RE_BASE`, opening TB offsets, three-rollup P&L/BS/SCF queries, dept-299 non-cash): [soc2/controls/financial_dashboard_cf_re_logic.md](./soc2/controls/financial_dashboard_cf_re_logic.md). That doc does **not** rewrite demo Board/FE formulas; it is the onboarding and Q&A source for customer builds.

Implemented in export validation: `closed_won_arr_ties_mrr_new_business`.

### Opportunity drilldown

For each pipeline `waterfall_type`, `pipeline_drilldown()` returns opportunities whose movements sum to the waterfall row amount for period `P`.

```
SUM(drilldown.amount WHERE waterfall_type = T) = pipeline.row(T, P)
```

---

## Pipeline waterfall logic

| Movement | Meaning |
|----------|---------|
| `new` | New opportunities created in period |
| `progression` | Stage or amount progression (net) |
| `closed_won` | Won deals — ties to **new_arr** |
| `closed_lost` | Lost deals |
| `slipped` | Close date pushed out |

Opening + movements = closing pipeline (by stage bucket if detailed).

---

## Deferred revenue waterfall logic

```
ending_deferred(P) = beginning_deferred(P)
                   + billings(P)
                   - recognized_revenue(P)
                   +/- adjustments(P)
```

**Source of truth** for:

- Billings forecast
- Revenue recognition forecast
- Change in deferred on **cash flow bridge**

P&L revenue line must reconcile:

```
recognized_revenue(P) ≈ income_statement.revenue(P)
```

---

## Cash flow bridge logic

Typical operating bridge (simplified):

```
ending_cash(P) = beginning_cash(P)
               + net_income(P)
               + non_cash_adjustments(P)      # D&A, SBC, etc.
               + working_capital_changes(P)   # ΔAR, Δdeferred, ΔAP, ...
               + other_operating(P)
```

### Required tie-outs

| Check | Rule |
|-------|------|
| Bridge → balance sheet | `bridge.ending_cash(P) = balance_sheet.cash(P)` |
| Statement → bridge | `cash_flow_statement.net_change_cash(P) = bridge.ending_cash(P) - bridge.beginning_cash(P)` |
| Forecast roll-forward | `forecast.beginning_cash(P+1) = actual.ending_cash(P)` after close |

Cash bridge is the **source of truth for cash forecasting**. Do not forecast cash by applying a growth rate directly to the balance sheet cash line.

---

## Balance sheet logic

```
total_assets(P) = total_liabilities(P) + total_equity(P)
```

Failure on any period blocks `block_on_failure` exports when wired to financial statement validation.

---

## Income statement (P&L) logic

- **Revenue** — Ties to deferred waterfall recognized amount (Actual) or revenue schedule (Forecast).
- **COGS / OpEx** — GL actuals by department (`gl_actuals`) or forecast headcount-driven plan.
- **Variance columns** — `Actual - Budget`, `Actual - Forecast` per period column layout.

### Variance commentary

Auto metrics pulled into Excel **Metric Context**:

- Largest `$` and `%` variances by line
- ARR and pipeline movement highlights
- Cash and deferred drivers

AI narrative (`include_ai_commentary=true`) only elaborates; it does not recalculate.

---

## Marketing performance logic

Reads `marketing.actual_budget_forecast` mart:

| Metric | Typical definition |
|--------|-------------------|
| Spend | Sum marketing expense by channel |
| Pipeline created | CRM opps sourced by channel |
| CPL | Spend / leads |
| CAC | Spend / new customers (define attribution window) |
| ROI | Pipeline ARR created / spend |

Channel drilldown: `/api/v1/marketing/channel-drilldown`.

---

## Excel period column layout

Exports use **months across the top** with scenario-specific columns:

| Period state | Columns |
|--------------|---------|
| Posted actual (Jan–Jun example) | `Actual`, `Budget`, `Var $`, `Var %` |
| Close month (`as_of_period`) | Above + `Forecast`, `Act vs Fc` when forecast exists |
| Future open months | `Budget`, `Forecast` only |

Service: `period_column_layout.py`, `comparison_pivot.py`.

---

## Validation catalog (starter)

Financial statement / closed-actuals identity checks use **`TOLERANCE = $1.00`** fail-closed (`financial_statement_validation_service`, `financial_statement_service`). `|Δ| ≤ $0.01` may be presented as rounding; `|Δ| > $1` is a significant miss — never “rounding.” See [soc2/controls/reconcile_financial_statements.md](./soc2/controls/reconcile_financial_statements.md).

| `validation_name` | Severity | Rule |
|-------------------|----------|------|
| `balance_sheet_balances` | fail | Assets = L + E |
| `cash_bridge_ties_balance_sheet` | fail | Ending cash match |
| `cash_statement_ties_bridge` | fail | Net change consistency |
| `closed_won_arr_ties_mrr_new_business` | fail/warn | Pipeline vs ARR |
| `pipeline_drilldown_ties_waterfall` | fail | Sum opps = movement |
| `deferred_rollforward` | fail | Beginning + billings − recognized = ending |
| `forecast_beginning_from_actual_ending` | warn | Roll-forward after close |
| `arr_waterfall_ties` | pass/fail | Internal waterfall math |
| `export_validation_no_checks` | warning | No data to validate |

Extend this table as new checks are added to `financial_statement_service` and `executive-flow` validation arrays.

---

## Board vs close package contents

### Month-end close (15 tabs)

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
11. Deferred Revenue Waterfall  
12. Headcount & Hiring  
13. GL Detail by Department  
14. Variance Commentary  
15. Validation Checks  

### Board deck (canonical slides)

- Executive summary KPIs  
- ARR / growth narrative  
- Pipeline and bookings  
- GAAP revenue and deferred revenue  
- Cash and runway  
- Validation summary  
- Risks & opportunities  

---

## What this platform does NOT compute

| Capability | Where it lives |
|------------|----------------|
| Journal entries | ERP |
| Revenue recognition policy enforcement | ERP + accounting policy |
| Payroll calculations | Payroll system |
| Invoice generation | Billing system |
| Tax provision | Tax software / ERP |

This platform **reports and reconciles** those outcomes.

---

## Related documents

- [Close_Process.md](./Close_Process.md) — when to run validations and exports  
- [Data_Model.md](./Data_Model.md) — tables behind each report  
- [Forecasting_Assumptions.md](./Forecasting_Assumptions.md) — forward period logic  
- [Architecture_Master.md](./Architecture_Master.md) — service map  
