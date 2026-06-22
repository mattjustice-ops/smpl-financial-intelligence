# Push fast-outlook backend + Vercel outlook proxy to production.
# Run from repo root. Requires git remote + Railway connected to main on sfi-api-production.
#
# Usage:
#   .\scripts\deploy-outlook-production.ps1
#   .\scripts\deploy-outlook-production.ps1 -SkipVercel

param(
    [switch]$SkipVercel,
    [string]$CommitMessage = "Speed up reporting outlook API for board and forecast live hydrate"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

$paths = @(
    "backend/app/api/reporting_outlook_routes.py"
    "backend/app/services/reporting/three_statement_payload.py"
    "frontend/app/api/v1/reporting/outlook/route.ts"
    "frontend/vercel.json"
    "scripts/deploy-outlook-production.ps1"
)

foreach ($rel in $paths) {
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $rel))) {
        Write-Host "Missing: $rel" -ForegroundColor Red
        exit 1
    }
}

git add @paths
$dirty = git diff --cached --quiet 2>$null
if ($LASTEXITCODE -ne 0) {
    git commit -m $CommitMessage
    Write-Host "Committed." -ForegroundColor Green
} else {
    Write-Host "Nothing new to commit (already committed?)." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Pushing to origin (triggers sfi-api-production if Railway watches main)..." -ForegroundColor Cyan
git push origin HEAD
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "After Railway sfi-api-production deploy succeeds, verify:" -ForegroundColor Cyan
Write-Host '  curl.exe -s "https://sfi-api-production.up.railway.app/api/v1/reporting/outlook?organization_id=8571e520-0687-4516-bdee-379f37c58c1f" | findstr outlook_build' -ForegroundColor White
Write-Host "  Expect: `"outlook_build`":`"light-v1`" and curl time under ~15s" -ForegroundColor DarkGray
Write-Host ""

if (-not $SkipVercel) {
    Write-Host "Deploying Vercel production..." -ForegroundColor Cyan
    Push-Location (Join-Path $repoRoot "frontend")
    try {
        npx @vercel/cli@latest --scope smplai --project smpl-financial-intelligence deploy --prod --yes
    } finally {
        Pop-Location
    }
}

Write-Host ""
Write-Host "Done. Test on https://www.smpl-ai.com/forecast-engine (signed in, hard refresh)." -ForegroundColor Green
