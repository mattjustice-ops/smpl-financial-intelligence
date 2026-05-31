# Reload dashboard CSV data for one organization.
# Run each section in order, or run the whole file:
#   powershell -ExecutionPolicy Bypass -File .\scripts\reload-dashboard-csvs.ps1
#
# Edit these two lines first:
$OrgId = "8571e520-0687-4516-bdee-379f37c58c1f"
$CsvFolder = "$env:USERPROFILE\OneDrive\Documents\simple CSVS"

$ErrorActionPreference = "Stop"
$BackendRoot = Split-Path -Parent $PSScriptRoot
$RepoRoot = Split-Path -Parent $BackendRoot
$ApiBase = "http://127.0.0.1:8000"

$Python = Join-Path $BackendRoot ".venv312\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = Join-Path $BackendRoot ".venv\Scripts\python.exe"
}
if (-not (Test-Path $Python)) {
    $Python = "python"
}

Write-Host ""
Write-Host "=== Step 1: Check Postgres (optional) ===" -ForegroundColor Cyan
Set-Location $RepoRoot
docker compose ps

Write-Host ""
Write-Host "=== Step 2: Check API is running ===" -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "$ApiBase/health" -TimeoutSec 5
    Write-Host "API OK: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "Start the backend in another terminal, then run this script again:" -ForegroundColor Yellow
    Write-Host "  cd $BackendRoot"
    Write-Host "  .\.venv312\Scripts\Activate.ps1"
    Write-Host "  python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
    exit 1
}

Write-Host ""
Write-Host "=== Step 3: List organizations (copy your Org ID if needed) ===" -ForegroundColor Cyan
$orgs = Invoke-RestMethod -Uri "$ApiBase/api/v1/organizations/" -TimeoutSec 10
$orgs | ForEach-Object { Write-Host "  $($_.id)  $($_.name)" }
if (-not $OrgId) {
    Write-Host "Set `$OrgId at the top of this script." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Using OrgId: $OrgId" -ForegroundColor Green
Write-Host "CSV folder:  $CsvFolder" -ForegroundColor Green
if (-not (Test-Path $CsvFolder)) {
    Write-Host "Folder not found. Edit `$CsvFolder at the top of this script." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Step 4: Delete old Actual/Budget/Forecast warehouse data ===" -ForegroundColor Cyan
Set-Location $BackendRoot
& $Python scripts\reset_versioned_warehouse.py $OrgId

Write-Host ""
Write-Host "=== Step 5: Apply DB migrations (forecast_gl_detail mart) ===" -ForegroundColor Cyan
& $Python -m alembic upgrade head

Write-Host ""
Write-Host "=== Step 6: Load new CSV files from folder ===" -ForegroundColor Cyan
& $Python scripts\load_versioned_csvs.py $OrgId $CsvFolder

Write-Host ""
Write-Host "=== Step 7: Ensure Forecast GL detail is in gl_actuals ===" -ForegroundColor Cyan
& $Python scripts\load_forecast_gl_detail.py $OrgId "$CsvFolder\Forecast_gl_detail.csv"

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Green
Write-Host "Open the dashboard (usually http://localhost:3002) and press Ctrl+F5."
Write-Host ""
