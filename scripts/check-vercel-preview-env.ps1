# List Vercel Preview env var NAMES (not values) for gl-5b debugging.
# Does NOT deploy — only runs `vercel env ls`.
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
    "EMAIL_FROM"
)

$optionalButImportant = @(
    "BILLING_INTERNAL_API_KEY"
)

function Get-NpxBaseArgs {
    $npxBase = @("--yes", "vercel@latest")
    if ($env:VERCEL_TOKEN) {
        $npxBase += @("--token", $env:VERCEL_TOKEN)
    }
    return $npxBase
}

Write-Host ""
Write-Host "=== Vercel Preview env (names only) ===" -ForegroundColor Cyan
Write-Host "Project: $Scope / $Project" -ForegroundColor DarkGray
Write-Host ""

Push-Location $frontendDir
try {
    $npxArgs = Get-NpxBaseArgs + @(
        "env", "ls",
        "--environment", "preview",
        "--scope", $Scope,
        "--project", $Project
    )
    $output = & npx @npxArgs 2>&1 | ForEach-Object { "$_" }
    $joined = $output -join "`n"
    Write-Host $joined
    Write-Host ""

    if ($joined -match "Uploading \[|Deploying outputs|Build Completed in /vercel/output") {
        Write-Host "ERROR: Vercel CLI ran a deploy instead of env ls. Do not use that URL." -ForegroundColor Red
        Write-Host "Use the GitHub branch Preview: gl-5b-sandbox" -ForegroundColor Yellow
        Write-Host "Verify env vars in Vercel dashboard -> Settings -> Environment Variables -> Preview" -ForegroundColor Yellow
        exit 1
    }

    $missing = @()
    foreach ($name in $required) {
        if ($joined -notmatch [regex]::Escape($name)) {
            $missing += $name
        }
    }

    foreach ($name in $optionalButImportant) {
        if ($joined -match [regex]::Escape($name)) {
            Write-Host "INFO: Optional $name is set — must match Railway sfi-api-staging (or unset on both)." -ForegroundColor DarkGray
        }
        else {
            Write-Host "INFO: $name not set on Preview (OK if Railway staging also unset)." -ForegroundColor DarkGray
        }
    }
    Write-Host ""

    if ($missing.Count -eq 0) {
        Write-Host "OK: All required Preview variable names appear in vercel env ls." -ForegroundColor Green
    }
    else {
        Write-Host "MISSING on Preview (dashboard or scripts):" -ForegroundColor Yellow
        foreach ($name in $missing) {
            Write-Host "  - $name" -ForegroundColor White
        }
        Write-Host ""
        Write-Host "API:  .\scripts\set-vercel-staging-env.ps1 -BackendUrl `"https://sfi-api-staging-production.up.railway.app`"" -ForegroundColor White
        Write-Host "Auth DB: .\scripts\set-vercel-preview-auth-db.ps1" -ForegroundColor White
        Write-Host "Auth keys: copy AUTH_SECRET, AUTH_RESEND_KEY, EMAIL_FROM from Production -> enable Preview" -ForegroundColor White
        Write-Host "Billing key: BILLING_INTERNAL_API_KEY must match Railway sfi-api-staging" -ForegroundColor White
    }
    Write-Host ""
}
finally {
    Pop-Location
}
