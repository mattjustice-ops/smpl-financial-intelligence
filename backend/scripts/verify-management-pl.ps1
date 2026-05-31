# Verify Management P&L routes are registered in THIS repo's venv.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$python = Join-Path $PWD ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = Join-Path $PWD ".venv312\Scripts\python.exe"
}
if (-not (Test-Path $python)) {
    Write-Host "No .venv found. Create venv and pip install -r requirements.txt" -ForegroundColor Red
    exit 1
}

Write-Host "Python: $python"
& $python -c @"
from app.main import app, _management_pl_mounted
paths = sorted({getattr(r, 'path', '') for r in app.routes})
mpl = [p for p in paths if 'management' in p]
print('management_pl_mounted:', _management_pl_mounted())
print('management paths:', mpl)
if not mpl:
    raise SystemExit('FAIL: no management-pl routes on app')
print('OK')
"@

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "HTTP probes (API must be running on :8000):" -ForegroundColor Cyan
foreach ($url in @(
        "http://127.0.0.1:8000/health",
        "http://127.0.0.1:8000/api/v1/management-pl/ping",
        "http://127.0.0.1:8000/api/v1/_diagnostics/routes"
    )) {
    try {
        $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5
        Write-Host "  [OK] $url -> $($r.StatusCode)" -ForegroundColor Green
        if ($url -like "*ping*") { Write-Host "       $($r.Content)" }
    } catch {
        Write-Host "  [FAIL] $url -> $($_.Exception.Message)" -ForegroundColor Red
    }
}
