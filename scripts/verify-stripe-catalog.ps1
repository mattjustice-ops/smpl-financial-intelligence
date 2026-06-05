# Lists Stripe products for the key in Stripe Token.txt (diagnostic)
# Run: .\scripts\verify-stripe-catalog.ps1

$ErrorActionPreference = "Stop"
$stripeTokenFile = "C:\Users\mattj\OneDrive\Documents\Stripe Token.txt"

if ($env:STRIPE_SECRET_KEY) {
  $secretKey = $env:STRIPE_SECRET_KEY.Trim()
} elseif (Test-Path $stripeTokenFile) {
  $content = Get-Content $stripeTokenFile -Raw
  $m = [regex]::Match($content, "sk_(?:test|live)_[A-Za-z0-9]+")
  if (-not $m.Success) { throw "No sk_test_ or sk_live_ in Stripe Token.txt" }
  $secretKey = $m.Value
} else {
  throw "Set STRIPE_SECRET_KEY or create $stripeTokenFile"
}

$mode = if ($secretKey -match "^sk_test_") { "test" } else { "live" }
Write-Host ""
Write-Host "Stripe API mode: $mode" -ForegroundColor Cyan
Write-Host "Key starts with: $($secretKey.Substring(0, 12))..." -ForegroundColor DarkGray
Write-Host ""

$headers = @{ Authorization = "Bearer $secretKey" }

try {
  $account = Invoke-RestMethod -Uri "https://api.stripe.com/v1/account" -Headers $headers
  Write-Host "Connected account:" -ForegroundColor Green
  Write-Host "  Business: $($account.business_profile.name)"
  Write-Host "  Account ID: $($account.id)"
  Write-Host "  Email: $($account.email)"
  Write-Host ""
} catch {
  Write-Host "Could not read account (key invalid or restricted): $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}

$products = Invoke-RestMethod -Uri "https://api.stripe.com/v1/products?limit=100&active=true" -Headers $headers
$archived = Invoke-RestMethod -Uri "https://api.stripe.com/v1/products?limit=100&active=false" -Headers $headers

Write-Host "Active products: $($products.data.Count)" -ForegroundColor $(if ($products.data.Count -gt 0) { "Green" } else { "Yellow" })
foreach ($p in $products.data) {
  Write-Host "  - $($p.name) ($($p.id))"
}

Write-Host "Archived products: $($archived.data.Count)" -ForegroundColor DarkGray
foreach ($p in $archived.data) {
  Write-Host "  - $($p.name) ($($p.id))"
}

Write-Host ""
$businessName = "$($account.business_profile.name)"
if ($mode -eq "test" -and $businessName -match "sandbox") {
  Write-Host "IMPORTANT: Your API key is for a Stripe SANDBOX, not the default Test mode catalog." -ForegroundColor Yellow
  Write-Host ""
  Write-Host "Products will NOT appear at dashboard.stripe.com/test/products until you switch environments." -ForegroundColor Yellow
  Write-Host ""
  Write-Host "To see these products in the Dashboard:" -ForegroundColor Cyan
  Write-Host "  1. Stripe Dashboard -> account picker (top-left)"
  Write-Host "  2. Switch to sandbox -> select: $businessName"
  Write-Host "     (or Manage sandboxes -> Open)"
  Write-Host "  3. Product catalog (left nav)"
  Write-Host ""
  Write-Host "Direct: https://dashboard.stripe.com/sandboxes" -ForegroundColor DarkGray
} elseif ($mode -eq "test") {
  Write-Host "Open (Test mode ON, same account $($account.email)):" -ForegroundColor Cyan
  Write-Host "  https://dashboard.stripe.com/test/products"
} else {
  Write-Host "Open (Live mode, same account $($account.email)):" -ForegroundColor Cyan
  Write-Host "  https://dashboard.stripe.com/products"
}

Write-Host ""
Write-Host "If API count > 0 but catalog is empty, you are in the wrong Dashboard environment (sandbox vs test vs live)." -ForegroundColor Yellow
Write-Host "If API count is 0, run: .\scripts\create-stripe-test-products.ps1" -ForegroundColor Yellow
Write-Host ""
