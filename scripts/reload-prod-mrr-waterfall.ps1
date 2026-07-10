# Reload full Actual_MRR_Waterfall.csv into Neon prod (full org snapshot replace).
#
# Usage:
#   .\scripts\reload-prod-mrr-waterfall.ps1
#   .\scripts\reload-prod-mrr-waterfall.ps1 -DatabaseUrl "postgresql://..."

param(
    [string]$DatabaseUrl = "",
    [string]$OrganizationId = "8571e520-0687-4516-bdee-379f37c58c1f",
    [string]$CsvPath = "$env:USERPROFILE\OneDrive\Documents\simple CSVS\Actual_MRR_Waterfall.csv"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
. (Join-Path $PSScriptRoot "lib\Resolve-ProdDatabaseUrl.ps1")

$resolved = Resolve-ProdDatabaseUrl -DatabaseUrl $DatabaseUrl -RepoRoot $repoRoot -PreferSavedProdFile
if (-not $resolved) {
    Write-ProdDatabaseUrlHelp
    exit 1
}

$backendDir = Join-Path $repoRoot "backend"
$python = Join-Path $backendDir ".venv312\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

$env:DATABASE_URL = $resolved.Url
Write-Host "Reloading Actual_MRR_Waterfall.csv -> Neon ($($resolved.Source))" -ForegroundColor Cyan
Write-Host ""

& $python (Join-Path $backendDir "scripts\reload_actual_mrr_waterfall.py") `
    --organization-id $OrganizationId `
    --csv $CsvPath

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Done. Hard-refresh /app/board and check SMPL Ops -> Platform health." -ForegroundColor Green
