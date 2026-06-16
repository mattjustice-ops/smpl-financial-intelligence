# Resolve staging API URL + Neon staging DB for gl-5 ops scripts.
# Skips production URLs unless -AllowProduction is set.

. (Join-Path $PSScriptRoot "Resolve-ProdDatabaseUrl.ps1")

$script:StagingProdApiHosts = @(
    "sfi-api-production.up.railway.app"
)

function Test-IsPlaceholderUrl {
    param([string]$Url)
    if (-not $Url) { return $true }
    return ($Url -match "(?i)YOUR-|REPLACE_ME|example\.com|xxxx")
}

function Get-EnvValueFromFile {
    param(
        [string]$FilePath,
        [string[]]$Names
    )

    if (-not (Test-Path -LiteralPath $FilePath)) {
        return $null
    }

    foreach ($line in Get-Content -LiteralPath $FilePath) {
        $trimmed = $line.Trim()
        if ($trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) { continue }
        foreach ($name in $Names) {
            if ($trimmed -match "^$([regex]::Escape($name))=(.+)$") {
                $value = $Matches[1].Trim().Trim('"').Trim("'")
                if (-not (Test-IsPlaceholderUrl $value)) {
                    return @{ Value = $value; Source = $FilePath; Name = $name }
                }
            }
        }
    }
    return $null
}

function Test-IsProductionApiUrl {
    param([string]$Url)
    if (-not $Url) { return $false }
    foreach ($prodHost in $script:StagingProdApiHosts) {
        if ($Url -match [regex]::Escape($prodHost)) {
            return $true
        }
    }
    return $false
}

