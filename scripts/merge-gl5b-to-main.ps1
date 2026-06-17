# Merge validated gl-5b-sandbox into main and push (promotes code to production).
#
# Usage:
#   .\scripts\merge-gl5b-to-main.ps1
#   .\scripts\merge-gl5b-to-main.ps1 -Stash    # stash local WIP, merge, restore WIP after

param(
    [switch]$Stash
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

$sourceBranch = "gl-5b-sandbox"
$targetBranch = "main"
$logFile = Join-Path $repoRoot "merge-gl5b-to-main.log"
$stashLabel = "pre-gl5b-merge-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

# Untracked local files that must never block a merge (secrets, logs, this script).
$localOnlyPatterns = @(
    "^frontend/\.env\.staging\.local$",
    "^frontend/\.env\.local$",
    "^merge-gl5b-to-main\.log$",
    "^git-push-log\.txt$",
    "^scripts/merge-gl5b-to-main\.ps1$"
)

function Write-Log {
    param([string]$Message, [string]$Color = "White")
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $Message"
    Add-Content -LiteralPath $logFile -Value $line -Encoding UTF8
    Write-Host $Message -ForegroundColor $Color
}

function Get-LastGitLine {
    param($Output)
    $lines = @($Output | ForEach-Object { "$_" } | Where-Object { $_.Trim() })
    if ($lines.Count -eq 0) { return "" }
    return $lines[-1].Trim()
}

function Get-PorcelainPath {
    param([string]$Line)
    $rest = ($Line -replace "^.. ", "").Trim()
    if ($rest -match " -> ") {
        return ($rest -split " -> ")[-1].Trim()
    }
    return $rest
}

function Test-LocalOnlyPath {
    param([string]$Path)
    foreach ($pattern in $localOnlyPatterns) {
        if ($Path -match $pattern) { return $true }
    }
    return $false
}

function Invoke-Git {
    param([string[]]$GitArgs)
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & git @GitArgs 2>&1 | ForEach-Object { "$_" }
    }
    finally {
        $ErrorActionPreference = $prevEap
    }
    if ($output) {
        $output | ForEach-Object { Add-Content -LiteralPath $logFile -Value $_ -Encoding UTF8 }
    }
    if ($LASTEXITCODE -ne 0) {
        throw "git $($GitArgs -join ' ') failed (exit $LASTEXITCODE)`n$($output -join "`n")"
    }
    return $output
}

"" | Set-Content -LiteralPath $logFile -Encoding UTF8

Write-Log "=== Merge $sourceBranch -> $targetBranch ===" "Cyan"

if (-not (Test-Path ".git")) {
    Write-Log "ERROR: Not a git repository." "Red"
    exit 1
}

$status = Invoke-Git @("status", "-sb")
Write-Log ($status -join " | ") "DarkGray"

$allDirty = @(Invoke-Git @("status", "--porcelain") | Where-Object { "$_".Trim() })
$ignoredLocal = @()
$blockingDirty = @()
foreach ($line in $allDirty) {
    $path = Get-PorcelainPath "$line"
    if (Test-LocalOnlyPath $path) {
        $ignoredLocal += $line
    }
    else {
        $blockingDirty += $line
    }
}

if ($ignoredLocal.Count -gt 0) {
    Write-Log "Ignoring local-only files (secrets/logs/tooling):" "DarkGray"
    $ignoredLocal | ForEach-Object { Write-Log "  $_" "DarkGray" }
}

$didStash = $false
if ($blockingDirty.Count -gt 0) {
    if (-not $Stash) {
        Write-Log "ERROR: Working tree has uncommitted changes." "Red"
        Write-Log "Commit them, or re-run with -Stash to save WIP temporarily:" "Yellow"
        Write-Log "  .\scripts\merge-gl5b-to-main.ps1 -Stash" "White"
        $blockingDirty | ForEach-Object { Write-Log "  $_" "Yellow" }
        exit 1
    }

    Write-Log "Stashing local WIP ($stashLabel) ..." "Yellow"
    Invoke-Git @("stash", "push", "-u", "-m", $stashLabel)
    $didStash = $true
    Write-Log "Stash saved. Nothing lost." "Green"
}

Invoke-Git @("fetch", "origin")

$remoteSource = Get-LastGitLine (Invoke-Git @("rev-parse", "--verify", "origin/$sourceBranch"))
if (-not $remoteSource) {
    Write-Log "ERROR: origin/$sourceBranch not found. Push gl-5b-sandbox first." "Red"
    exit 1
}

$current = Get-LastGitLine (Invoke-Git @("branch", "--show-current"))
if ($current -ne $targetBranch) {
    Write-Log "Checking out $targetBranch ..." "Yellow"
    Invoke-Git @("checkout", $targetBranch)
}

Invoke-Git @("pull", "origin", $targetBranch)

Write-Log "Merging origin/$sourceBranch ..." "Yellow"
try {
    Invoke-Git @("merge", "origin/$sourceBranch", "-m", "Merge gl-5b-sandbox: validated sandbox Preview into main")
}
catch {
    Write-Log "MERGE FAILED - resolve conflicts, then:" "Red"
    Write-Log "  git add -A" "White"
    Write-Log "  git commit" "White"
    Write-Log "  git push origin main" "White"
    if ($didStash) {
        Write-Log "Your WIP is in: git stash list  (look for $stashLabel)" "Yellow"
    }
    Write-Log $_.Exception.Message "Red"
    exit 1
}

Write-Log "Pushing origin/$targetBranch ..." "Yellow"
Invoke-Git @("push", "origin", $targetBranch)

$head = Get-LastGitLine (Invoke-Git @("log", "-1", "--oneline"))
Write-Log ""
Write-Log "OK: $head" "Green"
Write-Log "Production deploy should start on Vercel + Railway prod." "Green"
Write-Log "Check: https://smpl-financial-intelligence.vercel.app/progress" "Cyan"

if ($didStash) {
    Write-Log ""
    Write-Log "Restoring stashed WIP ..." "Yellow"
    try {
        Invoke-Git @("stash", "pop")
        Write-Log "Stash restored. Review with: git status -sb" "Green"
        Write-Log "Commit remaining WIP on main when ready." "DarkGray"
    }
    catch {
        Write-Log "Stash pop had conflicts. Your work is safe in the stash:" "Yellow"
        Write-Log "  git stash list" "White"
        Write-Log "  git stash show -p stash@{0}" "White"
    }
}

Write-Log "Log: $logFile" "DarkGray"
