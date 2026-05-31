# Show which process owns port 8000 and what /health reports.
param(
    [int]$Port = 8000,
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Continue"
Write-Host "=== Port $Port listeners ===" -ForegroundColor Cyan
$conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if (-not $conns) {
    Write-Host "No listener on port $Port" -ForegroundColor Yellow
} else {
    $procIds = $conns | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $procIds) {
        $wmi = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
        Write-Host "PID $procId"
        Write-Host "  $($wmi.CommandLine)"
    }
}

Write-Host ""
Write-Host "=== GET $BaseUrl/health ===" -ForegroundColor Cyan
try {
    $resp = Invoke-WebRequest -Uri "$BaseUrl/health" -UseBasicParsing
    Write-Host "Status: $($resp.StatusCode)"
    Write-Host "X-SFI-Build: $($resp.Headers['X-SFI-Build'])"
    Write-Host "X-SFI-Workforce-Build: $($resp.Headers['X-SFI-Workforce-Build'])"
    Write-Host $resp.Content
} catch {
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== GET $BaseUrl/api/v1/sfi/whoami ===" -ForegroundColor Cyan
try {
    Invoke-RestMethod "$BaseUrl/api/v1/sfi/whoami" | ConvertTo-Json -Depth 5
} catch {
    Write-Host "FAILED (endpoint missing = stale API): $($_.Exception.Message)" -ForegroundColor Red
    try {
        Invoke-RestMethod "$BaseUrl/api/v1/export/whoami" | ConvertTo-Json -Depth 5
    } catch {
        Write-Host "export/whoami also failed." -ForegroundColor Red
    }
}

Write-Host ""
$mainPy = Join-Path $PSScriptRoot "..\app\main.py"
if (Test-Path -LiteralPath $mainPy) {
    $mainContent = Get-Content -LiteralPath $mainPy -Raw
    if ($mainContent -match 'WORKFORCE_BUILD_ID\s*=\s*"([^"]+)"') {
        Write-Host "Expected workforce_build: $($Matches[1])" -ForegroundColor Green
    }
    if ($mainContent -match 'SFI_BUILD_ID\s*=\s*"([^"]+)"') {
        Write-Host "Expected build: $($Matches[1])" -ForegroundColor Green
    }
}
