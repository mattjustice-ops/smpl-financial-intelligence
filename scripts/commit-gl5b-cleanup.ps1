# Commit + push gl-5b sandbox Preview cleanup (auth, debug route, scripts, docs).
# Excludes local secret env files.
#
# Usage:
#   .\scripts\commit-gl5b-cleanup.ps1
#   .\scripts\commit-gl5b-cleanup.ps1 -Push

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

$branch = "gl-5b-sandbox"
$current = (git branch --show-current 2>&1 | Select-Object -Last 1).Trim()
if ($current -ne $branch) {
    Write-Host "Checking out $branch ..." -ForegroundColor Yellow
    $exists = git branch --list $branch 2>&1
    if ($exists) {
        git checkout $branch
    }
    else {
        git checkout -b $branch
    }
}

$paths = @(
    "frontend/auth.ts",
    "frontend/auth.config.ts",
    "frontend/lib/auth/sync-backend-session.ts",
    "frontend/lib/billing/backend-client.ts",
    "frontend/lib/go-live-progress.ts",
    "frontend/app/api/debug",
    "frontend/app/health",
    "docs/ENVIRONMENTS.md",
    "docs/GO_LIVE_GL5_STAGING.md",
    "scripts/commit-gl5b-cleanup.ps1",
    "scripts/deploy-gl5b-preview-auth-fix.ps1",
    "scripts/set-railway-sandbox-cors.ps1",
    "scripts/fix-gl5b-preview.ps1",
    "scripts/audit-gl5b-stack.ps1",
    "scripts/set-vercel-staging-env.ps1",
    "scripts/set-vercel-preview-auth-db.ps1",
    "scripts/set-vercel-preview-billing-from-production.ps1",
    "scripts/verify-vercel-preview-api-url.ps1",
    "scripts/print-vercel-preview-api-values.ps1",
    "scripts/compare-session-sync.ps1",
    "scripts/verify-staging-session-sync.ps1",
    "scripts/verify-staging-stack.ps1",
    "scripts/verify-preview-deploy.ps1",
    "scripts/check-vercel-preview-env.ps1",
    "scripts/check-staging-login.ps1",
    "scripts/set-staging-demo-workspace.ps1",
    "scripts/save-staging-config.ps1",
    "scripts/smoke-test-staging.ps1",
    "scripts/lib/Invoke-VercelEnv.ps1",
    "scripts/lib/Resolve-StagingConfig.ps1"
)

Write-Host ""
Write-Host "=== gl-5b cleanup commit ===" -ForegroundColor Cyan
Write-Host "Branch: $branch" -ForegroundColor DarkGray
Write-Host ""

foreach ($rel in $paths) {
    $full = Join-Path $repoRoot $rel
    if (Test-Path $full) {
        git add -- $rel
        Write-Host "  + $rel" -ForegroundColor DarkGray
    }
}

$secretPaths = @(
    "frontend/.env.local",
    "frontend/.env.staging.local",
    "frontend/.env.neon-production.local",
    "frontend/.env.vercel-production.local",
    "scripts/config/staging.local.env",
    "backend/secrets.env"
)

foreach ($path in $secretPaths) {
    $inIndex = git ls-files --cached -- $path 2>$null
    if ($inIndex) {
        git restore --staged -- $path
        Write-Host "  - unstaged secret: $path" -ForegroundColor Yellow
    }
}

$staged = git diff --cached --name-only
if (-not $staged) {
    Write-Host ""
    Write-Host "Nothing to commit (working tree clean or files already committed)." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Staged:" -ForegroundColor Yellow
$staged | ForEach-Object { Write-Host "  $_" -ForegroundColor White }

$commitMessage = @"
Complete gl-5b sandbox Preview validation.

Preview login syncs to sandbox API/DB (SMPL Demo Co), adds a Preview-only debug
route, documents production vs sandbox in ENVIRONMENTS.md, and ships ops scripts
for Vercel Preview env and Railway sandbox CORS.
"@

$msgFile = [System.IO.Path]::GetTempFileName()
try {
    [System.IO.File]::WriteAllText($msgFile, $commitMessage, [System.Text.UTF8Encoding]::new($false))
    git commit -F $msgFile
}
finally {
    Remove-Item -LiteralPath $msgFile -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Committed:" (git log -1 --oneline) -ForegroundColor Green

if ($Push) {
    git push -u origin $branch
    Write-Host ""
    Write-Host "Pushed to origin/$branch" -ForegroundColor Green
    Write-Host "Preview: https://smpl-financial-intelligence-git-gl-5b-sandbox-smplai.vercel.app" -ForegroundColor Cyan
}
