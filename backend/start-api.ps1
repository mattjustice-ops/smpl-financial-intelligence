# Start the Financial Intelligence API using the Python inside this project's venv.
# Run from: backend\start-api.ps1

param(
    [switch]$Reload,
    [int]$Port = 8000
)

$ErrorActionPreference = "Continue"

Set-Location $PSScriptRoot

function Import-BackendSecrets {
    $secretsPath = Join-Path $PSScriptRoot "secrets.env"
    if (-not (Test-Path -LiteralPath $secretsPath)) { return }
    foreach ($line in Get-Content -LiteralPath $secretsPath) {
        if ($line -match '^\s*#\s*' -or $line -notmatch '\S') { continue }
        if ($line -match '^\s*OPENAI_API_KEY\s*=\s*(.+)\s*$') {
            $env:OPENAI_API_KEY = $Matches[1].Trim().Trim('"').Trim("'")
        }
        if ($line -match '^\s*OPENAI_MODEL\s*=\s*(.+)\s*$') {
            $env:OPENAI_MODEL = $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
}

Import-BackendSecrets

$venvPython = $null
foreach ($venvName in @(".venv312", ".venv")) {
    $candidate = Join-Path $PSScriptRoot "$venvName\Scripts\python.exe"
    if (Test-Path -LiteralPath $candidate) {
        $venvPython = $candidate
        break
    }
}

if (-not $venvPython) {
    Write-Host "ERROR: No venv found (.venv312 or .venv). Run: python -m venv .venv" -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "Python: $venvPython"

$listen = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listen) {
    $listenPid = ($listen | Select-Object -First 1).OwningProcess
    $alive = Get-Process -Id $listenPid -ErrorAction SilentlyContinue
    if ($alive) {
        Write-Host "ERROR: Port $Port is already in use by PID $listenPid ($($alive.ProcessName))." -ForegroundColor Red
        Write-Host "Run: powershell -ExecutionPolicy Bypass -File .\scripts\stop-api.ps1 -Port $Port" -ForegroundColor Yellow
        Read-Host "Press Enter to close"
        exit 1
    }
    Write-Host "WARN: Port $Port shows stale listener PID $listenPid (process gone)." -ForegroundColor Yellow
    Write-Host "Try another port: .\restart-api.ps1 -Port 8001" -ForegroundColor Yellow
    Read-Host "Press Enter to close"
    exit 2
}

Write-Host "Checking Excel export library (optional)..."
& $venvPython -c "import xlsxwriter; print('xlsxwriter OK')" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARN: xlsxwriter not installed (Excel export may fail). Continuing." -ForegroundColor Yellow
}

Write-Host "Checking OpenAI configuration..."
$openaiStatus = & $venvPython -c "from app.core.config import get_settings; s=get_settings(); print('yes' if s.openai_api_key else 'no')" 2>$null
if ($openaiStatus -eq "yes") {
    Write-Host "OpenAI: configured"
} else {
    Write-Host "OpenAI: NOT SET (optional for Management PL)" -ForegroundColor Yellow
}

Write-Host "Verifying Management PL routes..."
$verifyPy = Join-Path $PSScriptRoot "scripts\verify_mpl_routes.py"
& $venvPython $verifyPy 2>&1 | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Management PL verification failed." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "Verifying workforce routes..."
$verifyWf = Join-Path $PSScriptRoot "scripts\verify_workforce_routes.py"
& $venvPython $verifyWf 2>&1 | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Workforce route verification failed." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

$baseUrl = "http://127.0.0.1:$Port"
Write-Host ""
Write-Host "Starting API at $baseUrl"
Write-Host "Test: $baseUrl/api/v1/management-pl/ping"
Write-Host "Test: $baseUrl/api/v1/workforce/ping"
Write-Host "Test: $baseUrl/api/v1/workforce/plan-debug"
if ($Port -ne 8000) {
    Write-Host "NOTE: Frontend defaults to port 8000. Set both in frontend/.env.local:" -ForegroundColor Yellow
    Write-Host "  NEXT_PUBLIC_API_URL=http://127.0.0.1:$Port" -ForegroundColor Yellow
    Write-Host "  SFI_BACKEND_URL=http://127.0.0.1:$Port" -ForegroundColor Yellow
    Write-Host "Then restart Next.js (npm run dev)." -ForegroundColor Yellow
}
if ($Reload) {
    Write-Host "Mode: reload enabled (auto-restart on code changes)"
} else {
    Write-Host "Mode: stable (no reload). Use .\restart-api.ps1 -Reload for auto-reload."
}
Write-Host "Do not close this window."
Write-Host ""

$uvicornArgs = @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$Port")
if ($Reload) {
    $uvicornArgs += "--reload"
}

& $venvPython @uvicornArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: uvicorn exited with code $LASTEXITCODE" -ForegroundColor Red
    Read-Host "Press Enter to close"
}
