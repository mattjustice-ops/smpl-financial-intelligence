# SMPL Demo Co — FY24/FY25 Actuals Backcast Spec

> **Status:** Spec only — Matt approves assumptions → Claude generates CSVs → validate → load.  
> **Org:** Demo Co `8571e520-0687-4516-bdee-379f37c58c1f`  
> **Close month:** `2026-06` (June 2026)  
> **CSV pack (SoT):** `C:\Users\mattj\OneDrive\Documents\simple CSVS`  
> **Template headers (SoT):** `backend/templates/csv/` via `scripts/generate-csv-templates.ps1`  
> **Last updated:** 2026-09-01

---

## 1. Purpose

This backcast adds **synthetic but internally consistent** Actual history for **FY24 and FY25** (periods `2024-01` through `2025-12`) by extrapolating backward from the existing **FY26 H1** pack (`2026-01` through `2026-06`). It is **not** a substitute for audited books.

| Consumer | What historical actuals unlock |
|----------|--------------------------------|
| **PPI (Predictive Planning Intelligence)** | Trajectory, forecast accuracy (Phase 4), plan feasibility baselines — needs ≥24 months of Actual ARR, IS, cash, and headcount trends in the same org |
| **Plan / budget module (future)** | Top-down YoY growth and %‑of‑revenue drivers need prior-year Actual anchors |
| **LLM commentary** | Richer “vs prior year / vs trend” narratives from structured warehouse payloads — numbers still come from API, not invented in prose |

**Label everywhere:** synthetic backcast history for demo/PPI development — not for customer-facing audit or board certification claims.

---

## 2. Scope and constraints

### Target period coverage (one consolidated pack)

| Scenario | Period range | Row count (monthly summary files) |
|----------|--------------|-------------------------------------|
| **Actual (extended)** | `2024-01` → `2026-06` | **30 months** per monthly-summary file |
| Budget | unchanged | `2026-01` → `2026-12` |
| Forecast | unchanged | `2026-07` → `2026-12` |

### Loader behavior (non‑negotiable)

`load_versioned_csvs.py` → `_load_physical_version_csv` **deletes all org rows in each table**, then inserts from the CSV. Loading FY24 and FY25 in separate passes **overwrites** prior years.

**Rule:** One flat `simple CSVS` folder; each `Actual_*.csv` must contain **all** historical periods in a single file. Do not split by fiscal year folder (scripts read flat `Actual_*.csv` only).

### FY26 anchors (do not change without re‑baselining)

From current `simple CSVS` pack (June 22, 2026):

| Metric | Value | Source file |
|--------|-------|-------------|
| Jan 2026 beginning ARR | **$75,000,000** | `Actual_MRR_Waterfall.csv` |
| Jun 2026 ending ARR | **$85,308,020.62** | `Actual_MRR_Waterfall.csv` |
| Jan 2026 revenue | **$5,900,000** | `Actual_income_statement.csv` |
| Jun 2026 revenue | **$7,350,000** | `Actual_income_statement.csv` |
| Jun 2026 ending cash (BS) | **$50,257,902.27** | `Actual_balance_sheet.csv` |
| Customers (master count) | **700** | `Actual_dataset_summary.csv` |
| Gross retention (Jun) | **~99.4%** | `Actual_MRR_Waterfall.csv` |
| NDR (Jun) | **~100.2%** | `Actual_MRR_Waterfall.csv` |

**Known FY26 quirk:** Jun 2026 MRR row uses `organization_id = smpl-2026` while other rows use the demo UUID. Backcast rows must use **`8571e520-0687-4516-bdee-379f37c58c1f`** consistently.

---

## 3. Inventory — all `Actual_*.csv` files (45)

Source: `C:\Users\mattj\OneDrive\Documents\simple CSVS` (matches repo template naming).

