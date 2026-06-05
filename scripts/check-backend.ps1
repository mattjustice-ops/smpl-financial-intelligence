# Quick check that the SMPL backend API is reachable on port 8001.
# Run from repo root: .\scripts\check-backend.ps1

param(
  [string]$BaseUrl = "http://127.0.0.1:8001"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "Checking SMPL backend at $BaseUrl ..." -ForegroundColor Cyan

try {
  $health = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get -TimeoutSec 5
  Write-Host "OK - backend is running." -ForegroundColor Green
  if ($health.status) {
    Write-Host ("Status: " + $health.status)
  }
  exit 0
} catch {
  Write-Host "Backend is NOT reachable." -ForegroundColor Red
  Write-Host ""
  Write-Host "Start it in a separate terminal:" -ForegroundColor Yellow
  Write-Host "  cd backend" -ForegroundColor White
  Write-Host "  .\start-api.ps1 -Port 8001" -ForegroundColor White
  Write-Host ""
  Write-Host "Leave that window open while you click your SMPL sign-in link." -ForegroundColor Yellow
  exit 1
}
