# Copy BILLING_INTERNAL_API_KEY from Vercel Production to Preview (gl-5b session-sync).
# Does NOT deploy - uses safe env pull (see scripts/lib/Invoke-VercelEnv.ps1).
#
# Usage:
#   .\scripts\set-vercel-preview-billing-from-production.ps1
#   .\scripts\set-vercel-preview-billing-from-production.ps1 -BillingKey "your-key"

param(
    [string]$BillingKey = "",
    [string]$Scope = "smplai",
    [string]$Project = "smpl-financial-intelligence"
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path $PSScriptRoot -Parent
$frontendDir = Join-Path $repoRoot "frontend"
. (Join-Path $PSScriptRoot "lib\Invoke-VercelEnv.ps1")

Write-Host ""
Write-Host "=== Copy BILLING_INTERNAL_API_KEY: Production -> Preview ===" -ForegroundColor Cyan
Write-Host ""

if (-not $BillingKey) {
    $localProd = Join-Path $frontendDir ".env.vercel-production.local"
    $BillingKey = Get-EnvFileValue -FilePath $localProd -Key "BILLING_INTERNAL_API_KEY"
    if ($BillingKey) {
        Write-Host "Found key in .env.vercel-production.local" -ForegroundColor DarkGray
    }
}

if (-not $BillingKey) {
    $prodEnvFile = Join-Path $env:TEMP "sfi-billing-prod-$([guid]::NewGuid().ToString('N')).env"
    try {
        Write-Host "Pulling Production env from Vercel (safe env pull, not deploy)..." -ForegroundColor DarkGray
        Invoke-VercelEnvPull -FrontendDir $frontendDir -OutFile $prodEnvFile -Environment "production" -Scope $Scope -Project $Project | Out-Null
        $BillingKey = Get-EnvFileValue -FilePath $prodEnvFile -Key "BILLING_INTERNAL_API_KEY"
    }
    catch {
        Write-Host "WARN: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    finally {
        Remove-Item -LiteralPath $prodEnvFile -Force -ErrorAction SilentlyContinue
    }
}

if (-not $BillingKey) {
    Write-Host ""
    Write-Host "Could not read BILLING_INTERNAL_API_KEY automatically." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Option A - pass the key (same as Vercel Production + Railway sfi-api-staging):" -ForegroundColor White
    Write-Host '  .\scripts\set-vercel-preview-billing-from-production.ps1 -BillingKey "YOUR_KEY"' -ForegroundColor White
    Write-Host ""
    Write-Host "Option B - remove the key from Railway staging (session-sync works without it):" -ForegroundColor White
    Write-Host "  Railway -> sfi-api-staging -> Variables -> delete BILLING_INTERNAL_API_KEY -> redeploy API" -ForegroundColor White
    Write-Host ""
    Write-Host "Option C - Vercel dashboard manually:" -ForegroundColor White
    Write-Host "  Copy BILLING_INTERNAL_API_KEY from Production -> add to Preview" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host "Setting BILLING_INTERNAL_API_KEY on Preview..." -ForegroundColor DarkGray
try {
    Set-VercelPreviewEnvValue -FrontendDir $frontendDir -Name "BILLING_INTERNAL_API_KEY" -Value $BillingKey -Scope $Scope -Project $Project | Out-Null
    Write-Host "OK: BILLING_INTERNAL_API_KEY set on Preview." -ForegroundColor Green
    Write-Host ""
    Write-Host "Next:" -ForegroundColor Yellow
    Write-Host "  1. Railway sfi-api-staging must use the SAME key (or remove key on both)" -ForegroundColor White
    Write-Host "  2. Redeploy Preview from gl-5b-sandbox (do not run bare npx vercel from frontend/)" -ForegroundColor White
    Write-Host "  3. Incognito -> NEW magic link on the redeployed Visit URL" -ForegroundColor White
    Write-Host "  4. Open /api/debug/preview-workspace while logged in" -ForegroundColor White
    Write-Host ""
}
catch {
    Write-Host "FAIL: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
