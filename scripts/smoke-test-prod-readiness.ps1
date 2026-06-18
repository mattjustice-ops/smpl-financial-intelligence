# Pre-outreach prod readiness smoke (gl-6).
#
# Usage:
#   .\scripts\smoke-test-prod-readiness.ps1

param(
    [string]$FrontendUrl = "https://smpl-financial-intelligence.vercel.app",
    [string]$ApiBase = "https://sfi-api-production.up.railway.app"
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path $PSScriptRoot -Parent

Write-Host ""
Write-Host "=== Prod readiness smoke (gl-6) ===" -ForegroundColor Cyan
Write-Host "Frontend: $FrontendUrl" -ForegroundColor DarkGray
Write-Host "API:      $ApiBase" -ForegroundColor DarkGray
Write-Host ""

$failed = 0

function Test-UrlJson {
    param([string]$Label, [string]$Url, [string]$ExpectField, [string]$ExpectValue)
    try {
        $res = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 30
        if ($res.StatusCode -ne 200) {
            Write-Host "FAIL: $Label ($($res.StatusCode))" -ForegroundColor Red
            $script:failed++
            return
        }
        $json = $res.Content | ConvertFrom-Json
        if ($ExpectField -and ($json.$ExpectField -ne $ExpectValue)) {
            Write-Host "FAIL: $Label ($ExpectField expected $ExpectValue, got $($json.$ExpectField))" -ForegroundColor Red
            $script:failed++
            return
        }
        Write-Host "OK:   $Label" -ForegroundColor Green
    }
    catch {
        Write-Host "FAIL: $Label - $($_.Exception.Message)" -ForegroundColor Red
        $script:failed++
    }
}

Test-UrlJson -Label "Railway /health" -Url "$ApiBase/health" -ExpectField "status" -ExpectValue "ok"
Test-UrlJson -Label "Railway /health/db" -Url "$ApiBase/health/db" -ExpectField "status" -ExpectValue "ok"
Test-UrlJson -Label "Vercel /health (proxy)" -Url "$FrontendUrl/health" -ExpectField "status" -ExpectValue "ok"

Write-Host ""
Write-Host "Plan entitlements (hosted API + Neon)..." -ForegroundColor Yellow
& (Join-Path $repoRoot "scripts\smoke-test-plan-entitlements.ps1") -ApiBase $ApiBase
if ($LASTEXITCODE -ne 0) { $failed++ }

Write-Host ""
if ($failed -eq 0) {
    Write-Host "OK: prod readiness smoke passed" -ForegroundColor Green
    Write-Host "Manual: incognito prod /login -> magic link -> SMPL Demo Co on /app" -ForegroundColor DarkGray
    exit 0
}

Write-Host "FAIL: $failed check(s) failed - see docs/GO_LIVE_GL6_MONITORING.md" -ForegroundColor Red
exit 1
