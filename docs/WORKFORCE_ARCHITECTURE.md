# Workforce Operating Model Architecture

## Purpose

Replace the simplified `Forecast_Headcount_Plan.csv` (department × period × manual payroll) with an **HRIS-style workforce operating intelligence layer** that derives payroll from people data, not uploaded totals.

## Design principles

1. **Employee grain** — filled roles with hire/term dates, comp, quota, and ramp.
2. **Pipeline grain** — open requisitions with hiring timing and approval status.
3. **Assumption grain** — compensation bands and productivity ramps by role.
4. **Allocation grain** — department → P&L line mapping for downstream finance surfaces.
5. **Derived payroll** — `headcount × compensation × ramp × benefits`; never authoritative manual payroll on the workforce path.

## Source datasets (upload CSVs)

Upload uses **header matching**, not a `workforce_` filename prefix. These names from `simple CSVS` are supported:

| Dataset | Table | Accepted filenames |
|---------|--------|-------------------|
| Employees | `workforce_employees` | `Employees.csv`, `Forecast_Employees.csv`, `Actual_Employees.csv`, `Budget_Employees.csv` |
| Open requisitions | `workforce_open_requisitions` | `Open_Requisitions.csv`, `Forecast_Open_Requisitions.csv`, … |
| Hiring ramp assumptions | `workforce_hiring_ramp_assumptions` | `Hiring_Ramp_Assumptions.csv` |
| Compensation bands | `workforce_compensation_bands` | `Compensation_Bands.csv` |
| Department allocation rules | `workforce_department_allocation_rules` | `Department_Allocation_Rules.csv` |

`scenario` column (or `Actual_` / `Forecast_` / `Budget_` filename prefix) sets the planning version.

All tables include `version` (`Actual`, `Budget`, `Forecast`) and `organization_id`.

### Required departments

Sales, Marketing, R&D, Product, Customer Success, Support, G&A, Finance, HR / People, Operations

### Employee fields

`employee_id`, `department`, `sub_department`, `role`, `level`, `region`, `hire_date`, `termination_date`, `employment_status`, `salary_annual`, `bonus_annual`, `commission_annual`, `equity_sbc_annual`, `benefits_load_pct`, `quota_capacity_arr`, `productivity_ramp_pct`, `months_to_full_productivity`

### Open requisition fields

`req_id`, `role`, `department`, `hiring_manager`, `target_hire_date`, `planned_start_date`, `priority`, `approved_status`, `requisition_type` (`new` | `replacement`), comp/quota overrides

## Derived mart

`workforce_period_summary` — written by the engine (`POST /api/v1/workforce/recompute`):

- `filled_headcount`, `planned_hire_headcount`, `total_headcount_fte`
- `base_payroll_monthly`, `bonus_monthly`, `commission_monthly`, `equity_sbc_monthly`, `benefits_load_monthly`, `total_people_cost_monthly`
- `quota_capacity_arr`, `productive_quota_capacity_arr` (quota × productivity ramp)

## Payroll formula

For each active FTE-month:

```
base_monthly = salary_annual / 12
bonus_monthly = bonus_annual / 12
commission_monthly = commission_annual / 12
sbc_monthly = equity_sbc_annual / 12

productive = base_monthly + bonus_monthly  (× productivity_ramp)
benefits = productive × benefits_load_pct

total_people_cost = productive + benefits + commission_monthly + sbc_monthly
```

Productivity ramp comes from `workforce_hiring_ramp_assumptions` (by department/role/level/month_offset since hire) or `months_to_full_productivity` on the employee.

