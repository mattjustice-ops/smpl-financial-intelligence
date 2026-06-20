# Deploy tonight's Board Platform load fix to Railway (prod API) + Vercel (frontend).
#
# What this does:
#   1. Stage board-platform backend + frontend files
#   2. Optional local frontend build check
#   3. Commit + push origin/main  -> triggers Railway sfi-api + Vercel production
#   4. Poll until board payload returns HTTP 200
#
# Usage (repo root):
#   .\scripts\deploy-board-platform-tonight.ps1              # dry run (stage + status)
#   .\scripts\deploy-board-platform-tonight.ps1 -CommitPush  # commit, push, verify
#   .\scripts\deploy-board-platform-tonight.ps1 -CommitPush -SkipBuild
#
# Prerequisites:
#   - git remote origin -> GitHub (Railway + Vercel connected to main)
#   - gh auth login OR git push credentials configured

param(
    [switch]$CommitPush,
    [switch]$SkipBuild,
    [string]$Branch = "main",
    [string]$ApiBase = "https://sfi-api-production.up.railway.app",
    [string]$FrontendUrl = "https://smpl-financial-intelligence.vercel.app",
    [string]$OrganizationId = "8571e520-0687-4516-bdee-379f37c58c1f",
    [int]$PollSeconds = 900,
    [int]$PollIntervalSeconds = 20
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$frontendDir = Join-Path $repoRoot "frontend"

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

function Test-BoardPayload {
    param(
        [string]$BaseUrl,
        [string]$OrgId,
        [int]$TimeoutSec = 240
    )
    $url = "$($BaseUrl.TrimEnd('/'))/api/v1/board-platform/payload?organization_id=$OrgId&include_validation=false&include_three_statement=false"
    Write-Host "  GET $url" -ForegroundColor DarkGray
    try {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $response = Invoke-WebRequest -Uri $url -Method Get -TimeoutSec $TimeoutSec -UseBasicParsing
        $sw.Stop()
        return @{
            Ok = ($response.StatusCode -eq 200)
            StatusCode = $response.StatusCode
            Seconds = [math]::Round($sw.Elapsed.TotalSeconds, 1)
            Body = $response.Content
        }
    } catch {
        $status = $null
        if ($_.Exception.Response) {
            $status = [int]$_.Exception.Response.StatusCode
        }
        return @{
            Ok = $false
            StatusCode = $status
            Seconds = $null
            Body = $_.Exception.Message
        }
    }
}

Write-Host ""
Write-Host "=== Board Platform tonight deploy (Railway + Vercel) ===" -ForegroundColor Cyan
Write-Host "Repo:     $repoRoot"
Write-Host "Branch:   $Branch"
Write-Host "API:      $ApiBase"
Write-Host "Frontend: $FrontendUrl"
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

$paths = @(
    "backend/app/api/board_platform_routes.py",
    "backend/app/services/board_platform_service.py",
    "backend/app/services/reporting/export/data_collector.py",
    "backend/app/services/dashboard/opportunity_attribution_service.py",
    "backend/app/services/dashboard/executive_service.py",
    "backend/app/services/reporting/as_of_period.py",
    "backend/tests/test_board_platform_service.py",
    "backend/tests/test_opportunity_attribution_params.py",
    "frontend/components/board/BoardPlatformApp.tsx",
    "frontend/lib/apiBase.ts",
    "frontend/app/api/v1/board-platform/payload/route.ts",
    "frontend/vercel.json",
    "scripts/deploy-board-platform-tonight.ps1"
)

$missing = @()
foreach ($rel in $paths) {
    $full = Join-Path $repoRoot $rel
    if (-not (Test-Path -LiteralPath $full)) {
        $missing += $rel
    }
}

if ($missing.Count -gt 0) {
    Write-Host "Missing files (fix paths before deploy):" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  $_" }
    exit 1
}

Write-Host "Staging board platform files..." -ForegroundColor Yellow
foreach ($rel in $paths) {
    Invoke-Git @("add", $rel)
    Write-Host "  + $rel" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Git status:" -ForegroundColor Yellow
Invoke-Git @("status", "-sb")

if (-not $CommitPush) {
    Write-Host ""
    Write-Host "Dry run complete. To deploy tonight:" -ForegroundColor Cyan
    Write-Host "  .\scripts\deploy-board-platform-tonight.ps1 -CommitPush"
    Write-Host ""
    Write-Host "This will:" -ForegroundColor DarkGray
    Write-Host "  1. Push to origin/$Branch  -> Railway sfi-api auto-deploy"
    Write-Host "  2. Same push               -> Vercel production auto-deploy"
    Write-Host "  3. Poll board payload until HTTP 200"
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
}

$staged = @(& git -C $repoRoot diff --cached --name-only 2>&1)
if ($staged.Count -eq 0) {
    Write-Host ""
    Write-Host "Nothing staged to commit. Pushing current $Branch anyway..." -ForegroundColor Yellow
} else {
    $commitMessage = @"
fix: board platform load - bypass Vercel 502 and lighten payload

Skip validation and three-statement work on initial board load, call Railway
directly from the browser for long requests, and extend the board proxy route
timeout so /app/board loads without ROUTER_EXTERNAL_TARGET_ERROR.
"@

    Write-Host ""
    Write-Host "Committing..." -ForegroundColor Yellow
    $msgFile = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($msgFile, $commitMessage, [System.Text.UTF8Encoding]::new($false))
        Invoke-Git @("commit", "-F", $msgFile)
    } finally {
        Remove-Item -LiteralPath $msgFile -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ""
Write-Host "Pushing to origin/$Branch (triggers Railway + Vercel)..." -ForegroundColor Yellow
Invoke-Git @("push", "-u", "origin", $Branch)

$hash = (& git -C $repoRoot rev-parse --short HEAD 2>&1 | Select-Object -Last 1).Trim()
Write-Host ""
Write-Host "Pushed $hash to origin/$Branch" -ForegroundColor Green
Write-Host ""
Write-Host "Waiting for Railway deploy, then verifying board payload..." -ForegroundColor Cyan
Write-Host "(Board payload can take 1-3 minutes on cold start.)" -ForegroundColor DarkGray
Write-Host ""

$deadline = (Get-Date).AddSeconds($PollSeconds)
$attempt = 0
$apiOk = $false

while ((Get-Date) -lt $deadline) {
    $attempt++
    Write-Host "Attempt $attempt - API health..." -ForegroundColor Yellow
    try {
        $health = Invoke-RestMethod -Uri "$($ApiBase.TrimEnd('/'))/health" -Method Get -TimeoutSec 30
        Write-Host "  health.build = $($health.build)" -ForegroundColor DarkGray
    } catch {
        Write-Host "  /health not ready yet: $_" -ForegroundColor DarkYellow
        Start-Sleep -Seconds $PollIntervalSeconds
        continue
    }

    Write-Host "Attempt $attempt - board payload..." -ForegroundColor Yellow
    $result = Test-BoardPayload -BaseUrl $ApiBase -OrgId $OrganizationId -TimeoutSec 240
    if ($result.Ok) {
        $apiOk = $true
        Write-Host ""
        Write-Host "OK: Railway board payload returned HTTP 200 in $($result.Seconds)s" -ForegroundColor Green
        break
    }

    $code = if ($null -ne $result.StatusCode) { $result.StatusCode } else { "error" }
    Write-Host "  Not ready (HTTP $code). Retrying in ${PollIntervalSeconds}s..." -ForegroundColor DarkYellow
    Start-Sleep -Seconds $PollIntervalSeconds
}

Write-Host ""
Write-Host "=== Deploy summary ===" -ForegroundColor Cyan
Write-Host "  Git:      $hash on origin/$Branch"
Write-Host "  Railway:  $ApiBase"
Write-Host "  Vercel:   $FrontendUrl"
Write-Host "  Board UI: $FrontendUrl/app/board"
Write-Host ""

if (-not $apiOk) {
    Write-Host "Railway board payload did not return 200 within ${PollSeconds}s." -ForegroundColor Red
    Write-Host "Check Railway dashboard -> sfi-api -> Deployments -> latest logs." -ForegroundColor Yellow
    exit 1
}

Write-Host "Next (manual smoke test after Vercel finishes ~1-2 min):" -ForegroundColor Yellow
Write-Host "  1. Hard refresh: $FrontendUrl/app/board  (Ctrl+Shift+R)"
Write-Host "  2. Confirm KPI cards load (no 502 / ROUTER_EXTERNAL_TARGET_ERROR)"
Write-Host ""
Write-Host "If browser shows CORS error, add to Railway prod API_CORS_ORIGINS:" -ForegroundColor DarkGray
Write-Host "  $FrontendUrl"
Write-Host ""
Write-Host "Speed + validation cleanup: tackle tomorrow." -ForegroundColor DarkGray
