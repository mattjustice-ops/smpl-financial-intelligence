# Register Windows Task Scheduler jobs for SMPL Ops (Phase 2).
#
# Creates two daily tasks (6:00 AM local):
#   - SMPL Ops storage snapshot (local Neon, no API key)
#   - SMPL Ops alerts smoke (Railway + Vercel health)
#
# Usage (repo root, run as your user):
#   .\scripts\setup-ops-scheduled-tasks.ps1
#   .\scripts\setup-ops-scheduled-tasks.ps1 -WhatIf
#   .\scripts\setup-ops-scheduled-tasks.ps1 -Unregister

param(
    [switch]$WhatIf,
    [switch]$Unregister,
    [string]$Time = "06:00"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$storageScript = Join-Path $repoRoot "scripts\collect-ops-storage-snapshot.ps1"
$smokeScript = Join-Path $repoRoot "scripts\smoke-test-ops-alerts.ps1"

$tasks = @(
    @{
        Name        = "SMPL Ops Storage Snapshot"
        Description = "Daily Neon storage_snapshot for SMPL Ops dashboard"
        Arguments   = "-NoProfile -ExecutionPolicy Bypass -File `"$storageScript`" -Local"
    },
    @{
        Name        = "SMPL Ops Alerts Smoke"
        Description = "Daily Railway/Vercel health smoke for SMPL Ops"
        Arguments   = "-NoProfile -ExecutionPolicy Bypass -File `"$smokeScript`" -RecordBackendCheck"
    }
)

if ($Unregister) {
    foreach ($task in $tasks) {
        $existing = Get-ScheduledTask -TaskName $task.Name -ErrorAction SilentlyContinue
        if ($existing) {
            Unregister-ScheduledTask -TaskName $task.Name -Confirm:$false
            Write-Host "Removed: $($task.Name)" -ForegroundColor Yellow
        }
    }
    exit 0
}

if (-not (Test-Path $storageScript)) { throw "Missing $storageScript" }
if (-not (Test-Path $smokeScript)) { throw "Missing $smokeScript" }

$actionTemplate = {
    param($Args)
    New-ScheduledTaskAction -Execute "powershell.exe" -Argument $Args -WorkingDirectory $repoRoot
}

$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Write-Host ""
Write-Host "=== SMPL Ops scheduled tasks ===" -ForegroundColor Cyan
Write-Host "Repo:  $repoRoot" -ForegroundColor DarkGray
Write-Host "Daily: $Time" -ForegroundColor DarkGray
Write-Host ""

foreach ($task in $tasks) {
    $action = & $actionTemplate $task.Arguments
    if ($WhatIf) {
        Write-Host "Would register: $($task.Name)" -ForegroundColor Yellow
        continue
    }
    Register-ScheduledTask `
        -TaskName $task.Name `
        -Description $task.Description `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Force | Out-Null
    Write-Host "Registered: $($task.Name)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Verify in Task Scheduler or run manually:" -ForegroundColor Cyan
Write-Host "  .\scripts\collect-ops-storage-snapshot.ps1 -Local" -ForegroundColor White
Write-Host "  .\scripts\smoke-test-ops-alerts.ps1 -RecordBackendCheck" -ForegroundColor White
Write-Host ""
