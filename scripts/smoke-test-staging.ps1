# gl-5: run staging smoke suite before merging to production.
#
# Usage:
#   .\scripts\smoke-test-staging.ps1
#   .\scripts\smoke-test-staging.ps1 -SkipEntitlements

param(
    [string]$ApiBase = "",
    [string]$DatabaseUrl = "",
    [string]$OrganizationId = "",
    [switch]$SkipEntitlements,
    [switch]$SkipVerify,
    [switch]$AllowProduction
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\Resolve-StagingConfig.ps1")

$repoRoot = Split-Path $PSScriptRoot -Parent
$config = Resolve-StagingConfig `
    -ApiBase $ApiBase `
    -DatabaseUrl $DatabaseUrl `
    -RepoRoot $repoRoot `
    -AllowProduction:$AllowProduction

if (-not $config.ApiBase) {
    Write-StagingConfigHelp
    exit 1
}
if ($config.ApiBase.ProductionBlocked) {
    Write-Host "ERROR: Refusing to run staging smoke against production API." -ForegroundColor Red
    exit 1
}

$resolvedApi = $config.ApiBase.Url
$resolvedDb = if ($config.DatabaseUrl) { $config.DatabaseUrl.Url } else { "" }

if (-not $OrganizationId) {
    $orgFromFile = Get-EnvValueFromFile -FilePath (Join-Path $repoRoot "frontend\.env.staging.local") -Names @("STAGING_ORGANIZATION_ID")
    if (-not $orgFromFile) {
        $orgFromFile = Get-EnvValueFromFile -FilePath (Join-Path $repoRoot "scripts\config\staging.env.example") -Names @("STAGING_ORGANIZATION_ID")
    }
    if ($orgFromFile) {
        $OrganizationId = $orgFromFile.Value
    }
    else {
        $OrganizationId = "8571e520-0687-4516-bdee-379f37c58c1f"
    }
}

Write-Host ""
Write-Host "=== gl-5 staging smoke ===" -ForegroundColor Cyan
Write-Host ""

if (-not $SkipVerify) {
    $verifyArgs = @(
        "-File", (Join-Path $PSScriptRoot "verify-staging-stack.ps1"),
        "-ApiBase", $resolvedApi
    )
    if ($resolvedDb) {
        $verifyArgs += @("-DatabaseUrl", $resolvedDb)
    }
    & pwsh @verifyArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    Write-Host ""
}

if ($SkipEntitlements) {
    Write-Host "Skipped plan entitlements smoke (-SkipEntitlements)." -ForegroundColor Yellow
    exit 0
}

if (-not $resolvedDb) {
    Write-Host "ERROR: STAGING_DATABASE_URL required for entitlements smoke." -ForegroundColor Red
    Write-Host "Save with .\scripts\save-staging-config.ps1 or pass -DatabaseUrl" -ForegroundColor Yellow
    exit 1
}

$entArgs = @(
    "-File", (Join-Path $PSScriptRoot "smoke-test-plan-entitlements.ps1"),
    "-ApiBase", $resolvedApi,
    "-DatabaseUrl", $resolvedDb,
    "-OrganizationId", $OrganizationId,
    "-KeepPlan", "restore"
)
& pwsh @entArgs
exit $LASTEXITCODE
