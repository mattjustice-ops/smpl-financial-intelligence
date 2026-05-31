# =============================================================================
# SaaS Financial Intelligence - ONE startup path (run this script first)
# =============================================================================
# Run from PowerShell:
#   cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence
#   powershell -ExecutionPolicy Bypass -File .\scripts\START-HERE.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Backend  = Join-Path $RepoRoot "backend"
$Frontend = Join-Path $RepoRoot "frontend"
$ExpectedBuild = "management-pl-v5-workforce-inline"
$ExpectedWorkforceBuild = "workforce-integration-v1"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " SFI Local Stack - START-HERE" -ForegroundColor Cyan
Write-Host " Repo: $RepoRoot" -ForegroundColor Cyan
Write-Host " Expected API build: $ExpectedBuild" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Free ports 8000 (API) and 3002 (Next.js)
Write-Host "[1/7] Stopping processes on ports 8000 and 3002..." -ForegroundColor Yellow
foreach ($port in @(8000, 3002)) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        $procId = $c.OwningProcess
        if ($procId -gt 0) {
            $procName = (Get-Process -Id $procId -ErrorAction SilentlyContinue).ProcessName
            Write-Host "  Stopping port $port : PID $procId ($procName)"
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
}
Start-Sleep -Seconds 2
Write-Host "  Ports cleared." -ForegroundColor Green
Write-Host ""

# Step 2: Postgres
Write-Host "[2/7] Starting Postgres (docker compose up -d)..." -ForegroundColor Yellow
Set-Location $RepoRoot
docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: docker compose failed. Open Docker Desktop, wait until it is running, then run this script again." -ForegroundColor Red
    exit 1
}
Write-Host "  Postgres started (localhost:5432)." -ForegroundColor Green
Write-Host ""

# Step 3: Find venv Python
Write-Host "[3/7] Checking backend virtualenv..." -ForegroundColor Yellow
$venvPython = $null
foreach ($venvName in @(".venv312", ".venv")) {
    $candidate = Join-Path $Backend "$venvName\Scripts\python.exe"
    if (Test-Path -LiteralPath $candidate) {
        $venvPython = $candidate
        break
    }
}
if (-not $venvPython) {
    Write-Host "ERROR: No backend venv. Run these commands once:" -ForegroundColor Red
    Write-Host "  cd $Backend"
    Write-Host "  python -m venv .venv"
    Write-Host "  .\.venv\Scripts\Activate.ps1"
    Write-Host "  python -m pip install --upgrade pip"
    Write-Host "  pip install -r requirements.txt"
    exit 1
}
Write-Host "  Python: $venvPython" -ForegroundColor Green

Write-Host "  Clearing Python bytecode cache..."
Get-ChildItem -LiteralPath (Join-Path $Backend "app") -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Step 4: DB migrations (safe to re-run)
Write-Host "[4/7] Running database migrations (alembic upgrade head)..." -ForegroundColor Yellow
Set-Location $Backend
& $venvPython -m alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Alembic upgrade failed; syncing revision stamp to head (schema may already exist)..." -ForegroundColor Yellow
    & $venvPython -m alembic stamp head
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: alembic failed. Fix Postgres connection, then run this script again." -ForegroundColor Red
        exit 1
    }
}
Write-Host "  Migrations OK." -ForegroundColor Green

# Step 5: Verify routes in code
Write-Host "[5/7] Verifying Management PL and workforce routes in app.main..." -ForegroundColor Yellow
Set-Location $Backend
$verifyMpl = Join-Path $Backend "scripts\verify_mpl_routes.py"
$verifyWf = Join-Path $Backend "scripts\verify_workforce_routes.py"
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$verifyOut = & $venvPython $verifyMpl 2>&1 | Out-String
$verifyExit = $LASTEXITCODE
Write-Host $verifyOut
if ($verifyExit -ne 0 -or $verifyOut -notmatch "VERIFY_OK") {
    Write-Host "ERROR: Management PL verification failed." -ForegroundColor Red
    exit 1
}
$verifyWfOut = & $venvPython $verifyWf 2>&1 | Out-String
$verifyWfExit = $LASTEXITCODE
Write-Host $verifyWfOut
if ($verifyWfExit -ne 0 -or $verifyWfOut -notmatch "VERIFY_WORKFORCE_OK") {
    Write-Host "ERROR: Workforce route verification failed." -ForegroundColor Red
    exit 1
}
$ErrorActionPreference = $prevEap
Write-Host "  Code verification OK." -ForegroundColor Green
Write-Host ""

