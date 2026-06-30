# Deploy SMPL Ops (Phase 0 + 1): Neon migration, Vercel env, git push, redeploy.
#
# Railway does NOT run Alembic inside the container - migrations hit Neon from your
# machine using the saved prod DATABASE_URL (same Neon branch Railway uses).
#
# Usage (repo root):
#   .\scripts\deploy-smpl-ops.ps1 -AdminEmails "you@smpl-ai.com"
#   .\scripts\deploy-smpl-ops.ps1 -AdminEmails "you@smpl-ai.com" -CommitPush
#   .\scripts\deploy-smpl-ops.ps1 -AdminEmails "you@smpl-ai.com" -CommitPush -SkipMigration
#
# Steps:
#   1. alembic upgrade head on production Neon (ops_001 usage_events)
#   2. Set SMPL_OPS_ADMIN_EMAILS on Vercel Production
#   3. Optional: commit + push main -> Railway + Vercel auto-deploy
#   4. Optional: explicit Vercel production redeploy (picks up env without waiting)

param(
    [Parameter(Mandatory = $true)]
    [string]$AdminEmails,
    [switch]$CommitPush,
    [switch]$SkipMigration,
    [switch]$SkipVercelEnv,
    [switch]$RedeployVercel,
    [switch]$SkipConfirmMigration,
    [string]$CommitMessage = "Add SMPL Ops dashboard with usage_events instrumentation"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent

Write-Host ""
Write-Host "=== Deploy SMPL Ops ===" -ForegroundColor Cyan
Write-Host ""

if (-not $SkipMigration) {
    Write-Host "1. Neon migration (production) - run locally, not on Railway" -ForegroundColor Yellow
    Write-Host "   Uses frontend/.env.neon-production.local DATABASE_URL" -ForegroundColor DarkGray
    $migrateScript = Join-Path $PSScriptRoot "run-alembic-migration.ps1"
    if ($SkipConfirmMigration) {
        & $migrateScript -Environment prod -SkipConfirm
    }
    else {
        & $migrateScript -Environment prod
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
else {
    Write-Host "1. Skipping migration (-SkipMigration)." -ForegroundColor DarkGray
}

if (-not $SkipVercelEnv) {
    Write-Host ""
    Write-Host "2. Vercel env: SMPL_OPS_ADMIN_EMAILS" -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot "set-vercel-ops-admin-env.ps1") -AdminEmails $AdminEmails
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
else {
    Write-Host ""
    Write-Host "2. Skipping Vercel env (-SkipVercelEnv)." -ForegroundColor DarkGray
}

if ($CommitPush) {
    Write-Host ""
    Write-Host "3. Commit + push main (Railway API auto-deploys from GitHub)" -ForegroundColor Yellow
    Push-Location $repoRoot
    try {
        $opsFiles = @(
            "backend/alembic/versions/ops_001_usage_events.py",
            "backend/app/api/ops_routes.py",
            "backend/app/models/usage_event.py",
            "backend/app/services/ops",
            "backend/tests/test_ops_usage.py",
            "backend/app/api/export_routes.py",
            "backend/app/main.py",
            "backend/app/models/__init__.py",
            "backend/app/services/commentary/anthropic_client.py",
            "backend/app/services/reporting/export/export_jobs.py",
            "backend/.env.example",
            "frontend/app/api/ops",
            "frontend/app/app/ops",
            "frontend/components/ops",
            "frontend/lib/ops",
            "frontend/lib/auth/require-ops-admin.ts",
            "frontend/components/app/AppSessionBanner.tsx",
            "frontend/.env.example",
            "scripts/set-vercel-ops-admin-env.ps1",
            "scripts/deploy-smpl-ops.ps1"
        )
        foreach ($f in $opsFiles) {
            $full = Join-Path $repoRoot $f
            if (Test-Path $full) {
                git add $f
            }
        }

        $staged = git diff --cached --name-only
        if ($staged) {
            $msgFile = [System.IO.Path]::GetTempFileName()
            [System.IO.File]::WriteAllText($msgFile, $CommitMessage, [System.Text.UTF8Encoding]::new($false))
            git commit -F $msgFile
            Remove-Item -LiteralPath $msgFile -Force -ErrorAction SilentlyContinue
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        }
        else {
            Write-Host "   Nothing new to commit - pushing current main if needed." -ForegroundColor DarkGray
        }

        git push origin main
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Write-Host "   Pushed. Railway + Vercel deploy in ~2-5 min." -ForegroundColor Green
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host ""
    Write-Host "3. Skipping git push (pass -CommitPush when code is ready)." -ForegroundColor DarkGray
}

if ($RedeployVercel -or (-not $SkipVercelEnv)) {
    Write-Host ""
    Write-Host "4. Vercel production redeploy (env vars need a fresh deploy)" -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot "redeploy-vercel-production.ps1") -SkipBuild
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host ""
Write-Host "=== SMPL Ops deploy complete ===" -ForegroundColor Green
Write-Host "  Migration: usage_events on Neon (revision ops_001)" -ForegroundColor White
Write-Host "  Dashboard: https://www.smpl-ai.com/app/ops" -ForegroundColor White
Write-Host "  Seed data: run a board export with AI on demo org, then refresh Ops" -ForegroundColor DarkGray
Write-Host ""
