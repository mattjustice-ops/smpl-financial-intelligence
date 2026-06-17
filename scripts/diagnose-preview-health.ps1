# Diagnose Preview /health fetch failed (gl-5b).
#
# Usage:
#   .\scripts\diagnose-preview-health.ps1

param(
    [string]$StagingApi = "",
    [string]$Scope = "smplai",
    [string]$Project = "smpl-financial-intelligence"
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path $PSScriptRoot -Parent
$frontendDir = Join-Path $repoRoot "frontend"

if (-not $StagingApi) {
    $stagingFile = Join-Path $repoRoot "frontend\.env.staging.local"
    if (Test-Path $stagingFile) {
        foreach ($line in Get-Content $stagingFile) {
            if ($line -match "^STAGING_API_URL=(.+)$") {
                $StagingApi = $Matches[1].Trim()
                break
            }
        }
    }
}
$StagingApi = $StagingApi.Trim().TrimEnd("/")

Write-Host ""
Write-Host "=== Preview /health diagnosis ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "1) Railway staging (from your machine):" -ForegroundColor Yellow
if ($StagingApi) {
    try {
        $h = Invoke-RestMethod -Uri "$StagingApi/health" -TimeoutSec 30
        Write-Host "   OK: $($h.status) build=$($h.build)" -ForegroundColor Green
    }
    catch {
        Write-Host "   FAIL: $_" -ForegroundColor Red
    }
}
else {
    Write-Host "   SKIP: no STAGING_API_URL in .env.staging.local" -ForegroundColor DarkYellow
}
Write-Host ""

Write-Host "2) Vercel Preview env pull (checks SFI_BACKEND_URL exists for Preview):" -ForegroundColor Yellow
$envFile = Join-Path $env:TEMP "sfi-preview-env-check.env"
if (Test-Path $envFile) { Remove-Item $envFile -Force }

Push-Location $frontendDir
try {
    $npxBase = @("--yes", "vercel@latest")
    if ($env:VERCEL_TOKEN) { $npxBase += @("--token", $env:VERCEL_TOKEN) }
    $pullArgs = $npxBase + @(
        "env", "pull", $envFile,
        "--environment", "preview",
        "--yes",
        "--scope", $Scope,
        "--project", $Project
    )
    $pullOut = & npx @pullArgs 2>&1 | ForEach-Object { "$_" }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   vercel env pull failed. Set vars manually in dashboard:" -ForegroundColor Red
        Write-Host ($pullOut -join "`n") -ForegroundColor DarkGray
    }
    elseif (Test-Path $envFile) {
        $sfi = Get-Content $envFile | Where-Object { $_ -match "^SFI_BACKEND_URL=" } | Select-Object -First 1
        $pub = Get-Content $envFile | Where-Object { $_ -match "^NEXT_PUBLIC_API_URL=" } | Select-Object -First 1
        if ($sfi -match '^SFI_BACKEND_URL=(.+)$' -and $Matches[1].Trim() -and $Matches[1] -notmatch '^\s*$') {
            $hostOnly = ($Matches[1] -replace '^https?://', '' -split '/')[0]
            Write-Host "   OK: SFI_BACKEND_URL host = $hostOnly" -ForegroundColor Green
        }
        else {
            Write-Host "   MISSING or EMPTY: SFI_BACKEND_URL on Preview" -ForegroundColor Red
            Write-Host "   Run: .\scripts\set-vercel-staging-env.ps1 -BackendUrl `"$StagingApi`"" -ForegroundColor White
        }
        if ($pub -match '^NEXT_PUBLIC_API_URL=(.+)$' -and $Matches[1].Trim()) {
            Write-Host "   OK: NEXT_PUBLIC_API_URL set" -ForegroundColor Green
        }
        else {
            Write-Host "   WARN: NEXT_PUBLIC_API_URL missing on Preview" -ForegroundColor Yellow
        }
    }
}
finally {
    Pop-Location
    if (Test-Path $envFile) { Remove-Item $envFile -Force -ErrorAction SilentlyContinue }
}
Write-Host ""

Write-Host "3) Most common cause of fetch failed on Preview /health" -ForegroundColor Yellow
Write-Host "   Preview deployment has no runtime SFI_BACKEND_URL (falls back to localhost)." -ForegroundColor White
Write-Host ""
Write-Host "   Fix:" -ForegroundColor Yellow
Write-Host "   a) Vercel -> Settings -> Environment Variables" -ForegroundColor White
Write-Host "      SFI_BACKEND_URL = $StagingApi" -ForegroundColor White
Write-Host "      Environments: Preview CHECKED (not Production only)" -ForegroundColor White
Write-Host "      Git branch: All Preview branches (not scoped to main only)" -ForegroundColor White
Write-Host "   b) Redeploy gl-5b-sandbox after saving" -ForegroundColor White
Write-Host "   c) Push latest health route fix, then redeploy again" -ForegroundColor White
Write-Host ""
Write-Host "   After deploy, /health should show either status ok OR configured_host in error JSON." -ForegroundColor DarkGray
Write-Host ""
