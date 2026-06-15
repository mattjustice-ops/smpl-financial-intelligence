# Resolve Neon/Railway production DATABASE_URL for ops scripts.
# Skips localhost. Optional Vercel env pull when logged in via CLI.

function Test-IsLocalDatabaseUrl {
    param([string]$Url)
    if (-not $Url) { return $true }
    return ($Url -match "localhost|127\.0\.0\.1|:5432/sfi\b|YOUR_PASSWORD|YOUR-RAILWAY")
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
        [switch]$TryVercelPull
    )

    if ($DatabaseUrl -and -not (Test-IsLocalDatabaseUrl $DatabaseUrl)) {
        return @{ Url = $DatabaseUrl.Trim().Trim('"').Trim("'"); Source = "-DatabaseUrl parameter"; Name = "DATABASE_URL" }
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

    if (-not $RepoRoot) {
        $RepoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
        if (-not (Test-Path (Join-Path $RepoRoot "backend"))) {
            $RepoRoot = Split-Path $PSScriptRoot -Parent
        }
    }

    $frontendDir = Join-Path $RepoRoot "frontend"
    $candidates = @(
        (Join-Path $frontendDir ".env.neon-production.local"),
        (Join-Path $frontendDir ".env.vercel-production.local"),
        (Join-Path $frontendDir ".env.production.local")
    )

    foreach ($file in $candidates) {
        $found = Get-DatabaseUrlFromEnvFile -FilePath $file
        if ($found) { return $found }
    }

    if ($TryVercelPull) {
        $fromVercel = Get-DatabaseUrlFromVercelPull -FrontendDir $frontendDir
        if ($fromVercel) { return $fromVercel }
    }

    return $null
}

function Write-ProdDatabaseUrlHelp {
    Write-Host ""
    Write-Host "Could not find a production Neon connection string." -ForegroundColor Red
    Write-Host ""
    Write-Host "Option A - pass it once:" -ForegroundColor Yellow
    Write-Host '  .\scripts\provision-prod-customer.ps1 -DatabaseUrl "postgresql://...@ep-....neon.tech/neondb?sslmode=require" -Email ...' -ForegroundColor White
    Write-Host ""
    Write-Host "Option B - save locally (gitignored) for future scripts:" -ForegroundColor Yellow
    Write-Host '  .\scripts\save-prod-database-url.ps1 -DatabaseUrl "postgresql://..."' -ForegroundColor White
    Write-Host ""
    Write-Host "Option C - pull from Vercel (requires: npx vercel login):" -ForegroundColor Yellow
    Write-Host "  .\scripts\provision-prod-customer.ps1 -Email ... -TryVercelPull" -ForegroundColor White
    Write-Host ""
    Write-Host "Get the URL from Neon dashboard -> Connection details, or Vercel -> AUTH_DATABASE_URL." -ForegroundColor DarkGray
    Write-Host ""
}
