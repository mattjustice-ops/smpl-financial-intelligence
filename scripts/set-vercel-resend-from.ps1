# Set production EMAIL_FROM on Vercel after Resend domain verification (gl-2).
#
# Usage:
#   .\scripts\set-vercel-resend-from.ps1 -EmailFrom "SMPL.ai <noreply@smpl-ai.com>"

param(
    [string]$EmailFrom = "SMPL.ai <noreply@smpl-ai.com>",
    [string]$VercelToken = "",
    [string]$Scope = "smplai",
    [string]$Project = "smpl-financial-intelligence"
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path $PSScriptRoot -Parent
$frontendDir = Join-Path $repoRoot "frontend"
$value = $EmailFrom.Trim()

if ($value -match "onboarding@resend\.dev") {
    Write-Host "ERROR: Use a verified @smpl-ai.com address, not onboarding@resend.dev." -ForegroundColor Red
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
    param([string]$Name, [string]$Val)
    $npxArgs = Get-NpxBaseArgs + Get-VercelProjectArgs
    $tempFile = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($tempFile, $Val, [System.Text.UTF8Encoding]::new($false))
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
Write-Host "=== Vercel Production EMAIL_FROM (gl-2) ===" -ForegroundColor Cyan
Write-Host "Value: $value" -ForegroundColor DarkGray
Write-Host ""

Push-Location $frontendDir
try {
    Set-VercelProdEnvValue -Name "EMAIL_FROM" -Val $value
    Write-Host "  OK: EMAIL_FROM" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next:" -ForegroundColor Yellow
    Write-Host "  1. Vercel -> Deployments -> Redeploy latest" -ForegroundColor White
    Write-Host "  2. .\scripts\test-resend-email.ps1 -To external@email.com -From `"$value`"" -ForegroundColor White
    Write-Host "  3. Prod login smoke test at /login" -ForegroundColor White
    Write-Host ""
}
finally {
    Pop-Location
}
