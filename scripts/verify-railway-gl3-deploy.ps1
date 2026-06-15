# Check whether Railway production has gl-3 plan entitlements deployed.
#
# Usage:
#   .\scripts\verify-railway-gl3-deploy.ps1
#   .\scripts\verify-railway-gl3-deploy.ps1 -ApiBase "https://sfi-api-production.up.railway.app"

param(
    [string]$ApiBase = "https://sfi-api-production.up.railway.app"
)

$ErrorActionPreference = "Stop"
$url = "$($ApiBase.TrimEnd('/'))/health"

Write-Host ""
Write-Host "Checking $url" -ForegroundColor Cyan

try {
    $health = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 30
} catch {
    Write-Host "ERROR: Could not reach API /health: $_" -ForegroundColor Red
    exit 1
}

$build = $health.build
$entitlementsBuild = $health.entitlements_build
$planEntitlements = $health.plan_entitlements

Write-Host "  build:              $build"
Write-Host "  plan_entitlements:  $planEntitlements"
Write-Host "  entitlements_build: $entitlementsBuild"
Write-Host ""

if ($planEntitlements -eq $true -and $entitlementsBuild) {
    Write-Host "OK: gl-3 backend is deployed on Railway." -ForegroundColor Green
    Write-Host "Re-run: .\scripts\smoke-test-plan-entitlements.ps1" -ForegroundColor Yellow
    exit 0
}

Write-Host "NOT DEPLOYED: Railway is still on pre-gl-3 backend." -ForegroundColor Red
Write-Host ""
Write-Host "Fix:" -ForegroundColor Yellow
Write-Host "  1. Commit and push gl-3 backend changes to the branch Railway tracks (usually main)"
Write-Host "  2. Railway dashboard -> sfi-api -> Deployments -> Redeploy (or wait for auto-deploy)"
Write-Host "  3. Re-run this script until entitlements_build appears"
Write-Host "  4. .\scripts\smoke-test-plan-entitlements.ps1"
Write-Host ""
exit 1
