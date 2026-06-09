param(
    [int]$Port = 3002
)

function Get-PortListenerPids {
    param([int]$Port)

    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $connections) {
        return @()
    }

    return @(
        $connections |
            Select-Object -ExpandProperty OwningProcess -Unique |
            Where-Object { $_ -gt 0 }
    )
}

function Stop-NodeProcess {
    param([int]$ProcId, [int]$Port)

    $proc = Get-Process -Id $ProcId -ErrorAction SilentlyContinue
    if (-not $proc) {
        return
    }

    $isNode = $proc.ProcessName -match '^node' -or ($proc.Path -and $proc.Path -match 'node\.exe')
    if (-not $isNode) {
        Write-Host "Port $Port is used by PID $ProcId ($($proc.ProcessName)) - not node; close manually if needed." -ForegroundColor Yellow
        return
    }

    Write-Host "Stopping PID $ProcId ($($proc.ProcessName)) on port $Port..."
    Stop-Process -Id $ProcId -Force -ErrorAction SilentlyContinue
}

$pids = Get-PortListenerPids -Port $Port
if (-not $pids) {
    Write-Host "No process listening on port $Port."
    exit 0
}

foreach ($procId in $pids) {
    Stop-NodeProcess -ProcId $procId -Port $Port
}

for ($attempt = 1; $attempt -le 12; $attempt++) {
    Start-Sleep -Milliseconds 500
    $remaining = Get-PortListenerPids -Port $Port
    if (-not $remaining) {
        Write-Host "Port $Port is free." -ForegroundColor Green
        exit 0
    }

    foreach ($procId in $remaining) {
        Stop-NodeProcess -ProcId $procId -Port $Port
    }
}

Write-Host "Port $Port may still be in use. Close other terminals using Next.js or reboot the stale process." -ForegroundColor Yellow
exit 1
