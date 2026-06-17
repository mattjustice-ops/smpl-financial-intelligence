# Commit and push remaining local WIP on main (excludes secret env files).
#
# Usage:
#   .\scripts\commit-local-wip.ps1
#   .\scripts\commit-local-wip.ps1 -Push

param(
    [switch]$Push
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot
$logFile = Join-Path $repoRoot 'commit-local-wip.log'

function Write-Log {
    param([string]$Message, [string]$Color = 'White')
    Add-Content -LiteralPath $logFile -Value $Message -Encoding UTF8
    Write-Host $Message -ForegroundColor $Color
}

'' | Set-Content -LiteralPath $logFile -Encoding UTF8

Write-Log '=== Commit local WIP on main ===' 'Cyan'

$branch = (git branch --show-current 2>&1 | Select-Object -Last 1).ToString().Trim()
if ($branch -ne 'main') {
    Write-Log "ERROR: Expected branch main, on: $branch" 'Red'
    exit 1
}

git add -A

$secretPaths = @(
    'frontend/.env.local',
    'frontend/.env.staging.local',
    'frontend/.env.neon-production.local',
    'frontend/.env.vercel-production.local',
    'scripts/config/staging.local.env',
    'backend/secrets.env',
    'merge-gl5b-to-main.log',
    'git-push-log.txt',
    'commit-local-wip.log',
    '.wip-restore-backup'
)

foreach ($path in $secretPaths) {
    $cached = git ls-files --cached -- $path 2>$null
    if ($cached) {
        git restore --staged -- $path
        Write-Log "  unstaged secret/log: $path" 'Yellow'
    }
}

$staged = @(git diff --cached --name-only)
if ($staged.Count -eq 0) {
    Write-Log 'Nothing to commit.' 'Yellow'
    exit 0
}

Write-Log ''
Write-Log 'Staged files:' 'Yellow'
$staged | ForEach-Object { Write-Log "  $_" 'White' }

$commitMessage = @'
Add poc ops scripts, merge helpers, and go-live tooling from local WIP.

Includes direct-access POC scripts, Railway env helpers, progress dashboard
tweaks, gitignore for local secrets, and gl-5b merge/stash restore scripts.
'@

$msgFile = [System.IO.Path]::GetTempFileName()
try {
    [System.IO.File]::WriteAllText($msgFile, $commitMessage, [System.Text.UTF8Encoding]::new($false))
    git commit -F $msgFile
}
finally {
    Remove-Item -LiteralPath $msgFile -Force -ErrorAction SilentlyContinue
}

$head = (git log -1 --oneline 2>&1 | Select-Object -Last 1).ToString().Trim()
Write-Log ''
Write-Log "Committed: $head" 'Green'

if ($Push) {
    git push origin main
    Write-Log 'Pushed to origin/main' 'Green'
}
else {
    Write-Log 'Run with -Push or: git push origin main' 'Cyan'
}

Write-Log "Log: $logFile" 'DarkGray'
