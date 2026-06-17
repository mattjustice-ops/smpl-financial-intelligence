# Save staging API + Neon URLs for gl-5 ops scripts (gitignored).
#
# Usage:
#   .\scripts\save-staging-config.ps1 `
#     -ApiBase "https://sfi-api-staging-xxxx.up.railway.app" `
#     -DatabaseUrl "postgresql://...@ep-STAGING.neon.tech/neondb?sslmode=require"

param(
    [Parameter(Mandatory = $true)]
    [string]$ApiBase,
    [Parameter(Mandatory = $true)]
    [string]$DatabaseUrl,
    [string]$FrontendUrl = ""
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\Resolve-StagingConfig.ps1")

$api = $ApiBase.Trim().Trim('"').Trim("'").TrimEnd("/")
$db = $DatabaseUrl.Trim().Trim('"').Trim("'")
$frontend = $FrontendUrl.Trim().TrimEnd("/")

if (Test-IsPlaceholderUrl $api) {
    Write-Host "ERROR: Use your real Railway staging URL." -ForegroundColor Red
    exit 1
}
if (Test-IsLocalDatabaseUrl $db) {
    Write-Host "ERROR: Use the real Neon staging branch URL (not localhost or ep-xxxx placeholder)." -ForegroundColor Red
    exit 1
}
if ((Test-IsProductionApiUrl $api)) {
    Write-Host "ERROR: That looks like production API. Create a separate Railway staging service." -ForegroundColor Red
    exit 1
}

$repoRoot = Split-Path $PSScriptRoot -Parent
$target = Join-Path $repoRoot "frontend\.env.staging.local"

$lines = @(
    "# Staging stack (gl-5) - gitignored. Do not commit.",
    "",
    "STAGING_API_URL=$api",
    "STAGING_DATABASE_URL=$db"
)
if ($frontend) {
    $lines += "STAGING_FRONTEND_URL=$frontend"
}
$lines += ""

$lines -join "`n" | Set-Content -Path $target -Encoding UTF8

Write-Host ""
Write-Host "Saved to frontend/.env.staging.local" -ForegroundColor Green
Write-Host "Next: .\scripts\verify-staging-stack.ps1" -ForegroundColor Yellow
Write-Host ""
