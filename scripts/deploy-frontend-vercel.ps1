# Deploy frontend to Vercel (staging auth milestone).
#
# Prerequisites:
#   - Git remote: origin -> GitHub (Vercel project connected to repo, Root Directory = frontend)
#   - Vercel env vars set (run .\scripts\print-vercel-auth-env.ps1 first)
#
# Usage (repo root):
#   .\scripts\deploy-frontend-vercel.ps1              # build + status only
#   .\scripts\deploy-frontend-vercel.ps1 -CommitPush  # commit, push main, trigger Vercel

param(
  [switch]$CommitPush,
  [string]$CommitMessage = "Add customer login (Auth.js), session sync, and Vercel auth deploy prep"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$frontendDir = Join-Path $repoRoot "frontend"
$prodUrl = "https://smpl-financial-intelligence.vercel.app"

Write-Host ""
Write-Host "=== SMPL frontend -> Vercel deploy ===" -ForegroundColor Cyan
Write-Host ""

Push-Location $frontendDir
try {
  Write-Host "Installing dependencies..." -ForegroundColor Yellow
  npm install 2>&1 | ForEach-Object { Write-Host $_ }
  if ($LASTEXITCODE -ne 0) { throw "npm install failed" }

  Write-Host ""
  Write-Host "Running production build (logging to deploy-build.log)..." -ForegroundColor Yellow
  $buildLog = Join-Path $repoRoot "deploy-build.log"
  npm run build *>&1 | Tee-Object -FilePath $buildLog
  if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "BUILD FAILED - see $buildLog" -ForegroundColor Red
    Write-Host ""
    Get-Content $buildLog | Select-String -Pattern "Type error|Failed to compile|error TS" -Context 0,6
    exit 1
  }
  Write-Host ""
  Write-Host "Build OK." -ForegroundColor Green
} finally {
  Pop-Location
}

Push-Location $repoRoot
try {
  Write-Host ""
  Write-Host "Git status:" -ForegroundColor Yellow
  git status -sb
  Write-Host ""

  if (-not $CommitPush) {
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Set Vercel env vars: .\scripts\print-vercel-auth-env.ps1"
    Write-Host "  2. Commit and push:     .\scripts\deploy-frontend-vercel.ps1 -CommitPush"
    Write-Host "  3. Confirm deploy at:   https://vercel.com (project smpl-financial-intelligence)"
    Write-Host "  4. Smoke test:          $prodUrl/login (magic link needs prod AUTH_DATABASE_URL + API)"
    exit 0
  }

  $dirty = git status --porcelain
  if ($dirty) {
    Write-Host "Committing changes..." -ForegroundColor Yellow
    git add -A
    git commit -m $CommitMessage
    if ($LASTEXITCODE -ne 0) { throw "git commit failed" }
  } else {
    Write-Host "Working tree clean - nothing to commit." -ForegroundColor DarkGray
  }

  Write-Host "Pushing to origin main..." -ForegroundColor Yellow
  git push origin main
  if ($LASTEXITCODE -ne 0) { throw "git push failed" }

  Write-Host ""
  Write-Host "Pushed. Vercel should auto-deploy if the GitHub integration is connected." -ForegroundColor Green
  Write-Host ""
  Write-Host "Verify:" -ForegroundColor Cyan
  Write-Host "  Site:     $prodUrl"
  Write-Host "  Login:    $prodUrl/login"
  Write-Host "  Board:    $prodUrl/board"
  Write-Host ""
  Write-Host "Before inviting customers:" -ForegroundColor Yellow
  Write-Host "  - AUTH_DATABASE_URL on Neon/Supabase + alembic upgrade head"
  Write-Host "  - SFI_BACKEND_URL pointing to hosted API (not localhost)"
  Write-Host "  - Wire /app to session.activeOrganizationId (PR2)"
  Write-Host ""
  Write-Host "Docs: docs/VERCEL_AUTH_DEPLOY.md"
} finally {
  Pop-Location
}
