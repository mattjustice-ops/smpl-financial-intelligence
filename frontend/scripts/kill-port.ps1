param(
    [int]$Port = 3002
)

$ErrorActionPreference = "SilentlyContinue"
$pids = Get-NetTCPConnection -LocalPort $Port -State Listen |
    Select-Object -ExpandProperty OwningProcess -Unique |
    Where-Object { $_ -gt 0 }

if (-not $pids) {
    Write-Host "No process listening on port $Port."
    exit 0
}

foreach ($procId in $pids) {
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if (-not $proc) {
        continue
    }
    $isNode = $proc.ProcessName -match '^node' -or ($proc.Path -and $proc.Path -match 'node\.exe')
    if (-not $isNode) {
        Write-Host "Port $Port is used by PID $procId ($($proc.ProcessName)) - not node; skip (close manually if needed)." -ForegroundColor Yellow
        continue
    }
    Write-Host "Stopping PID $procId ($($proc.ProcessName)) on port $Port..."
    Stop-Process -Id $procId -Force
}

Start-Sleep -Milliseconds 500
$still = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($still) {
    Write-Host "Port $Port may still be in use. Close other terminals or restart Windows Terminal." -ForegroundColor Yellow
    exit 1
}

Write-Host "Port $Port is free." -ForegroundColor Green
