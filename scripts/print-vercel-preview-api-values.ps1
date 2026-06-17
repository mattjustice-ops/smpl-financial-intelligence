# Print Preview API env values for Vercel dashboard (no CLI required).
#
# Usage:
#   .\scripts\print-vercel-preview-api-values.ps1

param(
    [string]$StagingApi = "https://sfi-api-staging-production.up.railway.app"
)

$url = $StagingApi.Trim().TrimEnd("/")

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  FIX: Preview -> sandbox API (dashboard)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Your debug JSON showed backend_host = sfi-api-production (WRONG)." -ForegroundColor Yellow
Write-Host "Preview (sandbox) must use the sandbox API or you get Customer Corp." -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Open:" -ForegroundColor White
Write-Host "   https://vercel.com/smplai/smpl-financial-intelligence/settings/environment-variables" -ForegroundColor DarkGray
Write-Host ""
Write-Host "2. For EACH variable below, click the row (or Add New):" -ForegroundColor White
Write-Host "   - Name: as shown" -ForegroundColor DarkGray
Write-Host "   - Value: sandbox API URL (below)" -ForegroundColor DarkGray
Write-Host "   - Environments: check PREVIEW only (leave Production unchanged)" -ForegroundColor DarkGray
Write-Host "   - If Preview already has the production URL, Edit -> change Preview value" -ForegroundColor DarkGray
Write-Host ""
Write-Host "   SFI_BACKEND_URL" -ForegroundColor Green
Write-Host "   $url" -ForegroundColor White
Write-Host ""
Write-Host "   NEXT_PUBLIC_API_URL" -ForegroundColor Green
Write-Host "   $url" -ForegroundColor White
Write-Host ""
Write-Host "3. Save both variables." -ForegroundColor White
Write-Host ""
Write-Host "4. Redeploy Preview from GitHub (NOT npx vercel):" -ForegroundColor White
Write-Host "   git push origin gl-5b-sandbox" -ForegroundColor DarkGray
Write-Host "   OR Vercel -> Deployments -> gl-5b-sandbox -> Redeploy" -ForegroundColor DarkGray
Write-Host ""
Write-Host "5. Incognito -> NEW magic link on the new Visit URL" -ForegroundColor White
Write-Host ""
Write-Host "6. Confirm (logged in):" -ForegroundColor White
Write-Host "   /api/debug/preview-workspace" -ForegroundColor DarkGray
Write-Host "   backend_host = sfi-api-staging-production.up.railway.app" -ForegroundColor DarkGray
Write-Host "   sync_workspace = 8571e520-0687-4516-bdee-379f37c58c1f" -ForegroundColor DarkGray
Write-Host ""
