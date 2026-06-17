# gl-5: verify Railway staging API (+ optional Vercel Preview + DB connectivity).
#
# Usage:
#   .\scripts\verify-staging-stack.ps1
#   .\scripts\verify-staging-stack.ps1 -ApiBase "https://sfi-api-staging-xxxx.up.railway.app"

param(
    [string]$ApiBase = "",
    [string]$DatabaseUrl = "",
    [string]$FrontendUrl = "",
    [switch]$SkipDb,
    [switch]$SkipFrontend,
    [switch]$AllowProduction
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\Resolve-StagingConfig.ps1")

$repoRoot = Split-Path $PSScriptRoot -Parent
$config = Resolve-StagingConfig `
    -ApiBase $ApiBase `
    -DatabaseUrl $DatabaseUrl `
    -FrontendUrl $FrontendUrl `
    -RepoRoot $repoRoot `
    -AllowProduction:$AllowProduction

if (-not $config.ApiBase) {
    Write-StagingConfigHelp
    exit 1
}

if ($config.ApiBase.ProductionBlocked) {
    Write-Host ""
    Write-Host "ERROR: $($config.ApiBase.Url) is production API." -ForegroundColor Red
    Write-Host "Create a separate Railway staging service and save with save-staging-config.ps1" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

$apiUrl = $config.ApiBase.Url
$healthUrl = "$apiUrl/health"
$failures = 0

Write-Host ""
Write-Host "=== gl-5 staging stack verify ===" -ForegroundColor Cyan
Write-Host "API:  $apiUrl" -ForegroundColor DarkGray
Write-Host "from: $($config.ApiBase.Source)" -ForegroundColor DarkGray
Write-Host ""

Write-Host "1) GET $healthUrl" -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 45
    Write-Host "   status:             $($health.status)" -ForegroundColor Green
    Write-Host "   build:              $($health.build)"
    Write-Host "   plan_entitlements:  $($health.plan_entitlements)"
    Write-Host "   entitlements_build: $($health.entitlements_build)"
    if ($health.plan_entitlements -ne $true) {
        Write-Host "   WARN: plan_entitlements not true - deploy latest backend to staging" -ForegroundColor Yellow
        $failures++
    }
}
catch {
    Write-Host "   FAIL: $_" -ForegroundColor Red
    $failures++
}

if (-not $SkipDb) {
    $dbUrl = $null
    if ($config.DatabaseUrl) {
        $dbUrl = $config.DatabaseUrl.Url
        Write-Host ""
        Write-Host "2) GET $apiUrl/health/db" -ForegroundColor Cyan
        Write-Host "   DB from: $($config.DatabaseUrl.Source)" -ForegroundColor DarkGray
        try {
            $dbHealth = Invoke-RestMethod -Uri "$apiUrl/health/db" -Method Get -TimeoutSec 45
            if ($dbHealth.status -eq "ok") {
                Write-Host "   OK: $($dbHealth.database)" -ForegroundColor Green
            }
            else {
                Write-Host "   FAIL: unexpected response" -ForegroundColor Red
                $failures++
            }
        }
        catch {
            Write-Host "   FAIL: $_" -ForegroundColor Red
            $failures++
        }
    }
    else {
        Write-Host ""
        Write-Host "2) DB check skipped - no STAGING_DATABASE_URL configured" -ForegroundColor Yellow
    }
}

if (-not $SkipFrontend -and $config.FrontendUrl) {
    $front = $config.FrontendUrl.Url
    Write-Host ""
    Write-Host "3) GET $front/login" -ForegroundColor Cyan
    Write-Host "   from: $($config.FrontendUrl.Source)" -ForegroundColor DarkGray
    try {
        $resp = Invoke-WebRequest -Uri "$front/login" -Method Get -TimeoutSec 45 -UseBasicParsing
        if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400) {
            Write-Host "   OK: HTTP $($resp.StatusCode)" -ForegroundColor Green
        }
        else {
            Write-Host "   FAIL: HTTP $($resp.StatusCode)" -ForegroundColor Red
            $failures++
        }
    }
    catch {
        Write-Host "   FAIL: $_" -ForegroundColor Red
        $failures++
    }
}

Write-Host ""
if ($failures -eq 0) {
    Write-Host "OK: staging stack looks healthy." -ForegroundColor Green
    Write-Host "Next: .\scripts\smoke-test-staging.ps1" -ForegroundColor Yellow
    exit 0
}

Write-Host "FAILED: $failures check(s) - see docs/GO_LIVE_GL5_STAGING.md" -ForegroundColor Red
exit 1