| File | FY24–FY25 extend? | Grain | Tie-out |
|------|-------------------|-------|---------|
| `Actual_MRR_Waterfall.csv` | **Yes** | Monthly summary (1 row/period) | **$1 bar** — `waterfall_check = 0` |
| `Actual_income_statement.csv` | **Yes** | Monthly summary | **$1 bar** — revenue ↔ MRR implied MRR |
| `Actual_cash_flow_statement.csv` | **Yes** | Monthly summary | **$1 bar** — ending cash ↔ BS; bridge to IS NI |
| `Actual_balance_sheet.csv` | **Yes** | Monthly summary | **$1 bar** — `balance_check = 0` |
| `Actual_cash_flow_bridge.csv` | **Partial** | Monthly summary | **$1 bar** on `bridge_check` (fix Jun 2026 drift in FY26 first) |
| `Actual_Headcount_Plan.csv` | **Yes** | Monthly × department summary | **Soft** — dept totals ↔ IS payroll implied |
| `Actual_accounts_receivable_rollforward.csv` | **Yes** | Monthly summary | **$1 bar** — `rollforward_check = 0` |
| `Actual_accounts_payable_rollforward.csv` | **Yes** | Monthly summary | **$1 bar** |
| `Actual_Working_Capital_Driver_Summary.csv` | **Yes** | Monthly summary | **Soft** — DSO/DPO vs AR/AP |
| `Actual_cash_flow_driver_assumptions.csv` | **Yes** | Monthly summary | **Soft** — driver constants |
| `Actual_SBC_Schedule.csv` | **Yes** | Monthly summary | **Soft** — ~1% of revenue |
| `Actual_Prepaids_Rollforward.csv` | **Yes** | Monthly summary | **$1 bar** |
| `Actual_cash_collections.csv` | **Partial** | Monthly summary | **Soft** — align to AR rollforward |
| `Actual_cash_flow_statement.csv` | **Yes** | Monthly summary | **$1 bar** |
| `Actual_gl_detail.csv` | **Partial** (Tier 2) | Transaction (account × period) | **Soft** — monthly sums ↔ IS |
| `Actual_deferred_revenue_waterfall.csv` | **Partial** (Tier 2) | Monthly summary | **$1 bar** when extended |
| `Actual_deferred_revenue_waterfall_SUPPORTING_ONLY.csv` | **Skip** | Duplicate/support | N/A |
| `Actual_pipeline_waterfall.csv` | **Partial** (Tier 2) | Monthly × opp type | **Soft** |
| `Actual_marketing_pipeline.csv` | **Partial** (Tier 2) | Monthly × channel | **Soft** |
| `Actual_marketing_spend_by_channel.csv` | **Partial** (Tier 2) | Monthly × channel | **Soft** |
| `Actual_funnel_conversion_rates.csv` | **Partial** (Tier 2) | Monthly × channel | **Soft** |
| `Actual_AP_Aging.csv` | **Partial** (Tier 2) | Monthly × bucket | **Soft** — sums to AP |
| `Actual_vendor_accrual_payment_schedule.csv` | **Partial** (Tier 2) | Monthly summary | **Soft** |
| `Actual_Prepaid_Amortization_Schedule.csv` | **Partial** (Tier 2) | Vendor schedule | **Soft** |
| `Actual_revenue_recognition.csv` | **Partial** (Tier 2) | Customer × period | **Soft** — monthly aggregate ↔ IS only |
| `Actual_customers.csv` | **Skip** | Master (700 rows) | N/A — keep Jan 2026 snapshot |
| `Actual_invoices.csv` | **Skip** | Transaction (~7.5k) | Cannot tie at $1 without full rebuild |
| `Actual_invoice_billing_schedule.csv` | **Skip** | Transaction (~4.3k) | Same |
| `Actual_opportunity_movements.csv` | **Skip** | Transaction (~225) | Deal detail won't sum to backcast waterfall |
| `Actual_opportunities.csv` | **Skip** | Transaction (~99) | Same |
| `Actual_opportunity_mix_summary.csv` | **Skip** | Aggregate snapshot | Derived from skipped detail |
| `Actual_commission_payouts.csv` | **Skip** | Transaction (~202) | Requires fake deal history |
| `Actual_renewal_commissions.csv` | **Skip** | Transaction (~385) | Same |
| `Actual_Employees.csv` | **Skip** | Master (~130) | Point-in-time roster; backcast HC via Headcount_Plan |
| `Actual_renewal_pipeline.csv` | **Skip** | Deal-level (~385) | Same |
| `Actual_Sales_Quotas.csv` | **Skip** | Rep × period | Requires rep/deal fabric |
| `Actual_sales_reps.csv` | **Skip** | Master (~48) | Static reference |
| `Actual_Open_Requisitions.csv` | **Skip** | Requisition master (~9) | Static |
| `Actual_vendor_payments.csv` | **Skip** | Transaction (~32) | AP rollforward sufficient |
| `Actual_commission_plans.csv` | **Skip** | Plan master (2) | Static |
| `Actual_chart_of_accounts.csv` | **Skip** | Master (38) | Static |
| `Actual_department_cost_centers.csv` | **Skip** | Master (35) | Static |
| `Actual_data_dictionary.csv` | **Skip** | Meta | Update descriptions post-generation if desired |
| `Actual_dataset_summary.csv` | **Update after gen** | Meta | Refresh period ranges + row counts |
| `Actual_marketing_pipeline_validation.csv` | **Skip** | Validation (1 row) | Regenerate when Tier 2 marketing extended |
| `Actual_pipeline_marketing_reconciliation.csv` | **Skip** | Reconciliation | Regenerate when Tier 2 extended |

