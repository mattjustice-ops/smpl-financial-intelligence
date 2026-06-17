# Verify Vercel Preview API env points at staging (not production).
#
# Usage:
#   .\scripts\verify-vercel-preview-api-url.ps1

param(
    [string]$Scope = "smplai",
    [string]$Project = "smpl-financial-intelligence",
    [string]$ExpectedStagingHost = "sfi-api-staging-production.up.railway.app"
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path $PSScriptRoot -Parent
$frontendDir = Join-Path $repoRoot "frontend"
$prodApiHost = "sfi-api-production.up.railway.app"
. (Join-Path $PSScriptRoot "lib\Invoke-VercelEnv.ps1")

function Get-UrlHost {
    param([string]$Url)
    if (-not $Url) { return $null }
    if ($Url -match "^https?://([^/]+)") { return $Matches[1] }
    return $Url
}

Write-Host ""
Write-Host "=== Vercel Preview API URL check ===" -ForegroundColor Cyan
Write-Host ""

$tmpFile = Join-Path $env:TEMP "sfi-preview-env-$([guid]::NewGuid().ToString('N')).env"
try {
    Invoke-VercelEnvPull -FrontendDir $frontendDir -OutFile $tmpFile -Environment "preview" -Scope $Scope -Project $Project | Out-Null

    $sfi = Get-EnvFileValue -FilePath $tmpFile -Key "SFI_BACKEND_URL"
    $pub = Get-EnvFileValue -FilePath $tmpFile -Key "NEXT_PUBLIC_API_URL"
    $sfiHost = Get-UrlHost $sfi
    $pubHost = Get-UrlHost $pub

    Write-Host "SFI_BACKEND_URL host:       $(if ($sfiHost) { $sfiHost } else { '(not set)' })" -ForegroundColor $(if ($sfiHost -eq $ExpectedStagingHost) { "Green" } elseif ($sfiHost -eq $prodApiHost) { "Red" } else { "Yellow" })
    Write-Host "NEXT_PUBLIC_API_URL host:   $(if ($pubHost) { $pubHost } else { '(not set)' })" -ForegroundColor $(if ($pubHost -eq $ExpectedStagingHost) { "Green" } elseif ($pubHost -eq $prodApiHost) { "Red" } else { "Yellow" })
    Write-Host ""

    $ok = $true
    foreach ($pair in @(@{ Name = "SFI_BACKEND_URL"; Host = $sfiHost }, @{ Name = "NEXT_PUBLIC_API_URL"; Host = $pubHost })) {
        if (-not $pair.Host) {
            Write-Host "MISSING: $($pair.Name) on Preview" -ForegroundColor Red
            $ok = $false
        }
        elseif ($pair.Host -eq $prodApiHost) {
            Write-Host "WRONG: $($pair.Name) points at PRODUCTION API" -ForegroundColor Red
            $ok = $false
        }
        elseif ($pair.Host -ne $ExpectedStagingHost) {
            Write-Host "WARN: $($pair.Name) host is not the expected staging URL" -ForegroundColor Yellow
            $ok = $false
        }
    }

    if ($ok) {
        Write-Host "OK: Preview env targets staging API." -ForegroundColor Green
        Write-Host "Redeploy Preview after any env change (git push -> Vercel build)." -ForegroundColor DarkGray
        Write-Host ""
        exit 0
    }

    Write-Host ""
    Write-Host "Fix:" -ForegroundColor Yellow
    Write-Host '  .\scripts\set-vercel-staging-env.ps1 -BackendUrl "https://sfi-api-staging-production.up.railway.app"' -ForegroundColor White
    Write-Host "  .\scripts\verify-vercel-preview-api-url.ps1" -ForegroundColor White
    Write-Host "  git push origin gl-5b-sandbox   # do NOT run bare npx vercel from frontend/" -ForegroundColor White
    Write-Host ""
    exit 1
}
catch {
    Write-Host "FAIL: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Remove-Item -LiteralPath $tmpFile -Force -ErrorAction SilentlyContinue
}
