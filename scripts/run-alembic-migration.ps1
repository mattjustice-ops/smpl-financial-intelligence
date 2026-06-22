# Run Alembic migrations using saved Neon URLs (no copy/paste).
#
# Prod URL:    frontend/.env.neon-production.local  (DATABASE_URL)
# Sandbox URL: frontend/.env.staging.local           (STAGING_DATABASE_URL)
#
# Usage (repo root):
#   .\scripts\run-alembic-migration.ps1 -Environment prod
#   .\scripts\run-alembic-migration.ps1 -Environment sandbox
#   .\scripts\run-alembic-migration.ps1 -Environment both
#   .\scripts\run-alembic-migration.ps1 -Environment prod -DatabaseUrl "postgresql://..."

param(
    [ValidateSet("prod", "sandbox", "both")]
    [string]$Environment = "prod",
    [string]$DatabaseUrl = "",
    [switch]$SkipConfirm
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $repoRoot "backend"
$python = Join-Path $backendDir ".venv312\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

. (Join-Path $PSScriptRoot "lib\Convert-DatabaseUrl.ps1")
. (Join-Path $PSScriptRoot "lib\Resolve-ProdDatabaseUrl.ps1")
. (Join-Path $PSScriptRoot "lib\Resolve-StagingConfig.ps1")

function Resolve-MigrationTarget {
    param(
        [ValidateSet("prod", "sandbox")]
        [string]$Name,
        [string]$OverrideUrl = ""
    )

    if ($OverrideUrl -and -not (Test-IsLocalDatabaseUrl $OverrideUrl)) {
        return @{
            Label  = $Name
            Url    = $OverrideUrl.Trim().Trim('"').Trim("'")
            Source = "-DatabaseUrl parameter"
        }
    }

    if ($Name -eq "prod") {
        $resolved = Resolve-ProdDatabaseUrl -RepoRoot $repoRoot -PreferSavedProdFile
        if (-not $resolved) {
            Write-ProdDatabaseUrlHelp
            exit 1
        }
        $hostName = Get-DatabaseUrlHost $resolved.Url
        if ($hostName -match "fragrant-grass") {
            Write-Host "ERROR: Resolved prod URL looks like sandbox Neon ($hostName)." -ForegroundColor Red
            Write-Host "Fix frontend/.env.neon-production.local or pass -DatabaseUrl explicitly." -ForegroundColor Yellow
            exit 1
        }
        return @{
            Label  = "production"
            Url    = $resolved.Url
            Source = "$($resolved.Name) from $($resolved.Source)"
        }
    }

    $staging = Resolve-StagingConfig -RepoRoot $repoRoot
    if (-not $staging.DatabaseUrl) {
        Write-Host ""
        Write-Host "ERROR: Could not find STAGING_DATABASE_URL." -ForegroundColor Red
        Write-Host "Save it in frontend/.env.staging.local (see scripts/config/staging.env.example)." -ForegroundColor Yellow
        Write-StagingConfigHelp
        exit 1
    }
    $hostName = Get-DatabaseUrlHost $staging.DatabaseUrl.Url
    if ($hostName -match "cool-moon") {
        Write-Host "ERROR: Resolved sandbox URL looks like production Neon ($hostName)." -ForegroundColor Red
        exit 1
    }
    return @{
        Label  = "sandbox"
        Url    = $staging.DatabaseUrl.Url
        Source = "$($staging.DatabaseUrl.Name) from $($staging.DatabaseUrl.Source)"
    }
}

function Invoke-AlembicUpgrade {
    param(
        [hashtable]$Target
    )

    $alembicUrl = Convert-ToAlembicDatabaseUrl $Target.Url
    $hostName = Get-DatabaseUrlHost $alembicUrl

    Write-Host ""
    Write-Host "=== Alembic upgrade ($($Target.Label)) ===" -ForegroundColor Cyan
    Write-Host "Host: $hostName" -ForegroundColor DarkGray
    Write-Host "Source: $($Target.Source)" -ForegroundColor DarkGray
    Write-Host ""

    if (-not $SkipConfirm) {
        $answer = Read-Host "Run 'alembic upgrade head' on $($Target.Label)? [y/N]"
        if ($answer -notmatch '^[yY]') {
            Write-Host "Skipped $($Target.Label)." -ForegroundColor Yellow
            return
        }
    }

    Push-Location $backendDir
    try {
        $env:DATABASE_URL = $alembicUrl
        Write-Host "Current revision:" -ForegroundColor Yellow
        & $python -m alembic current
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

        Write-Host ""
        Write-Host "Upgrading..." -ForegroundColor Yellow
        & $python -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

        Write-Host ""
        Write-Host "After upgrade:" -ForegroundColor Green
        & $python -m alembic current
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    finally {
        Pop-Location
    }
}

Write-Host ""
Write-Host "Saved database URLs:" -ForegroundColor Cyan
Write-Host "  prod:    frontend/.env.neon-production.local" -ForegroundColor DarkGray
Write-Host "  sandbox: frontend/.env.staging.local (STAGING_DATABASE_URL)" -ForegroundColor DarkGray

$targets = @()
if ($Environment -eq "prod" -or $Environment -eq "both") {
    $override = if ($Environment -eq "prod") { $DatabaseUrl } else { "" }
    $targets += Resolve-MigrationTarget -Name "prod" -OverrideUrl $override
}
if ($Environment -eq "sandbox" -or $Environment -eq "both") {
    $override = if ($Environment -eq "sandbox") { $DatabaseUrl } else { "" }
    $targets += Resolve-MigrationTarget -Name "sandbox" -OverrideUrl $override
}

foreach ($target in $targets) {
    Invoke-AlembicUpgrade -Target $target
}

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host ""
