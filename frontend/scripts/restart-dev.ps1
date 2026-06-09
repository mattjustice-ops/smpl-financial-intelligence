param(
    [int]$Port = 3002
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

Write-Host "Stopping anything on port $Port (node/next only)..." -ForegroundColor Cyan
$prevErrorAction = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& "$root\scripts\kill-port.ps1" -Port $Port
$killExitCode = if ($null -ne $LASTEXITCODE) { $LASTEXITCODE } else { 0 }
$ErrorActionPreference = $prevErrorAction
if ($killExitCode -ne 0) {
    Write-Host "Could not free port $Port. Close other terminals using Next.js or reboot the stale process." -ForegroundColor Red
    exit 1
}

# Stale .next output (e.g. after npm run build) breaks dev: missing main-app.js and CSS.
$nextDir = Join-Path $root ".next"
if (Test-Path $nextDir) {
    Write-Host "Removing stale .next cache..." -ForegroundColor Cyan
    Remove-Item -Recurse -Force $nextDir
}

Write-Host "Starting Next.js on http://127.0.0.1:$Port ..." -ForegroundColor Cyan
npm run dev
