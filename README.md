# SaaS Financial Intelligence (local dev scaffold)

This repository contains a minimal local development setup:

- **Backend**: FastAPI + SQLAlchemy + Alembic (Python)
- **Database**: PostgreSQL via Docker Compose
- **Frontend**: Next.js dashboard with health check and **demo CSV upload** UI

Live CRM / billing / ERP connectors are not included yet; use the bundled demo CSVs or your own files that match the same headers exactly.

## Prerequisites (Windows)

1. **Docker Desktop** (includes Docker Compose)  
   - Install and start Docker Desktop before running the database.

2. **Python 3.11+**  
   - During install, enable **“Add python.exe to PATH”** (or use the Microsoft Store Python).

3. **Node.js LTS** (includes `npm`)  
   - Install from [nodejs.org](https://nodejs.org/).

## Quick start (one script)

Full step-by-step instructions: **[LOCAL-DEV-START.md](LOCAL-DEV-START.md)**

```powershell
cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence
powershell -ExecutionPolicy Bypass -File .\scripts\START-HERE.ps1
```

When the script succeeds, confirm in your browser:

http://127.0.0.1:8000/api/v1/management-pl/ping → `"build": "management-pl-v4-inline"`

Then open the dashboard: http://localhost:3002

## Documentation

Product architecture, data model, forecasting, close process, and reporting tie-outs:

- [docs/README.md](docs/README.md) — documentation index
- [docs/Architecture_Master.md](docs/Architecture_Master.md)
- [docs/Data_Model.md](docs/Data_Model.md)
- [docs/Forecasting_Assumptions.md](docs/Forecasting_Assumptions.md)
- [docs/Close_Process.md](docs/Close_Process.md)
- [docs/Reporting_Logic.md](docs/Reporting_Logic.md)

## Project layout

```
saas-financial-intelligence/
  docs/                       # Product & domain documentation
  docker-compose.yml          # PostgreSQL only
  backend/
    app/                      # FastAPI application
    alembic/                  # Database migrations
    demo_data/                # Bundled demo CSVs (exact headers)
    scripts/                  # e.g. seed_demo_csv.py
    requirements.txt
    .env.example
  frontend/                   # Next.js app
    .env.example
```

## Step 1 — Start PostgreSQL

Open **PowerShell** and go to the project folder (adjust the path if yours differs):

```powershell
cd $HOME\.cursor\projects\empty-window\saas-financial-intelligence
```

Start the database:

```powershell
docker compose up -d
```

Wait until Postgres is healthy (Docker Desktop → Containers, or run `docker compose ps`).

Default credentials (used by the sample `DATABASE_URL`):

- **User**: `sfi`
- **Password**: `sfi_dev_password`
- **Database**: `sfi`
- **Port**: `5432`

## Step 2 — Backend (API)

Open a **new** PowerShell window:

```powershell
cd $HOME\.cursor\projects\empty-window\saas-financial-intelligence\backend
```

Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create your local environment file:

```powershell
Copy-Item .env.example .env
```

Apply database migrations (use **`python -m alembic`** so you do not rely on the `alembic` script being on your PATH):

```powershell
python -m alembic upgrade head
```

Start the API server (recommended — sets venv, checks deps, binds `0.0.0.0:8000`):

```powershell
.\start-api.ps1
```

Or manually:

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Sanity checks (browser or another terminal):

- [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) → `{"status":"ok"}`
- [http://127.0.0.1:8000/health/db](http://127.0.0.1:8000/health/db) → database connected
- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) → interactive API docs

### Demo CSV upload (API + UI)

- **Organizations:** `GET/POST /api/v1/organizations/` — create at least one org before importing (or use **New organization** on the dashboard).
- **Single file:** `POST /api/v1/demo-csv/upload` — multipart form fields: `organization_id` (UUID), `file` (CSV). The first row must be headers that **exactly** match one of the known demo profiles (same names as the SQL columns; column order may vary). If the header set does not match, the API returns **400** with `received_headers` and `mismatch_by_profile` (each profile lists **missing** and **extra** columns). There is **no manual column mapping**.
- **Seed all bundled files:** `POST /api/v1/demo-csv/seed?organization_id=<uuid>` loads every CSV under `backend/demo_data/` in one transaction, in this order:
  1. `customers.csv`
  2. `subscriptions.csv`
  3. `opportunities.csv`
  4. `invoices.csv`
  5. `payments.csv`
  6. `gl_actuals.csv`
  7. `headcount_plan.csv`
  8. `vendor_contracts.csv`
  9. `sales_quotas.csv`
  10. `commission_plans.csv`
  11. `mrr_waterfall.csv`
- **CLI (optional):** from `backend/`, run `python scripts/seed_demo_csv.py <organization-uuid>` after activating the virtualenv.
- **OpenAPI:** `/docs` lists these routes under **demo-csv** and **organizations**.

## Step 3 — Frontend (dashboard placeholder) — Window 2

Use a **second** terminal window. Leave **Window 1** (the backend) running with `uvicorn` still active.

You can use **PowerShell** or **Command Prompt**. Run **one command at a time**: paste a single line, press **Enter**, wait until it finishes, then run the next.

### PowerShell (Window 2)

Go to the frontend folder:

```powershell
cd $HOME\.cursor\projects\empty-window\saas-financial-intelligence\frontend
```

Install JavaScript dependencies (this can take a minute the first time).

In **PowerShell**, prefer `npm.cmd` so Windows does not try to run `npm.ps1` (often blocked by script security settings). If you use **Command Prompt** instead, plain `npm` is fine.

```powershell
npm.cmd install
```

(Optional) Only if your API is **not** at `http://localhost:8000`: copy the sample env file, then edit `frontend/.env.local` in a text editor and set `NEXT_PUBLIC_API_URL` to your API URL.

```powershell
Copy-Item .env.example .env.local
```

Start the Next.js dev server:

```powershell
npm.cmd run dev
```

When it says it is ready, open [http://localhost:3002](http://localhost:3002) (this project’s default dev port). You should see status lines for `/health` and `/health/db` if the API and database are running.

### Command Prompt — Window 2 (same steps, different copy command)

```bat
cd %USERPROFILE%\.cursor\projects\empty-window\saas-financial-intelligence\frontend
```

```bat
npm install
```

(Optional) Copy env sample before editing:

```bat
copy .env.example .env.local
```

```bat
npm run dev
```

## Stopping services

- **Frontend / backend**: press `Ctrl+C` in each terminal.
- **Postgres**:

```powershell
cd $HOME\.cursor\projects\empty-window\saas-financial-intelligence
docker compose down
```

To delete the database volume as well (wipes local data):

```powershell
docker compose down -v
```

## Financial statement dashboard validation

The dashboard now reads normalized financial statement API outputs from uploaded CSV-backed tables. It does not use frontend placeholder statement values.

Run the backend and frontend, then open [http://localhost:3000](http://localhost:3000):

```powershell
cd $HOME\.cursor\projects\empty-window\saas-financial-intelligence\backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```powershell
cd $HOME\.cursor\projects\empty-window\saas-financial-intelligence\frontend
npm.cmd run dev
```

Use the **Financial Statements** card to select `Actual`, `Budget`, `Forecast`, or `Combined`. The normalized API endpoints are:

- `GET /api/v1/financial-statements/income-statement`
- `GET /api/v1/financial-statements/balance-sheet`
- `GET /api/v1/financial-statements/cash-flow`
- `GET /api/v1/financial-statements/summary`
- `GET /api/v1/financial-statements/validation`

Each endpoint accepts `organization_id`, `scenario`, `start_period`, and `end_period`. `Combined` returns Actual periods through May 2026 and Forecast periods from June 2026 onward.

Run reporting tests from `backend/`:

```powershell
python -m pytest tests/test_financial_statement_reporting.py tests/test_demo_csv_expanded_headers.py tests/test_financial_statements_engine.py -q
```

## Marketing performance dashboard

The Marketing Performance module uses the shared reporting foundation under `backend/app/services/reporting/` and reads CSV-backed warehouse tables such as `actual_marketing_pipeline`, `budget_marketing_pipeline`, and `forecast_marketing_pipeline`.

If you add or change versioned CSV files, sync and reload the warehouse tables from `backend/`:

```powershell
python scripts\sync_warehouse_schema.py "C:\Users\mattj\OneDrive\Documents\simple CSVS"
python scripts\load_versioned_csvs.py 8571e520-0687-4516-bdee-379f37c58c1f "C:\Users\mattj\OneDrive\Documents\simple CSVS"
```

`Forecast_gl_detail.csv` loads into the typed `forecast_gl_detail` table and is synced to `gl_actuals` (version `Forecast`) for Management P&L drilldown and FY outlook charts. After adding that file, run:

```powershell
cd backend
python -m alembic upgrade head
python scripts\load_forecast_gl_detail.py 8571e520-0687-4516-bdee-379f37c58c1f "C:\Users\mattj\OneDrive\Documents\simple CSVS\Forecast_gl_detail.csv"
```

To fully clear and reload CSV-backed Actual/Budget/Forecast warehouse data for one org:

```powershell
python scripts\sync_warehouse_schema.py "C:\Users\mattj\OneDrive\Documents\simple CSVS"
python scripts\reset_versioned_warehouse.py 8571e520-0687-4516-bdee-379f37c58c1f
python scripts\load_versioned_csvs.py 8571e520-0687-4516-bdee-379f37c58c1f "C:\Users\mattj\OneDrive\Documents\simple CSVS"
```

Start the backend and frontend, then open [http://localhost:3000](http://localhost:3000). Use the **Marketing Performance** card for scenario, period, and channel filtering.

Marketing API endpoints:

- `GET /api/v1/marketing/performance-summary`
- `GET /api/v1/marketing/channel-performance`
- `GET /api/v1/marketing/pipeline-waterfall`
- `GET /api/v1/marketing/funnel-conversion`
- `GET /api/v1/marketing/spend-efficiency`
- `GET /api/v1/marketing/actual-budget-forecast`

Each endpoint accepts `organization_id`, `scenario`, `start_period`, `end_period`, and optional `marketing_channel`. Periods use `YYYY-MM`, for example `2026-01`.

Run focused reporting tests from `backend/`:

```powershell
python -m pytest tests/test_reporting_foundation.py tests/test_demo_csv_expanded_headers.py tests/test_financial_statement_reporting.py -q
```

## Executive flow and expandable waterfalls

The dashboard includes an **Executive Flow Dashboard** card with expandable waterfall attribution. It uses only API/database data from the CSV-backed warehouse tables.

Primary API endpoints:

- `GET /api/v1/dashboard/executive-flow`
- `GET /api/v1/waterfalls/arr`
- `GET /api/v1/waterfalls/arr/attribution`
- `GET /api/v1/waterfalls/pipeline`
- `GET /api/v1/waterfalls/pipeline/attribution`
- `GET /api/v1/waterfalls/deferred-revenue`
- `GET /api/v1/waterfalls/deferred-revenue/attribution`
- `GET /api/v1/waterfalls/cash-flow`
- `GET /api/v1/waterfalls/cash-flow/attribution`
- `GET /api/v1/opportunities/stage-summary`
- `GET /api/v1/opportunities/closed-by-month`
- `GET /api/v1/opportunities/remaining-pipeline`
- `GET /api/v1/marketing/channel-drilldown`

Common query parameters:

- `organization_id`
- `scenario` (`Actual`, `Budget`, `Forecast`, `Combined`)
- `start_period` / `end_period` in `YYYY-MM`
- optional `period`, `quarter`, `fiscal_year`, `waterfall_type`, `marketing_channel`, `region`, `segment`, `owner`

Run focused tests from `backend/`:

```powershell
python -m pytest tests/test_dashboard_attribution.py tests/test_reporting_foundation.py -q
```

## Common Windows issues

### `Activate.ps1` is disabled

If PowerShell blocks the activate script, run **once** in that window:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then try `.\.venv\Scripts\Activate.ps1` again.

### `npm` fails in PowerShell (`npm.ps1 cannot be loaded` / execution policy)

Node installs **`npm.ps1`** for PowerShell. If your PC blocks running scripts, use either:

**Option A — use the Command Prompt launcher (no policy change):** run `npm.cmd` instead of `npm`:

```powershell
npm.cmd install
npm.cmd run dev
```

**Option B — allow local scripts for your user (one-time, then plain `npm` works):**

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

**Option C — use Command Prompt (cmd.exe)** for Window 2; `npm install` / `npm run dev` call `npm.cmd` and usually work without changing policy.

### `alembic` is not recognized (PowerShell)

The Alembic CLI is installed **inside** your project’s virtual environment. Either activate the venv first (`.\.venv\Scripts\Activate.ps1`), or call Alembic through Python (works even when `alembic` is not on your PATH and avoids `alembic.ps1` script policy issues):

```powershell
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "your message"
.\.venv\Scripts\python.exe -m alembic upgrade head
```

After activation, `python -m alembic ...` uses the same venv.

### `docker compose` not found

Use Docker Desktop’s current CLI (`docker compose`, with a space). If you only have the older plugin, try `docker-compose` instead.

### `/health/db` fails but Docker is running

Usually means Postgres is not ready yet, or port `5432` is already used by another Postgres install.  
Check `DATABASE_URL` in `backend/.env` matches `docker-compose.yml`.

## What to run next (short version)

After cloning or creating this folder on your machine:

1. `docker compose up -d` (in the repo root)  
2. Backend: create venv → `pip install -r requirements.txt` → `Copy-Item .env.example .env` → `python -m alembic upgrade head` → `python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`  
3. Frontend (new terminal, one command at a time): `cd` to `frontend` → `npm.cmd install` (PowerShell) or `npm install` (cmd) → (optional) copy `.env.example` to `.env.local` → `npm.cmd run dev` or `npm run dev`  
4. Open `http://localhost:3000`
