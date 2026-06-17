# Finish restoring tracked files still in stash@{0}, then drop stash.
# Untracked script files already on disk are kept (stash could not overwrite them).
#
# Usage:
#   .\scripts\finish-stash-restore.ps1
#   .\scripts\finish-stash-restore.ps1 -DropStash

param(
    [string]$StashRef = 'stash@{0}',
    [switch]$DropStash
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

$skipPaths = @(
    '.gitignore'
)

Write-Host ''
Write-Host '=== Finish stash restore ===' -ForegroundColor Cyan
Write-Host ''

$stashList = git stash list 2>&1
if (-not $stashList) {
    Write-Host 'No stash entries.' -ForegroundColor Yellow
    exit 0
}

Write-Host 'Stash:' -ForegroundColor DarkGray
$stashList | Select-Object -First 3 | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
Write-Host ''

$names = @(git stash show --name-only $StashRef 2>&1 | Where-Object { "$_".Trim() })
if ($names.Count -eq 0) {
    Write-Host "No tracked files in $StashRef" -ForegroundColor Yellow
}
else {
    Write-Host "Applying tracked files from $StashRef ..." -ForegroundColor Yellow
    foreach ($rel in $names) {
        if ($skipPaths -contains $rel) {
            Write-Host "  skip: $rel (keep current)" -ForegroundColor DarkGray
            continue
        }
        git checkout $StashRef -- $rel
        Write-Host "  + $rel" -ForegroundColor Green
    }
}

Write-Host ''
Write-Host 'Untracked scripts already on disk (from earlier partial restore):' -ForegroundColor DarkGray
@(
    'backend/scripts/verify_warehouse_org.py',
    'scripts/config/staging.env.example',
    'scripts/diagnose-preview-health.ps1',
    'scripts/run-direct-access-poc.ps1',
    'scripts/set-prod-active-org.ps1',
    'scripts/smoke-test-direct-access-poc.ps1',
    'scripts/test-database-url.ps1'
) | ForEach-Object {
    if (Test-Path (Join-Path $repoRoot $_)) {
        Write-Host "  ok: $_" -ForegroundColor DarkGray
    }
    else {
        Write-Host "  missing: $_" -ForegroundColor Yellow
    }
}

Write-Host ''
Write-Host 'Status:' -ForegroundColor Yellow
git status -sb

if ($DropStash) {
    Write-Host ''
    Write-Host "Dropping $StashRef ..." -ForegroundColor Yellow
    git stash drop $StashRef
    Write-Host 'Stash dropped.' -ForegroundColor Green
}
else {
    Write-Host ''
    Write-Host "When status looks right, drop the stash:" -ForegroundColor Cyan
    Write-Host '  git stash drop stash@{0}' -ForegroundColor White
    Write-Host 'Or re-run: .\scripts\finish-stash-restore.ps1 -DropStash' -ForegroundColor White
}

Write-Host ''
