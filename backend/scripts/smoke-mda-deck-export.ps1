# MDA deck export smoke test + optional download (production Railway API)
#
# Quick smoke (default, ~30s):
#   powershell -ExecutionPolicy Bypass -File "C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence\backend\scripts\smoke-mda-deck-export.ps1"
#
# Full render smoke (slow, may 502 on Railway):
#   powershell -ExecutionPolicy Bypass -File "...\smoke-mda-deck-export.ps1" -FullRender
#
# Download via Railway (may 502 if render takes too long):
#   powershell -ExecutionPolicy Bypass -File "...\smoke-mda-deck-export.ps1" -Download
#
# Download locally (recommended - no HTTP timeout):
#   powershell -ExecutionPolicy Bypass -File "...\smoke-mda-deck-export.ps1" -LocalExport

param(
    [string]$OrgId = "8571e520-0687-4516-bdee-379f37c58c1f",
    [string]$ClosePeriod = "2026-06",
    [string]$ApiBase = "https://sfi-api-production.up.railway.app",
    [switch]$FullRender,
    [switch]$Download,
    [switch]$LocalExport,
    [switch]$NoAI
)

$ErrorActionPreference = "Stop"
$year = $ClosePeriod.Substring(0, 4)
$timeoutSec = 600
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Split-Path -Parent $scriptDir
$repoRoot = Split-Path -Parent $backendRoot

function Write-Step {
    param([string]$Number, [string]$Message)
    Write-Host ""
    Write-Host ("=== [{0}] {1} ===" -f $Number, $Message) -ForegroundColor Cyan
}

