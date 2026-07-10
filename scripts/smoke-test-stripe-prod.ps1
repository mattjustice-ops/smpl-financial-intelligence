# Smoke test Stripe billing on production (gl-4).
#
# Usage:
#   .\scripts\smoke-test-stripe-prod.ps1
#   .\scripts\smoke-test-stripe-prod.ps1 -FrontendUrl "https://www.smpl-ai.com"

param(
    [string]$FrontendUrl = "https://www.smpl-ai.com",
    [string]$ApiBase = "https://sfi-api-production.up.railway.app"
)

$ErrorActionPreference = "Stop"
$frontend = $FrontendUrl.TrimEnd("/")
$api = $ApiBase.TrimEnd("/")

Write-Host ""
Write-Host "=== Stripe production smoke (gl-4) ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "1. Webhook endpoint (GET sanity)..." -ForegroundColor Yellow
$webhookUrl = "$frontend/api/stripe/webhook"
try {
    $webhook = Invoke-RestMethod -Uri $webhookUrl -Method Get -TimeoutSec 30
    if ($webhook.ok -eq $true) {
        Write-Host "   OK: $webhookUrl" -ForegroundColor Green
        Write-Host "   $($webhook.message)" -ForegroundColor DarkGray
    } else {
        Write-Host "   Unexpected response from webhook URL" -ForegroundColor Red
    }
} catch {
    Write-Host "   FAIL: $webhookUrl - $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "2. Board config (backend URL)..." -ForegroundColor Yellow
try {
    $cfg = Invoke-RestMethod -Uri "$frontend/api/smpl/board-config" -TimeoutSec 30
    Write-Host "   longRunningApiBase=$($cfg.longRunningApiBase)" -ForegroundColor Green
} catch {
    Write-Host "   WARN: board-config failed - $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "3. Railway health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$api/health" -TimeoutSec 30
    Write-Host "   OK: $($health.status) build=$($health.build)" -ForegroundColor Green
} catch {
    Write-Host "   FAIL: Railway /health - $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "4. Stripe catalog (local live key)..." -ForegroundColor Yellow
$verifyScript = Join-Path $PSScriptRoot "verify-stripe-catalog.ps1"
if (Test-Path $verifyScript) {
    & $verifyScript
} else {
    Write-Host "   SKIP: verify-stripe-catalog.ps1 not found" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Manual steps to finish gl-4:" -ForegroundColor Cyan
Write-Host "  - Stripe Dashboard -> Webhooks -> confirm live endpoint deliveries return 200"
Write-Host "  - Run one live checkout (contract) and confirm billing_subscriptions row in Neon"
Write-Host "  - Mark gl-4 done on /progress"
Write-Host ""
