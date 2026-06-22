# Build, optional Neon warehouse load, and push to Vercel (production deploy).
#
# Usage:
#   .\scripts\deploy-prod-live.ps1                    # build only
#   .\scripts\deploy-prod-live.ps1 -CommitPush        # build + git push -> Vercel
#   .\scripts\deploy-prod-live.ps1 -LoadWarehouse     # load Neon CSVs then build
#   .\scripts\deploy-prod-live.ps1 -CommitPush -LoadWarehouse

param(
    [switch]$CommitPush,
    [switch]$LoadWarehouse,
    [string]$CommitMessage = "Wire board to live warehouse and backend Claude APIs for prod deploy"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent

Write-Host ""
Write-Host "=== SMPL production deploy ===" -ForegroundColor Cyan
Write-Host ""

if ($LoadWarehouse) {
    Write-Host "Loading Neon warehouse..." -ForegroundColor Yellow
    & (Join-Path $repoRoot "scripts\load-prod-warehouse.ps1")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host ""
}

$deployScript = Join-Path $repoRoot "scripts\deploy-frontend-vercel.ps1"
if ($CommitPush) {
    & $deployScript -CommitPush -CommitMessage $CommitMessage
} else {
    & $deployScript -CommitMessage $CommitMessage
}

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "=== Post-deploy checklist ===" -ForegroundColor Cyan
Write-Host "  1. Railway DATABASE_URL = same Neon branch as warehouse load" -ForegroundColor White
Write-Host "  2. Vercel SFI_BACKEND_URL -> production Railway API" -ForegroundColor White
Write-Host "  3. Railway ANTHROPIC_API_KEY for commentary + exports" -ForegroundColor White
Write-Host "     .\scripts\set-railway-anthropic-keys.ps1 -SkipSandbox" -ForegroundColor DarkGray
Write-Host "  4. Redeploy Railway + Vercel if env vars changed" -ForegroundColor White
Write-Host "  5. Sign in -> /app/board -> confirm Live warehouse status" -ForegroundColor White
Write-Host ""
Write-Host "Full guide: docs/GO_LIVE_PROD_DEPLOY.md" -ForegroundColor DarkGray
Write-Host ""
