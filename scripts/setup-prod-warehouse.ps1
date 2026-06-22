# Phase B (ca-5) - Load warehouse schema + demo data into Neon (same DB Railway uses).
#
# Usage:
#   .\scripts\setup-prod-warehouse.ps1 `
#     -DatabaseUrl "postgresql://...@ep-....neon.tech/neondb?sslmode=require"
#
# Preview CSV files only:
#   .\scripts\setup-prod-warehouse.ps1 -DatabaseUrl "..." -ListOnly

param(
    [Parameter(Mandatory = $true)]
    [string]$DatabaseUrl,
    [string]$CsvFolder = "$env:USERPROFILE\OneDrive\Documents\simple CSVS",
    [string]$OrganizationId = "8571e520-0687-4516-bdee-379f37c58c1f",
    [string]$CloseMonth = "",
    [switch]$SkipMigrations,
    [switch]$SkipBundledDemo,
    [switch]$ForceBundledDemo,
    [switch]$SkipVersionedCsvs,
    [switch]$ListOnly
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $repoRoot "backend"
$python = Join-Path $backendDir ".venv312\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = Join-Path $backendDir ".venv\Scripts\python.exe"
}
if (-not (Test-Path $python)) {
    Write-Host "ERROR: backend venv not found (.venv312 under backend)." -ForegroundColor Red
    exit 1
}

function Convert-ToAlembicUrl {
    param([string]$Url)
    $normalized = $Url.Trim().Trim('"').Trim("'")
    if ($normalized -match "^postgresql://") {
        return $normalized -replace "^postgresql://", "postgresql+psycopg://"
    }
    if ($normalized -match "^postgres://") {
        return $normalized -replace "^postgres://", "postgresql+psycopg://"
    }
    return $normalized
}

function Invoke-BackendPython {
    param(
        [string[]]$ScriptArgs,
        [string]$Label
    )
    Push-Location $backendDir
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $env:DATABASE_URL = $alembicUrl
        & $python @ScriptArgs 2>&1 | Write-Host
        if ($LASTEXITCODE -ne 0) {
            throw "$Label failed (exit $LASTEXITCODE)"
        }
    }
    finally {
        $ErrorActionPreference = $prevEap
        Pop-Location
    }
}

function Test-WarehouseTableExists {
    param([string]$TableName)
    Push-Location $backendDir
    try {
        $env:DATABASE_URL = $alembicUrl
        $py = @"
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    row = conn.execute(
        text("""
            select 1 from information_schema.tables
            where table_schema = 'public' and table_name = :t
            limit 1
        """),
        {"t": "$TableName"},
    ).first()
    print("yes" if row else "no")
"@
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $result = ($py | & $python - 2>&1 | Out-String).Trim()
        }
        finally {
            $ErrorActionPreference = $prevEap
        }
        return $result -eq "yes"
    }
    finally {
        Pop-Location
    }
}

function Set-OrgCloseMonth {
    param([string]$Close)
    if (-not $Close) { return }
    Push-Location $backendDir
    try {
        $env:DATABASE_URL = $alembicUrl
        $env:SMPL_SETUP_ORG_ID = $OrganizationId
        $env:SMPL_SETUP_CLOSE_MONTH = $Close
        $py = @'
import os
from sqlalchemy import create_engine, text
org_id = os.environ["SMPL_SETUP_ORG_ID"].strip()
close_month = os.environ["SMPL_SETUP_CLOSE_MONTH"].strip()
engine = create_engine(os.environ["DATABASE_URL"])
with engine.begin() as conn:
    conn.execute(
        text("update organizations set close_month = :cm where id = cast(:oid as uuid)"),
        {"cm": close_month, "oid": org_id},
    )
print(f"OK: organizations.close_month = {close_month}")
'@
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $py | & $python - 2>&1 | Write-Host
            if ($LASTEXITCODE -ne 0) { throw "set close_month failed" }
        }
        finally {
            $ErrorActionPreference = $prevEap
        }
        Remove-Item Env:SMPL_SETUP_ORG_ID -ErrorAction SilentlyContinue
        Remove-Item Env:SMPL_SETUP_CLOSE_MONTH -ErrorAction SilentlyContinue
    }
    finally {
        Pop-Location
    }
}

