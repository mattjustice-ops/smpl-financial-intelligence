# Creates SMPL Starter + Professional products/prices in Stripe and writes price IDs to frontend/.env.local
#
# Run from repo root:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\scripts\create-stripe-test-products.ps1
#
# Requires: Stripe Token.txt with Secret Key (sk_test_... or sk_live_...)
# Default path: C:\Users\mattj\OneDrive\Documents\Stripe Token.txt

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$envLocal = Join-Path $repoRoot "frontend\.env.local"
$stripeTokenFile = "C:\Users\mattj\OneDrive\Documents\Stripe Token.txt"

function Get-StripeSecretKey {
  if ($env:STRIPE_SECRET_KEY) {
    return $env:STRIPE_SECRET_KEY.Trim()
  }
  if (-not (Test-Path $stripeTokenFile)) {
    throw "Stripe Token.txt not found at: $stripeTokenFile"
  }
  $content = Get-Content $stripeTokenFile -Raw
  $m = [regex]::Match($content, "sk_(?:test|live)_[A-Za-z0-9]+")
  if (-not $m.Success) {
    throw "No sk_test_ or sk_live_ key found in Stripe Token.txt"
  }
  return $m.Value
}

function Invoke-StripeApi {
  param(
    [string]$Path,
    [hashtable]$Body
  )
  $uri = "https://api.stripe.com/v1/$Path"
  $pairs = New-Object System.Collections.Generic.List[string]
  foreach ($key in $Body.Keys) {
    $val = $Body[$key]
    if ($null -ne $val -and "$val" -ne "") {
      $pairs.Add("$key=$([uri]::EscapeDataString("$val"))")
    }
  }
  $form = $pairs -join "&"
  return Invoke-RestMethod -Uri $uri -Method Post -Headers @{
    Authorization = "Bearer $(Get-StripeSecretKey)"
  } -ContentType "application/x-www-form-urlencoded" -Body $form
}

function Set-EnvLocalPriceId {
  param(
    [string]$Name,
    [string]$PriceId
  )
  if (-not (Test-Path $envLocal)) {
    throw "Missing $envLocal - run .\scripts\stripe-local-setup.ps1 first"
  }

  $prefix = $Name + "="
  $found = $false
  $lines = Get-Content $envLocal | ForEach-Object {
    if ($_.StartsWith($prefix)) {
      $found = $true
      $prefix + $PriceId
    } else {
      $_
    }
  }

  if (-not $found) {
    $lines += $prefix + $PriceId
  }

  Set-Content -Path $envLocal -Value $lines
  Write-Host "  $Name = $PriceId" -ForegroundColor Green
}

$secretKey = Get-StripeSecretKey
$mode = if ($secretKey -match "^sk_test_") { "test" } else { "live" }

Write-Host ""
Write-Host "=== Create Stripe products (SMPL) ===" -ForegroundColor Cyan
Write-Host "Stripe mode: $mode (open dashboard in this mode)" -ForegroundColor Yellow
Write-Host "Env file:    $envLocal" -ForegroundColor DarkGray

$account = Invoke-RestMethod -Uri "https://api.stripe.com/v1/account" -Headers @{
  Authorization = "Bearer $secretKey"
}
Write-Host ""
Write-Host "This key belongs to Stripe account:" -ForegroundColor Green
Write-Host "  $($account.business_profile.name)"
Write-Host "  $($account.email)"
Write-Host "  $($account.id)"
Write-Host "Log into THIS account in the browser, then open the product catalog URL printed at the end."
Write-Host ""

$starterProduct = Invoke-StripeApi -Path "products" -Body @{
  name        = "SMPL Starter"
  description = "Silver Support - 2 users, 1 integration, dedicated environment, dashboards, board reporting, AI commentary"
}
Write-Host "Created product: $($starterProduct.name) ($($starterProduct.id))"

$professionalProduct = Invoke-StripeApi -Path "products" -Body @{
  name        = "SMPL Professional"
  description = "Gold Support - 5 users, 3 integrations, forecasting, workforce planning, scenario analysis, AI commentary"
}
Write-Host "Created product: $($professionalProduct.name) ($($professionalProduct.id))"

