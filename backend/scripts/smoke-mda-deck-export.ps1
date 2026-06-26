# MD&A deck export smoke test + optional download (production Railway API)
#
# Run from anywhere in PowerShell:
#   powershell -ExecutionPolicy Bypass -File "C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence\backend\scripts\smoke-mda-deck-export.ps1"
#
# Download the full PPTX after smoke passes:
#   powershell -ExecutionPolicy Bypass -File "...\smoke-mda-deck-export.ps1" -Download

param(
    [string]$OrgId = "8571e520-0687-4516-bdee-379f37c58c1f",
    [string]$ClosePeriod = "2026-06",
    [string]$ApiBase = "https://sfi-api-production.up.railway.app",
    [switch]$Download
)

$ErrorActionPreference = "Stop"
$year = $ClosePeriod.Substring(0, 4)
$timeoutSec = 600

function Write-Step($n, $msg) {
    Write-Host ""
    Write-Host "=== [$n] $msg ===" -ForegroundColor Cyan
}

function Show-HttpError($err) {
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
    Write-Host "   Error: $($err.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "SMPL MD&A deck export test" -ForegroundColor White
Write-Host "  Org:     $OrgId"
Write-Host "  Period:  $ClosePeriod"
Write-Host "  API:     $ApiBase"
Write-Host "  Timeout: ${timeoutSec}s per request"

Write-Step "1" "Export ping"
try {
    $ping = Invoke-RestMethod -Uri "$ApiBase/api/v1/export/ping" -TimeoutSec 30
    Write-Host "   status: $($ping.status)" -ForegroundColor Green
    Write-Host "   ai_configured: $($ping.ai_configured)"
    Write-Host "   llm_provider: $($ping.llm_provider)"
} catch {
    Show-HttpError $_
    exit 1
}

Write-Step "2" "MD&A deck smoke (builds deck in memory — can take 2-4 min)"
$smokeUri = "$ApiBase/api/v1/export/mda-deck-smoke?organization_id=$OrgId&as_of_period=$ClosePeriod"
try {
    $smoke = Invoke-RestMethod -Uri $smokeUri -TimeoutSec $timeoutSec
    Write-Host "   status: $($smoke.status)" -ForegroundColor Green
    Write-Host "   source: $($smoke.source)"
    Write-Host "   deck_kind: $($smoke.deck_kind)"
    Write-Host "   bytes: $($smoke.bytes)"
    Write-Host "   validation: $($smoke.validation)"
    Write-Host "   period: $($smoke.period)"
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

Write-Step "3" "Download MD&A deck PPTX (can take 3-8 min with AI commentary)"
$params = @{
    organization_id = $OrgId
    scenario = "Combined"
    start_period = "$year-01"
    end_period = "$year-12"
    as_of_period = $ClosePeriod
    include_ai_commentary = "true"
    include_commentary = "true"
    include_appendix = "true"
    include_validation = "true"
    block_on_failure = "false"
    package_mode = "full_board"
}
$query = ($params.GetEnumerator() | ForEach-Object { "{0}={1}" -f $_.Key, [uri]::EscapeDataString([string]$_.Value) }) -join "&"
$downloadUri = "$ApiBase/api/v1/export/mda-deck.pptx?$query"
$outFile = Join-Path $env:USERPROFILE "Downloads" "mda_deck_$ClosePeriod.pptx"

try {
    Invoke-WebRequest -Uri $downloadUri -OutFile $outFile -TimeoutSec $timeoutSec -UseBasicParsing | Out-Null
    $size = (Get-Item $outFile).Length
    Write-Host "   Saved: $outFile ($size bytes)" -ForegroundColor Green
} catch {
    Show-HttpError $_
    exit 1
}

Write-Host ""
Write-Host "Done." -ForegroundColor Green
