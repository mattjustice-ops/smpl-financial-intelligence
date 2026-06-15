# gl-2 helper: open Resend domain setup and print Vercel update steps.
#
# Usage:
#   .\scripts\setup-prod-resend-domain.ps1
#
# After Resend shows smpl-ai.com as Verified:
#   .\scripts\set-vercel-resend-from.ps1 -EmailFrom "SMPL.ai <noreply@smpl-ai.com>"

param(
    [string]$Domain = "smpl-ai.com",
    [string]$EmailFrom = "SMPL.ai <noreply@smpl-ai.com>",
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== gl-2: Resend verified domain ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Domain:     $Domain" -ForegroundColor White
Write-Host "EMAIL_FROM: $EmailFrom" -ForegroundColor White
Write-Host ""
Write-Host "Step A - Resend dashboard" -ForegroundColor Yellow
Write-Host "  1. Add domain $Domain at https://resend.com/domains" -ForegroundColor White
Write-Host "  2. Copy DNS records (SPF, DKIM, DMARC) into your DNS host" -ForegroundColor White
Write-Host "  3. Wait until Resend shows Verified" -ForegroundColor White
Write-Host ""
Write-Host "Step B - Vercel (after Verified)" -ForegroundColor Yellow
Write-Host "  .\scripts\set-vercel-resend-from.ps1 -EmailFrom `"$EmailFrom`"" -ForegroundColor White
Write-Host "  Redeploy on Vercel" -ForegroundColor White
Write-Host ""
Write-Host "Step C - Smoke test" -ForegroundColor Yellow
Write-Host "  .\scripts\test-resend-email.ps1 -To someone-outside-resend@company.com -From `"$EmailFrom`"" -ForegroundColor White
Write-Host "  Seed invite + /login on production" -ForegroundColor White
Write-Host ""
Write-Host "Full guide: docs/GO_LIVE_STEP2_RESEND_DOMAIN.md" -ForegroundColor DarkGray
Write-Host ""

if ($OpenBrowser) {
    Start-Process "https://resend.com/domains"
}
