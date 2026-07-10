# Go-live gl-4: Stripe Live catalog, webhook, Vercel env checklist.
#
# Prerequisites:
#   - Stripe Token.txt contains sk_live_... and pk_live_... (Live mode keys)
#   - Optional: whsec_... for existing webhook (script creates one if missing)
#
# Usage:
#   .\scripts\setup-stripe-live-gl4.ps1
#   .\scripts\setup-stripe-live-gl4.ps1 -ApplyVercel
#   .\scripts\setup-stripe-live-gl4.ps1 -SkipProductCreate -ApplyVercel

param(
    [switch]$ApplyVercel,
    [switch]$SkipProductCreate,
    [string]$WebhookUrl = "https://www.smpl-ai.com/api/stripe/webhook",
    [string]$AppBaseUrl = "https://www.smpl-ai.com",
    [string]$BackendUrl = "https://sfi-api-production.up.railway.app",
    [string]$StripeTokenFile = "C:\Users\mattj\OneDrive\Documents\Stripe Token.txt",
    [string]$Scope = "smplai",
    [string]$Project = "smpl-financial-intelligence"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$envLocal = Join-Path $repoRoot "frontend\.env.local"
$envLiveRef = Join-Path $repoRoot "frontend\.env.stripe-live.prod"

function Get-StripeSecrets {
    param([string]$TokenFile)
    if ($env:STRIPE_SECRET_KEY) {
        $sk = $env:STRIPE_SECRET_KEY.Trim()
    } elseif (Test-Path $TokenFile) {
        $content = Get-Content $TokenFile -Raw
        $m = [regex]::Match($content, "sk_(?:test|live)_[A-Za-z0-9]+")
        if (-not $m.Success) { throw "No sk_ key in Token file" }
        $sk = $m.Value
    } else {
        throw "Set STRIPE_SECRET_KEY or create $TokenFile"
    }

    $pk = $null
    $whsec = $null
    if (Test-Path $TokenFile) {
        $content = Get-Content $TokenFile -Raw
        $pkm = [regex]::Match($content, "pk_(?:test|live)_[A-Za-z0-9]+")
        if ($pkm.Success) { $pk = $pkm.Value }
        $wm = [regex]::Match($content, "whsec_[A-Za-z0-9]+")
        if ($wm.Success) { $whsec = $wm.Value }
    }
    if (-not $pk -and $env:NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY) {
        $pk = $env:NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY.Trim()
    }
    return @{ SecretKey = $sk; PublishableKey = $pk; WebhookSecret = $whsec }
}

function Invoke-StripeApi {
    param(
        [string]$SecretKey,
        [string]$Method = "GET",
        [string]$Path,
        [hashtable]$Body
    )
    $uri = "https://api.stripe.com/v1/$Path"
    $headers = @{ Authorization = "Bearer $SecretKey" }
    if ($Method -eq "GET") {
        return Invoke-RestMethod -Uri $uri -Method Get -Headers $headers
    }
    $pairs = New-Object System.Collections.Generic.List[string]
    foreach ($key in $Body.Keys) {
        $val = $Body[$key]
        if ($null -eq $val) { continue }
        if ($val -is [array]) {
            foreach ($item in $val) {
                $pairs.Add("$key=$([uri]::EscapeDataString("$item"))")
            }
        } else {
            $pairs.Add("$key=$([uri]::EscapeDataString("$val"))")
        }
    }
    $form = $pairs -join "&"
    return Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -ContentType "application/x-www-form-urlencoded" -Body $form
}

function Set-EnvFileValue {
    param(
        [string]$FilePath,
        [string]$Name,
        [string]$Value
    )
    $prefix = "$Name="
    $lines = @()
    if (Test-Path $FilePath) {
        $lines = Get-Content $FilePath
    }
    $found = $false
    $lines = $lines | ForEach-Object {
        if ($_.StartsWith($prefix)) {
            $found = $true
            $prefix + $Value
        } else {
            $_
        }
    }
    if (-not $found) { $lines += $prefix + $Value }
    Set-Content -Path $FilePath -Value $lines
}

function Get-EnvFileValue {
    param([string]$FilePath, [string]$Key)
    if (-not (Test-Path $FilePath)) { return $null }
    $line = Get-Content $FilePath | Where-Object { $_ -like "$Key=*" } | Select-Object -First 1
    if ($line -match "^$Key=(.+)$") { return $Matches[1].Trim() }
    return $null
}

function Set-VercelProdEnvValue {
    param(
        [string]$FrontendDir,
        [string]$Name,
        [string]$Value
    )
    $npxArgs = @("--yes", "vercel@latest", "--scope", $Scope, "--project", $Project)
    if ($env:VERCEL_TOKEN) { $npxArgs += @("--token", $env:VERCEL_TOKEN) }
    $tempFile = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($tempFile, $Value, [System.Text.UTF8Encoding]::new($false))
        Push-Location $FrontendDir
        $output = Get-Content -LiteralPath $tempFile -Raw | & npx @npxArgs env add $Name production --yes --force 2>&1 | ForEach-Object { "$_" }
        if ($LASTEXITCODE -ne 0) {
            throw ($output -join "`n")
        }
    } finally {
        Pop-Location
        Remove-Item -LiteralPath $tempFile -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ""
Write-Host "=== gl-4: Stripe Live setup ===" -ForegroundColor Cyan
Write-Host ""

$secrets = Get-StripeSecrets -TokenFile $StripeTokenFile
if ($secrets.SecretKey -notmatch "^sk_live_") {
    Write-Host "ERROR: gl-4 requires a LIVE secret key (sk_live_...)." -ForegroundColor Red
    Write-Host "  Stripe Dashboard -> turn Test mode OFF -> Developers -> API keys" -ForegroundColor Yellow
    Write-Host "  Add sk_live_ and pk_live_ to: $StripeTokenFile" -ForegroundColor Yellow
    exit 1
}
if (-not $secrets.PublishableKey -or $secrets.PublishableKey -notmatch "^pk_live_") {
    Write-Host "ERROR: pk_live_... missing from Token file or NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY." -ForegroundColor Red
    exit 1
}

$account = Invoke-StripeApi -SecretKey $secrets.SecretKey -Path "account"
Write-Host "Stripe Live account: $($account.email) ($($account.id))" -ForegroundColor Green
Write-Host ""

if (-not $SkipProductCreate) {
    Write-Host "Creating live product catalog (or run with -SkipProductCreate if already done)..." -ForegroundColor Yellow
    $createScript = Join-Path $PSScriptRoot "create-stripe-test-products.ps1"
    if (-not (Test-Path $createScript)) {
        throw "Missing $createScript"
    }
    $env:STRIPE_SECRET_KEY = $secrets.SecretKey
    & $createScript
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "Skipping product creation (-SkipProductCreate)." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Ensuring live webhook endpoint..." -ForegroundColor Yellow
$webhookEvents = @(
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_succeeded",
    "invoice.payment_failed",
    "customer.updated"
)
$existing = Invoke-StripeApi -SecretKey $secrets.SecretKey -Path "webhook_endpoints?limit=100"
$match = $existing.data | Where-Object { $_.url -eq $WebhookUrl } | Select-Object -First 1
$webhookSecret = $secrets.WebhookSecret

if ($match) {
    Write-Host "  Webhook already exists: $($match.id)" -ForegroundColor Green
    Write-Host "  URL: $($match.url)" -ForegroundColor DarkGray
    if (-not $webhookSecret) {
        Write-Host "  Copy signing secret from Stripe Dashboard -> Webhooks -> this endpoint -> whsec_..." -ForegroundColor Yellow
    }
} else {
    Write-Host "  Creating webhook: $WebhookUrl" -ForegroundColor Yellow
    $body = @{
        url = $WebhookUrl
        "enabled_events[]" = $webhookEvents
    }
    $created = Invoke-StripeApi -SecretKey $secrets.SecretKey -Method POST -Path "webhook_endpoints" -Body $body
    $webhookSecret = $created.secret
    Write-Host "  Created: $($created.id)" -ForegroundColor Green
    Write-Host "  NEW signing secret (save to Vercel STRIPE_WEBHOOK_SECRET):" -ForegroundColor Cyan
    Write-Host "  $webhookSecret" -ForegroundColor White
    Write-Host ""
    Write-Host "  Add this line to Stripe Token.txt for local reference:" -ForegroundColor DarkGray
    Write-Host "  $webhookSecret" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Writing reference env file: frontend/.env.stripe-live.prod" -ForegroundColor Yellow
if (-not (Test-Path $envLocal)) {
    Write-Host "  WARN: frontend/.env.local missing - run create-stripe-test-products.ps1 first" -ForegroundColor Yellow
} else {
    Copy-Item -Path $envLocal -Destination $envLiveRef -Force
}
Set-EnvFileValue -FilePath $envLiveRef -Name "APP_BASE_URL" -Value $AppBaseUrl.TrimEnd("/")
Set-EnvFileValue -FilePath $envLiveRef -Name "SFI_BACKEND_URL" -Value $BackendUrl.TrimEnd("/")
Set-EnvFileValue -FilePath $envLiveRef -Name "STRIPE_SECRET_KEY" -Value $secrets.SecretKey
Set-EnvFileValue -FilePath $envLiveRef -Name "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY" -Value $secrets.PublishableKey
if ($webhookSecret) {
    Set-EnvFileValue -FilePath $envLiveRef -Name "STRIPE_WEBHOOK_SECRET" -Value $webhookSecret
}
Write-Host "  OK (do not commit this file - contains live secrets)" -ForegroundColor Green

$billingKey = Get-EnvFileValue -FilePath $envLocal -Key "BILLING_INTERNAL_API_KEY"
if ($billingKey) {
    Set-EnvFileValue -FilePath $envLiveRef -Name "BILLING_INTERNAL_API_KEY" -Value $billingKey
}

Write-Host ""
Write-Host "=== Vercel Production checklist ===" -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "print-vercel-stripe-env.ps1")

if ($ApplyVercel) {
    Write-Host ""
    Write-Host "Applying Stripe env vars to Vercel Production..." -ForegroundColor Yellow
    $frontendDir = Join-Path $repoRoot "frontend"
    $vars = @{
        STRIPE_SECRET_KEY                      = $secrets.SecretKey
        NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY     = $secrets.PublishableKey
        APP_BASE_URL                           = $AppBaseUrl.TrimEnd("/")
        SFI_BACKEND_URL                        = $BackendUrl.TrimEnd("/")
    }
    if ($webhookSecret) {
        $vars["STRIPE_WEBHOOK_SECRET"] = $webhookSecret
    }
    $priceNames = @(
        "STRIPE_STARTER_MONTHLY_PRICE_ID",
        "STRIPE_STARTER_ANNUAL_PRICE_ID",
        "STRIPE_PROFESSIONAL_MONTHLY_PRICE_ID",
        "STRIPE_PROFESSIONAL_ANNUAL_PRICE_ID",
        "STRIPE_STARTER_IMPLEMENTATION_PRICE_ID",
        "STRIPE_PROFESSIONAL_IMPLEMENTATION_PRICE_ID",
        "STRIPE_GROWTH_MONTHLY_PRICE_ID",
        "STRIPE_GROWTH_ANNUAL_PRICE_ID",
        "STRIPE_GROWTH_IMPLEMENTATION_PRICE_ID"
    )
    foreach ($name in $priceNames) {
        $val = Get-EnvFileValue -FilePath $envLocal -Key $name
        if ($val -and $val -notmatch "REPLACE") {
            $vars[$name] = $val
        }
    }
    if ($billingKey) {
        $vars["BILLING_INTERNAL_API_KEY"] = $billingKey
    }

    foreach ($entry in $vars.GetEnumerator()) {
        Set-VercelProdEnvValue -FrontendDir $frontendDir -Name $entry.Key -Value $entry.Value
        Write-Host "  OK: $($entry.Key)" -ForegroundColor Green
    }
    Write-Host "Vercel env updated. Redeploy Production:" -ForegroundColor Green
    Write-Host "  .\scripts\redeploy-vercel-production.ps1 -SkipBuild -SmokeTest" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "To push env vars automatically: .\scripts\setup-stripe-live-gl4.ps1 -ApplyVercel" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Next:" -ForegroundColor Cyan
Write-Host "  1. .\scripts\redeploy-vercel-production.ps1 -SkipBuild   (if env changed)"
Write-Host "  2. Confirm Railway BILLING_INTERNAL_API_KEY matches Vercel"
Write-Host "  3. .\scripts\smoke-test-stripe-prod.ps1"
Write-Host "  4. One live contract checkout -> verify webhook 200 in Stripe Dashboard"
Write-Host "  5. Mark gl-4 done on /progress"
Write-Host ""
Write-Host "Full guide: docs/GO_LIVE_GL4_STRIPE_LIVE.md" -ForegroundColor DarkGray
Write-Host ""
