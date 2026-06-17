# Set Railway backend service env vars via CLI.
#
# Prerequisites:
#   Railway project with backend service deployed (root = backend/)
#   npx @railway/cli login
#   cd backend && npx @railway/cli link   (select backend service)
#
# Usage (from repo root):
#   .\scripts\set-railway-backend-env.ps1 -DatabaseUrl "postgresql://..."
#
# Manual fallback:
#   .\scripts\print-railway-backend-env.ps1 -DatabaseUrl "..."

param(
    [Parameter(Mandatory = $true)]
    [string]$DatabaseUrl,
    [string]$ProdFrontendUrl = "https://smpl-financial-intelligence.vercel.app",
    [string]$BillingInternalApiKey = "",
    [string]$RailwayToken = ""
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $repoRoot "backend"
$envLocal = Join-Path $repoRoot "frontend\.env.local"

if ($RailwayToken) {
    $env:RAILWAY_TOKEN = $RailwayToken.Trim()
}

function Convert-ToRailwayDatabaseUrl {
    param([string]$Url)
    $normalized = $Url.Trim().Trim('"').Trim("'")
    if ($normalized -match "^postgresql://") {
        $normalized = $normalized -replace "^postgresql://", "postgresql+psycopg://"
    }
    if ($normalized -match "^postgres://") {
        $normalized = $normalized -replace "^postgres://", "postgresql+psycopg://"
    }
    # Neon copy/paste often includes channel_binding=require; psycopg on Railway fails with it.
    $normalized = $normalized -replace "[?&]channel_binding=require", ""
    $normalized = $normalized -replace "\?&", "?"
    $normalized = $normalized.TrimEnd("?").TrimEnd("&")
    return $normalized
}

function Get-RailwayInvoker {
    if (Get-Command railway -ErrorAction SilentlyContinue) {
        return @{
            Label = "railway"
            Invoke = { param([string[]]$CliArgs) & railway @CliArgs }
        }
    }
    if (Get-Command npx -ErrorAction SilentlyContinue) {
        return @{
            Label = "npx @railway/cli"
            Invoke = { param([string[]]$CliArgs) & npx --yes @railway/cli @CliArgs }
        }
    }
    return $null
}

function Invoke-RailwayCli {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$CliArgs)
    $output = & $railwayInvoker.Invoke $CliArgs 2>&1 | ForEach-Object { "$_" }
    return @{
        ExitCode = $LASTEXITCODE
        Output   = ($output -join "`n").Trim()
    }
}

function Set-RailwayVariable {
    param([string]$Name, [string]$Value)
    # Railway CLI: railway variables --set "KEY=VALUE"
    $pair = "$Name=$Value"
    $result = Invoke-RailwayCli variables --set $pair
    if ($result.ExitCode -ne 0) {
        Write-Host $result.Output -ForegroundColor Red
        throw "railway variables --set $Name failed (exit $($result.ExitCode))"
    }
    Write-Host "  OK: $Name" -ForegroundColor Green
}

$railwayInvoker = Get-RailwayInvoker
if (-not $railwayInvoker) {
    Write-Host "ERROR: Need railway CLI or npx." -ForegroundColor Red
    Write-Host "  npm i -g @railway/cli" -ForegroundColor Yellow
    exit 1
}

if (-not $BillingInternalApiKey -and (Test-Path $envLocal)) {
    $line = Get-Content $envLocal | Where-Object { $_ -match "^BILLING_INTERNAL_API_KEY=" } | Select-Object -First 1
    if ($line) {
        $BillingInternalApiKey = ($line -replace "^BILLING_INTERNAL_API_KEY=", "").Trim()
    }
}

$dbUrl = Convert-ToRailwayDatabaseUrl $DatabaseUrl
$cors = "$ProdFrontendUrl,http://localhost:3002,http://127.0.0.1:3002"

Write-Host ""
Write-Host "=== Railway backend env ===" -ForegroundColor Cyan
Write-Host "Using: $($railwayInvoker.Label)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Tip: link the backend service first:" -ForegroundColor Yellow
Write-Host "  cd backend" -ForegroundColor White
Write-Host "  npx @railway/cli login" -ForegroundColor White
Write-Host "  npx @railway/cli link" -ForegroundColor White
Write-Host ""

Push-Location $backendDir
try {
    if (-not (Test-Path (Join-Path $backendDir ".railway"))) {
        Write-Host "WARNING: backend/.railway not found. Run: npx @railway/cli link" -ForegroundColor Yellow
        Write-Host ""
    }

    $who = Invoke-RailwayCli whoami
    if ($who.ExitCode -ne 0 -or -not $who.Output) {
        Write-Host "ERROR: Railway CLI auth failed." -ForegroundColor Red
        Write-Host $who.Output -ForegroundColor DarkGray
        Write-Host ""
        Write-Host "Run: cd backend; npx @railway/cli login" -ForegroundColor Yellow
        Write-Host "Or paste manually: ..\scripts\print-railway-backend-env.ps1 -DatabaseUrl `"...`"" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Railway account: $($who.Output)" -ForegroundColor DarkGray
    Write-Host ""

    Set-RailwayVariable -Name "DATABASE_URL" -Value $dbUrl
    Set-RailwayVariable -Name "API_CORS_ORIGINS" -Value $cors
    if ($BillingInternalApiKey) {
        Set-RailwayVariable -Name "BILLING_INTERNAL_API_KEY" -Value $BillingInternalApiKey
    }

    Write-Host ""
    Write-Host "Variables set. Railway will redeploy the service automatically." -ForegroundColor Green
    Write-Host ""
    Write-Host "Next:" -ForegroundColor Cyan
    Write-Host "  1. Railway -> backend service -> Settings -> copy public URL" -ForegroundColor White
    Write-Host "  2. Vercel Production:" -ForegroundColor White
    Write-Host "       SFI_BACKEND_URL=https://YOUR-SERVICE.up.railway.app" -ForegroundColor White
    Write-Host "       NEXT_PUBLIC_API_URL=https://YOUR-SERVICE.up.railway.app" -ForegroundColor White
    Write-Host "  3. Redeploy Vercel, request fresh magic link" -ForegroundColor White
    Write-Host ""
}
finally {
    Pop-Location
}
