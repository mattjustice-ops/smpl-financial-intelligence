# Quick frontend production build check.
# Run from repo root: .\scripts\check-frontend-build.ps1

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$frontendDir = Join-Path $repoRoot "frontend"
$log = Join-Path $repoRoot "deploy-build.log"

Push-Location $frontendDir
try {
  Write-Host "Running TypeScript check..." -ForegroundColor Yellow
  cmd /c "npx tsc --noEmit > `"$log`" 2>&1"
  if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "TypeScript check failed:" -ForegroundColor Red
    Get-Content $log
    exit 1
  }

  Write-Host "Running Next.js production build..." -ForegroundColor Yellow
  cmd /c "npm run build >> `"$log`" 2>&1"
  if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Build failed. Last lines:" -ForegroundColor Red
    Get-Content $log | Select-Object -Last 40
    Write-Host ""
    Write-Host "Type errors (if any):" -ForegroundColor Red
    Get-Content $log | Select-String -Pattern "Type error|Failed to compile|error TS" -Context 0,8
    exit 1
  }

  Write-Host ""
  Write-Host "Build OK." -ForegroundColor Green
} finally {
  Pop-Location
}
