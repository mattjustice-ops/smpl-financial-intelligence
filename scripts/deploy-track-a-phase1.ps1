# Track A Phase 1 - single commit/push checklist for board export + live commentary.
#
# Stages the Phase 1 file bundle, optionally commits + pushes to origin/main
# (Railway sfi-api + Vercel production auto-deploy), then runs automated prod checks.
#
# Usage (repo root):
#   .\scripts\deploy-track-a-phase1.ps1                 # dry run (stage + status)
#   .\scripts\deploy-track-a-phase1.ps1 -CommitPush     # commit, push, verify
#   .\scripts\deploy-track-a-phase1.ps1 -CommitPush -SkipBuild
#
# Manual sign-off after deploy: mark dr-8, dr-9, dr-11, dr-12 on /progress.

param(
    [switch]$CommitPush,
    [switch]$SkipBuild,
    [string]$Branch = "main",
    [string]$ApiBase = "https://sfi-api-production.up.railway.app",
    [string]$FrontendUrl = "https://www.smpl-ai.com",
    [string]$OrganizationId = "8571e520-0687-4516-bdee-379f37c58c1f",
    [int]$PollSeconds = 600,
    [int]$PollIntervalSeconds = 20
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$frontendDir = Join-Path $repoRoot "frontend"
$apiRoot = $ApiBase.TrimEnd("/")

function Build-ExportQueryUrl {
    param(
        [string]$Path,
        [hashtable]$Query
    )
    $pairs = foreach ($key in $Query.Keys) {
        "{0}={1}" -f [uri]::EscapeDataString($key), [uri]::EscapeDataString([string]$Query[$key])
    }
    return '{0}{1}?{2}' -f $apiRoot, $Path, ($pairs -join '&')
}

function Invoke-Git {
    param([string[]]$GitArgs)
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & git -C $repoRoot @GitArgs 2>&1 | ForEach-Object { "$_" }
    } finally {
        $ErrorActionPreference = $prevEap
    }
    if ($LASTEXITCODE -ne 0) {
        if ($output) {
            Write-Host ($output -join "`n") -ForegroundColor Red
        }
        throw "git $($GitArgs -join ' ') failed (exit $LASTEXITCODE)"
    }
    if ($output) {
        Write-Host ($output -join "`n")
    }
}

# Phase 1 bundle - backend template commentary + export defaults + frontend async export
$paths = @(
    "backend/Dockerfile",
    "backend/templates/board/SMPL_Board_Review_Template.pptx",
    "backend/app/api/export_routes.py",
    "backend/app/services/reporting/export/export_jobs.py",
    "backend/app/services/reporting/export/pptx_template_export.py",
    "backend/app/services/reporting/export/board_commentary_service.py",
    "backend/app/services/reporting/export/board_api_prompts.py",
    "backend/app/services/reporting/export/board_slide_commentary_payload.py",
    "backend/app/services/reporting/export/mda_package_injection.py",
    "backend/app/services/reporting/export/mda_package_payload.py",
    "backend/tests/test_pptx_template_export.py",
    "backend/tests/test_mda_package.py",
    "frontend/public/shared/board-hydrate.js",
    "frontend/canonical/shared/board-hydrate.js",
    "frontend/public/board/index.html",
    "frontend/canonical/board/index.html",
    "frontend/lib/go-live-progress.ts",
    "scripts/deploy-track-a-phase1.ps1",
    "scripts/verify-board-exports-prod.ps1"
)

Write-Host ""
Write-Host "=== Track A Phase 1 - commit/push checklist ===" -ForegroundColor Cyan
Write-Host "Repo:     $repoRoot"
Write-Host "Branch:   $Branch"
Write-Host "API:      $apiRoot"
Write-Host "Frontend: $FrontendUrl"
Write-Host ""

Write-Host "CHECKLIST (automated + manual)" -ForegroundColor Yellow
Write-Host "  [ ] On branch main (Vercel + Railway deploy from main only)"
Write-Host "  [ ] Stage Phase 1 file bundle (this script)"
Write-Host "  [ ] Optional: frontend npm run build"
Write-Host "  [ ] Commit + push origin/main"
Write-Host "  [ ] Wait 2-5 min for Railway + Vercel"
Write-Host "  [ ] GET /api/v1/export/ping -> board_pptx_template_ready + anthropic_configured"
Write-Host "  [ ] POST /export/jobs/mda-deck -> 200 (async export live)"
Write-Host "  [ ] /app/board: MDA Deck export -> X-Board-AI-Commentary: true"
Write-Host "  [ ] Open PPTX: Key Takeaways reference June period + live metrics"
Write-Host "  [ ] Mark dr-8, dr-9, dr-11, dr-12 done on /progress after sign-off"
Write-Host ""

if (-not (Test-Path (Join-Path $repoRoot ".git"))) {
    Write-Error "Not a git repository: $repoRoot"
}

