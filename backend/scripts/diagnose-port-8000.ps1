# Show which process owns port 8000 (stale API vs restart-api).
# Note: $pid is reserved in PowerShell — we use $procId instead.
$ErrorActionPreference = "Continue"
$conns = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if (-not $conns) {
    Write-Host "Nothing listening on port 8000." -ForegroundColor Yellow
    exit 0
}
$procIds = $conns | Select-Object -ExpandProperty OwningProcess -Unique
foreach ($procId in $procIds) {
    Write-Host ""
    Write-Host "PID $procId" -ForegroundColor Cyan
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($proc) { Write-Host "  Name: $($proc.ProcessName)  Path: $($proc.Path)" }
    $wmi = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
    if ($wmi) { Write-Host "  CommandLine: $($wmi.CommandLine)" }
}
Write-Host ""
Write-Host "Ping checks:" -ForegroundColor Cyan
foreach ($url in @("http://127.0.0.1:8000/api/v1/export/whoami", "http://127.0.0.1:8000/api/v1/export/ping")) {
    try {
        $r = Invoke-WebRequest -Uri $url -UseBasicParsing -Headers @{ "Cache-Control" = "no-cache" }
        Write-Host $url
        Write-Host $r.Content
        if ($r.Headers["X-SFI-Api-Build"]) { Write-Host "  Header X-SFI-Api-Build: $($r.Headers['X-SFI-Api-Build'])" }
    } catch {
        Write-Host "$url FAILED: $_" -ForegroundColor Red
    }
}
