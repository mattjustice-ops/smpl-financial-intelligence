# Step C: commit + push auth fix to gl-5b-preview-test (triggers Vercel Preview rebuild).
#
# Usage:
#   .\scripts\deploy-gl5b-preview-auth-fix.ps1

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent

function Invoke-Git {
    param([string[]]$GitArgs)
    # Git prints benign line-ending warnings to stderr; do not treat as fatal.
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & git -C $repoRoot @GitArgs 2>&1 | ForEach-Object { "$_" }
    }
    finally {
        $ErrorActionPreference = $prevEap
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host ($output -join "`n") -ForegroundColor Red
        throw "git $($GitArgs -join ' ') failed (exit $LASTEXITCODE)"
    }
    if ($output) {
        Write-Host ($output -join "`n")
    }
}

Write-Host ""
Write-Host "=== Deploy gl-5b Preview auth fix ===" -ForegroundColor Cyan
Write-Host "Repo: $repoRoot" -ForegroundColor DarkGray
Write-Host ""

if (-not (Test-Path (Join-Path $repoRoot ".git"))) {
    Write-Host "ERROR: Not a git repo: $repoRoot" -ForegroundColor Red
    exit 1
}

$branch = "gl-5b-preview-test"
$commitMessage = @"
fix: refresh active org on magic-link sign-in for Preview staging

Session-sync on every signIn JWT trigger so Preview picks up staging workspace
changes after set-staging-demo-workspace.ps1. Includes staging helper scripts.
"@

Write-Host "Current branch:" -ForegroundColor Yellow
Invoke-Git @("branch", "--show-current")

$current = (& git -C $repoRoot branch --show-current 2>&1 | Select-Object -Last 1).Trim()
if ($current -ne $branch) {
    Write-Host "Checking out $branch ..." -ForegroundColor Yellow
    $exists = & git -C $repoRoot branch --list $branch 2>&1
    if ($exists) {
        Invoke-Git @("checkout", $branch)
    }
    else {
        Invoke-Git @("checkout", "-b", $branch)
    }
}

$paths = @(
    "frontend/auth.ts",
    "frontend/lib/billing/backend-client.ts",
    "frontend/next.config.js",
    "frontend/lib/go-live-progress.ts",
    "scripts/deploy-gl5b-preview-auth-fix.ps1",
    "scripts/set-staging-demo-workspace.ps1",
    "scripts/verify-staging-session-sync.ps1",
    "scripts/verify-preview-deploy.ps1",
    "scripts/check-staging-login.ps1",
    "scripts/set-vercel-preview-auth-db.ps1",
    "scripts/set-vercel-staging-env.ps1",
    "scripts/lib/Resolve-StagingConfig.ps1",
    "backend/scripts/check_login_access.py",
    "docs/GO_LIVE_GL5_STAGING.md"
)

Write-Host ""
Write-Host "Staging files..." -ForegroundColor Yellow
foreach ($rel in $paths) {
    $full = Join-Path $repoRoot $rel
    if (Test-Path $full) {
        Invoke-Git @("add", $rel)
        Write-Host "  + $rel" -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "Status before commit:" -ForegroundColor Yellow
Invoke-Git @("status", "-sb")

$staged = & git -C $repoRoot diff --cached --name-only 2>&1
if (-not $staged) {
    Write-Host ""
    Write-Host "Nothing staged to commit." -ForegroundColor Yellow
    Write-Host "If you expected backend-client.ts / next.config.js, check:" -ForegroundColor Yellow
    Write-Host "  git status -sb frontend/lib/billing/backend-client.ts frontend/next.config.js" -ForegroundColor White
    Write-Host "  git log -1 --oneline" -ForegroundColor White
    exit 0
}

Write-Host ""
Write-Host "Committing..." -ForegroundColor Yellow
$msgFile = [System.IO.Path]::GetTempFileName()
try {
    [System.IO.File]::WriteAllText($msgFile, $commitMessage, [System.Text.UTF8Encoding]::new($false))
    Invoke-Git @("commit", "-F", $msgFile)
}
finally {
    Remove-Item -LiteralPath $msgFile -Force -ErrorAction SilentlyContinue
}

$hash = (& git -C $repoRoot rev-parse --short HEAD 2>&1 | Select-Object -Last 1).Trim()
Write-Host ""
Write-Host "Pushing to origin/$branch ..." -ForegroundColor Yellow
Invoke-Git @("push", "-u", "origin", $branch)

Write-Host ""
Write-Host "OK: pushed $hash to origin/$branch" -ForegroundColor Green
Write-Host ""
Write-Host "Next:" -ForegroundColor Yellow
Write-Host "  1. Vercel -> Deployments -> wait for gl-5b-preview-test build (or Redeploy)" -ForegroundColor White
Write-Host "  2. .\scripts\set-staging-demo-workspace.ps1" -ForegroundColor White
Write-Host "  3. Preview: sign out -> NEW magic link -> banner should say SMPL Demo Co" -ForegroundColor White
Write-Host ""
