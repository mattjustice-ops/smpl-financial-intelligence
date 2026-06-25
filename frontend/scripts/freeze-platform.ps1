# Freeze current public/ Board + Forecast Engine into canonical/ baseline.
# Run from repo root or frontend/: .\scripts\freeze-platform.ps1
$ErrorActionPreference = "Stop"
$Frontend = Split-Path $PSScriptRoot -Parent
Set-Location $Frontend

Write-Host "=== SMPL platform baseline freeze ===" -ForegroundColor Cyan
npm run extract:demo-seed
npm run freeze:platform
npm run verify:platform
Write-Host ""
Write-Host "Done. Commit frontend/canonical/ (and public/ if changed) when ready." -ForegroundColor Green
Write-Host "Restore later: npm run reset:platform" -ForegroundColor DarkGray