---

## 4. Tier 1 — extend first

Matt and Claude backcast these **before** any warehouse load. Tier 1 must pass `$1` tie-outs among themselves.

### 4.1 `Actual_MRR_Waterfall.csv`

**Headers (preserve exactly):**

```
organization_id,version,period,beginning_arr,new_business_arr,expansion_arr,renewal_arr,contraction_arr,churn_arr,reactivation_arr,net_new_arr,ending_arr,gross_retention_rate,net_dollar_retention_rate,waterfall_check
```

**Sample FY26 row:**

```
8571e520-0687-4516-bdee-379f37c58c1f,Actual,2026-01,75000000,1200000,650000,68250000.0,180000,420000,60000,1310000,76310000,0.992,1.0007,0
```

**Method:**

1. Fix Jun 2026 row to demo `organization_id` (keep ending ARR **$85,308,020.62**).
2. Set **Dec 2025 ending ARR = Jan 2026 beginning ARR ($75M)** — continuity anchor.
3. Backcast monthly from Dec 2025 → Jan 2024 using Matt's **FY25→FY26** and **FY24→FY25** ARR growth % (§6).
4. Decompose `net_new_arr` into buckets using assumed **NDR**, **gross retention**, **churn %**, **expansion/new mix** (§6). Scale bucket dollars so:
   - `ending_arr = beginning_arr + net_new_arr`
   - `renewal_arr ≈ beginning_arr × gross_retention_rate` (within $1)
   - `waterfall_check = 0`

### 4.2 `Actual_income_statement.csv`

**Headers:**

```
period,revenue,cost_of_revenue,gross_profit,sales_and_marketing,research_and_development,general_and_administrative,ebitda,depreciation_and_amortization,interest_expense,tax_expense,net_income
```

**Method:**

- **Revenue:** `ending_arr / 12` for each month (MRR ≈ ARR/12; matches FY26 pattern within ~1%).
- **COGS:** ~29% of revenue (FY26 ratio).
- **OpEx lines:** hold FY26 **% of revenue** for S&M (~34%), R&D (~16%), G&A (~11%) unless Matt overrides in §6.
- **EBITDA, D&A, interest, tax, NI:** same formulas as FY26 (tax ≈ 20% of pre-tax where applicable).

**Tie-out:** Jun 2026 revenue **$7.35M** unchanged; monthly revenue track ARR/12 within **$1k soft / $100 hard** vs validation summary.

### 4.3 `Actual_balance_sheet.csv`

**Headers:**

```
period,cash,accounts_receivable,ppe_net,prepaids_and_other_current,total_assets,accounts_payable,deferred_revenue,debt,other_liabilities,total_liabilities,equity,total_liabilities_and_equity,balance_check
```

**Method:**

- **Cash:** roll forward from seed Jan 2024 cash using CFS `net_change_in_cash`.
- **AR / AP:** use rollforward files (§4.6–4.7).
- **Deferred revenue:** Tier 2 — for Tier 1 use `prior + (billings − revenue)` simplified or flat ratio to revenue until deferred waterfall extended.
- **PPE:** straight-line increase ~$35k/month (FY26 slope).
- **Debt / other liabilities:** flat $5M / $2.5M unless Matt enters changes.
- **Equity:** plug so `balance_check = 0`.

### 4.4 `Actual_cash_flow_statement.csv`

**Headers:**

```
period,net_income,depreciation_and_amortization,stock_based_compensation,change_in_accounts_receivable,change_in_accounts_payable,change_in_deferred_revenue,change_in_prepaids,net_cash_from_operating_activities,capital_expenditures,net_cash_from_investing_activities,debt_issuance_repayment,net_cash_from_financing_activities,net_change_in_cash,beginning_cash,ending_cash
```

