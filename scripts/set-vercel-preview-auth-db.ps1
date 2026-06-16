# Set AUTH_DATABASE_URL on Vercel Preview from local staging Neon URL (gl-5b).
#
# Usage:
#   .\scripts\set-vercel-preview-auth-db.ps1
#   .\scripts\set-vercel-preview-auth-db.ps1 -DatabaseUrl "postgresql://...@ep-STAGING.neon.tech/neondb?sslmode=require"

param(
    [string]$DatabaseUrl = "",
    [string]$VercelToken = "",
    [string]$Scope = "smplai",
    [string]$Project = "smpl-financial-intelligence"
)

# Vercel CLI writes banners to stderr; Stop would abort on harmless NativeCommandError.
$ErrorActionPreference = "Continue"
. (Join-Path $PSScriptRoot "lib\Resolve-StagingConfig.ps1")

$repoRoot = Split-Path $PSScriptRoot -Parent
$frontendDir = Join-Path $repoRoot "frontend"

if (-not $DatabaseUrl) {
    $config = Resolve-StagingConfig -RepoRoot $repoRoot
    if ($config.DatabaseUrl) {
        $DatabaseUrl = $config.DatabaseUrl.Url
    }
}

if (-not $DatabaseUrl) {
    Write-Host "ERROR: No staging DATABASE_URL. Run save-staging-config.ps1 or pass -DatabaseUrl." -ForegroundColor Red
    exit 1
}

$url = $DatabaseUrl.Trim().Trim('"').Trim("'")
if ($url -match "^postgresql\+psycopg://") {
    $url = $url -replace "^postgresql\+psycopg://", "postgresql://"
}
$url = $url -replace "[?&]channel_binding=require", ""
$url = $url -replace "\?&", "?"
$url = $url.TrimEnd("?").TrimEnd("&")

if ($VercelToken) {
    $env:VERCEL_TOKEN = $VercelToken.Trim()
}

function Get-NpxBaseArgs {
    $args = @("--yes", "vercel@latest")
    if ($env:VERCEL_TOKEN) {
        $args += @("--token", $env:VERCEL_TOKEN)
    }
    return $args
}

function Set-VercelPreviewEnvValue {
    param([string]$Name, [string]$Value)
    $npxArgs = Get-NpxBaseArgs + @("--scope", $Scope, "--project", $Project)
    $tempFile = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($tempFile, $Value, [System.Text.UTF8Encoding]::new($false))
        $output = Get-Content -LiteralPath $tempFile -Raw | & npx @npxArgs env add $Name preview --yes --force 2>&1 | ForEach-Object { "$_" }
        if ($LASTEXITCODE -ne 0) {
            Write-Host ($output -join "`n") -ForegroundColor Red
            throw "vercel env add $Name preview failed (exit $LASTEXITCODE)"
        }
    }
    finally {
        Remove-Item -LiteralPath $tempFile -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ""
Write-Host "=== Vercel Preview AUTH_DATABASE_URL (staging Neon) ===" -ForegroundColor Cyan
Write-Host "Host: $($url -replace '^[^:]+://[^@]+@','postgresql://***@')" -ForegroundColor DarkGray
Write-Host ""

Push-Location $frontendDir
try {
    Set-VercelPreviewEnvValue -Name "AUTH_DATABASE_URL" -Value $url
    Write-Host "  OK: AUTH_DATABASE_URL (preview)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Also required on Preview (copy from Production if missing):" -ForegroundColor Yellow
    Write-Host "  AUTH_SECRET, AUTH_RESEND_KEY, EMAIL_FROM" -ForegroundColor White
    Write-Host ""
    Write-Host "Then: Vercel -> Deployments -> Redeploy gl-5b-preview-test" -ForegroundColor Yellow
    Write-Host ""
}
finally {
    Pop-Location
}
