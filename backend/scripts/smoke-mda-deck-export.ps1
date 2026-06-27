# MDA deck export smoke + local iteration (read-only Neon — no DB schema changes)
#
# === Railway smoke (no DATABASE_URL needed) ===
# Instant check (~5s after deploy):
#   powershell -ExecutionPolicy Bypass -File "...\smoke-mda-deck-export.ps1"
#
# === Local full pipeline (same Neon as prod, read-only) ===
# One-time in PowerShell — paste Railway DATABASE_URL (Variables tab):
#   $env:DATABASE_URL = "postgresql://..."
# Then:
#   powershell -ExecutionPolicy Bypass -File "...\smoke-mda-deck-export.ps1" -LocalSmoke
#   powershell -ExecutionPolicy Bypass -File "...\smoke-mda-deck-export.ps1" -LocalExport

param(
    [string]$OrgId = "8571e520-0687-4516-bdee-379f37c58c1f",
    [string]$ClosePeriod = "2026-06",
    [string]$ApiBase = "https://sfi-api-production.up.railway.app",
    [switch]$LocalSmoke,
    [switch]$LocalExport,
    [switch]$NoAI
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Split-Path -Parent $scriptDir
$timeoutSec = 120

function Write-Step {
    param([string]$Number, [string]$Message)
    Write-Host ""
    Write-Host ("=== [{0}] {1} ===" -f $Number, $Message) -ForegroundColor Cyan
}

function Show-HttpError {
    param($err)
    Write-Host "   FAILED" -ForegroundColor Red
    if ($err.ErrorDetails.Message) {
        Write-Host $err.ErrorDetails.Message -ForegroundColor Yellow
    } elseif ($err.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($err.Exception.Response.GetResponseStream())
        Write-Host $reader.ReadToEnd() -ForegroundColor Yellow
    } else {
        Write-Host $err.Exception.Message -ForegroundColor Yellow
    }
}

function Normalize-DatabaseUrl {
    param([string]$Url)
    $u = $Url.Trim()
    if ($u.StartsWith("postgresql://")) {
        return "postgresql+psycopg://" + $u.Substring("postgresql://".Length)
    }
    if ($u.StartsWith("postgres://")) {
        return "postgresql+psycopg://" + $u.Substring("postgres://".Length)
    }
    return $u
}

function Import-DatabaseUrlFromEnvFiles {
    if ($env:DATABASE_URL) {
        $env:DATABASE_URL = Normalize-DatabaseUrl $env:DATABASE_URL
        return
    }
    foreach ($file in @(
            (Join-Path $backendRoot ".env"),
            (Join-Path $backendRoot "secrets.env"),
            (Join-Path $backendRoot ".env.local")
        )) {
        if (-not (Test-Path $file)) { continue }
        Get-Content $file | ForEach-Object {
            if ($_ -match '^\s*DATABASE_URL\s*=\s*(.+)\s*$') {
                $env:DATABASE_URL = Normalize-DatabaseUrl $matches[1].Trim().Trim('"').Trim("'")
            }
        }
        if ($env:DATABASE_URL) {
            Write-Host ("  Loaded DATABASE_URL from {0}" -f $file) -ForegroundColor DarkGray
            return
        }
    }
}

function Invoke-LocalPython {
    param([string[]]$PythonArgs)
    $python = Join-Path $backendRoot ".venv312\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        $python = Join-Path $backendRoot ".venv\Scripts\python.exe"
    }
    if (-not (Test-Path $python)) {
        Write-Host "   No backend venv. Create backend\.venv312 first." -ForegroundColor Red
        exit 1
    }
    Import-DatabaseUrlFromEnvFiles
    if (-not $env:DATABASE_URL) {
        Write-Host "   DATABASE_URL not set." -ForegroundColor Red
        Write-Host ""
        Write-Host "   1. Open https://railway.app -> sfi-api-production service" -ForegroundColor Yellow
        Write-Host "   2. Variables tab -> copy DATABASE_URL (full postgresql://... string)" -ForegroundColor Yellow
        Write-Host '   3. $env:DATABASE_URL = "postgresql://neondb_owner:PASSWORD@ep-....neon.tech/neondb?sslmode=require"' -ForegroundColor Yellow
        Write-Host "   4. Re-run this script" -ForegroundColor Yellow
        exit 1
    }
    if ($env:DATABASE_URL -match "paste-your-railway|your-railway-url|example\.com") {
        Write-Host "   DATABASE_URL is still a placeholder from the docs — paste the real Railway value." -ForegroundColor Red
        exit 1
    }
    $hostHint = ""
    if ($env:DATABASE_URL -match "@([^/?]+)") { $hostHint = $matches[1] }
    Write-Host ("   DB host: {0}" -f $(if ($hostHint) { $hostHint } else { "(unknown)" })) -ForegroundColor DarkGray
    Write-Host "   DB driver: psycopg v3" -ForegroundColor DarkGray
    if ($NoAI) { $env:MDA_USE_AI = "false" } else { $env:MDA_USE_AI = "true" }
    $env:MDA_CLOSE_PERIOD = $ClosePeriod
    Push-Location $backendRoot
    try {
        & $python @PythonArgs
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally {
        Pop-Location
    }
}

Write-Host "SMPL MDA deck smoke" -ForegroundColor White
Write-Host ("  Org:    {0}" -f $OrgId)
Write-Host ("  Period: {0}" -f $ClosePeriod)

if ($LocalSmoke) {
    Write-Step -Number "1" -Message "Local pipeline smoke (read-only Neon, no schema changes)"
    Invoke-LocalPython @((Join-Path $backendRoot "scripts\local_mda_smoke.py"))
    Write-Host "Done." -ForegroundColor Green
    exit 0
}

if ($LocalExport) {
    Write-Step -Number "1" -Message "Local MDA deck export (read-only Neon, writes PPTX only)"
    Invoke-LocalPython @((Join-Path $backendRoot "scripts\export_mda_deck_local.py"))
    Write-Host "Done." -ForegroundColor Green
    exit 0
}

Write-Host ("  API:    {0}" -f $ApiBase)

Write-Step -Number "1" -Message "Export ping"
try {
    $ping = Invoke-RestMethod -Uri ("{0}/api/v1/export/ping" -f $ApiBase) -TimeoutSec 30
    Write-Host ("   status: {0}" -f $ping.status) -ForegroundColor Green
    Write-Host ("   api_build: {0}" -f $ping.api_build)
    Write-Host ("   ai_configured: {0}" -f $ping.ai_configured)
    if ($ping.api_build -ne "mda-smoke-v5") {
        Write-Host "   WARNING: Railway may not have latest deploy yet (expected api_build=mda-smoke-v5)" -ForegroundColor Yellow
        Write-Host "   Wait 2-3 min after push, then re-run." -ForegroundColor Yellow
    }
} catch {
    Show-HttpError $_
    exit 1
}

Write-Step -Number "2" -Message "MDA deck ping smoke (org check only, ~5s)"
$smokeUri = "{0}/api/v1/export/mda-deck-smoke?organization_id={1}&as_of_period={2}&level=ping" -f $ApiBase, $OrgId, $ClosePeriod
try {
    $smoke = Invoke-RestMethod -Uri $smokeUri -TimeoutSec $timeoutSec
    Write-Host ("   status: {0}" -f $smoke.status) -ForegroundColor Green
    Write-Host ("   level: {0}" -f $smoke.level)
    Write-Host ("   organization_name: {0}" -f $smoke.organization_name)
    Write-Host ("   period: {0}" -f $smoke.period)
} catch {
    Show-HttpError $_
    exit 1
}

Write-Host ""
Write-Host "Railway smoke passed." -ForegroundColor Green
Write-Host ""
Write-Host "Full deck build (read-only Neon, no DB changes):" -ForegroundColor Cyan
Write-Host '  $env:DATABASE_URL = "postgresql://..."   # from Railway Variables' -ForegroundColor Yellow
Write-Host ('  powershell -ExecutionPolicy Bypass -File "{0}" -LocalSmoke' -f $MyInvocation.MyCommand.Path) -ForegroundColor Yellow
Write-Host ('  powershell -ExecutionPolicy Bypass -File "{0}" -LocalExport' -f $MyInvocation.MyCommand.Path) -ForegroundColor Yellow
