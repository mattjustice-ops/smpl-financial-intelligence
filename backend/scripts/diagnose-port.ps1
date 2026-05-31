param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Continue"

Write-Host "=== Port $Port diagnostics ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "--- netstat (LISTENING on :$Port) ---" -ForegroundColor Yellow
netstat -ano -p tcp | Select-String ":$Port\s" | ForEach-Object { Write-Host $_.Line }

Write-Host ""
Write-Host "--- Get-NetTCPConnection (Listen) ---" -ForegroundColor Yellow
Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Format-Table LocalAddress, LocalPort, State, OwningProcess -AutoSize

$pids = @(
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
)
if (-not $pids -or $pids.Count -eq 0) {
    $lines = netstat -ano -p tcp 2>$null | Select-String ":$Port\s"
    foreach ($line in $lines) {
        if ($line -match "LISTENING\s+(\d+)\s*$") {
            $pids += [int]$Matches[1]
        }
    }
    $pids = @($pids | Select-Object -Unique)
}

Write-Host ""
Write-Host "--- Process details ---" -ForegroundColor Yellow
foreach ($procId in ($pids | Select-Object -Unique)) {
    Write-Host "PID $procId"
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "  Name: $($proc.ProcessName)"
        Write-Host "  Path: $($proc.Path)"
        Write-Host "  StartTime: $($proc.StartTime)"
    } else {
        Write-Host "  Process NOT FOUND (zombie/stale TCP entry)" -ForegroundColor Red
    }
    $wmi = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
    if ($wmi) {
        Write-Host "  CommandLine: $($wmi.CommandLine)"
    }
}

Write-Host ""
Write-Host "--- All python.exe processes ---" -ForegroundColor Yellow
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "uvicorn|8000|8001" } |
    ForEach-Object {
        Write-Host "PID $($_.ProcessId): $($_.CommandLine)"
    }

Write-Host ""
Write-Host "--- Windows excluded port ranges (Hyper-V/WSL can block ports) ---" -ForegroundColor Yellow
netsh interface ipv4 show excludedportrange protocol=tcp 2>$null

Write-Host ""
Write-Host "--- Recommendations ---" -ForegroundColor Green
$alive = @()
foreach ($procId in ($pids | Select-Object -Unique)) {
    if (Get-Process -Id $procId -ErrorAction SilentlyContinue) { $alive += $procId }
}
if ($alive.Count -gt 0) {
    Write-Host "1. Run PowerShell as Administrator, then:"
    foreach ($procId in $alive) {
        Write-Host "   taskkill /F /T /PID $procId"
    }
} elseif ($pids.Count -gt 0) {
    Write-Host "1. Port $Port shows PID(s) $($pids -join ', ') but process(es) are gone (Windows stale socket)."
    Write-Host "   Options:"
    Write-Host "   a) Reboot Windows (fastest fix for stale listeners)"
    Write-Host "   b) Start API on alternate port 8001:"
    Write-Host "      powershell -ExecutionPolicy Bypass -File .\restart-api.ps1 -Port 8001"
} else {
    Write-Host "Port $Port appears free from netstat."
}
