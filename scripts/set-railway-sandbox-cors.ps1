# Set API_CORS_ORIGINS on Railway sandbox API (sfi-api-staging) for gl-5b-sandbox Preview URLs.
#
# Prerequisites:
#   npx @railway/cli login
#   cd backend && npx @railway/cli link   (select sfi-api-staging)
#
# Usage (repo root):
#   .\scripts\set-railway-sandbox-cors.ps1
#   .\scripts\set-railway-sandbox-cors.ps1 -ServiceName "sfi-api-staging"

param(
    [string]$ServiceName = "sfi-api-staging",
    [string]$SandboxBranch = "gl-5b-sandbox",
    [string]$TeamSlug = "smplai",
    [string]$ProjectSlug = "smpl-financial-intelligence",
    [string]$ProdFrontendUrl = "https://smpl-financial-intelligence.vercel.app",
    [string]$RailwayToken = "",
    [switch]$PrintOnly
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $repoRoot "backend"

if ($RailwayToken) {
    $env:RAILWAY_TOKEN = $RailwayToken.Trim()
}

function Get-RailwayInvoker {
    if (Get-Command railway -ErrorAction SilentlyContinue) {
        return @{
            Label  = "railway"
            Invoke = { param([string[]]$CliArgs) & railway @CliArgs }
        }
    }
    return @{
        Label  = "npx @railway/cli"
        Invoke = { param([string[]]$CliArgs) & npx --yes @railway/cli @CliArgs }
    }
}

function Invoke-RailwayCli {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$CliArgs)

    Push-Location $backendDir
    try {
        $raw = & $railwayInvoker.Invoke $CliArgs 2>&1
        $lines = @()
        foreach ($item in $raw) { $lines += "$item" }
        return @{
            ExitCode = $LASTEXITCODE
            Output   = ($lines -join "`n").Trim()
        }
    }
    finally {
        Pop-Location
    }
}

function Get-SandboxCorsOrigins {
    param(
        [string]$Branch,
        [string]$Team,
        [string]$Project,
        [string]$ProdUrl
    )

    $origins = @(
        $ProdUrl
        "https://${Project}-git-${Branch}-${Team}.vercel.app"
        "https://${Project}-mattjustice-ops-${Team}.vercel.app"
        "http://localhost:3002"
        "http://127.0.0.1:3002"
    )

    return ($origins | Select-Object -Unique) -join ","
}

$railwayInvoker = Get-RailwayInvoker

Write-Host ""
Write-Host "=== Railway sandbox CORS (sfi-api-staging) ===" -ForegroundColor Cyan
Write-Host ""

$cors = Get-SandboxCorsOrigins -Branch $SandboxBranch -Team $TeamSlug -Project $ProjectSlug -ProdUrl $ProdFrontendUrl

Write-Host "Service: $ServiceName" -ForegroundColor DarkGray
Write-Host "CORS origins:" -ForegroundColor Yellow
foreach ($origin in ($cors -split ",")) {
    Write-Host "  $origin" -ForegroundColor DarkGray
}
Write-Host ""

if ($PrintOnly) {
    Write-Host "Dashboard: Railway -> smpl-ai -> $ServiceName -> Variables" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "API_CORS_ORIGINS" -ForegroundColor Green
    Write-Host $cors
    Write-Host ""
    exit 0
}

$who = Invoke-RailwayCli whoami
if ($who.ExitCode -ne 0 -or -not $who.Output) {
    Write-Host "ERROR: Railway CLI not logged in." -ForegroundColor Red
    Write-Host $who.Output -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "Run:" -ForegroundColor Yellow
    Write-Host "  cd backend" -ForegroundColor White
    Write-Host "  npx @railway/cli login" -ForegroundColor White
    Write-Host "  npx @railway/cli link   # select sfi-api-staging" -ForegroundColor White
    Write-Host ""
    Write-Host "Dashboard fallback - paste into Railway -> $ServiceName -> Variables:" -ForegroundColor Yellow
    Write-Host "API_CORS_ORIGINS" -ForegroundColor Green
    Write-Host $cors
    Write-Host ""
    exit 1
}

Write-Host "Railway account: $($who.Output -split "`n" | Where-Object { $_ -and $_ -notmatch 'Vercel CLI|railway' } | Select-Object -First 1)" -ForegroundColor DarkGray
Write-Host ""

$setArgs = @("variables", "--set", "API_CORS_ORIGINS=$cors")
if ($ServiceName) {
    $setArgs += @("--service", $ServiceName)
}

$result = Invoke-RailwayCli @setArgs
if ($result.ExitCode -ne 0) {
    Write-Host "WARN: --service failed; trying linked service..." -ForegroundColor Yellow
    if ($result.Output) { Write-Host $result.Output -ForegroundColor DarkGray }
    $result = Invoke-RailwayCli variables --set "API_CORS_ORIGINS=$cors"
}

if ($result.ExitCode -ne 0) {
    Write-Host "FAIL: could not set API_CORS_ORIGINS." -ForegroundColor Red
    Write-Host $result.Output -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "Dashboard fallback:" -ForegroundColor Yellow
    Write-Host "API_CORS_ORIGINS=$cors" -ForegroundColor White
    exit 1
}

Write-Host "OK: API_CORS_ORIGINS updated on Railway $ServiceName" -ForegroundColor Green
Write-Host "Railway will redeploy the service automatically." -ForegroundColor DarkGray
Write-Host ""

# Verify DATABASE_URL host if staging config exists
$stagingFile = Join-Path $repoRoot "frontend\.env.staging.local"
if (Test-Path $stagingFile) {
    foreach ($line in Get-Content $stagingFile) {
        if ($line -match '^STAGING_DATABASE_URL=(.+)$') {
            $db = $Matches[1].Trim()
            if ($db -match '@([^/]+)/') {
                $dbHost = $Matches[1]
                if ($dbHost -match 'fragrant-grass') {
                    Write-Host "OK: Local sandbox Neon host matches staging branch ($dbHost)" -ForegroundColor Green
                }
                else {
                    Write-Host "WARN: STAGING_DATABASE_URL host is $dbHost (expected fragrant-grass sandbox Neon)" -ForegroundColor Yellow
                }
            }
            break
        }
    }
}

Write-Host ""
Write-Host "Next: open sandbox Preview, hard refresh /app, confirm dashboards load." -ForegroundColor Cyan
Write-Host ""
