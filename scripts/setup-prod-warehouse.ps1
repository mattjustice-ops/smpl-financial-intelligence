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
    [switch]$SkipMigrations,
    [switch]$SkipBundledDemo,
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
    try {
        $env:DATABASE_URL = $alembicUrl
        & $python @ScriptArgs
        if ($LASTEXITCODE -ne 0) {
            throw "$Label failed (exit $LASTEXITCODE)"
        }
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

Write-Host ""
Write-Host "=== SMPL prod warehouse load (ca-5) ===" -ForegroundColor Cyan
Write-Host "Target DB: Neon (same as Railway sfi-api DATABASE_URL)" -ForegroundColor DarkGray
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
    Push-Location $backendDir
    try {
        $env:DATABASE_URL = $alembicUrl
        & $python -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) { throw "alembic upgrade head failed" }
        Write-Host "  Migrations OK." -ForegroundColor Green
    }
    finally {
        Pop-Location
    }
} else {
    Write-Host "[1/6] Skipping migrations (-SkipMigrations)" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "[2/6] sync_warehouse_schema.py ..." -ForegroundColor Yellow
Invoke-BackendPython @("scripts\sync_warehouse_schema.py", $resolvedCsvFolder) "sync_warehouse_schema"

Write-Host ""
Write-Host "[3/6] seed_demo_org.py ..." -ForegroundColor Yellow
Invoke-BackendPython @("scripts\seed_demo_org.py", "--organization-id", $OrganizationId) "seed_demo_org"

if (-not $SkipBundledDemo) {
    Write-Host ""
    Write-Host "[4/6] seed_demo_csv.py (backend/demo_data: opportunities, MRR, workforce) ..." -ForegroundColor Yellow
    Invoke-BackendPython @("scripts\seed_demo_csv.py", $OrganizationId) "seed_demo_csv"
} else {
    Write-Host ""
    Write-Host "[4/6] Skipping bundled demo_data (-SkipBundledDemo)" -ForegroundColor DarkGray
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
    "opportunities",
    "mrr_waterfall",
    "gl_actuals",
    "forecast_opportunities",
    "workforce_employees",
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
    $verifyPy | & $python -
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Done. Refresh https://smpl-financial-intelligence.vercel.app/app" -ForegroundColor Green
Write-Host "Railway sfi-api reads the same Neon DB. No Railway env change needed." -ForegroundColor DarkGray
Write-Host ""
