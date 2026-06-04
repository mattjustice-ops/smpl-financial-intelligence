# Append Stripe billing vars to frontend/.env.local and optionally list Stripe prices.
# Run from repo root:  .\scripts\stripe-local-setup.ps1

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$envLocal = Join-Path $repoRoot "frontend\.env.local"
$stripeTokenFile = "C:\Users\mattj\OneDrive\Documents\Stripe Token.txt"

Write-Host ""
Write-Host "=== SMPL Stripe local setup ===" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $stripeTokenFile)) {
  Write-Warning "Stripe Token.txt not found at: $stripeTokenFile"
} else {
  Write-Host "OK: Stripe Token.txt found (sk/pk/whsec read automatically)." -ForegroundColor Green
}

$block = @"

# --- Stripe billing (Week 2) ---
STRIPE_TOKEN_FILE=C:\Users\mattj\OneDrive\Documents\Stripe Token.txt
APP_BASE_URL=http://localhost:3002
# Paste price_... IDs from Stripe Dashboard -> Products (see docs/STRIPE_BILLING.md)
STRIPE_STARTER_MONTHLY_PRICE_ID=price_REPLACE_ME
STRIPE_STARTER_ANNUAL_PRICE_ID=price_REPLACE_ME
STRIPE_GROWTH_MONTHLY_PRICE_ID=price_REPLACE_ME
STRIPE_GROWTH_ANNUAL_PRICE_ID=price_REPLACE_ME
STRIPE_STARTER_IMPLEMENTATION_PRICE_ID=price_REPLACE_ME
STRIPE_GROWTH_IMPLEMENTATION_PRICE_ID=price_REPLACE_ME
"@

if (-not (Test-Path $envLocal)) {
  Copy-Item (Join-Path $repoRoot "frontend\.env.example") $envLocal
  Write-Host "Created frontend/.env.local from .env.example"
}

$content = Get-Content $envLocal -Raw
if ($content -match "STRIPE_STARTER_MONTHLY_PRICE_ID") {
  Write-Host "frontend/.env.local already has Stripe price ID lines - edit price_REPLACE_ME values." -ForegroundColor Yellow
} else {
  Add-Content -Path $envLocal -Value $block
  Write-Host "Appended Stripe block to frontend/.env.local" -ForegroundColor Green
  Write-Host "Edit the six price_REPLACE_ME values before testing checkout." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Get price IDs:" -ForegroundColor Cyan
Write-Host "  1. https://dashboard.stripe.com/test/products"
Write-Host "  2. Create Starter + Growth (monthly + annual recurring prices)"
Write-Host "  3. Optional: one-time Implementation prices (`$5k / `$7.5k)"
Write-Host "  4. Click each price -> copy ID (starts with price_)"
Write-Host ""

if (Get-Command stripe -ErrorAction SilentlyContinue) {
  Write-Host "Your Stripe test prices (stripe prices list):" -ForegroundColor Cyan
  stripe prices list --limit 20 2>$null
} else {
  Write-Host "Install Stripe CLI to list prices: https://stripe.com/docs/stripe-cli" -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "Next:" -ForegroundColor Green
Write-Host "  1. Replace price_REPLACE_ME in frontend/.env.local"
Write-Host "  2. Terminal A: stripe listen --forward-to localhost:3002/api/stripe/webhook"
Write-Host "  3. Add whsec_... from that terminal into Stripe Token.txt"
Write-Host "  4. Terminal B: docker compose up -d; cd backend; .\start-api.ps1"
Write-Host "  5. Terminal C: cd frontend; npm install; npm run dev"
Write-Host "  6. Open http://localhost:3002/pricing"
Write-Host ""
