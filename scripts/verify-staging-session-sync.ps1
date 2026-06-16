# Call staging session-sync the same way Preview login does (proves active org from API).
#
# Usage:
#   .\scripts\verify-staging-session-sync.ps1
#   .\scripts\verify-staging-session-sync.ps1 -InternalKey "your-key"

param(
    [string]$Email = "mattjustice@smpl-ai.com",
    [string]$ApiBase = "",
    [string]$InternalKey = ""
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path $PSScriptRoot -Parent

if (-not $ApiBase) {
    $stagingFile = Join-Path $repoRoot "frontend\.env.staging.local"
    if (Test-Path $stagingFile) {
        foreach ($line in Get-Content $stagingFile) {
            if ($line -match "^STAGING_API_URL=(.+)$") {
                $ApiBase = $Matches[1].Trim()
                break
            }
        }
    }
}

if (-not $ApiBase) {
    Write-Host "ERROR: STAGING_API_URL not found in frontend/.env.staging.local" -ForegroundColor Red
    exit 1
}

$ApiBase = $ApiBase.Trim().TrimEnd("/")
$headers = @{ "Content-Type" = "application/json" }
if ($InternalKey) {
    $headers["X-Billing-Internal-Key"] = $InternalKey.Trim()
}

Write-Host ""
Write-Host "=== Staging session-sync ===" -ForegroundColor Cyan
Write-Host "API:   $ApiBase" -ForegroundColor DarkGray
Write-Host "Email: $Email" -ForegroundColor DarkGray
Write-Host ""

$body = @{ email = $Email.Trim().ToLower() } | ConvertTo-Json

try {
    $res = Invoke-RestMethod `
        -Uri "$ApiBase/api/v1/auth/session-sync" `
        -Method Post `
        -Headers $headers `
        -Body $body `
        -TimeoutSec 45
}
catch {
    Write-Host "FAIL: $_" -ForegroundColor Red
    if ($_.Exception.Response.StatusCode.value__ -eq 401) {
        Write-Host "Pass -InternalKey (same as Railway BILLING_INTERNAL_API_KEY / Vercel Preview)." -ForegroundColor Yellow
    }
    exit 1
}

Write-Host "activeOrganizationId: $($res.activeOrganizationId)" -ForegroundColor Green
Write-Host "organizations:" -ForegroundColor Yellow
foreach ($org in $res.organizations) {
    $mark = if ($org.organizationId -eq $res.activeOrganizationId) { " <-- active" } else { "" }
    Write-Host "  $($org.organizationName) ($($org.organizationId)) plan=$($org.plan) status=$($org.organizationStatus)$mark"
}
Write-Host ""

$demoOrg = "8571e520-0687-4516-bdee-379f37c58c1f"
if ($res.activeOrganizationId -ne $demoOrg) {
    Write-Host "WARN: API still prefers non-demo org. Run .\scripts\set-staging-demo-workspace.ps1" -ForegroundColor Yellow
}
else {
    Write-Host "OK: Staging API returns SMPL Demo Co as active org." -ForegroundColor Green
}
