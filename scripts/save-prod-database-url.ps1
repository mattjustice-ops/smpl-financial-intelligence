# Save Neon production DATABASE_URL for ops scripts (gitignored).
#
# Usage:
#   .\scripts\save-prod-database-url.ps1 -DatabaseUrl "postgresql://...@ep-....neon.tech/neondb?sslmode=require"

param(
    [Parameter(Mandatory = $true)]
    [string]$DatabaseUrl
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\Resolve-ProdDatabaseUrl.ps1")

$url = $DatabaseUrl.Trim().Trim('"').Trim("'")
if (Test-IsLocalDatabaseUrl $url) {
    Write-Host "ERROR: Use the real Neon production URL (not localhost or ep-xxxx placeholder)." -ForegroundColor Red
    exit 1
}

$repoRoot = Split-Path $PSScriptRoot -Parent
$target = Join-Path $repoRoot "frontend\.env.neon-production.local"

@"
# Neon production DB (same as Vercel AUTH_DATABASE_URL and Railway DATABASE_URL)
# Gitignored - do not commit.

DATABASE_URL=$url

"@ | Set-Content -Path $target -Encoding UTF8

Write-Host ""
Write-Host "Saved to frontend/.env.neon-production.local" -ForegroundColor Green
Write-Host "Provision scripts will use this automatically." -ForegroundColor DarkGray
Write-Host ""
Write-Host "Run migrations against prod Neon:" -ForegroundColor Cyan
Write-Host "  .\scripts\run-alembic-migration.ps1 -Environment prod" -ForegroundColor White
Write-Host ""