$currentBranch = (& git -C $repoRoot branch --show-current 2>&1 | Select-Object -Last 1).Trim()
if ($currentBranch -ne $Branch) {
    Write-Host "WARNING: current branch is '$currentBranch' (expected '$Branch')." -ForegroundColor Yellow
    if ($CommitPush) {
        Write-Host "Checking out $Branch ..." -ForegroundColor Yellow
        Invoke-Git @("checkout", $Branch)
    }
}

$missing = @()
foreach ($rel in $paths) {
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $rel))) {
        $missing += $rel
    }
}

if ($missing.Count -gt 0) {
    Write-Host "Missing files (fix paths before deploy):" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  $_" }
    exit 1
}

Write-Host "Staging Phase 1 files..." -ForegroundColor Yellow
foreach ($rel in $paths) {
    Invoke-Git @("add", $rel)
    Write-Host "  + $rel" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Git status:" -ForegroundColor Yellow
Invoke-Git @("status", "-sb")

if (-not $CommitPush) {
    Write-Host ""
    Write-Host "Dry run complete. To deploy:" -ForegroundColor Cyan
    Write-Host "  .\scripts\deploy-track-a-phase1.ps1 -CommitPush"
    Write-Host ""
    exit 0
}

if (-not $SkipBuild) {
    Write-Host ""
    Write-Host "Running frontend production build..." -ForegroundColor Yellow
    Push-Location $frontendDir
    try {
        npm install 2>&1 | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
        npm run build 2>&1 | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) { throw "npm run build failed" }
        Write-Host "Frontend build OK." -ForegroundColor Green
    } finally {
        Pop-Location
    }
    foreach ($rel in @(
        "frontend/public/shared/board-hydrate.js",
        "frontend/canonical/shared/board-hydrate.js",
        "frontend/public/board/index.html",
        "frontend/canonical/board/index.html",
        "frontend/lib/go-live-progress.ts"
    )) {
        Invoke-Git @("add", $rel)
    }
}

$staged = @(& git -C $repoRoot diff --cached --name-only 2>&1)
if ($staged.Count -eq 0) {
    Write-Host ""
    Write-Host "Nothing staged to commit. Pushing current $Branch anyway..." -ForegroundColor Yellow
} else {
    $msg = @"
feat: Track A Phase 1 board export - API-spec Claude commentary per slide

Wire template PPTX export to enrich_slide_with_ai per mapped slide_key,
default include_ai_commentary on async deck/package jobs, and add dr-7..dr-12
to go-live progress dashboard.
"@
    $msgFile = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($msgFile, $msg, [System.Text.UTF8Encoding]::new($false))
        Invoke-Git @("commit", "-F", $msgFile)
    } finally {
        Remove-Item -LiteralPath $msgFile -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ""
Write-Host "Pushing to origin/$Branch ..." -ForegroundColor Yellow
Invoke-Git @("push", "origin", $Branch)

Write-Host ""
Write-Host "Waiting for Railway export/ping (template + Anthropic) ..." -ForegroundColor Yellow
$deadline = (Get-Date).AddSeconds($PollSeconds)
$pingOk = $false

while ((Get-Date) -lt $deadline) {
    try {
        $ping = Invoke-RestMethod -Uri "$apiRoot/api/v1/export/ping" -TimeoutSec 30
        $build = [string]$ping.api_build
        $templateReady = [bool]$ping.board_pptx_template_ready
        $anthropic = [bool]$ping.anthropic_configured
        Write-Host "  ping build=$build template=$templateReady anthropic=$anthropic" -ForegroundColor DarkGray
        if ($templateReady -and $anthropic) {
            $pingOk = $true
            break
        }
    } catch {
        Write-Host "  ping not ready yet: $($_.Exception.Message)" -ForegroundColor DarkGray
    }
    Start-Sleep -Seconds $PollIntervalSeconds
}

Write-Host ""
if ($pingOk) {
    Write-Host "Automated checks passed (template + Anthropic on Railway)." -ForegroundColor Green
} else {
    Write-Host "Railway may still be deploying - re-run export/ping in a few minutes." -ForegroundColor Yellow
}

$jobUrl = Build-ExportQueryUrl -Path "/api/v1/export/jobs/mda-deck" -Query @{
    organization_id       = $OrganizationId
    scenario              = "Combined"
    start_period          = "2026-01"
    end_period            = "2026-12"
    as_of_period          = "2026-06"
    include_ai_commentary = "true"
}
$jobCode = curl.exe -s -o NUL -w "%{http_code}" -X POST $jobUrl
Write-Host "POST async mda-deck (no wait for completion): HTTP $jobCode"

Write-Host ""
Write-Host '=== Manual sign-off (/app/board, signed in) ===' -ForegroundColor Cyan
Write-Host "  1. Hard refresh: $FrontendUrl/app/board"
Write-Host "  2. Regenerate commentary on Executive Summary"
Write-Host "  3. Export MDA Deck - wait for download (3-10 min)"
Write-Host "  4. Confirm response headers: X-Board-PPTX-Source=template, X-Board-AI-Commentary=true"
Write-Host "  5. Spot-check Key Takeaways in the downloaded PPTX"
Write-Host "  6. Update dr-8..dr-12 on https://www.smpl-ai.com/progress"
Write-Host ""
