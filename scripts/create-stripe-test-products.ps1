# Creates SMPL Starter/Growth test products + prices in Stripe and writes price IDs into frontend/.env.local
#
# Run from repo root:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\scripts\create-stripe-test-products.ps1
#
# Requires: C:\Users\mattj\OneDrive\Documents\Stripe Token.txt with Secret Key (sk_test_...)

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
    throw "Missing $envLocal - run stripe-local-setup.ps1 first or copy .env.example"
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
    throw "$Name not found in .env.local"
  }

  Set-Content -Path $envLocal -Value $lines
  Write-Host "  $Name = $PriceId" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Create Stripe test products (SMPL) ===" -ForegroundColor Cyan
Write-Host "Paste target file: $envLocal" -ForegroundColor DarkGray
Write-Host ""

$starterProduct = Invoke-StripeApi -Path "products" -Body @{
  name        = "SMPL Starter"
  description = "3 users, basic dashboards, standard reporting, CSV uploads, basic AI commentary"
}
Write-Host "Created product: $($starterProduct.name) ($($starterProduct.id))"

$growthProduct = Invoke-StripeApi -Path "products" -Body @{
  name        = "SMPL Growth"
  description = "8 users, board reporting, forecasting, workforce planning, AI commentary, scenario analysis"
}
Write-Host "Created product: $($growthProduct.name) ($($growthProduct.id))"

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
$growthMonthly = Invoke-StripeApi -Path "prices" -Body @{
  product                     = $growthProduct.id
  unit_amount                 = "500000"
  currency                    = "usd"
  "recurring[interval]"       = "month"
  "recurring[interval_count]" = "1"
  nickname                    = "Growth Monthly"
}
$growthAnnual = Invoke-StripeApi -Path "prices" -Body @{
  product                     = $growthProduct.id
  unit_amount                 = "6000000"
  currency                    = "usd"
  "recurring[interval]"       = "year"
  "recurring[interval_count]" = "1"
  nickname                    = "Growth Annual"
}
$starterImpl = Invoke-StripeApi -Path "prices" -Body @{
  product     = $starterProduct.id
  unit_amount = "500000"
  currency    = "usd"
  nickname    = "Starter Implementation"
}
$growthImpl = Invoke-StripeApi -Path "prices" -Body @{
  product     = $growthProduct.id
  unit_amount = "750000"
  currency    = "usd"
  nickname    = "Growth Implementation"
}

Write-Host ""
Write-Host "Updating frontend/.env.local ..." -ForegroundColor Cyan
Set-EnvLocalPriceId -Name "STRIPE_STARTER_MONTHLY_PRICE_ID" -PriceId $starterMonthly.id
Set-EnvLocalPriceId -Name "STRIPE_STARTER_ANNUAL_PRICE_ID" -PriceId $starterAnnual.id
Set-EnvLocalPriceId -Name "STRIPE_GROWTH_MONTHLY_PRICE_ID" -PriceId $growthMonthly.id
Set-EnvLocalPriceId -Name "STRIPE_GROWTH_ANNUAL_PRICE_ID" -PriceId $growthAnnual.id
Set-EnvLocalPriceId -Name "STRIPE_STARTER_IMPLEMENTATION_PRICE_ID" -PriceId $starterImpl.id
Set-EnvLocalPriceId -Name "STRIPE_GROWTH_IMPLEMENTATION_PRICE_ID" -PriceId $growthImpl.id

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "View in Stripe: https://dashboard.stripe.com/test/products" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next:" -ForegroundColor Yellow
Write-Host "  1. Restart frontend if it is running (npm run dev)"
Write-Host "  2. stripe listen --forward-to localhost:3002/api/stripe/webhook"
Write-Host "  3. Add whsec_... line to Stripe Token.txt"
Write-Host "  4. Open http://localhost:3002/pricing"
Write-Host ""
