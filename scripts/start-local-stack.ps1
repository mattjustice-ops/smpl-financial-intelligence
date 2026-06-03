# Start Postgres (Docker), backend API, and frontend dev server for local /app testing.
# Run from repo root: powershell -ExecutionPolicy Bypass -File .\scripts\start-local-stack.ps1

param(
    [int]$ApiPort = 8001,
    [int]$WebPort = 3002
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== SMPL local stack ===" -ForegroundColor Cyan
Write-Host "Repo: $Root"

Write-Host ""
Write-Host "[1/4] Docker Postgres..." -ForegroundColor Cyan
docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: docker compose failed. Is Docker Desktop running?" -ForegroundColor Red
    exit 1
}
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "[2/4] Backend health on port $ApiPort..." -ForegroundColor Cyan
$healthUrl = "http://127.0.0.1:$ApiPort/health"
try {
    $r = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 3
    Write-Host "API already running: $healthUrl ($($r.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "Starting API in a new window (keep it open)..." -ForegroundColor Yellow
    $restartScript = Join-Path $Root "backend\restart-api.ps1"
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-File", $restartScript,
        "-Port", "$ApiPort"
    )
    Write-Host "Waiting up to 45s for $healthUrl ..."
    $ready = $false
    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Seconds 3
        try {
            $r = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 3
            if ($r.StatusCode -eq 200) {
                $ready = $true
                break
            }
        } catch {
            # keep waiting
        }
    }
    if (-not $ready) {
        Write-Host "ERROR: API did not respond at $healthUrl" -ForegroundColor Red
        Write-Host "Check the backend PowerShell window for errors." -ForegroundColor Yellow
        exit 1
    }
    Write-Host "API ready." -ForegroundColor Green
}

Write-Host ""
Write-Host "[3/4] Database check..." -ForegroundColor Cyan
$dbUrl = "http://127.0.0.1:$ApiPort/health/db"
try {
    $db = Invoke-WebRequest -Uri $dbUrl -UseBasicParsing -TimeoutSec 8
    Write-Host "Database: $($db.Content)" -ForegroundColor Green
} catch {
    Write-Host "WARN: Database not reachable yet. Run alembic upgrade head in backend/." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[4/4] Frontend on port $WebPort..." -ForegroundColor Cyan
$feDir = Join-Path $Root "frontend"
$envPath = Join-Path $feDir ".env.local"
$apiUrl = "http://127.0.0.1:$ApiPort"
if (Test-Path $envPath) {
    $existing = Get-Content $envPath -Raw
    if ($existing -notmatch "NEXT_PUBLIC_API_URL") {
        Add-Content $envPath "NEXT_PUBLIC_API_URL=$apiUrl"
    }
    if ($existing -notmatch "SFI_BACKEND_URL") {
        Add-Content $envPath "SFI_BACKEND_URL=$apiUrl"
    }
} else {
    @(
        "NEXT_PUBLIC_API_URL=$apiUrl",
        "SFI_BACKEND_URL=$apiUrl"
    ) | Set-Content $envPath -Encoding UTF8
}

$listen = Get-NetTCPConnection -LocalPort $WebPort -State Listen -ErrorAction SilentlyContinue
$appUrl = "http://localhost:$WebPort/app"
if ($listen) {
    Write-Host "Port $WebPort already in use. Open $appUrl" -ForegroundColor Green
} else {
    Write-Host "Starting frontend in a new window..." -ForegroundColor Yellow
    $frontendCmd = "Set-Location '$feDir'; npm run dev"
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command", $frontendCmd
    )
    Start-Sleep -Seconds 8
}

Write-Host ""
Write-Host "Done. Open $appUrl" -ForegroundColor Green
Write-Host "Direct API test: $healthUrl" -ForegroundColor DarkGray
