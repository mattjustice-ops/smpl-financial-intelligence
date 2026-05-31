# Kill port 8000, clear cache, start API in this window.
param(
    [switch]$Reload,
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Checking what is currently on port $Port..." -ForegroundColor Cyan
& "$PSScriptRoot\scripts\check-running-api.ps1" -Port $Port -BaseUrl "http://127.0.0.1:$Port"

& "$PSScriptRoot\scripts\kill-port.ps1" -Port $Port
$killCode = $LASTEXITCODE
if ($killCode -eq 2) {
    if ($Port -eq 8000) {
        Write-Host ""
        Write-Host "Port 8000 has a stale listener. Retrying on port 8001..." -ForegroundColor Yellow
        $retryParams = @{}
        if ($Reload) { $retryParams["Reload"] = $true }
        & "$PSScriptRoot\restart-api.ps1" -Port 8001 @retryParams
        exit $LASTEXITCODE
    }
    Write-Host ""
    Write-Host "ERROR: Port $Port has a stale listener. Reboot Windows or pick another port." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 2
}
if ($killCode -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Could not free port $Port." -ForegroundColor Red
    Write-Host "Run: powershell -ExecutionPolicy Bypass -File .\scripts\diagnose-port.ps1 -Port $Port" -ForegroundColor Yellow
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "Clearing Python bytecode cache..."
Get-ChildItem -LiteralPath $PSScriptRoot\app -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Starting fresh API process on port $Port..." -ForegroundColor Cyan
if ($Reload) {
    & "$PSScriptRoot\start-api.ps1" -Reload -Port $Port
} else {
    & "$PSScriptRoot\start-api.ps1" -Port $Port
}
