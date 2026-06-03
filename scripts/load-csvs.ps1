# Bulk-load versioned CSVs from OneDrive into Postgres (no browser UI required).
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\load-csvs.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\load-csvs.ps1 -Prefix Forecast
#   powershell -ExecutionPolicy Bypass -File .\scripts\load-csvs.ps1 -Prefix Budget
#
# Forecast-only (all Forecast_*.csv, not just GL detail):
#   cd backend
#   .\.venv312\Scripts\python.exe scripts\load_forecast_csvs.py <org_id> "<csv-folder>"

param(
    [string]$OrgId = "8571e520-0687-4516-bdee-379f37c58c1f",
    [string]$CsvFolder = "$env:USERPROFILE\OneDrive\Documents\simple CSVS",
    [ValidateSet("", "Actual", "Actuals", "Budget", "Forecast")]
    [string]$Prefix = "",
    [switch]$ListOnly
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Python = Join-Path $Backend ".venv312\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Host "ERROR: Python venv not found at $Python" -ForegroundColor Red
    exit 1
}

Set-Location $Backend

$resolvedFolder = (Resolve-Path -LiteralPath $CsvFolder).Path
Write-Host "CSV folder (resolved): $resolvedFolder" -ForegroundColor Cyan

$listArgs = @("scripts\load_versioned_csvs.py", $OrgId, $resolvedFolder)
if ($Prefix) { $listArgs += $Prefix }

if ($ListOnly) {
    $patterns = if ($Prefix) { @("${Prefix}_*.csv") } else { @("Actual_*.csv", "Actuals_*.csv", "Budget_*.csv", "Forecast_*.csv") }
    $files = foreach ($pat in $patterns) {
        Get-ChildItem -LiteralPath $resolvedFolder -Filter $pat -File -ErrorAction SilentlyContinue
    }
    $files = $files | Sort-Object Name -Unique
    Write-Host "Found $($files.Count) file(s) matching versioned patterns:" -ForegroundColor Cyan
    $files | ForEach-Object { Write-Host "  $($_.Name)" }
    exit 0
}

Write-Host "Checking API..." -ForegroundColor Cyan
try {
    $health = Invoke-WebRequest -Uri "http://127.0.0.1:8001/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "API OK: $($health.Content)" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Start the API first: cd backend; .\restart-api.ps1 -Port 8001" -ForegroundColor Red
    exit 1
}

Write-Host "Checking Postgres..." -ForegroundColor Cyan
try {
    $db = Invoke-WebRequest -Uri "http://127.0.0.1:8001/health/db" -UseBasicParsing -TimeoutSec 10
    Write-Host "Database OK: $($db.Content)" -ForegroundColor Green
} catch {
    Write-Host "WARN: Database not ready. Starting docker and running migrations..." -ForegroundColor Yellow
    Set-Location $Root
    docker compose up -d
    Start-Sleep -Seconds 4
    Set-Location $Backend
    & $Python -m alembic upgrade head
}

$args = @("scripts\load_versioned_csvs.py", $OrgId, $resolvedFolder)
if ($Prefix) {
    $args += $Prefix
}

Write-Host "Loading CSVs from: $resolvedFolder" -ForegroundColor Cyan
if ($Prefix -eq "Forecast") {
    Write-Host "Using load_forecast_csvs.py (all Forecast_*.csv + GL migration)" -ForegroundColor Cyan
    & $Python scripts\load_forecast_csvs.py $OrgId $resolvedFolder
} else {
    & $Python @args
}
