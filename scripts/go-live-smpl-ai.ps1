# Go-live sequence: smpl-ai.com -> auth -> Neon warehouse -> local forecast promote test.
#
# Usage:
#   .\scripts\go-live-smpl-ai.ps1 -Step 1          # domain setup instructions + Vercel add
#   .\scripts\go-live-smpl-ai.ps1 -Step 2          # Resend test + EMAIL_FROM on Vercel
#   .\scripts\go-live-smpl-ai.ps1 -Step 3          # Neon warehouse load
#   .\scripts\go-live-smpl-ai.ps1 -Step 4          # local forecast promote checklist
#   .\scripts\go-live-smpl-ai.ps1 -Step all        # print full checklist

param(
    [ValidateSet("1", "2", "3", "4", "all")]
    [string]$Step = "all",
    [string]$DatabaseUrl = "",
    [string]$TestEmail = "mattjustice@smpl-ai.com"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent

function Show-Step1 {
    & (Join-Path $repoRoot "scripts\setup-smpl-ai-domain.ps1")
}

function Show-Step2 {
    Write-Host ""
    Write-Host "=== Step 2: Resend + auth on smpl-ai.com ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. Resend -> Domains -> smpl-ai.com must show Verified" -ForegroundColor White
    Write-Host "2. Set production env:" -ForegroundColor White
    Write-Host '   .\scripts\set-vercel-prod-auth-env.ps1 -DatabaseUrl "..." -ProdUrl "https://smpl-ai.com" -EmailFrom "SMPL.ai <noreply@smpl-ai.com>"' -ForegroundColor Yellow
    Write-Host '   .\scripts\set-vercel-resend-from.ps1' -ForegroundColor Yellow
    Write-Host "3. Redeploy Vercel production" -ForegroundColor White
    Write-Host "4. Test email:" -ForegroundColor White
    Write-Host "   .\scripts\test-resend-email.ps1 -To $TestEmail -From `"SMPL.ai <noreply@smpl-ai.com>`"" -ForegroundColor Yellow
    Write-Host "5. Magic link smoke test: https://smpl-ai.com/login" -ForegroundColor White
    Write-Host ""
}

function Show-Step3 {
    & (Join-Path $repoRoot "scripts\load-prod-warehouse.ps1") -DatabaseUrl $DatabaseUrl
}

function Show-Step4 {
    Write-Host ""
    Write-Host "=== Step 4: Local forecast promote test ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Prerequisites:" -ForegroundColor Yellow
    Write-Host "  - Local stack: .\scripts\start-local-stack.ps1 (or API :8001 + frontend :3002)" -ForegroundColor White
    Write-Host "  - Signed in as admin on org 8571e520-0687-4516-bdee-379f37c58c1f" -ForegroundColor White
    Write-Host "  - Enterprise forecast_engine entitlement" -ForegroundColor White
    Write-Host ""
    Write-Host "Test:" -ForegroundColor Yellow
    Write-Host "  1. Open http://localhost:3002/forecast-engine" -ForegroundColor White
    Write-Host "  2. Confirm 6+6 horizon, default levers, warehouse numbers visible" -ForegroundColor White
    Write-Host "  3. GET /api/v1/export/validation — resolve warnings before promote" -ForegroundColor White
    Write-Host "  4. Save Draft -> Promote to Final" -ForegroundColor White
    Write-Host "  5. Confirm outlook shows active_forecast_version_name; Jul-Dec forecast updated" -ForegroundColor White
    Write-Host ""
    Write-Host "Without opportunities: promote writes 5 tables (MRR, IS, CFS, BS, bookings)." -ForegroundColor DarkGray
    Write-Host ""
}

switch ($Step) {
    "1" { Show-Step1 }
    "2" { Show-Step2 }
    "3" { Show-Step3 }
    "4" { Show-Step4 }
    "all" {
        Show-Step1
        Show-Step2
        Write-Host "=== Step 3 (run when ready) ===" -ForegroundColor Cyan
        Write-Host "  .\scripts\go-live-smpl-ai.ps1 -Step 3" -ForegroundColor Yellow
        Write-Host ""
        Show-Step4
    }
}
