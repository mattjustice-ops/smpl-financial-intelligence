# MDA deck export smoke + local iteration (read-only Neon, no DB schema changes)
#
# Local export (uses backend\.env DATABASE_URL if set):
#   Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
#   powershell -ExecutionPolicy Bypass -File "...\smoke-mda-deck-export.ps1" -LocalExport
#
# Railway smoke only (no DATABASE_URL):
#   powershell -ExecutionPolicy Bypass -File "...\smoke-mda-deck-export.ps1"

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
$amp = [char]38

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

function Test-PlaceholderDatabaseUrl {
    param([string]$Url)
    $lower = $Url.ToLower()
    $bad = @(
        "paste-your-railway",
        "your-railway-url",
        "your_password",
        "ep-xxxxx",
        "example.com",
        "neondb_owner:password@"
    )
    foreach ($token in $bad) {
        if ($lower.Contains($token)) { return $true }
    }
    return $false
}

function Normalize-DatabaseUrl {
    param([string]$Url)
    $u = $Url.Trim().Trim('"').Trim("'")
    if ($u.StartsWith("postgresql://")) {
        return "postgresql+psycopg://" + $u.Substring("postgresql://".Length)
    }
    if ($u.StartsWith("postgres://")) {
        return "postgresql+psycopg://" + $u.Substring("postgres://".Length)
    }
    return $u
}

function Get-DatabaseHostHint {
    param([string]$Url)
    $at = $Url.IndexOf("@")
    if ($at -lt 0) { return "(unknown host)" }
    $rest = $Url.Substring($at + 1)
    $slash = $rest.IndexOf("/")
    if ($slash -lt 0) { return $rest }
    return $rest.Substring(0, $slash)
}

function Import-DatabaseUrlFromEnvFiles {
    $placeholderInSession = $false
    if ($env:DATABASE_URL) {
        if (Test-PlaceholderDatabaseUrl $env:DATABASE_URL) {
            $placeholderInSession = $true
            Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
        } else {
            $env:DATABASE_URL = Normalize-DatabaseUrl $env:DATABASE_URL
            return
        }
    }
    foreach ($file in @(
            (Join-Path $backendRoot ".env"),
            (Join-Path $backendRoot "secrets.env"),
            (Join-Path $backendRoot ".env.local")
        )) {
        if (-not (Test-Path $file)) { continue }
        Get-Content $file | ForEach-Object {
            if ($_ -match '^\s*DATABASE_URL\s*=\s*(.+)\s*$') {
                $candidate = Normalize-DatabaseUrl $matches[1]
                if (-not (Test-PlaceholderDatabaseUrl $candidate)) {
                    $env:DATABASE_URL = $candidate
                }
            }
        }
        if ($env:DATABASE_URL) {
            Write-Host ("  Loaded DATABASE_URL from {0}" -f $file) -ForegroundColor DarkGray
            if ($placeholderInSession) {
                Write-Host "  (Ignored placeholder DATABASE_URL from your PowerShell session)" -ForegroundColor DarkGray
            }
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
        Write-Host "   DATABASE_URL not found." -ForegroundColor Red
        Write-Host ""
        Write-Host "   Option A (easiest): put DATABASE_URL in backend\.env" -ForegroundColor Yellow
        Write-Host "   Copy the full value from Railway -> sfi-api-production -> Variables -> DATABASE_URL" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "   Option B: paste the full copied Railway string (do not type YOUR_PASSWORD):" -ForegroundColor Yellow
        Write-Host '   $env:DATABASE_URL = "<paste entire Railway DATABASE_URL here>"' -ForegroundColor Yellow
        exit 1
    }
    if (Test-PlaceholderDatabaseUrl $env:DATABASE_URL) {
        Write-Host "   DATABASE_URL is still an example/placeholder, not your real Railway value." -ForegroundColor Red
        exit 1
    }
    $hostHint = Get-DatabaseHostHint $env:DATABASE_URL
    Write-Host ("   DB host: {0}" -f $hostHint) -ForegroundColor DarkGray
    Write-Host "   DB driver: psycopg v3" -ForegroundColor DarkGray
    if ($NoAI) {
        Write-Host "   Note: -NoAI is ignored. MDA deck uses Claude Prompt 5 full build." -ForegroundColor DarkGray
    }
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
    $pingUri = "{0}/api/v1/export/ping" -f $ApiBase
    $ping = Invoke-RestMethod -Uri $pingUri -TimeoutSec 30
    Write-Host ("   status: {0}" -f $ping.status) -ForegroundColor Green
    Write-Host ("   api_build: {0}" -f $ping.api_build)
    Write-Host ("   ai_configured: {0}" -f $ping.ai_configured)
    if ($ping.api_build -ne "mda-smoke-v5") {
        Write-Host "   WARNING: expected api_build=mda-smoke-v5 (wait for Railway deploy)" -ForegroundColor Yellow
    }
} catch {
    Show-HttpError $_
    exit 1
}

Write-Step -Number "2" -Message "MDA deck ping smoke (org check only, about 5s)"
$smokeUri = "{0}/api/v1/export/mda-deck-smoke?organization_id={1}{2}as_of_period={3}{2}level=ping" -f $ApiBase, $OrgId, $amp, $ClosePeriod
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
Write-Host "Local deck build (uses backend\.env DATABASE_URL):" -ForegroundColor Cyan
Write-Host "  Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue" -ForegroundColor Yellow
$localCmd = "powershell -ExecutionPolicy Bypass -File `"$($MyInvocation.MyCommand.Path)`" -LocalExport"
Write-Host "  $localCmd" -ForegroundColor Yellow
