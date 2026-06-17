# Safely restore pre-gl5b-merge stash when .gitignore / merge script block git stash pop.
#
# Usage:
#   .\scripts\restore-stashed-wip.ps1
#   .\scripts\restore-stashed-wip.ps1 -StashRef 'stash@{0}'

param(
    [string]$StashRef = 'stash@{0}'
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

$backupDir = Join-Path $repoRoot '.wip-restore-backup'
$blockingPaths = @(
    '.gitignore',
    'scripts/merge-gl5b-to-main.ps1'
)

Write-Host ''
Write-Host '=== Restore stashed WIP ===' -ForegroundColor Cyan
Write-Host ''

$stashList = git stash list 2>&1
if (-not $stashList) {
    Write-Host 'No stash entries found.' -ForegroundColor Yellow
    exit 0
}

Write-Host 'Stash list:' -ForegroundColor DarkGray
$stashList | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
Write-Host ''

if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir | Out-Null
}

foreach ($rel in $blockingPaths) {
    $full = Join-Path $repoRoot $rel
    $backup = Join-Path $backupDir ($rel -replace '[/\\]', '__')
    if (Test-Path $full) {
        Copy-Item -LiteralPath $full -Destination $backup -Force
        Write-Host "Backed up: $rel" -ForegroundColor DarkGray
    }
    if ($rel -eq '.gitignore') {
        git restore -- $rel 2>$null
        if ($LASTEXITCODE -ne 0) {
            git checkout HEAD -- $rel 2>$null
        }
    }
    else {
        if (Test-Path $full) {
            Remove-Item -LiteralPath $full -Force
        }
    }
}

Write-Host ''
Write-Host "Applying $StashRef ..." -ForegroundColor Yellow
git stash pop $StashRef
$popExit = $LASTEXITCODE

foreach ($rel in $blockingPaths) {
    $full = Join-Path $repoRoot $rel
    $backup = Join-Path $backupDir ($rel -replace '[/\\]', '__')
    if (Test-Path $backup) {
        Copy-Item -LiteralPath $backup -Destination $full -Force
        Write-Host "Restored preferred version: $rel" -ForegroundColor Green
    }
}

Write-Host ''
if ($popExit -eq 0) {
    Write-Host 'OK: stash applied.' -ForegroundColor Green
}
else {
    Write-Host "WARN: stash pop returned exit $popExit - check git status; stash may be kept." -ForegroundColor Yellow
}

Write-Host ''
Write-Host 'Status:' -ForegroundColor Yellow
git status -sb

Write-Host ''
Write-Host 'Next: review changes, then commit WIP on main when ready.' -ForegroundColor Cyan
Write-Host "Backup dir (safe to delete after review): $backupDir" -ForegroundColor DarkGray
Write-Host ''
