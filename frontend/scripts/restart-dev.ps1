param(
    [int]$Port = 3002
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

Write-Host "Stopping anything on port $Port (node/next only)..." -ForegroundColor Cyan
& "$root\scripts\kill-port.ps1" -Port $Port
if ($LASTEXITCODE -ne 0) {
    Write-Host "Could not free port $Port. Close other terminals using Next.js or reboot the stale process." -ForegroundColor Red
    exit 1
}

Write-Host "Starting Next.js on http://127.0.0.1:$Port ..." -ForegroundColor Cyan
npm run dev
