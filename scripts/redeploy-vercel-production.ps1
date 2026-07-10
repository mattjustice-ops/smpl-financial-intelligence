# Redeploy Vercel Production (picks up latest env vars without a git push).
#
# Use after changing Vercel Environment Variables (e.g. Stripe gl-4 keys)
# or when you need a fresh production build on the current main commit.
#
# Usage (repo root):
#   .\scripts\redeploy-vercel-production.ps1
#   .\scripts\redeploy-vercel-production.ps1 -SkipBuild
#   .\scripts\redeploy-vercel-production.ps1 -SkipBuild -SmokeTest
#
# Prerequisites:
#   - vercel login   OR   VERCEL_TOKEN env var
#   - Project: smpl-financial-intelligence (Root Directory = frontend)

param(
    [switch]$SkipBuild,
    [switch]$SmokeTest,
    [string]$Scope = "smplai",
    [string]$Project = "smpl-financial-intelligence",
    [string]$FrontendUrl = "https://www.smpl-ai.com",
    [string]$VercelAliasUrl = "https://smpl-financial-intelligence.vercel.app",
    [int]$PollSeconds = 300,
    [int]$PollIntervalSeconds = 15
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$frontendDir = Join-Path $repoRoot "frontend"

function Get-NpxVercelArgs {
    $args = @("--yes", "vercel@latest", "--scope", $Scope, "--project", $Project)
    if ($env:VERCEL_TOKEN) {
        $args += @("--token", $env:VERCEL_TOKEN.Trim())
    }
    return $args
}

function Test-FrontendReachable {
    param(
        [string]$Url,
        [int]$TimeoutSec = 30
    )
    try {
        $res = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec $TimeoutSec -UseBasicParsing
        return @{ Ok = ($res.StatusCode -eq 200); StatusCode = $res.StatusCode; Body = $res.Content }
    } catch {
        $code = $null
        if ($_.Exception.Response) {
            $code = [int]$_.Exception.Response.StatusCode
        }
        return @{ Ok = $false; StatusCode = $code; Body = $_.Exception.Message }
    }
}

Write-Host ""
Write-Host "=== Redeploy Vercel Production ===" -ForegroundColor Cyan
Write-Host "Project: $Project ($Scope)" -ForegroundColor DarkGray
Write-Host "Site:    $FrontendUrl" -ForegroundColor DarkGray
Write-Host ""

if (-not $SkipBuild) {
    Write-Host "1. Local production build (same checks as Vercel prebuild)..." -ForegroundColor Yellow
    Push-Location $frontendDir
    try {
        npm install 2>&1 | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
        $buildLog = Join-Path $repoRoot "deploy-build.log"
        npm run build 2>&1 | Tee-Object -FilePath $buildLog
        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "BUILD FAILED - fix before redeploying. See $buildLog" -ForegroundColor Red
            exit 1
        }
        Write-Host "   Build OK." -ForegroundColor Green
    } finally {
        Pop-Location
    }
} else {
    Write-Host "1. Skipping local build (-SkipBuild)." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "2. Triggering Vercel production deploy..." -ForegroundColor Yellow
Push-Location $frontendDir
try {
    $npxArgs = Get-NpxVercelArgs
    & npx @npxArgs deploy --prod --yes
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "Deploy failed. Try: vercel login" -ForegroundColor Red
        Write-Host "Or set VERCEL_TOKEN and rerun." -ForegroundColor Yellow
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "3. Waiting for production URLs to respond..." -ForegroundColor Yellow
$deadline = (Get-Date).AddSeconds($PollSeconds)
$ready = $false
$attempt = 0
while ((Get-Date) -lt $deadline) {
    $attempt++
    $primary = Test-FrontendReachable -Url "$FrontendUrl/api/smpl/board-config"
    $alias = Test-FrontendReachable -Url "$VercelAliasUrl/api/smpl/board-config"
    if ($primary.Ok -or $alias.Ok) {
        $ready = $true
        $hit = if ($primary.Ok) { $FrontendUrl } else { $VercelAliasUrl }
        Write-Host "   OK: $hit responded (attempt $attempt)" -ForegroundColor Green
        break
    }
    $code = if ($null -ne $primary.StatusCode) { $primary.StatusCode } else { "..." }
    Write-Host "   Attempt $attempt - not ready yet (HTTP $code). Retrying in ${PollIntervalSeconds}s..." -ForegroundColor DarkYellow
    Start-Sleep -Seconds $PollIntervalSeconds
}

if (-not $ready) {
    Write-Host ""
    Write-Host "Deploy triggered but site did not respond within ${PollSeconds}s." -ForegroundColor Yellow
    Write-Host "Check https://vercel.com/$Scope/$Project/deployments" -ForegroundColor DarkGray
    exit 1
}

Write-Host ""
Write-Host "=== Redeploy complete ===" -ForegroundColor Green
Write-Host "  $FrontendUrl"
Write-Host "  $VercelAliasUrl"
Write-Host ""
Write-Host "Hard refresh after env changes: Ctrl+Shift+R on /app/board" -ForegroundColor Cyan
Write-Host ""

if ($SmokeTest) {
    Write-Host "4. Running Stripe/board smoke tests..." -ForegroundColor Yellow
    $stripeSmoke = Join-Path $PSScriptRoot "smoke-test-stripe-prod.ps1"
    if (Test-Path $stripeSmoke) {
        & $stripeSmoke -FrontendUrl $FrontendUrl
    } else {
        Write-Host "   smoke-test-stripe-prod.ps1 not found - skipped" -ForegroundColor DarkGray
    }
}
