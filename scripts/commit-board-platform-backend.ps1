# Stage backend files required for Board Platform + Forecast Engine + Anthropic deploy.
# Run from repo root, then: git commit && git push origin main

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

$paths = @(
    "backend/app/main.py"
    "backend/app/api/board_platform_routes.py"
    "backend/app/api/forecast_engine_routes.py"
    "backend/app/api/forecast_version_routes.py"
    "backend/app/schemas/forecast_version.py"
    "backend/app/models/forecast_version.py"
    "backend/app/models/organization.py"
    "backend/app/models/__init__.py"
    "backend/app/services/board_platform_service.py"
    "backend/app/services/dashboard/executive_service.py"
    "backend/app/services/forecast_version_service.py"
    "backend/app/services/reporting/as_of_period.py"
    "backend/app/services/reporting/three_statement_payload.py"
    "backend/app/services/reporting/validation_gate.py"
    "backend/app/services/reporting/org_reporting_settings.py"
    "backend/app/services/reporting/fiscal_year.py"
    "backend/app/services/commentary/llm_factory.py"
    "backend/app/services/commentary/anthropic_client.py"
    "backend/app/services/demo_csv/loader.py"
    "backend/app/services/entitlements.py"
    "backend/app/services/reporting/export/board_commentary_service.py"
    "backend/app/services/reporting/export/commentary_engine.py"
    "backend/app/services/reporting/export/multi_scenario.py"
    "backend/app/services/reporting/export/data_collector.py"
    "backend/tests/test_board_platform_service.py"
    "frontend/components/board/BoardPlatformApp.tsx"
    "backend/app/api/export_routes.py"
    "backend/app/api/commentary_routes.py"
    "backend/app/core/config.py"
    "backend/app/core/openai_status.py"
    "backend/requirements.txt"
    "backend/alembic/versions/forecast_001_versions_and_org_reporting.py"
    "backend/scripts/import-anthropic-keys.ps1"
    "backend/scripts/check-openai-config.py"
    "backend/secrets.env.example"
    "scripts/set-railway-anthropic-keys.ps1"
    "docs/ANTHROPIC_SETUP.md"
)

$missing = @()
foreach ($rel in $paths) {
    $full = Join-Path $repoRoot $rel
    if (-not (Test-Path -LiteralPath $full)) {
        $missing += $rel
    }
}

if ($missing.Count -gt 0) {
    Write-Host "Missing files (create or fix paths before commit):" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  $_" }
    exit 1
}

git add @paths
Write-Host ""
Write-Host "Staged backend platform + Anthropic files." -ForegroundColor Green
Write-Host ""
git status -sb
Write-Host ""
Write-Host "Next:" -ForegroundColor Cyan
Write-Host '  git commit -m "Fix board platform payload as_of_period and lighten bundle load"'
Write-Host "  git push origin main"
Write-Host ""
Write-Host "After Railway sfi-api deploy succeeds, verify:"
Write-Host '  curl.exe -s https://sfi-api-production.up.railway.app/api/v1/export/ping'
