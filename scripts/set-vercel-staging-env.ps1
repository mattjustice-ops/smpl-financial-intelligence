# Set SFI_BACKEND_URL + NEXT_PUBLIC_API_URL on Vercel Preview (gl-5 staging).
#
# Usage:
#   .\scripts\set-vercel-staging-env.ps1 -BackendUrl "https://sfi-api-staging-xxxx.up.railway.app"

param(
    [Parameter(Mandatory = $true)]
    [string]$BackendUrl,
    [string]$VercelToken = "",
    [string]$Scope = "smplai",
    [string]$Project = "smpl-financial-intelligence"
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path $PSScriptRoot -Parent
$frontendDir = Join-Path $repoRoot "frontend"
$url = $BackendUrl.Trim().Trim('"').Trim("'").TrimEnd("/")

if ($url -match "YOUR-|YOUR-SERVICE|example\.com") {
    Write-Host "ERROR: Replace the placeholder with your real Railway staging URL." -ForegroundColor Red
    exit 1
}

# Block prod API only (Railway staging URLs often end with -production.up.railway.app).
if ($url -match "sfi-api-production\.up\.railway\.app") {
    Write-Host "ERROR: That is the production API. Use sfi-api-staging (staging service URL)." -ForegroundColor Red
    exit 1
}

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

function Get-VercelProjectArgs {
    return @("--scope", $Scope, "--project", $Project)
}

function Set-VercelPreviewEnvValue {
    param([string]$Name, [string]$Value)
    $npxArgs = Get-NpxBaseArgs + Get-VercelProjectArgs
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
Write-Host "=== Vercel Preview (staging) API env ===" -ForegroundColor Cyan
Write-Host "Backend URL: $url" -ForegroundColor DarkGray
Write-Host ""

Push-Location $frontendDir
try {
    Set-VercelPreviewEnvValue -Name "SFI_BACKEND_URL" -Value $url
    Write-Host "  OK: SFI_BACKEND_URL (preview)" -ForegroundColor Green
    Set-VercelPreviewEnvValue -Name "NEXT_PUBLIC_API_URL" -Value $url
    Write-Host "  OK: NEXT_PUBLIC_API_URL (preview)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next:" -ForegroundColor Yellow
    Write-Host "  1. Ensure Preview AUTH_DATABASE_URL points at Neon *staging* branch (Vercel dashboard)" -ForegroundColor White
    Write-Host "  2. Push a branch or redeploy a Preview deployment" -ForegroundColor White
    Write-Host "  3. .\scripts\verify-staging-stack.ps1 -FrontendUrl https://YOUR-PREVIEW.vercel.app" -ForegroundColor White
    Write-Host ""
}
finally {
    Pop-Location
}
