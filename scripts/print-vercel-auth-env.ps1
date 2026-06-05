# Print Auth.js / customer-login env vars for Vercel (staging auth milestone).
# Run from repo root: .\scripts\print-vercel-auth-env.ps1
#
# Does NOT print AUTH_SECRET or API keys from token files - add those manually in Vercel.

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$envLocal = Join-Path $repoRoot "frontend\.env.local"

$prodUrl = "https://smpl-financial-intelligence.vercel.app"
$emailFromExample = 'SMPL.ai <onboarding@resend.dev>'

Write-Host ""
Write-Host "=== Vercel auth milestone - environment variables ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Vercel -> Project -> Settings -> Environment Variables -> Production" -ForegroundColor Yellow
Write-Host "Apply to Production (and Preview if you want staging previews)." -ForegroundColor Yellow
Write-Host ""

function Show-Var {
  param([string]$Name, [string]$Value, [string]$Note = "")
  Write-Host "Key:   $Name" -ForegroundColor White
  Write-Host "Value: $Value" -ForegroundColor DarkGray
  if ($Note) { Write-Host "Note:  $Note" -ForegroundColor DarkYellow }
  Write-Host ""
}

Show-Var "AUTH_URL" $prodUrl "Must match your public site URL (no trailing slash)."
Show-Var "APP_BASE_URL" $prodUrl "Used for Stripe return URLs and magic-link redirects."

Write-Host "Key:   AUTH_SECRET" -ForegroundColor White
Write-Host "Value: (generate a NEW secret for production - do not reuse local)" -ForegroundColor DarkGray
Write-Host "       openssl rand -base64 32" -ForegroundColor DarkGray
Write-Host ""

Write-Host "Key:   AUTH_RESEND_KEY" -ForegroundColor White
Write-Host "Value: re_... from Resend (Sending API key)" -ForegroundColor DarkGray
Write-Host "Note:  Do NOT use RESEND_TOKEN_FILE on Vercel - file paths only work locally." -ForegroundColor DarkYellow
Write-Host ""

Show-Var "EMAIL_FROM" $emailFromExample "Replace with verified domain before customer invites (e.g. login@yourdomain.com)."

Write-Host "Key:   AUTH_DATABASE_URL" -ForegroundColor White
Write-Host "Value: postgresql://... from Neon / Supabase / Railway Postgres" -ForegroundColor DarkGray
Write-Host "Note:  Run backend alembic migrations on this DB (authjs_* + users tables)." -ForegroundColor DarkYellow
Write-Host ""

Write-Host "Key:   SFI_BACKEND_URL" -ForegroundColor White
Write-Host "Value: https://YOUR-PRODUCTION-API.example.com (no trailing slash)" -ForegroundColor DarkGray
Write-Host "Note:  Magic-link click calls session-sync on this API. Localhost will NOT work from Vercel." -ForegroundColor DarkYellow
Write-Host ""

Show-Var "NEXT_PUBLIC_API_URL" "https://YOUR-PRODUCTION-API.example.com" "Same host as SFI_BACKEND_URL for /app dashboards."

Write-Host "Key:   BILLING_INTERNAL_API_KEY" -ForegroundColor White
Write-Host "Value: (same random secret on Vercel AND on the production API)" -ForegroundColor DarkGray
Write-Host ""

Write-Host "--- Optional for now (Stripe checkout on production) ---" -ForegroundColor Green
Write-Host "See: .\scripts\print-vercel-stripe-env.ps1 and docs/VERCEL_STRIPE_SETUP_BEGINNER.md"
Write-Host ""

if (Test-Path $envLocal) {
  Write-Host "--- Values detected in frontend/.env.local (review before copying) ---" -ForegroundColor Green
  $localNames = @("AUTH_RESEND_KEY", "EMAIL_FROM", "SFI_BACKEND_URL", "NEXT_PUBLIC_API_URL", "BILLING_INTERNAL_API_KEY")
  $lines = Get-Content $envLocal
  foreach ($name in $localNames) {
    $prefix = "$name="
    $match = $lines | Where-Object { $_ -like "$prefix*" } | Select-Object -First 1
    if ($match) {
      $value = $match.Substring($prefix.Length)
      if ($name -match "KEY|SECRET") {
        Write-Host "$name = (set - hidden)" -ForegroundColor DarkGray
      } elseif ($value -match "127\.0\.0\.1|localhost") {
        Write-Host "$name = $value  <- replace with production URLs on Vercel" -ForegroundColor Yellow
      } else {
        Write-Host "$name = $value" -ForegroundColor DarkGray
      }
    }
  }
  Write-Host ""
}

Write-Host "After saving env vars: Vercel -> Deployments -> Redeploy latest." -ForegroundColor Cyan
Write-Host "Full guide: docs/VERCEL_AUTH_DEPLOY.md" -ForegroundColor Cyan
Write-Host ""
