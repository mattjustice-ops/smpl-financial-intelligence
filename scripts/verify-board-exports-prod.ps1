# Verify board export wiring on production (Railway API + Vercel frontend).
#
# Usage (repo root):
#   .\scripts\verify-board-exports-prod.ps1
#   .\scripts\verify-board-exports-prod.ps1 -CommitPush

param(
    [switch]$CommitPush,
    [string]$ApiBase = "https://sfi-api-production.up.railway.app",
    [string]$FrontendUrl = "https://www.smpl-ai.com",
    [string]$OrganizationId = "8571e520-0687-4516-bdee-379f37c58c1f"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$apiRoot = $ApiBase.TrimEnd("/")

function Build-ExportQueryUrl {
    param(
        [string]$Path,
        [hashtable]$Query
    )
    $pairs = foreach ($key in $Query.Keys) {
        "{0}={1}" -f [uri]::EscapeDataString($key), [uri]::EscapeDataString([string]$Query[$key])
    }
    return "{0}{1}?{2}" -f $apiRoot, $Path, ($pairs -join '&')
}

Write-Host ""
Write-Host "=== Board export production verification ===" -ForegroundColor Cyan
Write-Host ""

Push-Location $repoRoot
try {
    Write-Host "1. Git sync" -ForegroundColor Yellow
    git fetch origin 2>&1 | Out-Null
    $local = (git rev-parse --short HEAD).Trim()
    $remote = (git rev-parse --short origin/main).Trim()
    Write-Host "   local main:  $local"
    Write-Host "   origin/main: $remote"
    if ($local -ne $remote) {
        Write-Host "   WARNING: local main differs from origin/main - push before testing prod." -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "2. Railway API health" -ForegroundColor Yellow
    $health = Invoke-RestMethod -Uri "$apiRoot/health" -TimeoutSec 30
    Write-Host "   status=$($health.status) build=$($health.build)" -ForegroundColor Green

    Write-Host ""
    Write-Host "3. Export smoke ping" -ForegroundColor Yellow
    $pingUrl = Build-ExportQueryUrl -Path "/api/v1/export/mda-deck-smoke" -Query @{
        organization_id = $OrganizationId
        as_of_period    = "2026-06"
        level           = "ping"
    }
    $ping = Invoke-RestMethod -Uri $pingUrl -TimeoutSec 30
    Write-Host "   org=$($ping.organization_name) period=$($ping.period)" -ForegroundColor Green

    Write-Host ""
    Write-Host "4. Async export job routes (POST required; HEAD returns 405)" -ForegroundColor Yellow
    $jobUrl = Build-ExportQueryUrl -Path "/api/v1/export/jobs/mda-package" -Query @{
        organization_id       = $OrganizationId
        scenario              = "Combined"
        start_period          = "2026-01"
        end_period            = "2026-12"
        as_of_period          = "2026-06"
        include_ai_commentary = "false"
        block_on_failure      = "false"
    }
    $jobProbe = curl.exe -s -o NUL -w "%{http_code}" -X POST $jobUrl
    if ($jobProbe -eq "200") {
        Write-Host "   POST /jobs/mda-package -> 200 (async export live)" -ForegroundColor Green
    } else {
        Write-Host "   POST /jobs/mda-package -> $jobProbe (deploy latest backend if not 200)" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "5. Vercel board-config + hydrate version" -ForegroundColor Yellow
    $cfg = Invoke-RestMethod -Uri "$FrontendUrl/api/smpl/board-config" -TimeoutSec 30
    Write-Host "   longRunningApiBase=$($cfg.longRunningApiBase)"
    $boardHtml = (Invoke-WebRequest -Uri "$FrontendUrl/board/index.html" -UseBasicParsing).Content
    if ($boardHtml -match "board-hydrate\.js\?v=(\d+)") {
        Write-Host "   board-hydrate.js?v=$($Matches[1])" -ForegroundColor Green
    } else {
        Write-Host "   board-hydrate version not found in HTML" -ForegroundColor Red
    }
    $hydrateJs = Get-Content -Raw (Join-Path $repoRoot "frontend/public/shared/board-hydrate.js")
    if ($hydrateJs -match "pollAndDownloadExport") {
        Write-Host "   async export polling: present in board-hydrate.js" -ForegroundColor Green
    } else {
        Write-Host "   async export polling: missing from board-hydrate.js" -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "6. Frontend verify (local, same as Vercel prebuild)" -ForegroundColor Yellow
    Push-Location (Join-Path $repoRoot "frontend")
    npm run verify:board 2>&1 | ForEach-Object { Write-Host "   $_" }
    Pop-Location

    if ($CommitPush) {
        Write-Host ""
        Write-Host "7. Commit + push to origin/main (Railway + Vercel auto-deploy)" -ForegroundColor Yellow
        $files = @(
            "backend/app/api/export_routes.py",
            "backend/app/services/reporting/export/export_jobs.py",
            "backend/tests/test_export_jobs.py",
            "frontend/public/shared/board-hydrate.js",
            "frontend/canonical/shared/board-hydrate.js",
            "frontend/public/board/index.html",
            "frontend/canonical/board/index.html",
            "frontend/scripts/verify-board-platform.mjs",
            "scripts/verify-board-exports-prod.ps1"
        )
        foreach ($f in $files) {
            if (Test-Path (Join-Path $repoRoot $f)) {
                git add $f
            }
        }
        $staged = git diff --cached --name-only
        if ($staged) {
            $msg = @"
fix: async board exports to survive Railway 5-minute gateway timeout

Start MDA deck and package via POST /export/jobs/*; board polls until complete
then downloads. Avoids 502 on long Claude and warehouse builds.
"@
            $msgFile = [System.IO.Path]::GetTempFileName()
            try {
                [System.IO.File]::WriteAllText($msgFile, $msg, [System.Text.UTF8Encoding]::new($false))
                git commit -F $msgFile
            } finally {
                Remove-Item -LiteralPath $msgFile -Force -ErrorAction SilentlyContinue
            }
        } else {
            Write-Host "   Nothing staged to commit - pushing current main if needed." -ForegroundColor DarkGray
        }
        git push origin main
        Write-Host "   Pushed. Wait 2-5 min for Railway + Vercel, then hard refresh /app/board." -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "=== Manual test on /app/board ===" -ForegroundColor Cyan
    Write-Host "  1. Hard refresh: $FrontendUrl/app/board  (Ctrl+Shift+R)"
    Write-Host '  2. Sign in - footer must show Live, not Demo/no-org'
    Write-Host '  3. MDA Deck / Variance Commentary - alert says export started; wait 3-10 min'
    Write-Host "  4. Download should start automatically when job completes"
    Write-Host ""
    Write-Host "If POST /jobs/* returns 404, Railway has not finished deploying latest backend." -ForegroundColor DarkGray
    Write-Host ""
} finally {
    Pop-Location
}
