# gl-3 smoke test: plan entitlements on Neon DB + hosted API.
#
# Usage:
#   .\scripts\smoke-test-plan-entitlements.ps1
#   .\scripts\smoke-test-plan-entitlements.ps1 -KeepPlan starter   # leave starter for UI test
#   .\scripts\smoke-test-plan-entitlements.ps1 -ApiBase http://127.0.0.1:8001

param(
    [string]$OrganizationId = "8571e520-0687-4516-bdee-379f37c58c1f",
    [string]$DatabaseUrl = "",
    [string]$ApiBase = "https://sfi-api-production.up.railway.app",
    [ValidateSet("restore", "starter", "professional", "enterprise")]
    [string]$KeepPlan = "restore",
    [switch]$SkipApi,
    [switch]$LocalApi,
    [switch]$TryVercelPull
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\Resolve-ProdDatabaseUrl.ps1")

$repoRoot = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $repoRoot "backend"
$python = Join-Path $backendDir ".venv312\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

if ($LocalApi) {
    $ApiBase = "http://127.0.0.1:8001"
}

$resolved = Resolve-ProdDatabaseUrl -DatabaseUrl $DatabaseUrl -RepoRoot $repoRoot -TryVercelPull:$TryVercelPull -PreferSavedProdFile:(-not $DatabaseUrl)
if (-not $resolved) {
    Write-ProdDatabaseUrlHelp
    exit 1
}

$dbUrl = $resolved.Url
if ($dbUrl -match "^postgresql://") {
    $dbUrl = $dbUrl -replace "^postgresql://", "postgresql+psycopg://"
}

$dbHost = "unknown"
if ($dbUrl -match '@([^/]+)/') {
    $dbHost = $Matches[1]
}

Write-Host ""
Write-Host "Using DB from: $($resolved.Source)" -ForegroundColor DarkGray
Write-Host "DB host:       $dbHost" -ForegroundColor DarkGray
Write-Host "API base:      $ApiBase" -ForegroundColor DarkGray
if ($resolved.Source -eq "DATABASE_URL env var") {
    Write-Host ""
    Write-Host "NOTE: Shell DATABASE_URL is used. If this is sandbox Neon, entitlements API checks will fail." -ForegroundColor Yellow
    Write-Host "      Prefer: save-prod-database-url.ps1 or pass -DatabaseUrl / -TryVercelPull" -ForegroundColor Yellow
}
Write-Host ""

$argsList = @(
    (Join-Path $backendDir "scripts\smoke_plan_entitlements.py"),
    "--organization-id", $OrganizationId,
    "--api-base", $ApiBase,
    "--keep-plan", $KeepPlan
)
if ($SkipApi) { $argsList += "--skip-api" }

Push-Location $backendDir
try {
    $env:DATABASE_URL = $dbUrl
    & $python @argsList
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
