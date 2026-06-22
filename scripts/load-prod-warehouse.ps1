# Step 3 - Load validated CSV pack into Neon production warehouse.
#
# Usage:
#   .\scripts\load-prod-warehouse.ps1
#   .\scripts\load-prod-warehouse.ps1 -DatabaseUrl "postgresql://..."
#   .\scripts\load-prod-warehouse.ps1 -ListOnly

param(
    [string]$DatabaseUrl = "",
    [string]$CsvFolder = "$env:USERPROFILE\OneDrive\Documents\simple CSVS",
    [string]$OrganizationId = "8571e520-0687-4516-bdee-379f37c58c1f",
    [string]$CloseMonth = "2026-06",
    [switch]$SkipValidation,
    [switch]$ListOnly
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
. (Join-Path $PSScriptRoot "lib\Resolve-ProdDatabaseUrl.ps1")

Write-Host ""
Write-Host "=== Step 3: Neon production warehouse load ===" -ForegroundColor Cyan
Write-Host ""

if (-not $SkipValidation -and -not $ListOnly) {
    Write-Host "Validating CSV pack..." -ForegroundColor Yellow
    Push-Location (Join-Path $repoRoot "frontend")
    try {
        node scripts/validate-csv-pack.mjs 2>&1 | Write-Host
        if ($LASTEXITCODE -ne 0) {
            Write-Host "WARN: validation reported issues - review validate-csv-pack-result.json" -ForegroundColor Yellow
        }
    }
    finally {
        Pop-Location
    }
    Write-Host ""
}

$resolved = Resolve-ProdDatabaseUrl -DatabaseUrl $DatabaseUrl -RepoRoot $repoRoot -PreferSavedProdFile
if (-not $resolved) {
    Write-ProdDatabaseUrlHelp
    exit 1
}

Write-Host "Using DB from: $($resolved.Source)" -ForegroundColor DarkGray
Write-Host ""

$setupParams = @{
    DatabaseUrl    = $resolved.Url
    CsvFolder      = $CsvFolder
    OrganizationId = $OrganizationId
}
if ($CloseMonth) { $setupParams.CloseMonth = $CloseMonth }
if ($ListOnly) { $setupParams.ListOnly = $true }

& (Join-Path $repoRoot "scripts\setup-prod-warehouse.ps1") @setupParams
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $ListOnly) {
    Write-Host ""
    Write-Host "Warehouse load complete." -ForegroundColor Green
    Write-Host 'Next: restart Railway API if needed, then hard-refresh Board and Forecast Engine.' -ForegroundColor Yellow
    Write-Host ""
}