$alembicUrl = Convert-ToAlembicUrl $DatabaseUrl

if ($DatabaseUrl -match "YOUR_PASSWORD|YOUR-RAILWAY") {
    Write-Host "ERROR: Use the real Neon connection string (Railway DATABASE_URL)." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path -LiteralPath $CsvFolder)) {
    Write-Host "ERROR: CSV folder not found: $CsvFolder" -ForegroundColor Red
    Write-Host "Pass -CsvFolder with your OneDrive path to simple CSVS." -ForegroundColor Yellow
    exit 1
}
$resolvedCsvFolder = (Resolve-Path -LiteralPath $CsvFolder).Path

$isLocalDb = $DatabaseUrl -match "localhost|127\.0\.0\.1"
$dbLabel = if ($isLocalDb) { "Local Postgres (localhost dev)" } else { "Hosted Postgres (Neon / Railway DATABASE_URL)" }

Write-Host ""
Write-Host "=== SMPL warehouse load (ca-5) ===" -ForegroundColor Cyan
Write-Host "Target DB: $dbLabel" -ForegroundColor DarkGray
Write-Host "Org ID:    $OrganizationId" -ForegroundColor DarkGray
Write-Host "CSV folder: $resolvedCsvFolder" -ForegroundColor DarkGray
Write-Host ""

$patterns = @("Actual_*.csv", "Actuals_*.csv", "Budget_*.csv", "Forecast_*.csv")
$csvFiles = foreach ($pat in $patterns) {
    Get-ChildItem -LiteralPath $resolvedCsvFolder -Filter $pat -File -ErrorAction SilentlyContinue
}
$csvFiles = $csvFiles | Sort-Object Name -Unique
Write-Host "Versioned CSV files found: $($csvFiles.Count)" -ForegroundColor Yellow
$csvFiles | ForEach-Object { Write-Host "  $($_.Name)" -ForegroundColor DarkGray }

if ($ListOnly) {
    exit 0
}

