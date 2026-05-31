# Quick probe: is FastAPI listening on port 8000?
$urls = @(
    "http://127.0.0.1:8000/health",
    "http://localhost:8000/health"
)

Write-Host "Checking backend..." -ForegroundColor Cyan
$anyUp = $false
foreach ($url in $urls) {
    try {
        $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 4
        Write-Host "  OK  $url -> $($r.Content)" -ForegroundColor Green
        $anyUp = $true
    } catch {
        Write-Host "  FAIL $url -> $($_.Exception.Message)" -ForegroundColor Red
    }
}

if (-not $anyUp) {
    Write-Host ""
    Write-Host "Backend is not reachable. Start it:" -ForegroundColor Yellow
    Write-Host "  cd backend"
    Write-Host "  .\start-api.ps1"
    Write-Host ""
    Write-Host "Also ensure Postgres:" -ForegroundColor Yellow
    Write-Host "  docker compose up -d"
    exit 1
}

try {
    $db = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health/db" -UseBasicParsing -TimeoutSec 6
    Write-Host "  OK  /health/db -> $($db.Content)" -ForegroundColor Green
} catch {
    Write-Host "  WARN /health/db -> $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "       Run: docker compose up -d"
}

Write-Host ""
Write-Host "Frontend should use: NEXT_PUBLIC_API_URL=http://127.0.0.1:8000" -ForegroundColor Cyan
exit 0