**Method:**

- Pull **NI, D&A, SBC** from IS + SBC schedule.
- **Working capital changes** from AR/AP/deferred/prepaid rollforwards.
- **Capex:** scale with revenue (~2% monthly, FY26 pattern).
- **Tie-out:** `ending_cash` = BS cash; `beginning_cash(t) = ending_cash(t−1)`.

### 4.5 `Actual_cash_flow_bridge.csv`

**Headers:**

```
organization_id,version,period,beginning_cash,cash_collections_from_invoices,payroll_cash_out,commission_cash_out,vendor_cash_out_n30,tax_cash_out,interest_cash_out,other_operating_cash_out,capex,financing_to_maintain_cash_floor,ending_cash,cash_floor,bridge_check,notes,cash_collections,collections
```

**Method:**

- Derive outflows as **% of revenue** from FY26 ratios (payroll ~52%, vendor ~19%, commission ~3% of S&M).
- Set `bridge_check = 0` for all backcast months.
- **Reconcile FY26 Jun row** to BS cash before backcast (current pack shows `bridge_check ≈ 294k` on Jun 2026).

### 4.6 `Actual_Headcount_Plan.csv`

**Headers:**

```
scenario,period,department,headcount_beginning,new_hires,attrition,headcount_ending,open_requisitions,monthly_cash_payroll_cost,monthly_gaap_payroll_cost,monthly_sbc,quota_capacity_arr,ramped_quota_capacity_arr,source
```

**Method:**

- **Step function:** total HC at Jan 2024 = Matt's entered value; add hires per §6 at Jan each year + small monthly attrition (2%/yr).
- Scale department mix from FY26 Jan proportions (Sales 26, Marketing 13, R&D 34, etc.).
- **Payroll costs:** scale with HC × FY26 avg fully-loaded cost per dept.
- **Quota capacity:** tie to Sales HC × FY26 quota/head.

### 4.7 Rollforwards and drivers

| File | Backcast method |
|------|-----------------|
| `Actual_accounts_receivable_rollforward.csv` | `new_billings ≈ revenue × 1.05`; collections from DSO (37 days); `rollforward_check = 0` |
| `Actual_accounts_payable_rollforward.csv` | Accruals ~63% of total costs; payments Net 30; `rollforward_check = 0` |
| `Actual_Prepaids_Rollforward.csv` | Flat $180k additions, $195k amortization (FY26 pattern) |
| `Actual_Working_Capital_Driver_Summary.csv` | DSO 37, DPO 30, vendor 63% of costs |
| `Actual_cash_flow_driver_assumptions.csv` | Copy FY26 constants unless Matt overrides |
| `Actual_SBC_Schedule.csv` | 1% of revenue; split 10/40/35/15 COGS/S&M/R&D/G&A |
| `Actual_cash_collections.csv` | Align to AR rollforward `cash_collections` |

---

## 5. Tier 2 — only if Tier 1 ties

Extend after Tier 1 validates and loads cleanly.

| File | Approach |
|------|----------|
| `Actual_gl_detail.csv` | Generate **summary GL rows per IS line** per month (~15–25 rows/period), not 894-row rebuild. Monthly sum by `statement_category` ↔ IS. |
| `Actual_deferred_revenue_waterfall.csv` | Standard roll: `ending = beginning + new_billings − revenue_recognized`; anchor Dec 2025 to bridge Jan 2026 BS deferred. |
| `Actual_pipeline_waterfall.csv` | Scale pipeline buckets from MRR `new_business` + `expansion` at 1.0× coverage. |
| `Actual_marketing_pipeline.csv` + spend + funnel | Scale spend as **S&M × entered marketing %**; hold conversion rates near FY26 averages. |
| `Actual_revenue_recognition.csv` | **Monthly aggregate rows only** (1 synthetic “AGGREGATE” customer per month) unless full customer rebuild approved. |
| `Actual_AP_Aging.csv` | Split AP ending into aging buckets (60/25/10/5%). |

**Gate:** Tier 2 load only when `validate-csv-pack.mjs` passes on Tier 1 + existing Budget/Forecast continuity (Jun Actual ARR → Jul Forecast ARR).

---

## 6. Tier 3 — skip for v1 (and why)

