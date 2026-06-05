# One-command local login prep: seed invite + verify session-sync.
# Run from repo root:
#   .\scripts\ensure-dev-login.ps1 -Email mattjustice@smpl-ai.com

param(
  [Parameter(Mandatory = $true)]
  [string]$Email,
  [string]$OrganizationId = "8571e520-0687-4516-bdee-379f37c58c1f"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent

Write-Host ""
Write-Host "=== Ensure dev login access ===" -ForegroundColor Cyan
Write-Host ""

& (Join-Path $repoRoot "scripts\check-backend.ps1")
if ($LASTEXITCODE -ne 0) {
  exit 1
}

Write-Host ""
& (Join-Path $repoRoot "scripts\seed-dev-invite.ps1") -Email $Email -OrganizationId $OrganizationId
if ($LASTEXITCODE -ne 0) {
  exit 1
}

Write-Host ""
& (Join-Path $repoRoot "scripts\check-login-access.ps1") -Email $Email -OrganizationId $OrganizationId
