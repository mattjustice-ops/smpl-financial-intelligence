# MDA deck export smoke test + optional download (production Railway API)
#
# Smoke test only:
#   powershell -ExecutionPolicy Bypass -File "C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence\backend\scripts\smoke-mda-deck-export.ps1"
#
# Smoke test + download PPTX:
#   powershell -ExecutionPolicy Bypass -File "C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence\backend\scripts\smoke-mda-deck-export.ps1" -Download

param(
    [string]$OrgId = "8571e520-0687-4516-bdee-379f37c58c1f",
    [string]$ClosePeriod = "2026-06",
    [string]$ApiBase = "https://sfi-api-production.up.railway.app",
    [switch]$Download
)

$ErrorActionPreference = "Stop"
$year = $ClosePeriod.Substring(0, 4)
$timeoutSec = 600

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
        return
    }
    if ($err.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($err.Exception.Response.GetResponseStream())
        $body = $reader.ReadToEnd()
        if ($body) {
            Write-Host "   Server said:" -ForegroundColor Yellow
            Write-Host $body
            return
        }
    }
    Write-Host ("   Error: {0}" -f $err.Exception.Message) -ForegroundColor Yellow
}

Write-Host "SMPL MDA deck export test" -ForegroundColor White
Write-Host ("  Org:     {0}" -f $OrgId)
Write-Host ("  Period:  {0}" -f $ClosePeriod)
Write-Host ("  API:     {0}" -f $ApiBase)
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

Write-Step -Number "2" -Message "MDA deck smoke (builds deck in memory - can take 2-4 min)"
$smokeUri = "{0}/api/v1/export/mda-deck-smoke?organization_id={1}&as_of_period={2}" -f $ApiBase, $OrgId, $ClosePeriod
try {
    $smoke = Invoke-RestMethod -Uri $smokeUri -TimeoutSec $timeoutSec
    Write-Host ("   status: {0}" -f $smoke.status) -ForegroundColor Green
    Write-Host ("   source: {0}" -f $smoke.source)
    Write-Host ("   deck_kind: {0}" -f $smoke.deck_kind)
    Write-Host ("   bytes: {0}" -f $smoke.bytes)
    Write-Host ("   validation: {0}" -f $smoke.validation)
    Write-Host ("   period: {0}" -f $smoke.period)
} catch {
    Show-HttpError $_
    exit 1
}

if (-not $Download) {
    Write-Host ""
    Write-Host "Smoke passed. To download the PPTX, re-run with -Download:" -ForegroundColor Green
    Write-Host '  powershell -ExecutionPolicy Bypass -File "...\backend\scripts\smoke-mda-deck-export.ps1" -Download' -ForegroundColor Yellow
    exit 0
}

Write-Step -Number "3" -Message "Download MDA deck PPTX (can take 3-8 min with AI commentary)"
$params = @{
    organization_id       = $OrgId
    scenario              = "Combined"
    start_period          = "{0}-01" -f $year
    end_period            = "{0}-12" -f $year
    as_of_period          = $ClosePeriod
    include_ai_commentary = "true"
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
$outFile = Join-Path -Path $env:USERPROFILE -ChildPath "Downloads\mda_deck_{0}.pptx" -f $ClosePeriod

try {
    Invoke-WebRequest -Uri $downloadUri -OutFile $outFile -TimeoutSec $timeoutSec -UseBasicParsing | Out-Null
    $size = (Get-Item -LiteralPath $outFile).Length
    Write-Host ("   Saved: {0} ({1} bytes)" -f $outFile, $size) -ForegroundColor Green
} catch {
    Show-HttpError $_
    exit 1
}

Write-Host ""
Write-Host "Done." -ForegroundColor Green
