# Commit landing + request-quote changes and push to GitHub (triggers Vercel).
# Run from repo root:  .\scripts\push-to-vercel.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (git rev-parse --is-inside-work-tree 2>$null)) {
  Write-Error "Not a git repository. Clone https://github.com/mattjustice-ops/smpl-financial-intelligence first."
}

Write-Host "Branch:" (git branch --show-current)
Write-Host "Remote:" (git remote get-url origin)

git status

$envFiles = @(".env.local", "frontend/.env.local", "backend/.env", "backend/secrets.env")
git add -A
foreach ($f in $envFiles) {
  if (Test-Path $f) {
    git restore --staged $f 2>$null
  }
}

$staged = git diff --cached --name-only
if (-not $staged) {
  Write-Host "Nothing to commit — working tree clean. Pushing current branch..."
} else {
  Write-Host "Staging:"
  $staged | ForEach-Object { Write-Host "  $_" }
  git commit -m "Polish landing page and request-quote flow" -m "Update landing copy and header CTAs, add request-quote workflow with HubSpot sync, and fix hero interactions."
}

git push origin HEAD
Write-Host ""
Write-Host "Done. Vercel will redeploy from GitHub if the project is connected."
Write-Host "Production: https://smpl-financial-intelligence.vercel.app/"
Write-Host ""
Write-Host "Set these in Vercel (frontend project) for request-quote + HubSpot:"
Write-Host "  HUBSPOT_PRIVATE_APP_TOKEN"
Write-Host "  HUBSPOT_PIPELINE_NAME=SMPL Inbound Sales"
Write-Host "  NEXT_PUBLIC_SCHEDULING_URL (optional, already has default)"
