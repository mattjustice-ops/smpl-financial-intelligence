# Start local SaaS Financial Intelligence stack (Postgres -> API -> frontend).
# Run from project root:
#   powershell -ExecutionPolicy Bypass -File .\scripts\start-local-dev.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"

Write-Host ""
Write-Host "SaaS Financial Intelligence - local dev" -ForegroundColor Cyan
Write-Host "Project: $Root"
Write-Host ""

Write-Host "Step 1/3: Postgres (docker compose up -d)..." -ForegroundColor Cyan
Push-Location $Root
docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARN: docker compose failed. Start Docker Desktop, then run: docker compose up -d" -ForegroundColor Yellow
} else {
    Write-Host "  Postgres on localhost:5432" -ForegroundColor Green
}
Pop-Location
Write-Host ""

Write-Host "Checking services..." -ForegroundColor Cyan
foreach ($probe in @(
        @{ Name = "API :8000"; Url = "http://127.0.0.1:8000/health" },
        @{ Name = "Frontend :3002"; Url = "http://127.0.0.1:3002" }
    )) {
    try {
        $r = Invoke-WebRequest -Uri $probe.Url -UseBasicParsing -TimeoutSec 2
        Write-Host ("  [up]   {0} -> HTTP {1}" -f $probe.Name, $r.StatusCode) -ForegroundColor Green
    } catch {
        Write-Host ("  [down] {0}" -f $probe.Name) -ForegroundColor DarkYellow
    }
}

$port3002 = Get-NetTCPConnection -LocalPort 3002 -ErrorAction SilentlyContinue
if ($port3002) {
    Write-Host ""
    Write-Host "Port 3002 is already in use. Use http://localhost:3002 or stop the old dev server before starting another." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 2/3: Opening backend terminal (.\start-api.ps1)..." -ForegroundColor Cyan
$backendCmd = "Set-Location '$Backend'; .\start-api.ps1"
Start-Process powershell -ArgumentList @("-NoExit", "-Command", $backendCmd)
Start-Sleep -Seconds 3

Write-Host "Step 3/3: Opening frontend terminal (npm run dev)..." -ForegroundColor Cyan
$frontendCmd = "Set-Location '$Frontend'; npm.cmd run dev"
Start-Process powershell -ArgumentList @("-NoExit", "-Command", $frontendCmd)

Write-Host ""
Write-Host "When the API terminal is up, confirm: http://127.0.0.1:8000/health" -ForegroundColor Green
Write-Host "When Next.js says Ready, open: http://localhost:3002" -ForegroundColor Green
Write-Host "Backend docs: http://127.0.0.1:8000/docs" -ForegroundColor DarkGray
Write-Host ""
Write-Host "First-time DB migrations (once):" -ForegroundColor DarkGray
Write-Host '  cd backend; .\.venv\Scripts\Activate.ps1; python -m alembic upgrade head'
Write-Host ""

