# Set SMPL_OPS_ADMIN_EMAILS on Vercel Production (and optionally Preview).
#
# Usage (repo root):
#   .\scripts\set-vercel-ops-admin-env.ps1 -AdminEmails "you@smpl-ai.com"
#   .\scripts\set-vercel-ops-admin-env.ps1 -AdminEmails "a@smpl-ai.com,b@smpl-ai.com" -IncludePreview

param(
    [Parameter(Mandatory = $true)]
    [string]$AdminEmails,
    [switch]$IncludePreview,
    [string]$VercelToken = "",
    [string]$Scope = "smplai",
    [string]$Project = "smpl-financial-intelligence"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$frontendDir = Join-Path $repoRoot "frontend"
$value = ($AdminEmails -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ }) -join ","

if (-not $value) {
    Write-Error "AdminEmails is empty after parsing."
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

function Set-VercelEnvValue {
    param(
        [string]$Name,
        [string]$EnvValue,
        [ValidateSet("production", "preview")]
        [string]$Target
    )
    $npxArgs = @("--yes", "vercel@latest", "env", "add", $Name, $Target, "--value", $EnvValue, "--yes", "--force", "--scope", $Scope)
    if ($env:VERCEL_TOKEN) {
        $npxArgs += @("--token", $env:VERCEL_TOKEN)
    }
    $output = & npx @npxArgs 2>&1 | ForEach-Object { "$_" }
    if ($LASTEXITCODE -ne 0) {
        Write-Host ($output -join "`n") -ForegroundColor Red
        throw "vercel env add $Name $Target failed (exit $LASTEXITCODE)"
    }
}

Write-Host ""
Write-Host "=== Vercel SMPL Ops admin emails ===" -ForegroundColor Cyan
Write-Host "SMPL_OPS_ADMIN_EMAILS=$value" -ForegroundColor DarkGray
Write-Host ""

Push-Location $frontendDir
try {
    Set-VercelEnvValue -Name "SMPL_OPS_ADMIN_EMAILS" -EnvValue $value -Target "production"
    Write-Host "  OK: SMPL_OPS_ADMIN_EMAILS (production)" -ForegroundColor Green
    if ($IncludePreview) {
        Set-VercelEnvValue -Name "SMPL_OPS_ADMIN_EMAILS" -EnvValue $value -Target "preview"
        Write-Host "  OK: SMPL_OPS_ADMIN_EMAILS (preview)" -ForegroundColor Green
    }
    Write-Host ""
    Write-Host "Next: redeploy so /app/ops picks up the variable:" -ForegroundColor Yellow
    Write-Host "  .\scripts\redeploy-vercel-production.ps1 -SkipBuild" -ForegroundColor White
    Write-Host ""
}
finally {
    Pop-Location
}
