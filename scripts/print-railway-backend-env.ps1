# Print Railway backend env vars (manual dashboard paste).
#
# Usage:
#   .\scripts\print-railway-backend-env.ps1 -DatabaseUrl "postgresql://..."

param(
    [Parameter(Mandatory = $true)]
    [string]$DatabaseUrl,
    [string]$ProdFrontendUrl = "https://smpl-financial-intelligence.vercel.app"
)

function Convert-ToRailwayDatabaseUrl {
    param([string]$Url)
    $normalized = $Url.Trim().Trim('"').Trim("'")
    if ($normalized -match "^postgresql://") {
        $normalized = $normalized -replace "^postgresql://", "postgresql+psycopg://"
    }
    if ($normalized -match "^postgres://") {
        $normalized = $normalized -replace "^postgres://", "postgresql+psycopg://"
    }
    $normalized = $normalized -replace "[?&]channel_binding=require", ""
    $normalized = $normalized -replace "\?&", "?"
    $normalized = $normalized.TrimEnd("?").TrimEnd("&")
    return $normalized
}

$dbUrl = Convert-ToRailwayDatabaseUrl $DatabaseUrl
$cors = "$ProdFrontendUrl,http://localhost:3002,http://127.0.0.1:3002"

Write-Host ""
Write-Host "=== Paste into Railway -> backend service -> Variables ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Important: use Neon for DATABASE_URL until warehouse data is loaded on Railway Postgres." -ForegroundColor Yellow
Write-Host "           (Invites + session-sync already live on Neon from setup-prod-auth-db.ps1)" -ForegroundColor Yellow
Write-Host ""
Write-Host "DATABASE_URL" -ForegroundColor Green
Write-Host $dbUrl
Write-Host ""
Write-Host "API_CORS_ORIGINS" -ForegroundColor Green
Write-Host $cors
Write-Host ""
Write-Host "Optional later (match Vercel when billing webhooks are enabled):" -ForegroundColor DarkGray
Write-Host "BILLING_INTERNAL_API_KEY = same random secret on Vercel + Railway"
Write-Host ""
Write-Host "After deploy, copy the Railway public URL and set on Vercel Production:" -ForegroundColor Cyan
Write-Host "  SFI_BACKEND_URL=https://YOUR-SERVICE.up.railway.app"
Write-Host "  NEXT_PUBLIC_API_URL=https://YOUR-SERVICE.up.railway.app"
Write-Host ""
