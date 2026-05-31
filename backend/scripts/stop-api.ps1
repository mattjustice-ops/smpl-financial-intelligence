# Force-stop any API process on port 8000 (use when restart-api.ps1 cannot free the port).
param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot\..

Write-Host "Stopping API on port $Port..." -ForegroundColor Cyan
& "$PSScriptRoot\kill-port.ps1" -Port $Port
$code = $LASTEXITCODE
if ($code -eq 0) {
    Write-Host "Done. Port $Port is free." -ForegroundColor Green
    exit 0
}
if ($code -eq 2) {
    Write-Host ""
    Write-Host "Port $Port has a stale/zombie listener. Use port 8001 instead:" -ForegroundColor Yellow
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\restart-api.ps1 -Port 8001"
    exit 2
}

Write-Host ""
Write-Host "Port $Port is still busy. Run diagnostics:" -ForegroundColor Yellow
Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\diagnose-port.ps1 -Port $Port"
exit 1
