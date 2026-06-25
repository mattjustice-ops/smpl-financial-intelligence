# Commit + push board AI fixes (Railway startup + live Claude routes + exports).
#
# Usage (repo root):
#   .\scripts\deploy-board-ai-fix.ps1              # dry run
#   .\scripts\deploy-board-ai-fix.ps1 -CommitPush  # commit, push, verify API

param(
    [switch]$CommitPush,
    [switch]$SkipBuild,
    [string]$Branch = "main",
    [string]$ApiBase = "https://sfi-api-production.up.railway.app",
    [int]$PollSeconds = 900,
    [int]$PollIntervalSeconds = 20
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent

function Invoke-Git {
    param([string[]]$GitArgs)
    $output = & git -C $repoRoot @GitArgs 2>&1 | ForEach-Object { "$_" }
    if ($LASTEXITCODE -ne 0) {
        if ($output) { Write-Host ($output -join "`n") -ForegroundColor Red }
        throw "git $($GitArgs -join ' ') failed (exit $LASTEXITCODE)"
    }
    if ($output) { Write-Host ($output -join "`n") }
}

function Test-ApiImport {
    Push-Location (Join-Path $repoRoot "backend")
    try {
        python -c "from app.main import app; print('import_ok')" 2>&1 | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) { throw "Backend import failed" }
        python -m pytest tests/test_output_requirements.py -q 2>&1 | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) { throw "Backend tests failed" }
    } finally {
        Pop-Location
    }
}

Write-Host ""
Write-Host "=== Board AI fix deploy ===" -ForegroundColor Cyan
Write-Host "Repo:   $repoRoot"
Write-Host "Branch: $Branch"
Write-Host "API:    $ApiBase"
Write-Host ""

$paths = @(
    "backend/app/services/reporting/export/export_sheet_registry.py",
    "backend/app/services/reporting/export/output_requirements.py",
    "backend/app/services/reporting/export/board_commentary_service.py",
    "backend/app/api/board_platform_routes.py",
    "backend/app/services/reporting/export/pptx_template_export.py",
    "backend/app/services/reporting/export/commentary_engine.py",
    "backend/tests/test_output_requirements.py",
    "frontend/public/shared/board-hydrate.js",
    "frontend/public/board/index.html",
    "frontend/vercel.json",
    "scripts/deploy-board-ai-fix.ps1"
)

foreach ($rel in $paths) {
    $full = Join-Path $repoRoot $rel
    if (-not (Test-Path -LiteralPath $full)) {
        Write-Error "Missing file: $rel"
    }
}

Write-Host "Backend smoke test..." -ForegroundColor Yellow
Test-ApiImport
Write-Host "Backend OK." -ForegroundColor Green
Write-Host ""

Write-Host "Staging files..." -ForegroundColor Yellow
foreach ($rel in $paths) {
    Invoke-Git @("add", $rel)
    Write-Host "  + $rel" -ForegroundColor DarkGray
}

Write-Host ""
Invoke-Git @("status", "-sb")

if (-not $CommitPush) {
    Write-Host ""
    Write-Host "Dry run complete. Deploy with:" -ForegroundColor Cyan
    Write-Host "  .\scripts\deploy-board-ai-fix.ps1 -CommitPush"
    exit 0
}

if (-not $SkipBuild) {
    Write-Host ""
    Write-Host "Frontend build..." -ForegroundColor Yellow
    Push-Location (Join-Path $repoRoot "frontend")
    try {
        npm run build 2>&1 | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) { throw "npm run build failed" }
    } finally {
        Pop-Location
    }
}

$staged = @(& git -C $repoRoot diff --cached --name-only 2>&1)
if ($staged.Count -gt 0) {
    $msg = @"
fix: board AI — Railway startup, live Claude routes, export timeouts

Merge output requirements into export_sheet_registry so Railway boots.
Wire board commentary/copilot/exports through authenticated API proxies.
"@
    $msgFile = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($msgFile, $msg, [System.Text.UTF8Encoding]::new($false))
        Invoke-Git @("commit", "-F", $msgFile)
    } finally {
        Remove-Item -LiteralPath $msgFile -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "Nothing staged — pushing current branch." -ForegroundColor Yellow
}

Invoke-Git @("push", "-u", "origin", $Branch)
$hash = (& git -C $repoRoot rev-parse --short HEAD 2>&1 | Select-Object -Last 1).Trim()
Write-Host "Pushed $hash" -ForegroundColor Green

Write-Host ""
Write-Host "Polling Railway /export/ping ..." -ForegroundColor Cyan
$deadline = (Get-Date).AddSeconds($PollSeconds)
$ok = $false
while ((Get-Date) -lt $deadline) {
    try {
        $r = Invoke-RestMethod -Uri "$ApiBase/api/v1/export/ping" -TimeoutSec 30
        if ($r) {
            Write-Host "  ping OK: anthropic_configured=$($r.anthropic_configured)" -ForegroundColor Green
            $ok = $true
            break
        }
    } catch {
        Write-Host "  waiting... $($_.Exception.Message)" -ForegroundColor DarkGray
    }
    Start-Sleep -Seconds $PollIntervalSeconds
}

if (-not $ok) {
    Write-Host "Railway ping did not succeed within $PollSeconds s — check Railway logs." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Deploy complete. Test /app/board commentary, Copilot, and MD&A exports." -ForegroundColor Green
