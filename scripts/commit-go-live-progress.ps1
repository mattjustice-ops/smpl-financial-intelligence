# Commit and push go-live /progress checklist updates (excludes local secrets).
#
# Usage:
#   .\scripts\commit-go-live-progress.ps1
#   .\scripts\commit-go-live-progress.ps1 -Push

param(
    [switch]$Push
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

if (-not (Test-Path ".git")) {
    Write-Host "ERROR: Not a git repository." -ForegroundColor Red
    exit 1
}

$secretPaths = @(
    "frontend/.env.local",
    "frontend/.env.neon-production.local",
    "frontend/.env.vercel-production.local"
)

git add -A
foreach ($path in $secretPaths) {
    $inIndex = git ls-files --cached -- $path 2>$null
    if ($inIndex) {
        git restore --staged -- $path
    }
}

$staged = git diff --cached --name-only
if (-not $staged) {
    Write-Host "Nothing to commit (working tree clean or only secret files changed)." -ForegroundColor Yellow
    exit 0
}

Write-Host "Staged files:" -ForegroundColor Cyan
$staged | ForEach-Object { Write-Host "  $_" }

git commit -m "Track GL-1/GL-2 go-live progress and customer provisioning tooling." -m "Update /progress checklist, Resend domain docs, provision scripts, and test-resend fix."
Write-Host ""
Write-Host "Committed:" (git log -1 --oneline) -ForegroundColor Green

if ($Push) {
    $branch = git rev-parse --abbrev-ref HEAD
    $upstream = git rev-parse --abbrev-ref "@{u}" 2>$null
    if ($LASTEXITCODE -ne 0) {
        git push -u origin HEAD
    } else {
        git push
    }
    Write-Host ""
    Write-Host "Pushed $branch. Vercel should redeploy if this branch is connected." -ForegroundColor Green
    Write-Host "Check: https://smpl-financial-intelligence.vercel.app/progress" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "Run with -Push to push to origin, or: git push" -ForegroundColor Yellow
}
