# Insert a pending_user_invites row for local login testing.
# Usage:
#   .\scripts\seed-dev-invite.ps1 -Email you@company.com -OrganizationId 8571e520-0687-4516-bdee-379f37c58c1f

param(
  [Parameter(Mandatory = $true)]
  [string]$Email,
  [Parameter(Mandatory = $true)]
  [string]$OrganizationId,
  [string]$Role = "admin"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $repoRoot "backend"
$pythonScript = Join-Path $backendDir "scripts\seed_dev_invite.py"

Write-Host ""
Write-Host "Seeding pending invite for $Email on org $OrganizationId ..." -ForegroundColor Cyan

function Test-PostgresPort {
  return (Test-NetConnection -ComputerName 127.0.0.1 -Port 5432 -WarningAction SilentlyContinue).TcpTestSucceeded
}

if (-not (Test-PostgresPort)) {
  Write-Host ""
  Write-Host "Postgres is not running on localhost:5432." -ForegroundColor Yellow
  Write-Host "Start it from the repo root:" -ForegroundColor Yellow
  Write-Host "  docker compose up -d" -ForegroundColor White
  Write-Host ""
  Write-Host "Wait a few seconds, then run this script again." -ForegroundColor Yellow
  exit 1
}

$venvPython = Join-Path $backendDir ".venv312\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }

Push-Location $backendDir
try {
  & $python $pythonScript --email $Email --organization-id $OrganizationId --role $Role
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
  Write-Host ""
  Write-Host "Next: open http://localhost:3002/login and use that email." -ForegroundColor Green
  Write-Host ""
}
finally {
  Pop-Location
}
