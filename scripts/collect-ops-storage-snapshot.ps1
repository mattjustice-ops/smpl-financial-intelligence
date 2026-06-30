# Record a Neon storage_snapshot (daily cron / Task Scheduler).
#
# Usage (repo root):
#   .\scripts\collect-ops-storage-snapshot.ps1 -Local
#   .\scripts\collect-ops-storage-snapshot.ps1
#   .\scripts\collect-ops-storage-snapshot.ps1 -TryVercelPull
#   .\scripts\collect-ops-storage-snapshot.ps1 -Force
#
# -Local hits Neon directly (uses frontend/.env.neon-production.local) — no API key.
# Default mode POSTs to Railway /api/v1/ops/collect-storage-snapshot (needs billing key).

param(
    [string]$ApiBase = "https://sfi-api-production.up.railway.app",
    [switch]$Local,
    [switch]$Force,
    [switch]$TryVercelPull
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $repoRoot "backend"
$python = Join-Path $backendDir ".venv312\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

function Invoke-LocalStorageSnapshot {
    . (Join-Path $PSScriptRoot "lib\Convert-DatabaseUrl.ps1")
    . (Join-Path $PSScriptRoot "lib\Resolve-ProdDatabaseUrl.ps1")

    $resolved = Resolve-ProdDatabaseUrl -RepoRoot $repoRoot -PreferSavedProdFile
    if (-not $resolved) {
        Write-ProdDatabaseUrlHelp
        exit 1
    }

    Write-Host ""
    Write-Host "=== Storage snapshot (local Neon) ===" -ForegroundColor Cyan
    Write-Host "Source: $($resolved.Source)" -ForegroundColor DarkGray
    Write-Host ""

    Push-Location $backendDir
    try {
        $env:DATABASE_URL = Convert-ToAlembicDatabaseUrl $resolved.Url
        $args = @(Join-Path $backendDir "scripts\collect_storage_snapshot.py")
        if ($Force) { $args += "--force" }
        & $python @args
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    finally {
        Pop-Location
    }
}

function Invoke-ApiStorageSnapshot {
    . (Join-Path $PSScriptRoot "lib\Resolve-BillingInternalKey.ps1")

    $resolvedKey = Resolve-BillingInternalKey -RepoRoot $repoRoot -TryVercelPull:$TryVercelPull
    if (-not $resolvedKey) {
        Write-BillingInternalKeyHelp
        exit 1
    }

    Write-Host ""
    Write-Host "=== Storage snapshot (production API) ===" -ForegroundColor Cyan
    Write-Host "Key source: $($resolvedKey.Source)" -ForegroundColor DarkGray
    Write-Host ""

    $uri = "$ApiBase/api/v1/ops/collect-storage-snapshot"
    if ($Force) { $uri += "?force=true" }

    $headers = @{ "X-Billing-Internal-Key" = $resolvedKey.Key }
    $result = Invoke-RestMethod -Method Post -Uri $uri -Headers $headers -TimeoutSec 180

    Write-Host "Storage snapshot recorded." -ForegroundColor Green
    Write-Host "  database_gb=$($result.snapshot.database_gb)" -ForegroundColor DarkGray
    Write-Host "  tenant_table_gb=$($result.snapshot.tenant_table_gb)" -ForegroundColor DarkGray
    $orgCount = 0
    if ($result.snapshot.org_footprint) {
        $orgCount = @($result.snapshot.org_footprint.PSObject.Properties).Count
    }
    Write-Host "  orgs=$orgCount" -ForegroundColor DarkGray
    Write-Host ""
}

if ($Local) {
    Invoke-LocalStorageSnapshot
}
else {
    Invoke-ApiStorageSnapshot
}