| Category | Files | Why skip |
|----------|-------|----------|
| **Customer / billing detail** | `customers`, `invoices`, `invoice_billing_schedule`, `revenue_recognition` (customer grain) | 700 customers × 30 months = fake precision; won't tie to backcast MRR at $1 |
| **CRM / deal detail** | `opportunities`, `opportunity_movements`, `renewal_pipeline`, mix/reconciliation | Pipeline drilldown requires deal IDs tied to waterfall movements |
| **Commissions** | `commission_payouts`, `renewal_commissions`, `Sales_Quotas` | Downstream of fake opportunities |
| **Workforce master** | `Employees`, `sales_reps`, `Open_Requisitions` | Point-in-time; use `Headcount_Plan` for historical HC trend |
| **Static reference** | `chart_of_accounts`, `department_cost_centers`, `commission_plans` | Timeless — no period extension |
| **Vendor detail** | `vendor_payments` | AP rollforward + bridge sufficient for cash |

PPI Phase 4 (forecast accuracy) and trajectory need **summary Actuals**, not customer-level audit trails.

---

## 7. Growth assumptions template (Matt fills before Claude runs)

Copy this table into the chat or a `backcast_assumptions.csv` beside `simple CSVS`. Claude reads it; does not invent growth rates.

### 7.1 Entered by Matt

| Assumption | FY24 | FY25 | FY26 (H1 actual — verify only) | Notes |
|------------|------|------|----------------------------------|-------|
| **ARR YoY growth %** (Jan→Jan) | ___% | ___% | ~___% (Jan $75M → Jun $85.3M) | Defines backcast path into Jan 2026 $75M |
| **Net dollar retention (NDR)** | ___% | ___% | ~100.2% (Jun 2026) | Monthly `net_dollar_retention_rate` |
| **Gross retention %** | ___% | ___% | ~99.4% (Jun 2026) | `renewal_arr / beginning_arr` |
| **Churn ARR % of BoP ARR** | ___% | ___% | ~0.6%/mo | Feeds `churn_arr` |
| **New business % of net new ARR** | ___% | ___% | ~50% | Split with expansion |
| **Expansion % of net new ARR** | ___% | ___% | ~35% | |
| **Headcount — total FTE (Jan)** | ___ | ___ | 121 (Jan 2026 from Headcount_Plan) | Step at fiscal year |
| **Headcount growth % YoY** | ___% | ___% | ___% | Alternative to absolute FTE |
| **S&M as % of revenue** | ___% | ___% | ~34% | IS line |
| **R&D as % of revenue** | ___% | ___% | ~16% | |
| **G&A as % of revenue** | ___% | ___% | ~11% | |
| **Marketing spend as % of S&M** | ___% | ___% | ___% | Tier 2 only |
| **Jan 2024 beginning cash ($)** | ___ | — | — | Seed for CFS/BS roll |
| **DSO / DPO (days)** | 37 / 30 | 37 / 30 | 37 / 30 | Match FY26 unless changed |

### 7.2 Derived by Claude (document in `Actual_dataset_summary.csv`)

| Derived field | Formula |
|---------------|---------|
| Jan 2025 beginning ARR | Jan 2026 ARR ÷ (1 + FY25→FY26 growth) |
| Jan 2024 beginning ARR | Jan 2025 ARR ÷ (1 + FY24→FY25 growth) |
| Monthly revenue | `ending_arr / 12` |
| OpEx lines | Revenue × Matt's % assumptions |
| IS → CFS → BS | Roll-forward chain (§4) |

### 7.3 Derived vs entered (budget module alignment)

| Metric | Backcast v1 | Future budget builder |
|--------|-------------|----------------------|
| Revenue | **Derived** from ARR waterfall | **Entered** top-down YoY % |
| OpEx (except payroll) | **Derived** from % revenue | **Entered** or derived |
| Headcount / payroll | **Entered** step + **derived** cost | **Entered** HC placeholders |
| MRR buckets | **Derived** from NDR/churn mix | N/A for budget |

Mark each assumption **entered** vs **derived** in generation notes so the future budget module can flip the driver direction.

---

## 8. Claude generation instructions

**Do not run until Matt fills §7.**

### Step 0 — Backup

```powershell
$src = "$env:USERPROFILE\OneDrive\Documents\simple CSVS"
$bak = "$env:USERPROFILE\OneDrive\Documents\simple CSVS_backup_FY26_only_$(Get-Date -Format yyyyMMdd)"
Copy-Item -Path $src -Destination $bak -Recurse
```

