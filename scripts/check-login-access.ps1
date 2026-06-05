# Inspect whether an email can sign in (invites + memberships in Postgres).
# Run from repo root:
#   .\scripts\check-login-access.ps1 -Email mattjustice@smpl-ai.com

param(
  [Parameter(Mandatory = $true)]
  [string]$Email,
  [string]$OrganizationId = "8571e520-0687-4516-bdee-379f37c58c1f"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $repoRoot "backend"
$pythonScript = Join-Path $backendDir "scripts\check_login_access.py"
$venvPython = Join-Path $backendDir ".venv312\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }

Push-Location $backendDir
try {
  & $python $pythonScript --email $Email --organization-id $OrganizationId
} finally {
  Pop-Location
}

Write-Host ""
Write-Host "Testing session-sync API..." -ForegroundColor Cyan
try {
  $body = @{ email = $Email.Trim().ToLower() } | ConvertTo-Json
  $result = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8001/api/v1/auth/session-sync" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body `
    -TimeoutSec 10
  Write-Host "session-sync OK:" -ForegroundColor Green
  Write-Host ("  userId: " + $result.userId)
  Write-Host ("  activeOrganizationId: " + $result.activeOrganizationId)
} catch {
  Write-Host "session-sync FAILED:" -ForegroundColor Red
  if ($_.ErrorDetails.Message) {
    Write-Host $_.ErrorDetails.Message
  } else {
    Write-Host $_.Exception.Message
  }
  Write-Host ""
  Write-Host "If access is denied, run:" -ForegroundColor Yellow
  Write-Host "  .\scripts\seed-dev-invite.ps1 -Email $Email -OrganizationId $OrganizationId" -ForegroundColor White
}
