# Load local Postgres warehouse for board + forecast engine (localhost:3002).
#
# Usage (repo root):
#   .\scripts\setup-local-warehouse.ps1
#   .\scripts\setup-local-warehouse.ps1 -SkipMigrations   # resume after steps 1-3 already ran
#   .\scripts\setup-local-warehouse.ps1 -ListOnly

param(
    [string]$OrganizationId = "8571e520-0687-4516-bdee-379f37c58c1f",
    [string]$CsvFolder = "$env:USERPROFILE\OneDrive\Documents\simple CSVS",
    [string]$CloseMonth = "2026-06",
    [string]$DatabaseUrl = "",
    [switch]$SkipMigrations,
    [switch]$ListOnly
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent

if (-not $DatabaseUrl) {
    $localEnv = Join-Path $repoRoot "frontend\.env.local"
    if (Test-Path $localEnv) {
        foreach ($line in Get-Content $localEnv) {
            if ($line -match "^AUTH_DATABASE_URL=(.+)$") {
                $DatabaseUrl = $Matches[1].Trim()
                break
            }
        }
    }
}

if (-not $DatabaseUrl) {
    $DatabaseUrl = "postgresql://sfi:sfi_dev_password@localhost:5432/sfi"
}

Write-Host ""
Write-Host "=== Local warehouse load (board + forecast engine) ===" -ForegroundColor Cyan
Write-Host ""

& (Join-Path $repoRoot "scripts\setup-prod-warehouse.ps1") `
    -DatabaseUrl $DatabaseUrl `
    -OrganizationId $OrganizationId `
    -CsvFolder $CsvFolder `
    -CloseMonth $CloseMonth `
    -SkipMigrations:$SkipMigrations `
    -ListOnly:$ListOnly

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $ListOnly) {
    Write-Host ""
    Write-Host "Next:" -ForegroundColor Cyan
    Write-Host "  .\scripts\set-local-demo-enterprise.ps1 -Email you@company.com" -ForegroundColor White
    Write-Host "  cd backend; .\restart-api.ps1 -Port 8001" -ForegroundColor White
    Write-Host "  cd frontend; npm run dev" -ForegroundColor White
}