## API

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/workforce/plan` | Full plan: period summary, P&L allocations, GTM capacity, operating metrics |
| `POST /api/v1/workforce/recompute` | Persist `workforce_period_summary`; optional legacy `headcount_plan` sync |
| `GET /api/v1/workforce/feeds/payroll` | Department payroll for Management P&L / department spend |
| `GET /api/v1/workforce/feeds/cash-payroll` | Cash payroll outflow schedule |
| `GET /api/v1/workforce/feeds/gtm-capacity` | Sales/Marketing quota capacity |
| `GET /api/v1/workforce/departments` | Canonical department list |
| `GET /api/v1/workforce/validation` | Workforce integration validation checks |

## Downstream feeds (integration map)

| Consumer | Feed | Status |
|----------|------|--------|
| Management P&L | `feeds.pnl_people_cost_lines` | Wired — open months overlay; GL payroll excluded |
| Cash Forecast | `feeds.cash_payroll_outflow` | Wired — `forecast_cash_collections` manual fallback |
| Department spend | `feeds.payroll_by_department` | Wired |
| GTM / ARR capacity | `feeds.gtm_quota_capacity_feed` | Wired — `forecast_quota_capacity` fallback; bookings coverage |
| Operating leverage / Rev per FTE / Burn multiple | `operating_metrics` on plan response | Ready |
| Scenario planning | `version` on all source tables | Ready |
| Board / Excel headcount | `workforce_period_summary` | Wired — legacy `headcount_plan` fallback |
| CSV upload | auto-recompute | Wired — `loader.py` recomputes after workforce CSV upsert |
| Validation | `validation_service.run_workforce_validations` | Wired — `GET /workforce/validation` |

## Legacy compatibility

- `forecast_headcount_plan` / `headcount_plan` remain for existing board exports.
- `POST /workforce/recompute?sync_legacy_headcount=true` overwrites derived `monthly_payroll_cost` from the engine.
- Manual payroll on legacy tables triggers validation warning `legacy_manual_payroll_detected`.

## Migration

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
```

Revision: `demo_csv_007_workforce_operating_model`

---

## Post-load checklist

Run these in **PowerShell** after uploading workforce CSVs (not in Cursor chat). Start the API first (`backend\restart-api.ps1`).

### 1. Confirm migration and upload support

```powershell
cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence\backend

# Should show demo_csv_007 (head)
.\.venv\Scripts\python.exe -m alembic current

# Should return workforce_upload_v2 / workforce_comp_bands_detected: true
Invoke-RestMethod "http://localhost:8000/api/v1/demo-csv/ping"
Invoke-RestMethod "http://localhost:8000/api/v1/workforce/ping"
```

### 2. Upload order (Demo CSV UI or API)

1. `Compensation_Bands.csv`
2. `Hiring_Ramp_Assumptions.csv`
3. `Department_Allocation_Rules.csv`
4. `Forecast_Employees.csv` (and Actual/Budget if used)
5. `Forecast_Open_Requisitions.csv`

### 3. Recompute derived payroll

```powershell
$org = "8571e520-0687-4516-bdee-379f37c58c1f"

# Preview plan (no DB write)
Invoke-RestMethod "http://localhost:8000/api/v1/workforce/plan?organization_id=$org&scenario=Forecast&start_period=2026-01-01&end_period=2026-12-31&persist=false"

# Persist workforce_period_summary + optional legacy headcount sync
Invoke-RestMethod -Method Post "http://localhost:8000/api/v1/workforce/recompute?organization_id=$org&scenario=Forecast&start_period=2026-01-01&end_period=2026-12-31&sync_legacy_headcount=true"
```

If recompute fails, read the error body:

```powershell
try {
  Invoke-RestMethod -Method Post "http://localhost:8000/api/v1/workforce/recompute?organization_id=$org&scenario=Forecast&start_period=2026-01-01&end_period=2026-12-31&sync_legacy_headcount=true"
} catch {
  $_.ErrorDetails.Message
}
```

### 4. One-shot local verification (no API required)

```powershell
cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence\backend
.\.venv\Scripts\python.exe .\scripts\verify_workforce_baseline.py
```

Expect: `PASS: workforce baseline OK` and non-zero `total_people_cost_monthly` rows.

### 5. Acceptance criteria

| Check | Expected |
|-------|----------|
| `GET /workforce/plan` | `period_summary` array with rows |
| `POST /workforce/recompute` | `"status": "ok"`, `periods_computed` > 0 |
| `workforce_period_summary` | Non-zero `total_people_cost_monthly` for active months |
| Validations | Warnings OK; fix fails before integration work |

**Note:** Paste implementation prompts into **Cursor Agent chat**, not PowerShell. Use `Invoke-RestMethod` for HTTP calls — PowerShell does not support `GET http://...` as a command.

---

## Seed / demo load order

Load compensation bands and ramp assumptions before employees/requisitions, then:

```bash
# Upload five workforce CSVs via demo CSV API, or seed from backend/demo_data/
POST /api/v1/workforce/recompute?organization_id=...&scenario=Forecast&start_period=2026-01-01&end_period=2026-12-31
```

## What not to use

- **Do not** use `Forecast_Headcount_Plan.csv` `monthly_payroll_cost` as source of truth for forecast payroll.
- **Do not** manually maintain `forecast_cash_collections.payroll_cash_out` when workforce data exists — derive from `feeds.cash_payroll_outflow`.