### Step 1 — Read sources

1. Read all FY26 rows from Tier 1 `Actual_*.csv` in `simple CSVS`.
2. Read headers from `backend/templates/csv/` if any column mismatch (headers must match templates **exactly**).
3. Read Matt's §7 assumption table.

### Step 2 — Generate backcast rows

For each Tier 1 file:

1. Prepend periods `2024-01` … `2025-12` (24 rows) before existing `2026-01` … `2026-06` rows.
2. Preserve **column order and names** character-for-character.
3. Use `organization_id = 8571e520-0687-4516-bdee-379f37c58c1f`, `version = Actual` on all rows.
4. Ensure **Dec 2025 → Jan 2026** continuity on ARR, cash, AR, AP, HC.
5. Do **not** modify Budget_* or Forecast_* files.
6. Do **not** touch Tier 3 files (leave FY26-only content as-is).

### Step 3 — Update metadata

- `Actual_dataset_summary.csv`: set `Actual months` to `2024-01 to 2026-06`; update row counts.
- Add note in summary: `History label,Synthetic backcast for PPI — not audited`.

### Step 4 — Validate before load

```powershell
cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence\frontend
$env:SMPL_CSV_DIR = "$env:USERPROFILE\OneDrive\Documents\simple CSVS"
node scripts\validate-csv-pack.mjs
# Review: frontend\scripts\validate-csv-pack-result.json
```

Fix any failures on:

- MRR `waterfall_check`
- Jun 2026 → Jul 2026 Forecast ARR continuity (unchanged Forecast files)
- IS validation summaries

### Step 5 — Optional Tier 2

Repeat Steps 2–4 for Tier 2 files only if Tier 1 validation passes.

---

## 9. Load procedure

### Local (recommended first)

```powershell
cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence
.\scripts\load-and-validate-local.ps1
```

This runs: `validate-csv-pack.mjs` → `setup-prod-warehouse.ps1` with `-CloseMonth 2026-06` → `verify_warehouse_org.py` → ARR spot-check.

### Prod / Neon

```powershell
.\scripts\setup-prod-warehouse.ps1 `
  -DatabaseUrl "<neon-postgresql-url>" `
  -CsvFolder "$env:USERPROFILE\OneDrive\Documents\simple CSVS" `
  -OrganizationId "8571e520-0687-4516-bdee-379f37c58c1f" `
  -CloseMonth "2026-06"
```

### API load (local dev, API running)

```powershell
.\scripts\load-csvs.ps1 -Prefix Actual
.\scripts\load-csvs.ps1 -Prefix Budget
# Forecast via load_forecast_csvs.py (see load-csvs.ps1 header)
```

### Post-load verification

| Check | Expected |
|-------|----------|
| `organizations.close_month` | `2026-06` |
| `actual_mrr_waterfall` periods | `2024-01` … `2026-06` (30 rows) |
| `actual_income_statement` periods | 30 rows |
| Jun 2026 ending ARR | ~$85.3M |
| Combined scenario in UI | Actual through Jun 2026; Forecast Jul–Dec 2026 |
| PPI seed / outlook API | Returns multi-year Actual series without gap |

```powershell
cd backend
.\.venv312\Scripts\python.exe scripts\verify_warehouse_org.py --organization-id 8571e520-0687-4516-bdee-379f37c58c1f
```

---

## 10. Validation checklist

Run after generation and after load.

### Structural

- [ ] Every Tier 1 file has **30** monthly rows (`2024-01`–`2026-06`)
- [ ] No duplicate `period` keys within a file
- [ ] Column headers byte-match templates / pre-backup files
- [ ] All `organization_id` values = demo UUID (no `smpl-2026` stragglers)

### $1 bar (hard)

- [ ] MRR: `waterfall_check = 0` all periods
- [ ] MRR: `ending_arr(t-1) = beginning_arr(t)`
- [ ] IS: `gross_profit = revenue − COGS`; components sum to EBITDA path
- [ ] BS: `balance_check = 0`
- [ ] AR/AP rollforwards: `rollforward_check = 0`
- [ ] CFS: `ending_cash = beginning_cash + net_change_in_cash`
- [ ] CFS ending cash = BS cash each period
- [ ] Dec 2025 ending ARR = Jan 2026 beginning ARR ($75M)
- [ ] Jun 2026 ending ARR = Jul 2026 Forecast beginning ARR (~$85.3M)

