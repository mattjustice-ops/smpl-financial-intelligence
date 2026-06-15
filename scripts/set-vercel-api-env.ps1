# Set SFI_BACKEND_URL + NEXT_PUBLIC_API_URL on Vercel Production.
#
# Usage:
#   .\scripts\set-vercel-api-env.ps1 -BackendUrl "https://sfi-api-production-xxxx.up.railway.app"

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

if ($url -match "YOUR-RAILWAY|YOUR-SERVICE|YOUR-APP") {
    Write-Host "ERROR: Replace the placeholder with your real Railway public URL." -ForegroundColor Red
    Write-Host "  cd backend; npx @railway/cli domain" -ForegroundColor Yellow
    Write-Host "  Or Railway -> sfi-api -> Settings -> Networking" -ForegroundColor Yellow
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

function Set-VercelProdEnvValue {
    param([string]$Name, [string]$Value)
    $npxArgs = Get-NpxBaseArgs + Get-VercelProjectArgs
    $tempFile = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($tempFile, $Value, [System.Text.UTF8Encoding]::new($false))
        $output = Get-Content -LiteralPath $tempFile -Raw | & npx @npxArgs env add $Name production --yes --force 2>&1 | ForEach-Object { "$_" }
        if ($LASTEXITCODE -ne 0) {
            Write-Host ($output -join "`n") -ForegroundColor Red
            throw "vercel env add $Name failed (exit $LASTEXITCODE)"
        }
    }
    finally {
        Remove-Item -LiteralPath $tempFile -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ""
Write-Host "=== Vercel Production API env ===" -ForegroundColor Cyan
Write-Host "Backend URL: $url" -ForegroundColor DarkGray
Write-Host ""

Push-Location $frontendDir
try {
    Set-VercelProdEnvValue -Name "SFI_BACKEND_URL" -Value $url
    Write-Host "  OK: SFI_BACKEND_URL" -ForegroundColor Green
    Set-VercelProdEnvValue -Name "NEXT_PUBLIC_API_URL" -Value $url
    Write-Host "  OK: NEXT_PUBLIC_API_URL" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next: Vercel -> Deployments -> Redeploy latest" -ForegroundColor Yellow
    Write-Host "Then: fresh magic link at /login" -ForegroundColor Yellow
    Write-Host ""
}
finally {
    Pop-Location
}
