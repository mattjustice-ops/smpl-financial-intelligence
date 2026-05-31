# Compare ping responses — browser often hits localhost (IPv6) vs 127.0.0.1 (IPv4).
$ErrorActionPreference = "Continue"
$urls = @(
    "http://127.0.0.1:8000/api/v1/export/ping",
    "http://localhost:8000/api/v1/export/ping"
)
$whoami = "http://127.0.0.1:8000/api/v1/export/whoami"
Write-Host ""
Write-Host "=== $whoami ===" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri $whoami -UseBasicParsing -Headers @{ "Cache-Control" = "no-cache" }
    Write-Host $r.Content
} catch {
    Write-Host "FAILED (start API first): $_" -ForegroundColor Red
}

foreach ($url in $urls) {
    Write-Host ""
    Write-Host "=== $url ===" -ForegroundColor Cyan
    try {
        $r = Invoke-WebRequest -Uri "$url`?t=$(Get-Date -Format 'yyyyMMddHHmmss')" -UseBasicParsing -Headers @{ "Cache-Control" = "no-cache" }
        Write-Host $r.Content
        if ($r.Headers["X-SFI-Api-Build"]) {
            Write-Host "X-SFI-Api-Build: $($r.Headers['X-SFI-Api-Build'])" -ForegroundColor Green
        } else {
            Write-Host "MISSING X-SFI-Api-Build header (stale API process)" -ForegroundColor Red
        }
        if ($r.Content -notmatch '"api_build"\s*:\s*"openai-ping-v3"') {
            Write-Host "STALE: json has no api_build openai-ping-v3" -ForegroundColor Red
        }
    } catch {
        Write-Host "FAILED: $_" -ForegroundColor Red
    }
}
