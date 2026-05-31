param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Continue"

function Get-ListenPids {
    param([int]$TargetPort)
    $pids = @(
        Get-NetTCPConnection -LocalPort $TargetPort -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    )
    if ($pids.Count -gt 0) {
        return @($pids | Select-Object -Unique)
    }
    $fromNetstat = @()
    $lines = netstat -ano -p tcp 2>$null | Select-String ":$TargetPort\s"
    foreach ($line in $lines) {
        if ($line -notmatch "LISTENING\s+(\d+)\s*$") { continue }
        $fromNetstat += [int]$Matches[1]
    }
    return @($fromNetstat | Select-Object -Unique)
}

function Test-ProcessAlive {
    param([int]$ProcessId)
    if ($ProcessId -le 4) { return $false }
    return [bool](Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)
}

function Stop-PidTree {
    param([int]$ProcessId)
    if ($ProcessId -le 4) { return }
    $wmi = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
    $cmd = if ($wmi) { $wmi.CommandLine } else { "(unknown / already exited)" }
    Write-Host "  Killing PID $ProcessId : $cmd"
    cmd /c "taskkill /F /T /PID $ProcessId" 2>$null | Out-Null
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

function Stop-UvicornProcesses {
    param([int]$TargetPort)
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -and
            ($_.CommandLine -match "uvicorn") -and
            (
                $_.CommandLine -match "--port\s+$TargetPort" -or
                $_.CommandLine -match "port\s+$TargetPort" -or
                $_.CommandLine -match ":$TargetPort"
            )
        } |
        ForEach-Object { Stop-PidTree -ProcessId $_.ProcessId }
}

Write-Host "Listeners on port $Port..."
for ($attempt = 1; $attempt -le 5; $attempt++) {
    $procIds = Get-ListenPids -TargetPort $Port
    foreach ($procId in $procIds) {
        if (Test-ProcessAlive -ProcessId $procId) {
            Stop-PidTree -ProcessId $procId
        } else {
            Write-Host "  Stale listener PID $procId (process already gone)" -ForegroundColor Yellow
        }
    }
    Stop-UvicornProcesses -TargetPort $Port
    Start-Sleep -Seconds 2

    $left = Get-ListenPids -TargetPort $Port
    if (-not $left -or $left.Count -eq 0) {
        Write-Host "Port $Port is free." -ForegroundColor Green
        exit 0
    }

    $aliveLeft = @($left | Where-Object { Test-ProcessAlive -ProcessId $_ })
    if ($aliveLeft.Count -eq 0) {
        Write-Host ""
        Write-Host "Port $Port is held by stale TCP entry(ies): $($left -join ', ')" -ForegroundColor Red
        Write-Host "The process is gone but Windows has not released the port yet." -ForegroundColor Yellow
        Write-Host "Fix options:" -ForegroundColor Yellow
        Write-Host "  1) Reboot Windows"
        Write-Host "  2) Start on another port: .\restart-api.ps1 -Port 8001"
        Write-Host "  3) Run diagnostics: .\scripts\diagnose-port.ps1 -Port $Port"
        exit 2
    }

    Write-Host "Port $Port still in use (attempt $attempt/5). Live PIDs: $($aliveLeft -join ', ')" -ForegroundColor Yellow
}

Write-Host "WARNING: port $Port still in use." -ForegroundColor Red
Write-Host "Run as Administrator: .\scripts\diagnose-port.ps1 -Port $Port" -ForegroundColor Yellow
exit 1