# Placeholder recurring amounts for post-contract checkout (public /pricing is sales-led).
$starterMonthly = Invoke-StripeApi -Path "prices" -Body @{
  product                     = $starterProduct.id
  unit_amount                 = "250000"
  currency                    = "usd"
  "recurring[interval]"       = "month"
  "recurring[interval_count]" = "1"
  nickname                    = "Starter Monthly"
}
$starterAnnual = Invoke-StripeApi -Path "prices" -Body @{
  product                     = $starterProduct.id
  unit_amount                 = "3000000"
  currency                    = "usd"
  "recurring[interval]"       = "year"
  "recurring[interval_count]" = "1"
  nickname                    = "Starter Annual"
}
$professionalMonthly = Invoke-StripeApi -Path "prices" -Body @{
  product                     = $professionalProduct.id
  unit_amount                 = "500000"
  currency                    = "usd"
  "recurring[interval]"       = "month"
  "recurring[interval_count]" = "1"
  nickname                    = "Professional Monthly"
}
$professionalAnnual = Invoke-StripeApi -Path "prices" -Body @{
  product                     = $professionalProduct.id
  unit_amount                 = "6000000"
  currency                    = "usd"
  "recurring[interval]"       = "year"
  "recurring[interval_count]" = "1"
  nickname                    = "Professional Annual"
}

$starterImpl = Invoke-StripeApi -Path "prices" -Body @{
  product     = $starterProduct.id
  unit_amount = "500000"
  currency    = "usd"
  nickname    = "Starter Implementation"
}
$professionalImpl = Invoke-StripeApi -Path "prices" -Body @{
  product     = $professionalProduct.id
  unit_amount = "750000"
  currency    = "usd"
  nickname    = "Professional Implementation"
}

Write-Host ""
Write-Host "Updating frontend/.env.local ..." -ForegroundColor Cyan
Set-EnvLocalPriceId -Name "STRIPE_STARTER_MONTHLY_PRICE_ID" -PriceId $starterMonthly.id
Set-EnvLocalPriceId -Name "STRIPE_STARTER_ANNUAL_PRICE_ID" -PriceId $starterAnnual.id
Set-EnvLocalPriceId -Name "STRIPE_PROFESSIONAL_MONTHLY_PRICE_ID" -PriceId $professionalMonthly.id
Set-EnvLocalPriceId -Name "STRIPE_PROFESSIONAL_ANNUAL_PRICE_ID" -PriceId $professionalAnnual.id
Set-EnvLocalPriceId -Name "STRIPE_STARTER_IMPLEMENTATION_PRICE_ID" -PriceId $starterImpl.id
Set-EnvLocalPriceId -Name "STRIPE_PROFESSIONAL_IMPLEMENTATION_PRICE_ID" -PriceId $professionalImpl.id
# Legacy aliases (app still accepts GROWTH_* as fallback)
Set-EnvLocalPriceId -Name "STRIPE_GROWTH_MONTHLY_PRICE_ID" -PriceId $professionalMonthly.id
Set-EnvLocalPriceId -Name "STRIPE_GROWTH_ANNUAL_PRICE_ID" -PriceId $professionalAnnual.id
Set-EnvLocalPriceId -Name "STRIPE_GROWTH_IMPLEMENTATION_PRICE_ID" -PriceId $professionalImpl.id

Write-Host ""
Write-Host "Done. Enterprise is sales-led only (no Stripe product)." -ForegroundColor Green
if ($mode -eq "test") {
  Write-Host "Dashboard: https://dashboard.stripe.com/test/products" -ForegroundColor Cyan
} else {
  Write-Host "Dashboard: https://dashboard.stripe.com/products" -ForegroundColor Cyan
}
Write-Host ""
Write-Host "Next:" -ForegroundColor Yellow
Write-Host "  1. Confirm Test/Live toggle in Stripe matches key in Token.txt"
Write-Host "  2. Copy the six price_ IDs to Vercel env vars for production"
Write-Host "  3. Restart frontend: cd frontend; npm run dev"
Write-Host ""
