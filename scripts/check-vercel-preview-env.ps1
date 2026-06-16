# List Vercel Preview env var NAMES (not values) for gl-5b debugging.
#
# Usage:
#   .\scripts\check-vercel-preview-env.ps1

param(
    [string]$Scope = "smplai",
    [string]$Project = "smpl-financial-intelligence"
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path $PSScriptRoot -Parent
$frontendDir = Join-Path $repoRoot "frontend"

$required = @(
    "SFI_BACKEND_URL",
    "NEXT_PUBLIC_API_URL",
    "AUTH_DATABASE_URL",
    "AUTH_SECRET",
    "AUTH_RESEND_KEY",
    "EMAIL_FROM",
    "BILLING_INTERNAL_API_KEY"
)

function Get-NpxBaseArgs {
    $args = @("--yes", "vercel@latest")
    if ($env:VERCEL_TOKEN) {
        $args += @("--token", $env:VERCEL_TOKEN)
    }
    return $args
}

Write-Host ""
Write-Host "=== Vercel Preview env (names only) ===" -ForegroundColor Cyan
Write-Host "Project: $Scope / $Project" -ForegroundColor DarkGray
Write-Host ""

Push-Location $frontendDir
try {
    $npxArgs = Get-NpxBaseArgs + @("env", "ls", "preview", "--scope", $Scope, "--project", $Project)
    $output = & npx @npxArgs 2>&1 | ForEach-Object { "$_" }
    Write-Host ($output -join "`n")
    Write-Host ""

    $joined = $output -join "`n"
    $missing = @()
    foreach ($name in $required) {
        if ($joined -notmatch [regex]::Escape($name)) {
            $missing += $name
        }
    }

    if ($missing.Count -eq 0) {
        Write-Host "OK: All required Preview variable names appear in vercel env ls." -ForegroundColor Green
    }
    else {
        Write-Host "MISSING on Preview (set in dashboard or via scripts):" -ForegroundColor Yellow
        foreach ($name in $missing) {
            Write-Host "  - $name" -ForegroundColor White
        }
        Write-Host ""
        Write-Host "API URL:" -ForegroundColor Yellow
        Write-Host '  .\scripts\set-vercel-staging-env.ps1 -BackendUrl "https://sfi-api-staging-production.up.railway.app"' -ForegroundColor White
    }
    Write-Host ""
}
finally {
    Pop-Location
}
