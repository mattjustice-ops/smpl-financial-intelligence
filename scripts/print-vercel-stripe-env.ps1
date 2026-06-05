# Prints Stripe-related lines from frontend/.env.local as a Vercel copy-paste checklist.
# Does NOT print secret keys from Stripe Token.txt (add those manually in Vercel).
#
# Run: .\scripts\print-vercel-stripe-env.ps1

$ErrorActionPreference = "Stop"
$envLocal = Join-Path (Split-Path $PSScriptRoot -Parent) "frontend\.env.local"

Write-Host ""
Write-Host "=== Vercel Environment Variables checklist ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "In Vercel: Project -> Settings -> Environment Variables" -ForegroundColor Yellow
Write-Host "For each row: Key = Name column, Value = paste from Value column" -ForegroundColor Yellow
Write-Host "Then Redeploy." -ForegroundColor Yellow
Write-Host ""
Write-Host "--- From frontend/.env.local (safe to copy) ---" -ForegroundColor Green

if (-not (Test-Path $envLocal)) {
  Write-Host "No .env.local found. Run create-stripe-test-products.ps1 first." -ForegroundColor Red
  exit 1
}

$stripeNames = @(
  "STRIPE_STARTER_MONTHLY_PRICE_ID",
  "STRIPE_STARTER_ANNUAL_PRICE_ID",
  "STRIPE_PROFESSIONAL_MONTHLY_PRICE_ID",
  "STRIPE_PROFESSIONAL_ANNUAL_PRICE_ID",
  "STRIPE_STARTER_IMPLEMENTATION_PRICE_ID",
  "STRIPE_PROFESSIONAL_IMPLEMENTATION_PRICE_ID",
  "STRIPE_GROWTH_MONTHLY_PRICE_ID",
  "STRIPE_GROWTH_ANNUAL_PRICE_ID",
  "STRIPE_GROWTH_IMPLEMENTATION_PRICE_ID",
  "APP_BASE_URL",
  "SFI_BACKEND_URL"
)

$lines = Get-Content $envLocal
foreach ($name in $stripeNames) {
  $prefix = "$name="
  $match = $lines | Where-Object { $_ -like "$prefix*" } | Select-Object -First 1
  if ($match) {
    $value = $match.Substring($prefix.Length)
    Write-Host ""
    Write-Host "Key:   $name" -ForegroundColor White
    Write-Host "Value: $value" -ForegroundColor DarkGray
  }
}

Write-Host ""
Write-Host "--- Add manually in Vercel (not in .env.local) ---" -ForegroundColor Green
Write-Host ""
Write-Host "Key:   STRIPE_SECRET_KEY"
Write-Host "Value: sk_test_... from Stripe Dashboard -> Developers -> API keys -> Secret key (Reveal)"
Write-Host "       (Use sk_live_... only when accepting real money in Live mode)"
Write-Host ""
Write-Host "Key:   NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY"
Write-Host "Value: pk_test_... from same API keys page"
Write-Host ""
Write-Host "Key:   STRIPE_WEBHOOK_SECRET"
Write-Host "Value: whsec_... from Stripe -> Developers -> Webhooks -> your endpoint -> Signing secret"
Write-Host ""
Write-Host "Do NOT add STRIPE_TOKEN_FILE to Vercel - it only works on your PC." -ForegroundColor Yellow
Write-Host ""
Write-Host "Full guide: docs/VERCEL_STRIPE_SETUP_BEGINNER.md" -ForegroundColor Cyan
Write-Host ""
