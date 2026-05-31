# One-shot: Postgres up -> alembic upgrade head -> workforce demo seed
# Run from repo root or backend:
#   powershell -ExecutionPolicy Bypass -File .\backend\scripts\fix-db-migrate-and-seed.ps1

$ErrorActionPreference = "Stop"
$Backend = Split-Path -Parent $PSScriptRoot
$RepoRoot = Split-Path -Parent $Backend
$Python = Join-Path $Backend ".venv312\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = Join-Path $Backend ".venv\Scripts\python.exe"
}
if (-not (Test-Path $Python)) {
    Write-Host "ERROR: No backend venv. Create .venv312 under backend first." -ForegroundColor Red
    exit 1
}

Write-Host "=== [1/4] Docker Postgres ===" -ForegroundColor Cyan
Set-Location $RepoRoot
docker compose up -d
Start-Sleep -Seconds 5
if (-not (Test-NetConnection -ComputerName 127.0.0.1 -Port 5432 -WarningAction SilentlyContinue).TcpTestSucceeded) {
    Write-Host "ERROR: Postgres not listening on 5432. Start Docker Desktop and retry." -ForegroundColor Red
    exit 1
}
Write-Host "  Postgres port 5432 OK" -ForegroundColor Green

Write-Host "=== [2/4] Alembic migrations ===" -ForegroundColor Cyan
Set-Location $Backend
& $Python -m alembic current
$upgrade = & $Python -m alembic upgrade head 2>&1
Write-Host $upgrade
if ($LASTEXITCODE -ne 0) {
    Write-Host "  upgrade head failed; trying stamp head (schema may already exist)..." -ForegroundColor Yellow
    & $Python -m alembic stamp head
    & $Python -m alembic current
}
Write-Host "  Alembic done." -ForegroundColor Green

Write-Host "=== [3/4] Check customers table ===" -ForegroundColor Cyan
$hasCustomers = & $Python -c @"
from sqlalchemy import inspect
from app.db.session import engine
print('yes' if 'customers' in inspect(engine).get_table_names() else 'no')
"@
Write-Host "  customers table: $hasCustomers"
if ($hasCustomers -ne "yes") {
    Write-Host "ERROR: customers table still missing after migrations." -ForegroundColor Red
    Write-Host "Paste output of: python -m alembic upgrade head" -ForegroundColor Red
    exit 1
}

Write-Host "=== [4/4] Workforce demo seed (skip full demo-csv/seed) ===" -ForegroundColor Cyan
& $Python (Join-Path $Backend "scripts\seed_workforce_demo.py")
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "DONE. Refresh Workforce tab or run:" -ForegroundColor Green
Write-Host '  Invoke-RestMethod "http://127.0.0.1:8000/api/v1/workforce/ping"' -ForegroundColor Green
Write-Host ""
Write-Host "Full demo-csv/seed is optional now (customers table exists):" -ForegroundColor Yellow
Write-Host '  $org = "8571e520-0687-4516-bdee-379f37c58c1f"' -ForegroundColor Yellow
Write-Host '  Invoke-RestMethod -Method Post "http://127.0.0.1:8000/api/v1/demo-csv/seed?organization_id=$org"' -ForegroundColor Yellow
