# Resolve Neon/Railway production DATABASE_URL for ops scripts.
# Skips localhost. Optional Vercel env pull when logged in via CLI.

function Test-IsPlaceholderDatabaseUrl {
    param([string]$Url)
    if (-not $Url) { return $true }
    return ($Url -match "(?i)ep-xxxx|USER:PASSWORD|YOUR_PASSWORD|YOUR-PASSWORD|REPLACE_ME|@USER@|password@ep-|://user:")
}

function Test-IsLocalDatabaseUrl {
    param([string]$Url)
    if (-not $Url) { return $true }
    if (Test-IsPlaceholderDatabaseUrl $Url) { return $true }
    return ($Url -match "localhost|127\.0\.0\.1|:5432/sfi\b|YOUR-RAILWAY")
}

function Get-DatabaseUrlFromEnvFile {
    param([string]$FilePath)

    if (-not (Test-Path -LiteralPath $FilePath)) {
        return $null
    }

    $names = @("DATABASE_URL", "AUTH_DATABASE_URL", "NEON_DATABASE_URL")
    foreach ($line in Get-Content -LiteralPath $FilePath) {
        $trimmed = $line.Trim()
        if ($trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) { continue }
        foreach ($name in $names) {
            if ($trimmed -match "^$([regex]::Escape($name))=(.+)$") {
                $value = $Matches[1].Trim().Trim('"').Trim("'")
                if (-not (Test-IsLocalDatabaseUrl $value)) {
                    return @{ Url = $value; Source = $FilePath; Name = $name }
                }
            }
        }
    }
    return $null
}

function Get-DatabaseUrlFromVercelPull {
    param(
        [string]$FrontendDir,
        [string]$Scope = "smplai",
        [string]$Project = "smpl-financial-intelligence"
    )

    $tmpFile = Join-Path $env:TEMP ("sfi-vercel-env-{0}.local" -f [guid]::NewGuid().ToString("N"))
    $npxArgs = @("--yes", "vercel@latest", "--scope", $Scope, "--project", $Project)
    if ($env:VERCEL_TOKEN) {
        $npxArgs += @("--token", $env:VERCEL_TOKEN)
    }

    Push-Location $FrontendDir
    try {
        $null = & npx @npxArgs env pull $tmpFile production --yes 2>&1
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $tmpFile)) {
            return $null
        }
        $found = Get-DatabaseUrlFromEnvFile -FilePath $tmpFile
        if ($found) {
            $found.Source = "Vercel Production (env pull)"
        }
        return $found
    }
    finally {
        Pop-Location
        Remove-Item -LiteralPath $tmpFile -Force -ErrorAction SilentlyContinue
    }
}

function Resolve-ProdDatabaseUrl {
    param(
        [string]$DatabaseUrl = "",
        [string]$RepoRoot = "",
        [switch]$TryVercelPull,
        [switch]$PreferSavedProdFile
    )

    if ($DatabaseUrl -and -not (Test-IsLocalDatabaseUrl $DatabaseUrl)) {
        return @{ Url = $DatabaseUrl.Trim().Trim('"').Trim("'"); Source = "-DatabaseUrl parameter"; Name = "DATABASE_URL" }
    }

    if (-not $RepoRoot) {
        $RepoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
        if (-not (Test-Path (Join-Path $RepoRoot "backend"))) {
            $RepoRoot = Split-Path $PSScriptRoot -Parent
        }
    }

    $frontendDir = Join-Path $RepoRoot "frontend"
    $fileCandidates = @(
        (Join-Path $frontendDir ".env.neon-production.local"),
        (Join-Path $frontendDir ".env.vercel-production.local"),
        (Join-Path $frontendDir ".env.production.local")
    )

    if ($PreferSavedProdFile) {
        foreach ($file in $fileCandidates) {
            $found = Get-DatabaseUrlFromEnvFile -FilePath $file
            if ($found) { return $found }
        }
    }

    if ($env:DATABASE_URL -and -not (Test-IsLocalDatabaseUrl $env:DATABASE_URL)) {
        return @{ Url = $env:DATABASE_URL.Trim(); Source = "DATABASE_URL env var"; Name = "DATABASE_URL" }
    }
    if ($env:NEON_DATABASE_URL -and -not (Test-IsLocalDatabaseUrl $env:NEON_DATABASE_URL)) {
        return @{ Url = $env:NEON_DATABASE_URL.Trim(); Source = "NEON_DATABASE_URL env var"; Name = "NEON_DATABASE_URL" }
    }
    if ($env:AUTH_DATABASE_URL -and -not (Test-IsLocalDatabaseUrl $env:AUTH_DATABASE_URL)) {
        return @{ Url = $env:AUTH_DATABASE_URL.Trim(); Source = "AUTH_DATABASE_URL env var"; Name = "AUTH_DATABASE_URL" }
    }

    if ($TryVercelPull) {
        $fromVercel = Get-DatabaseUrlFromVercelPull -FrontendDir $frontendDir
        if ($fromVercel) { return $fromVercel }
    }

    foreach ($file in $fileCandidates) {
        $found = Get-DatabaseUrlFromEnvFile -FilePath $file
        if ($found) { return $found }
    }

    return $null
}

function Write-ProdDatabaseUrlHelp {
    Write-Host ""
    Write-Host "Could not find a real production Neon connection string." -ForegroundColor Red
    Write-Host ""
    Write-Host "Your frontend/.env.neon-production.local may still be the example (ep-xxxx)." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Option A - save the real URL once (recommended):" -ForegroundColor Yellow
    Write-Host "  1. Neon dashboard -> Connection details -> copy connection string" -ForegroundColor White
    Write-Host "     OR Vercel -> smpl-financial-intelligence -> Settings -> AUTH_DATABASE_URL" -ForegroundColor White
    Write-Host '  2. .\scripts\save-prod-database-url.ps1 -DatabaseUrl "postgresql://...@ep-REAL.neon.tech/neondb?sslmode=require"' -ForegroundColor White
    Write-Host '  3. .\scripts\run-alembic-migration.ps1 -Environment prod' -ForegroundColor White
    Write-Host ""
    Write-Host "Option B - pass inline for this run only:" -ForegroundColor Yellow
    Write-Host '  .\scripts\smoke-test-plan-entitlements.ps1 -DatabaseUrl "postgresql://..."' -ForegroundColor White
    Write-Host ""
    Write-Host "Option C - Vercel CLI pull (requires: npx vercel login):" -ForegroundColor Yellow
    Write-Host "  .\scripts\smoke-test-plan-entitlements.ps1 -TryVercelPull" -ForegroundColor White
    Write-Host ""
}