if ($csvFiles.Count -eq 0) {
    Write-Host "WARN: No Actual/Budget/Forecast CSVs in folder. Bundled demo_data still loads." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "This may take several minutes over Neon..." -ForegroundColor Yellow
Write-Host ""

if (-not $SkipMigrations) {
    Write-Host "[1/6] alembic upgrade head ..." -ForegroundColor Yellow
    Invoke-BackendPython @("-m", "alembic", "upgrade", "head") "alembic upgrade head"
    Write-Host "  Migrations OK." -ForegroundColor Green
} else {
    Write-Host "[1/6] Skipping migrations (-SkipMigrations)" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "[2/6] sync_warehouse_schema.py ..." -ForegroundColor Yellow
Invoke-BackendPython @("scripts\sync_warehouse_schema.py", $resolvedCsvFolder) "sync_warehouse_schema"

Write-Host ""
Write-Host "[3/6] seed_demo_org.py ..." -ForegroundColor Yellow
Invoke-BackendPython @("scripts\seed_demo_org.py", "--organization-id", $OrganizationId) "seed_demo_org"

$customersTableOk = Test-WarehouseTableExists -TableName "customers"
$skipBundled = $SkipBundledDemo.IsPresent
$skipBundledReason = ""
if ($ForceBundledDemo) {
    $skipBundled = $false
} elseif (-not $skipBundled) {
    if ($csvFiles.Count -gt 0) {
        $skipBundled = $true
        $skipBundledReason = "versioned Actual/Budget/Forecast CSVs are the source of truth"
    } elseif (-not $customersTableOk) {
        $skipBundled = $true
        $skipBundledReason = "public.customers table missing (optional backend/demo_data seed)"
    }
}

if ($skipBundled) {
    Write-Host ""
    if ($skipBundledReason) {
        Write-Host "[4/6] Skipping bundled demo_data ($skipBundledReason)" -ForegroundColor DarkGray
    } else {
        Write-Host "[4/6] Skipping bundled demo_data (-SkipBundledDemo)" -ForegroundColor DarkGray
    }
} else {
    Write-Host ""
    Write-Host "[4/6] seed_demo_csv.py (backend/demo_data: opportunities, MRR, workforce) ..." -ForegroundColor Yellow
    Invoke-BackendPython @("scripts\seed_demo_csv.py", $OrganizationId) "seed_demo_csv"
}

if (-not $SkipVersionedCsvs) {
    Write-Host ""
    Write-Host "[5/6] load_versioned_csvs.py (Actual + Budget) ..." -ForegroundColor Yellow
    foreach ($prefix in @("Actual", "Actuals", "Budget")) {
        $matches = Get-ChildItem -LiteralPath $resolvedCsvFolder -Filter "${prefix}_*.csv" -File -ErrorAction SilentlyContinue
        if ($matches) {
            Write-Host "  Loading ${prefix}_*.csv ..." -ForegroundColor Cyan
            Invoke-BackendPython @("scripts\load_versioned_csvs.py", $OrganizationId, $resolvedCsvFolder, $prefix) "load_versioned_csvs $prefix"
        }
    }

    Write-Host ""
    Write-Host "[6/6] load_forecast_csvs.py (Forecast_*.csv + GL migration) ..." -ForegroundColor Yellow
    $forecastMatches = Get-ChildItem -LiteralPath $resolvedCsvFolder -Filter "Forecast_*.csv" -File -ErrorAction SilentlyContinue
    if ($forecastMatches) {
        Invoke-BackendPython @("scripts\load_forecast_csvs.py", $OrganizationId, $resolvedCsvFolder) "load_forecast_csvs"
    } else {
        Write-Host "  No Forecast_*.csv files - skipped." -ForegroundColor DarkGray
    }
} else {
    Write-Host ""
    Write-Host "[5/6] Skipping versioned CSVs (-SkipVersionedCsvs)" -ForegroundColor DarkGray
    Write-Host "[6/6] Skipped" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "=== Row counts (demo org) ===" -ForegroundColor Cyan
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
Push-Location $backendDir
try {
    $env:DATABASE_URL = $alembicUrl
    $verifyPy = @"
import os
import uuid
from sqlalchemy import create_engine, text

org = uuid.UUID("$OrganizationId")
engine = create_engine(os.environ["DATABASE_URL"])
tables = [
    "actual_income_statement",
    "actual_mrr_waterfall",
    "forecast_income_statement",
    "forecast_mrr_waterfall",
    "actual_opportunities",
    "forecast_opportunities",
    "gl_actuals",
]
with engine.connect() as conn:
    for name in tables:
        try:
            n = conn.execute(
                text(f"select count(*) from {name} where organization_id = :oid"),
                {"oid": str(org)},
            ).scalar()
            print(f"  {name}: {n}")
        except Exception as exc:
            print(f"  {name}: (skip) {exc}")
"@
    $verifyPy | & $python - 2>&1 | Write-Host
}
finally {
    Pop-Location
    $ErrorActionPreference = $prevEap
}

if ($CloseMonth) {
    Write-Host ""
    Write-Host "Setting organizations.close_month ..." -ForegroundColor Yellow
    Set-OrgCloseMonth -Close $CloseMonth
} elseif (-not $ListOnly) {
    Write-Host ""
    Write-Host "Tip: pass -CloseMonth 2026-06 so board/forecast cutover matches your Actual files." -ForegroundColor DarkGray
}

Write-Host ""
if ($isLocalDb) {
    Write-Host "Done. Restart backend + frontend, sign in, then open:" -ForegroundColor Green
    Write-Host "  http://localhost:3002/forecast-engine" -ForegroundColor White
    Write-Host "  http://localhost:3002/app/board" -ForegroundColor White
} else {
    Write-Host "Done. Refresh your Vercel app (/app/board, /forecast-engine)." -ForegroundColor Green
    Write-Host "Railway API reads the same DATABASE_URL - no Railway env change needed." -ForegroundColor DarkGray
}
Write-Host ""
