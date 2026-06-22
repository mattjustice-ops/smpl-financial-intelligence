# Local Postgres warehouse load + validation (no Neon).
# Run from repo root:
#   .\scripts\load-and-validate-local.ps1

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$csvFolder = Join-Path $env:USERPROFILE "OneDrive\Documents\simple CSVS"
$orgId = "8571e520-0687-4516-bdee-379f37c58c1f"
$dbUrl = "postgresql://sfi:sfi_dev_password@localhost:5432/sfi"
$logFile = Join-Path $repoRoot "local-warehouse-load.log"

Write-Host "=== 1/4 CSV pack validation ===" -ForegroundColor Cyan
Push-Location (Join-Path $repoRoot "frontend")
node scripts/validate-csv-pack.mjs 2>&1 | Tee-Object -FilePath $logFile
$validateExit = $LASTEXITCODE
$resultJson = Join-Path $repoRoot "frontend\scripts\validate-csv-pack-result.json"
if (Test-Path $resultJson) {
    Get-Content $resultJson | Write-Host
}
if ($validateExit -ne 0) {
    Write-Host "WARN: CSV validation reported issues (see validate-csv-pack-result.json). Continuing load..." -ForegroundColor Yellow
}
Pop-Location

Write-Host "`n=== 2/4 Docker + warehouse load ===" -ForegroundColor Cyan
Push-Location $repoRoot
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    docker compose up -d 2>&1 | Tee-Object -FilePath $logFile -Append | Write-Host
    if ($LASTEXITCODE -ne 0) { throw "docker compose up failed (exit $LASTEXITCODE)" }

    & (Join-Path $repoRoot "scripts\setup-prod-warehouse.ps1") `
        -DatabaseUrl $dbUrl `
        -OrganizationId $orgId `
        -CsvFolder $csvFolder `
        -CloseMonth "2026-06" 2>&1 | Tee-Object -FilePath $logFile -Append | Write-Host
    if ($LASTEXITCODE -ne 0) { throw "Warehouse load failed (exit $LASTEXITCODE)" }
}
finally {
    $ErrorActionPreference = $prevEap
}
Pop-Location

Write-Host "`n=== 3/4 verify_warehouse_org ===" -ForegroundColor Cyan
$python = Join-Path $repoRoot "backend\.venv312\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = Join-Path $repoRoot "backend\.venv\Scripts\python.exe" }
Push-Location (Join-Path $repoRoot "backend")
$env:DATABASE_URL = "postgresql+psycopg://sfi:sfi_dev_password@localhost:5432/sfi"
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    & $python scripts\verify_warehouse_org.py --organization-id $orgId 2>&1 | Tee-Object -FilePath $logFile -Append | Write-Host
}
finally {
    $ErrorActionPreference = $prevEap
    Pop-Location
}

Write-Host "`n=== 4/4 ARR spot-check (Jun actual / Dec forecast) ===" -ForegroundColor Cyan
$py = @"
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ['DATABASE_URL'])
org = '$orgId'
checks = [
    ('actual_mrr_waterfall', '2026-06'),
    ('forecast_mrr_waterfall', '2026-12'),
]
with engine.connect() as c:
    for table, period in checks:
        row = c.execute(text(f"""
            select period, ending_arr from {table}
            where organization_id = cast(:org as uuid)
              and (
                cast(period as text) like :period_prefix
                or period = cast(:period_date as date)
              )
            order by period desc
            limit 1
        """), {
            'org': org,
            'period_prefix': period + '%',
            'period_date': period + '-01',
        }).first()
        print(f'{table} {period}:', row[1] if row else 'MISSING')
"@
$env:DATABASE_URL = "postgresql+psycopg://sfi:sfi_dev_password@localhost:5432/sfi"
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    $py | & $python - 2>&1 | Tee-Object -FilePath $logFile -Append | Write-Host
}
finally {
    $ErrorActionPreference = $prevEap
}

Write-Host "`n=== Ports (start apps if not listening) ===" -ForegroundColor Cyan
foreach ($port in 3002, 8001) {
    $listen = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($listen) { Write-Host "  Port ${port}: LISTENING" -ForegroundColor Green }
    else { Write-Host "  Port ${port}: not running - start frontend (:3002) and backend (:8001)" -ForegroundColor Yellow }
}

Write-Host "`nDone. Log: $logFile" -ForegroundColor Green
Write-Host "Board: http://localhost:3002/board/index.html" -ForegroundColor White
Write-Host "Forecast: http://localhost:3002/forecast-engine/index.html" -ForegroundColor White
Write-Host ("Outlook API: http://localhost:8001/api/v1/reporting/outlook?organization_id=" + $orgId) -ForegroundColor White