# Step 6: Start API in new window
Write-Host "[6/7] Starting API in a new BACKEND terminal..." -ForegroundColor Yellow
$startApi = Join-Path $Backend "start-api.ps1"
Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", $startApi
)

Write-Host "  Waiting for API build $ExpectedBuild (up to 3 min)..." -ForegroundColor Yellow
$ready = $false
for ($i = 1; $i -le 90; $i++) {
    Start-Sleep -Seconds 2
    $portUp = $false
    try {
        $portUp = (Test-NetConnection -ComputerName 127.0.0.1 -Port 8000 -WarningAction SilentlyContinue).TcpTestSucceeded
    } catch {
        $portUp = $false
    }
    if ($portUp) {
        try {
            $ping = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/management-pl/ping" -TimeoutSec 8
            if ($ping.build -eq $ExpectedBuild) {
                Write-Host "  API ready: build=$($ping.build)" -ForegroundColor Green
                $ready = $true
                break
            }
            Write-Host "  Attempt $i : stale build=$($ping.build) (need $ExpectedBuild) - close old BACKEND windows and retry" -ForegroundColor Yellow
        } catch {
            Write-Host "  Attempt $i : port open, waiting for HTTP..."
        }
    } else {
        Write-Host "  Attempt $i : port 8000 not listening yet (check BACKEND window)..."
    }
}

if (-not $ready) {
    Write-Host ""
    Write-Host "ERROR: API did not become ready with build $ExpectedBuild." -ForegroundColor Red
    Write-Host "1. Close ALL PowerShell windows titled BACKEND / uvicorn." -ForegroundColor Red
    Write-Host "2. Run this script again." -ForegroundColor Red
    Write-Host "3. Or start manually:" -ForegroundColor Red
    Write-Host "     cd $Backend" -ForegroundColor Red
    Write-Host "     powershell -ExecutionPolicy Bypass -File .\restart-api.ps1" -ForegroundColor Red
    exit 1
}

# Step 7: Verify workforce + health
Write-Host "[7/7] Verifying workforce endpoints..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 8
} catch {
    Write-Host "ERROR: /health failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
if ($health.build -ne $ExpectedBuild) {
    Write-Host "ERROR: /health build=$($health.build) expected $ExpectedBuild" -ForegroundColor Red
    exit 1
}
if ($health.workforce_build -ne $ExpectedWorkforceBuild) {
    Write-Host "ERROR: /health workforce_build=$($health.workforce_build) expected $ExpectedWorkforceBuild" -ForegroundColor Red
    exit 1
}
try {
    $wfPing = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/workforce/ping" -TimeoutSec 8
} catch {
    Write-Host "ERROR: /workforce/ping failed: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message -ForegroundColor Red }
    exit 1
}
if ($wfPing.build -ne $ExpectedWorkforceBuild) {
    Write-Host "ERROR: workforce ping build=$($wfPing.build)" -ForegroundColor Red
    exit 1
}
Write-Host "  /health => build=$($health.build) workforce=$($health.workforce)" -ForegroundColor Green
Write-Host "  /workforce/ping => build=$($wfPing.build)" -ForegroundColor Green

Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", "Set-Location '$Frontend'; npm.cmd run dev"
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " SUCCESS - stack is starting" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "1. Keep the BACKEND window open (uvicorn on port 8000)." -ForegroundColor White
Write-Host "2. Wait for the FRONTEND window to say Ready, then open:" -ForegroundColor White
Write-Host "   http://localhost:3002" -ForegroundColor Cyan
Write-Host ""
Write-Host "Confirm in browser:" -ForegroundColor White
Write-Host "   http://127.0.0.1:8000/health" -ForegroundColor Cyan
Write-Host "   (build: $ExpectedBuild, workforce_build: $ExpectedWorkforceBuild)" -ForegroundColor White
Write-Host "   http://127.0.0.1:8000/api/v1/workforce/ping" -ForegroundColor Cyan
Write-Host ""
Write-Host "API docs: http://127.0.0.1:8000/docs" -ForegroundColor DarkGray
Write-Host ""