function Show-HttpError {
    param($err)
    Write-Host "   FAILED" -ForegroundColor Red
    if ($err.ErrorDetails.Message) {
        Write-Host "   Server said:" -ForegroundColor Yellow
        Write-Host $err.ErrorDetails.Message
    } elseif ($err.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($err.Exception.Response.GetResponseStream())
        $body = $reader.ReadToEnd()
        if ($body) {
            Write-Host "   Server said:" -ForegroundColor Yellow
            Write-Host $body
        }
    } else {
        Write-Host ("   Error: {0}" -f $err.Exception.Message) -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "   If you see 502, Railway timed out before the deck finished rendering." -ForegroundColor Yellow
    Write-Host "   Use quick smoke (default) or -LocalExport to build on your machine." -ForegroundColor Yellow
}

Write-Host "SMPL MDA deck export test" -ForegroundColor White
Write-Host ("  Org:     {0}" -f $OrgId)
Write-Host ("  Period:  {0}" -f $ClosePeriod)
Write-Host ("  API:     {0}" -f $ApiBase)

if ($LocalExport) {
    Write-Step -Number "1" -Message "Local MDA deck export (no Railway HTTP timeout)"
    $python = Join-Path $backendRoot ".venv312\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        $python = Join-Path $backendRoot ".venv\Scripts\python.exe"
    }
    if (-not (Test-Path $python)) {
        Write-Host "   No backend venv found. Create .venv312 under backend first." -ForegroundColor Red
        exit 1
    }
    if (-not $env:DATABASE_URL) {
        Write-Host "   DATABASE_URL is not set in this PowerShell session." -ForegroundColor Red
        Write-Host '   Example: $env:DATABASE_URL = "postgresql://..."' -ForegroundColor Yellow
        exit 1
    }
    if ($NoAI) { $env:MDA_USE_AI = "false" } else { $env:MDA_USE_AI = "true" }
    $env:MDA_CLOSE_PERIOD = $ClosePeriod
    Push-Location $backendRoot
    try {
        & $python (Join-Path $backendRoot "scripts\export_mda_deck_local.py")
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally {
        Pop-Location
    }
    Write-Host ""
    Write-Host "Done." -ForegroundColor Green
    exit 0
}

Write-Host ("  Timeout: {0}s per request" -f $timeoutSec)

Write-Step -Number "1" -Message "Export ping"
try {
    $pingUri = "{0}/api/v1/export/ping" -f $ApiBase
    $ping = Invoke-RestMethod -Uri $pingUri -TimeoutSec 30
    Write-Host ("   status: {0}" -f $ping.status) -ForegroundColor Green
    Write-Host ("   ai_configured: {0}" -f $ping.ai_configured)
    Write-Host ("   llm_provider: {0}" -f $ping.llm_provider)
} catch {
    Show-HttpError $_
    exit 1
}

if ($FullRender) {
    $smokeLabel = "MDA deck FULL smoke (renders PPTX - can take 3+ min, may 502)"
    $renderFlag = "true"
} else {
    $smokeLabel = "MDA deck quick smoke (assembles slides only - ~30s)"
    $renderFlag = "false"
}
Write-Step -Number "2" -Message $smokeLabel
$smokeUri = "{0}/api/v1/export/mda-deck-smoke?organization_id={1}&as_of_period={2}&render={3}" -f $ApiBase, $OrgId, $ClosePeriod, $renderFlag
try {
    $smoke = Invoke-RestMethod -Uri $smokeUri -TimeoutSec $timeoutSec
    Write-Host ("   status: {0}" -f $smoke.status) -ForegroundColor Green
    Write-Host ("   mode: {0}" -f $smoke.mode)
    Write-Host ("   source: {0}" -f $smoke.source)
    Write-Host ("   deck_kind: {0}" -f $smoke.deck_kind)
    Write-Host ("   slide_count: {0}" -f $smoke.slide_count)
    if ($smoke.bytes) { Write-Host ("   bytes: {0}" -f $smoke.bytes) }
    Write-Host ("   validation: {0}" -f $smoke.validation)
    Write-Host ("   period: {0}" -f $smoke.period)
} catch {
    Show-HttpError $_
    exit 1
}

if (-not $Download) {
    Write-Host ""
    Write-Host "Smoke passed." -ForegroundColor Green
    Write-Host "  Full render smoke: add -FullRender" -ForegroundColor Yellow
    Write-Host "  Download via Railway: add -Download (may 502 on long renders)" -ForegroundColor Yellow
    Write-Host "  Download locally (recommended): add -LocalExport" -ForegroundColor Yellow
    exit 0
}

Write-Step -Number "3" -Message "Download MDA deck PPTX from Railway (may 502 if slow)"
$aiFlag = if ($NoAI) { "false" } else { "true" }
$params = @{
    organization_id       = $OrgId
    scenario              = "Combined"
    start_period          = "{0}-01" -f $year
    end_period            = "{0}-12" -f $year
    as_of_period          = $ClosePeriod
    include_ai_commentary = $aiFlag
    include_commentary    = "true"
    include_appendix      = "true"
    include_validation    = "true"
    block_on_failure      = "false"
    package_mode          = "full_board"
}
$queryParts = @()
foreach ($entry in $params.GetEnumerator()) {
    $queryParts += ("{0}={1}" -f $entry.Key, [uri]::EscapeDataString([string]$entry.Value))
}
$query = $queryParts -join [char]38
$downloadUri = "{0}/api/v1/export/mda-deck.pptx?{1}" -f $ApiBase, $query
$outFile = Join-Path -Path $env:USERPROFILE -ChildPath ("Downloads\mda_deck_{0}.pptx" -f $ClosePeriod)

try {
    Invoke-WebRequest -Uri $downloadUri -OutFile $outFile -TimeoutSec $timeoutSec -UseBasicParsing | Out-Null
    $size = (Get-Item -LiteralPath $outFile).Length
    Write-Host ("   Saved: {0} ({1} bytes)" -f $outFile, $size) -ForegroundColor Green
} catch {
    Show-HttpError $_
    Write-Host "   Try: ...\smoke-mda-deck-export.ps1 -LocalExport" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Done." -ForegroundColor Green