### Soft (investigate if failed)

- [ ] Revenue ≈ ending ARR / 12 (±$1k)
- [ ] Headcount plan dept totals ↔ payroll implied in bridge
- [ ] DSO 35–40 days on WC summary
- [ ] No negative ARR, headcount, or cash (unless intentional bridge note)

### Impossible values

- [ ] No negative `ending_arr`, `gross_retention_rate` > 1, or NDR < 0
- [ ] Churn + contraction ≤ beginning ARR
- [ ] Tax/expense signs match FY26 convention (expenses positive in IS)

### Script / API

- [ ] `node frontend/scripts/validate-csv-pack.mjs` → exit 0
- [ ] `verify_warehouse_org.py` passes
- [ ] Board / forecast-engine show Actual history back to Jan 2024

---

## 11. Honest limits

1. **Synthetic label:** All FY24–FY25 rows are **modeled backward** from FY26 demo actuals using Matt's growth assumptions — not extracted from ERP, Maxio, or CRM.
2. **Not audit-grade:** Do not use for SOC2 tie-out claims, customer-facing “actuals,” or board packages presented as audited history.
3. **Customer/detail gap:** Tier 3 skipped intentionally — drilldowns (invoice → customer → opp) will show **FY26-only** detail while summaries show 30 months. UI should not imply customer-level FY24 history exists.
4. **Combined scenario:** Still **Actual through close month + Forecast after** — backcast does not create `actual_FY24` scenarios; it extends the same Actual spine.
5. **Budget module:** Backcast informs **feasibility baselines** for future top-down budget UX; it does not replace Matt's submit/approve workflow (not built yet).
6. **PPI:** Enables trajectory and accuracy **development** on demo data; production PPI still requires real tenant history when available.

---

## 12. References

| Doc / script | Relevance |
|--------------|-----------|
| [SMPL_Predictive_Planning_Intelligence_Framework.md](./SMPL_Predictive_Planning_Intelligence_Framework.md) | PPI needs Actual history; LLM reads structured payloads only |
| [SMPL_Agent_and_Predictive_Analytics_Checklist.md](./SMPL_Agent_and_Predictive_Analytics_Checklist.md) | Tie-out patterns, $1 bar |
| `scripts/load-csvs.ps1` | Default CSV folder |
| `scripts/setup-prod-warehouse.ps1` | Neon load + `-CloseMonth` |
| `scripts/load-and-validate-local.ps1` | Full local pipeline |
| `frontend/scripts/validate-csv-pack.mjs` | Pre-load cross-checks |
| `backend/app/services/demo_csv/loader.py` | Delete+insert per table |

---

## Appendix A — Quick header reference (Tier 1)

<details>
<summary>Click to expand all Tier 1 headers</summary>

**Actual_MRR_Waterfall.csv** — `organization_id,version,period,beginning_arr,new_business_arr,expansion_arr,renewal_arr,contraction_arr,churn_arr,reactivation_arr,net_new_arr,ending_arr,gross_retention_rate,net_dollar_retention_rate,waterfall_check`

**Actual_income_statement.csv** — `period,revenue,cost_of_revenue,gross_profit,sales_and_marketing,research_and_development,general_and_administrative,ebitda,depreciation_and_amortization,interest_expense,tax_expense,net_income`

**Actual_balance_sheet.csv** — `period,cash,accounts_receivable,ppe_net,prepaids_and_other_current,total_assets,accounts_payable,deferred_revenue,debt,other_liabilities,total_liabilities,equity,total_liabilities_and_equity,balance_check`

**Actual_cash_flow_statement.csv** — `period,net_income,depreciation_and_amortization,stock_based_compensation,change_in_accounts_receivable,change_in_accounts_payable,change_in_deferred_revenue,change_in_prepaids,net_cash_from_operating_activities,capital_expenditures,net_cash_from_investing_activities,debt_issuance_repayment,net_cash_from_financing_activities,net_change_in_cash,beginning_cash,ending_cash`

**Actual_Headcount_Plan.csv** — `scenario,period,department,headcount_beginning,new_hires,attrition,headcount_ending,open_requisitions,monthly_cash_payroll_cost,monthly_gaap_payroll_cost,monthly_sbc,quota_capacity_arr,ramped_quota_capacity_arr,source`

</details>

---

*Next step for Matt: fill §7 assumption table → hand spec + assumptions to Claude for CSV generation.*
