# Verify billing_subscriptions + billing_events in production Neon (gl-4 checkout sign-off).
#
# Usage:
#   .\scripts\verify-stripe-billing-neon.ps1

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\Resolve-ProdDatabaseUrl.ps1")

$repoRoot = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $repoRoot "backend"
$python = Join-Path $backendDir ".venv312\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

Write-Host ""
Write-Host "=== Stripe billing rows in Neon (gl-4) ===" -ForegroundColor Cyan
Write-Host ""

$resolved = Resolve-ProdDatabaseUrl -RepoRoot $repoRoot
if (-not $resolved) {
    Write-ProdDatabaseUrlHelp
    exit 1
}

$dbUrl = $resolved.Url
if ($dbUrl -match "^postgresql://") {
    $dbUrl = $dbUrl -replace "^postgresql://", "postgresql+psycopg://"
}

Push-Location $backendDir
try {
    $env:DATABASE_URL = $dbUrl
    & $python (Join-Path $backendDir "scripts\list_billing_subscriptions.py")
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "gl-4 checkout sign-off:" -ForegroundColor Cyan
Write-Host "  After a live checkout, expect at least one billing_subscriptions row (status active or trialing)."
Write-Host "  billing_events should show checkout.session.completed with status processed."
Write-Host ""
