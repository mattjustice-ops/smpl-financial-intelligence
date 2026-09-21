# Deploy Plan Assurance platform engine: Neon migration, commit/push, Vercel redeploy.
#
# Railway does NOT run Alembic inside the container - migrations hit Neon from your
# machine using the saved prod DATABASE_URL (same Neon branch Railway uses).
#
# No new Vercel env vars are required for Plan Assurance (uses existing API / session).
#
# Usage (repo root):
#   .\scripts\deploy-plan-assurance.ps1
#   .\scripts\deploy-plan-assurance.ps1 -CommitPush
#   .\scripts\deploy-plan-assurance.ps1 -CommitPush -SkipConfirmMigration
#   .\scripts\deploy-plan-assurance.ps1 -CommitPush -SkipMigration -RedeployVercel
#   .\scripts\deploy-plan-assurance.ps1 -CommitPush -RunTests
#
# Steps:
#   1. (optional) pytest Plan Assurance suite
#   2. alembic upgrade head on production Neon (ppi_001 plan_assessments)
#   3. Optional: commit + push main -> Railway API + Vercel auto-deploy
#   4. Explicit Vercel production redeploy (Budget/Forecast static HTML)

param(
    [switch]$CommitPush,
    [switch]$SkipMigration,
    [switch]$RedeployVercel,
    [switch]$SkipConfirmMigration,
    [switch]$RunTests,
    [switch]$SkipVercelRedeploy,
    [string]$CommitMessage = "Ship Plan Assurance platform engine (assess SoT, WHTT, persist, server MC, priors)"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $repoRoot "backend"
$python = Join-Path $backendDir ".venv312\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

Write-Host ""
Write-Host "=== Deploy Plan Assurance ===" -ForegroundColor Cyan
Write-Host ""

if ($RunTests) {
    Write-Host "0. Local pytest (Plan Assurance)" -ForegroundColor Yellow
    Push-Location $backendDir
    try {
        & $python -m pytest tests/test_predictive_planning.py tests/test_plan_assurance_platform.py -q --tb=line
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    finally {
        Pop-Location
    }
    Write-Host ""
}

if (-not $SkipMigration) {
    Write-Host "1. Neon migration (production) - run locally, not on Railway" -ForegroundColor Yellow
    Write-Host "   Applies ppi_001 (plan_assessments) via frontend/.env.neon-production.local" -ForegroundColor DarkGray
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

if ($CommitPush) {
    Write-Host ""
    Write-Host "2. Commit + push main (Railway API auto-deploys from GitHub)" -ForegroundColor Yellow
    Push-Location $repoRoot
    try {
        $paFiles = @(
            # Migration + model
            "backend/alembic/versions/ppi_001_plan_assessments.py",
            "backend/app/models/plan_assessment.py",
            "backend/app/models/__init__.py",
            # API + schemas + services
            "backend/app/api/predictive_planning_routes.py",
            "backend/app/schemas/predictive_planning.py",
            "backend/app/services/predictive_planning/__init__.py",
            "backend/app/services/predictive_planning/feasibility.py",
            "backend/app/services/predictive_planning/monte_carlo.py",
            "backend/app/services/predictive_planning/priors.py",
            "backend/app/services/predictive_planning/persistence.py",
            "backend/app/services/predictive_planning/forecast_adapter.py",
            "backend/app/services/predictive_planning/board_citation.py",
            # Board citation wiring
            "backend/app/services/reporting/export/board_commentary_service.py",
            "backend/app/services/reporting/export/board_slide_commentary_payload.py",
            # Tests + docs
            "backend/tests/test_plan_assurance_platform.py",
            "docs/product/SMPL_Predictive_Planning_Intelligence_Framework.md",
            # Budget + Forecast surfaces
            "frontend/public/budget-engine/index.html",
            "frontend/public/forecast-engine/index.html",
            "frontend/canonical/forecast-engine/index.html",
            # Deploy helper
            "scripts/deploy-plan-assurance.ps1",
            "scripts/_patch_budget_plan_assurance.py"
        )
        foreach ($f in $paFiles) {
            $full = Join-Path $repoRoot $f
            if (Test-Path $full) {
                git add -- $f
            }
            else {
                Write-Host "   skip (missing): $f" -ForegroundColor DarkGray
            }
        }

        $staged = git diff --cached --name-only
        if ($staged) {
            Write-Host "   Staged:" -ForegroundColor DarkGray
            $staged | ForEach-Object { Write-Host "     $_" -ForegroundColor DarkGray }
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
    Write-Host "2. Skipping git push (pass -CommitPush when code is ready)." -ForegroundColor DarkGray
}

# Frontend Budget/Forecast HTML lives on Vercel - redeploy so public/ copies go live.
# Default: redeploy after CommitPush unless -SkipVercelRedeploy.
$shouldRedeploy = $RedeployVercel -or ($CommitPush -and -not $SkipVercelRedeploy)
if ($shouldRedeploy) {
    Write-Host ""
    Write-Host "3. Vercel production redeploy (Budget / Forecast Plan Assurance UI)" -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot "redeploy-vercel-production.ps1") -SkipBuild
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
else {
    Write-Host ""
    Write-Host "3. Skipping Vercel redeploy (pass -RedeployVercel, or -CommitPush without -SkipVercelRedeploy)." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "=== Plan Assurance deploy complete ===" -ForegroundColor Green
Write-Host "  Migration: plan_assessments on Neon (revision ppi_001)" -ForegroundColor White
Write-Host "  API:       https://sfi-api-production.up.railway.app/api/v1/predictive-planning/constraints" -ForegroundColor White
Write-Host "  UI:        https://www.smpl-ai.com/app  -> Budget Engine -> Analytics" -ForegroundColor White
Write-Host "  Verify:    Open Analytics, Refresh status; WHTT + method card should appear after /assess." -ForegroundColor DarkGray
Write-Host ""
