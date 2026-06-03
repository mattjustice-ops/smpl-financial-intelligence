# Commit local changes and push to GitHub (triggers Vercel redeploy).
#
# Run from repo root in PowerShell:
#   cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence
#   .\scripts\push-to-vercel.ps1
#
# Optional custom commit subject:
#   .\scripts\push-to-vercel.ps1 -Message "Fix HubSpot duplicate companies on quote form"

param(
  [string]$Message = "Fix HubSpot duplicate company records on request-quote"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

Write-Host ""
Write-Host "=== SMPL deploy to Vercel ===" -ForegroundColor Cyan
Write-Host "Repo:   $repoRoot"
Write-Host ""

if (-not (git rev-parse --is-inside-work-tree 2>$null)) {
  Write-Error "Not a git repository. Clone https://github.com/mattjustice-ops/smpl-financial-intelligence first."
}

$branch = git branch --show-current
$remote = git remote get-url origin 2>$null
Write-Host "Branch: $branch"
Write-Host "Remote: $remote"
Write-Host ""

git status
Write-Host ""

$envFiles = @(".env.local", "frontend/.env.local", "backend/.env", "backend/secrets.env")
git add -A

foreach ($f in $envFiles) {
  if (-not (Test-Path $f)) {
    continue
  }

  $isStaged = git diff --cached --name-only -- $f
  if (-not $isStaged) {
    continue
  }

  git reset HEAD -- $f *> $null
  if ($LASTEXITCODE -eq 0) {
    Write-Host "Skipped staging secret file: $f" -ForegroundColor DarkYellow
  }
}

$staged = @(git diff --cached --name-only)
if ($staged.Count -eq 0) {
  Write-Host "Nothing new to commit. Pushing current branch anyway..." -ForegroundColor Yellow
} else {
  Write-Host "Files to commit:" -ForegroundColor Green
  $staged | ForEach-Object { Write-Host "  $_" }

  $body = @(
    "Use HubSpot domain upsert and contact-linked company reconciliation so quote submissions create one company record with contact, name, and industry."
    "Check hubspot.companyDebug.resolvedFrom in the /api/request-quote response after deploy."
  ) -join "`n`n"

  git commit -m $Message -m $body
  Write-Host ""
  Write-Host "Committed." -ForegroundColor Green
}

Write-Host ""
Write-Host "Pushing to origin/$branch ..." -ForegroundColor Cyan
git push origin HEAD
if ($LASTEXITCODE -ne 0) {
  Write-Error "git push failed. Check your GitHub auth (gh auth login or SSH key)."
}

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "Vercel should redeploy in ~1-2 minutes if the GitHub project is connected."
Write-Host ""
Write-Host "Production:  https://smpl-financial-intelligence.vercel.app/"
Write-Host "Quote form:  https://smpl-financial-intelligence.vercel.app/request-quote"
Write-Host ""
Write-Host "After deploy, submit a test quote and inspect the Network tab response:"
Write-Host "  hubspot.companyDebug.resolvedFrom  -> should be domain-upsert:update or domain-upsert:create"
Write-Host "  hubspot.companyId                  -> single company id used for contact + deal links"
Write-Host ""
Write-Host "Vercel env vars required (Project Settings -> Environment Variables):"
Write-Host "  HUBSPOT_PRIVATE_APP_TOKEN"
Write-Host "  HUBSPOT_PIPELINE_NAME=SMPL Inbound Sales"
Write-Host ""