function Resolve-StagingConfig {
    param(
        [string]$ApiBase = "",
        [string]$DatabaseUrl = "",
        [string]$FrontendUrl = "",
        [string]$RepoRoot = "",
        [switch]$AllowProduction,
        [switch]$TryVercelPull
    )

    if (-not $RepoRoot) {
        $RepoRoot = Split-Path $PSScriptRoot -Parent
    }
    $frontendDir = Join-Path $RepoRoot "frontend"

    $resolvedApi = $null
    if ($ApiBase -and -not (Test-IsPlaceholderUrl $ApiBase)) {
        $resolvedApi = @{
            Url    = $ApiBase.Trim().Trim('"').Trim("'").TrimEnd("/")
            Source = "-ApiBase parameter"
            Name   = "STAGING_API_URL"
        }
    }
    elseif ($env:STAGING_API_URL -and -not (Test-IsPlaceholderUrl $env:STAGING_API_URL)) {
        $resolvedApi = @{
            Url    = $env:STAGING_API_URL.Trim().TrimEnd("/")
            Source = "STAGING_API_URL env var"
            Name   = "STAGING_API_URL"
        }
    }
    else {
        $apiCandidates = @(
            (Join-Path $frontendDir ".env.staging.local"),
            (Join-Path $RepoRoot "scripts\config\staging.local.env")
        )
        foreach ($file in $apiCandidates) {
            $found = Get-EnvValueFromFile -FilePath $file -Names @(
                "STAGING_API_URL", "SFI_BACKEND_URL", "NEXT_PUBLIC_API_URL"
            )
            if ($found) {
                $resolvedApi = @{
                    Url    = $found.Value.TrimEnd("/")
                    Source = $found.Source
                    Name   = $found.Name
                }
                break
            }
        }
    }

    $resolvedDb = $null
    if ($DatabaseUrl -and -not (Test-IsLocalDatabaseUrl $DatabaseUrl)) {
        $resolvedDb = @{
            Url    = $DatabaseUrl.Trim().Trim('"').Trim("'")
            Source = "-DatabaseUrl parameter"
            Name   = "STAGING_DATABASE_URL"
        }
    }
    elseif ($env:STAGING_DATABASE_URL -and -not (Test-IsLocalDatabaseUrl $env:STAGING_DATABASE_URL)) {
        $resolvedDb = @{
            Url    = $env:STAGING_DATABASE_URL.Trim()
            Source = "STAGING_DATABASE_URL env var"
            Name   = "STAGING_DATABASE_URL"
        }
    }
    else {
        $dbCandidates = @(
            (Join-Path $frontendDir ".env.staging.local"),
            (Join-Path $RepoRoot "scripts\config\staging.local.env")
        )
        foreach ($file in $dbCandidates) {
            $found = Get-EnvValueFromFile -FilePath $file -Names @(
                "STAGING_DATABASE_URL", "STAGING_AUTH_DATABASE_URL", "DATABASE_URL", "AUTH_DATABASE_URL"
            )
            if ($found -and -not (Test-IsLocalDatabaseUrl $found.Value)) {
                $resolvedDb = @{
                    Url    = $found.Value
                    Source = $found.Source
                    Name   = $found.Name
                }
                break
            }
        }
    }

    if ($TryVercelPull -and -not $resolvedDb) {
        $tmpFile = Join-Path $env:TEMP ("sfi-vercel-staging-env-{0}.local" -f [guid]::NewGuid().ToString("N"))
        $npxArgs = @("--yes", "vercel@latest", "--scope", "smplai", "--project", "smpl-financial-intelligence")
        if ($env:VERCEL_TOKEN) {
            $npxArgs += @("--token", $env:VERCEL_TOKEN)
        }
        Push-Location $frontendDir
        try {
            $null = & npx @npxArgs env pull $tmpFile preview --yes 2>&1
            if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $tmpFile)) {
                $foundApi = Get-EnvValueFromFile -FilePath $tmpFile -Names @("SFI_BACKEND_URL", "NEXT_PUBLIC_API_URL")
                if ($foundApi -and -not $resolvedApi) {
                    $resolvedApi = @{
                        Url    = $foundApi.Value.TrimEnd("/")
                        Source = "Vercel Preview (env pull)"
                        Name   = $foundApi.Name
                    }
                }
                $foundDb = Get-EnvValueFromFile -FilePath $tmpFile -Names @("AUTH_DATABASE_URL", "DATABASE_URL")
                if ($foundDb -and -not (Test-IsLocalDatabaseUrl $foundDb.Value)) {
                    $resolvedDb = @{
                        Url    = $foundDb.Value
                        Source = "Vercel Preview AUTH_DATABASE_URL (env pull)"
                        Name   = $foundDb.Name
                    }
                }
            }
        }
        finally {
            Pop-Location
            Remove-Item -LiteralPath $tmpFile -Force -ErrorAction SilentlyContinue
        }
    }

    $resolvedFrontend = $null
    if ($FrontendUrl -and -not (Test-IsPlaceholderUrl $FrontendUrl)) {
        $resolvedFrontend = @{
            Url    = $FrontendUrl.Trim().TrimEnd("/")
            Source = "-FrontendUrl parameter"
            Name   = "STAGING_FRONTEND_URL"
        }
    }
    elseif ($env:STAGING_FRONTEND_URL -and -not (Test-IsPlaceholderUrl $env:STAGING_FRONTEND_URL)) {
        $resolvedFrontend = @{
            Url    = $env:STAGING_FRONTEND_URL.Trim().TrimEnd("/")
            Source = "STAGING_FRONTEND_URL env var"
            Name   = "STAGING_FRONTEND_URL"
        }
    }
    else {
        $frontendCandidates = @(
            (Join-Path $frontendDir ".env.staging.local"),
            (Join-Path $RepoRoot "scripts\config\staging.local.env")
        )
        foreach ($file in $frontendCandidates) {
            $found = Get-EnvValueFromFile -FilePath $file -Names @("STAGING_FRONTEND_URL", "AUTH_URL", "APP_BASE_URL")
            if ($found) {
                $resolvedFrontend = @{
                    Url    = $found.Value.TrimEnd("/")
                    Source = $found.Source
                    Name   = $found.Name
                }
                break
            }
        }
    }

    if ($resolvedApi -and (Test-IsProductionApiUrl $resolvedApi.Url) -and -not $AllowProduction) {
        $resolvedApi.ProductionBlocked = $true
    }

    return @{
        ApiBase      = $resolvedApi
        DatabaseUrl  = $resolvedDb
        FrontendUrl  = $resolvedFrontend
    }
}

function Write-StagingConfigHelp {
    Write-Host ""
    Write-Host "Could not resolve staging API + database URLs." -ForegroundColor Red
    Write-Host ""
    Write-Host "Option A - save once (recommended):" -ForegroundColor Yellow
    Write-Host '  .\scripts\save-staging-config.ps1 `' -ForegroundColor White
    Write-Host '    -ApiBase "https://sfi-api-staging-xxxx.up.railway.app" `' -ForegroundColor White
    Write-Host '    -DatabaseUrl "postgresql://...@ep-STAGING.neon.tech/neondb?sslmode=require"' -ForegroundColor White
    Write-Host ""
    Write-Host "Option B - pass inline for this run:" -ForegroundColor Yellow
    Write-Host '  .\scripts\smoke-test-staging.ps1 -ApiBase "https://..." -DatabaseUrl "postgresql://..."' -ForegroundColor White
    Write-Host ""
    Write-Host "See docs/GO_LIVE_GL5_STAGING.md for Neon branch + Railway staging setup." -ForegroundColor DarkGray
    Write-Host ""
}
