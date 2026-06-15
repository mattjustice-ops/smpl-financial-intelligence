# Phase A - Neon auth database + Vercel env prep (Auth milestone)
#
# Usage (after creating a Neon project and copying the connection string):
#   .\scripts\setup-prod-auth-db.ps1 -DatabaseUrl "postgresql://user:pass@ep-....neon.tech/neondb?sslmode=require"
#
# Optional - seed your login email for prod smoke test:
#   .\scripts\setup-prod-auth-db.ps1 -DatabaseUrl "..." -Email mattjustice@smpl-ai.com

param(
    [Parameter(Mandatory = $true)]
    [string]$DatabaseUrl,
    [string]$Email = "",
    [string]$OrganizationId = "8571e520-0687-4516-bdee-379f37c58c1f",
    [switch]$SkipMigrations
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $repoRoot "backend"
$python = Join-Path $backendDir ".venv312\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = Join-Path $backendDir ".venv\Scripts\python.exe"
}
if (-not (Test-Path $python)) {
    Write-Host "ERROR: backend venv not found. Create .venv312 under backend first." -ForegroundColor Red
    exit 1
}

function Convert-ToAlembicUrl {
    param([string]$Url)
    $normalized = $Url.Trim().Trim('"').Trim("'")
    if ($normalized -match "^postgresql://") {
        return $normalized -replace "^postgresql://", "postgresql+psycopg://"
    }
    if ($normalized -match "^postgres://") {
        return $normalized -replace "^postgres://", "postgresql+psycopg://"
    }
    return $normalized
}

$alembicUrl = Convert-ToAlembicUrl $DatabaseUrl
$authUrl = $DatabaseUrl
if ($authUrl -match "^postgresql\+psycopg://") {
    $authUrl = $authUrl -replace "^postgresql\+psycopg://", "postgresql://"
}

if ($DatabaseUrl -match "YOUR_PASSWORD") {
    Write-Host "ERROR: Replace YOUR_PASSWORD with the real password from Neon Connection details." -ForegroundColor Red
    Write-Host "       Copy the full connection string from the Neon dashboard." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "=== SMPL prod auth DB setup (Neon) ===" -ForegroundColor Cyan
Write-Host ""

if ($SkipMigrations) {
    Write-Host "[1/4] Skipping migrations (-SkipMigrations). Use when alembic upgrade head already succeeded." -ForegroundColor DarkGray
} else {
    Write-Host "[1/4] Running alembic upgrade head ..." -ForegroundColor Yellow
    Push-Location $backendDir
    try {
        $env:DATABASE_URL = $alembicUrl
        & $python -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) {
            throw "alembic upgrade head failed"
        }
        Write-Host "  Migrations OK." -ForegroundColor Green
    }
    finally {
        Pop-Location
    }
}

Write-Host ""
Write-Host "[2/4] Ensuring demo organization row ..." -ForegroundColor Yellow
Push-Location $backendDir
try {
    $env:DATABASE_URL = $alembicUrl
    & $python (Join-Path $backendDir "scripts\seed_demo_org.py") --organization-id $OrganizationId
    if ($LASTEXITCODE -ne 0) { throw "seed_demo_org failed" }
}
finally {
    Pop-Location
}

if ($Email) {
    Write-Host ""
    Write-Host "[3/4] Seeding pending invite for $Email ..." -ForegroundColor Yellow
    Push-Location $backendDir
    try {
        $env:DATABASE_URL = $alembicUrl
        & $python (Join-Path $backendDir "scripts\seed_dev_invite.py") `
            --email $Email `
            --organization-id $OrganizationId
        if ($LASTEXITCODE -ne 0) { throw "seed_dev_invite failed" }
    }
    finally {
        Pop-Location
    }
} else {
    Write-Host ""
    Write-Host "[3/4] Skipping invite seed (pass -Email you@company.com to add one)" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "[4/4] Vercel environment variables" -ForegroundColor Yellow
Write-Host ""
Write-Host "Add these in Vercel -> Project -> Settings -> Environment Variables -> Production:" -ForegroundColor White
Write-Host ""
Write-Host "  AUTH_DATABASE_URL" -ForegroundColor Cyan
Write-Host "  $authUrl" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  AUTH_SECRET          (generate: openssl rand -base64 32)" -ForegroundColor Cyan
Write-Host "  AUTH_URL             https://smpl-financial-intelligence.vercel.app" -ForegroundColor Cyan
Write-Host "  APP_BASE_URL         https://smpl-financial-intelligence.vercel.app" -ForegroundColor Cyan
Write-Host "  AUTH_RESEND_KEY      re_... from Resend dashboard" -ForegroundColor Cyan
Write-Host "  EMAIL_FROM           onboarding@resend.dev (or verified domain)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Then: Vercel -> Deployments -> Redeploy latest" -ForegroundColor Yellow
Write-Host ""
Write-Host "Smoke test:" -ForegroundColor Green
Write-Host "  1. https://smpl-financial-intelligence.vercel.app/login" -ForegroundColor White
Write-Host "  2. Enter invited email -> check inbox for magic link" -ForegroundColor White
Write-Host "  3. Click link -> /app (needs SFI_BACKEND_URL when API is hosted)" -ForegroundColor White
Write-Host ""
Write-Host "Note: magic-link CLICK calls session-sync on the backend." -ForegroundColor DarkYellow
Write-Host "      Email-only test works after AUTH_* vars. Full /app login needs hosted API (Phase B)." -ForegroundColor DarkYellow
Write-Host ""
Write-Host "Update checklist: frontend/lib/go-live-progress.ts" -ForegroundColor DarkGray
Write-Host ""
