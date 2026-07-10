# Mark checklist item(s) done on /app/progress (frontend/lib/go-live-progress.ts).
#
# Usage:
#   .\scripts\update-go-live-progress.ps1 -Item gl-4
#   .\scripts\update-go-live-progress.ps1 -Item gl-4,poc-0 -Focus "gl-7: first paying customer"
#   .\scripts\update-go-live-progress.ps1 -Item gl-4 -CommitPush
#   .\scripts\update-go-live-progress.ps1 -Item gl-4 -Redeploy

param(
    [Parameter(Mandatory = $true)]
    [string]$Item,
    [string]$Focus = "",
    [switch]$CommitPush,
    [switch]$Redeploy,
    [switch]$Undo
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$progressFile = Join-Path $repoRoot "frontend\lib\go-live-progress.ts"

if (-not (Test-Path $progressFile)) {
    Write-Error "Not found: $progressFile"
}

$itemIds = $Item -split "," | ForEach-Object { $_.Trim().ToLower() } | Where-Object { $_ }
if ($itemIds.Count -eq 0) {
    Write-Error "Provide at least one item id, e.g. -Item gl-4"
}

$content = Get-Content -Raw $progressFile
$today = Get-Date -Format "yyyy-MM-dd"

Write-Host ""
Write-Host "=== Update /progress checklist ===" -ForegroundColor Cyan
Write-Host "File: $progressFile" -ForegroundColor DarkGray
Write-Host ""

foreach ($id in $itemIds) {
    $escaped = [regex]::Escape($id)
    $pattern = "(?ms)(id:\s*`"$escaped`",[^\}]*?done:\s*)(true|false)"
    if ($content -notmatch $pattern) {
        Write-Host "ERROR: Item '$id' not found in go-live-progress.ts" -ForegroundColor Red
        exit 1
    }
    $target = if ($Undo) { "false" } else { "true" }
    $content = [regex]::Replace($content, $pattern, "`${1}$target", 1)
    $verb = if ($Undo) { "Unchecked" } else { "Checked off" }
    Write-Host "  $verb : $id" -ForegroundColor Green
}

$content = [regex]::Replace(
    $content,
    'lastUpdated:\s*"[^"]*"',
    "lastUpdated: `"$today`"",
    1
)

if ($Focus) {
    if ($content -notmatch 'currentFocus:\s*\n?\s*"') {
        Write-Error "currentFocus field not found in go-live-progress.ts"
    }
    $content = [regex]::Replace(
        $content,
        '(currentFocus:\s*\n?\s*")([^"]*)(")',
        "`${1}$Focus`${3}",
        1
    )
    Write-Host "  Focus: $Focus" -ForegroundColor Green
}

Set-Content -Path $progressFile -Value $content -NoNewline
Add-Content -Path $progressFile -Value ""

Write-Host ""
Write-Host "Updated lastUpdated -> $today" -ForegroundColor DarkGray
Write-Host "View locally: cd frontend; npm run dev  ->  http://localhost:3002/progress" -ForegroundColor DarkGray
Write-Host ""

if ($CommitPush) {
    Push-Location $repoRoot
    try {
        git add $progressFile
        $msg = "docs: mark go-live progress items done ($($itemIds -join ', '))"
        git commit -m $msg
        git push origin HEAD
        Write-Host "Committed and pushed. Vercel will redeploy if main is connected." -ForegroundColor Green
    } finally {
        Pop-Location
    }
}

if ($Redeploy) {
    $redeployScript = Join-Path $PSScriptRoot "redeploy-vercel-production.ps1"
    if (-not (Test-Path $redeployScript)) {
        Write-Error "Missing $redeployScript"
    }
    & $redeployScript -SkipBuild
}

if (-not $CommitPush -and -not $Redeploy) {
    Write-Host "Next:" -ForegroundColor Cyan
    Write-Host "  .\scripts\update-go-live-progress.ps1 -Item $($itemIds -join ',') -CommitPush -Redeploy"
    Write-Host "  Prod: https://www.smpl-ai.com/progress"
    Write-Host ""
}
