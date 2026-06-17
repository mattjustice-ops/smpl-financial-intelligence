# Compare session-sync active org: staging API vs production API (gl-5b diagnosis).
#
# Usage:
#   .\scripts\compare-session-sync.ps1

param(
    [string]$Email = "mattjustice@smpl-ai.com",
    [string]$StagingApi = "",
    [string]$ProductionApi = "https://sfi-api-production.up.railway.app",
    [string]$InternalKey = ""
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path $PSScriptRoot -Parent

if (-not $StagingApi) {
    $stagingFile = Join-Path $repoRoot "frontend\.env.staging.local"
    if (Test-Path $stagingFile) {
        foreach ($line in Get-Content $stagingFile) {
            if ($line -match "^STAGING_API_URL=(.+)$") {
                $StagingApi = $Matches[1].Trim().TrimEnd("/")
                break
            }
        }
    }
}

if (-not $StagingApi) {
    Write-Host "ERROR: STAGING_API_URL not found." -ForegroundColor Red
    exit 1
}

$demoOrg = "8571e520-0687-4516-bdee-379f37c58c1f"
$customerOrg = "cfa7c116-3a89-4dd1-91df-80d4ece5c59d"
$body = @{ email = $Email.Trim().ToLower() } | ConvertTo-Json
$headers = @{ "Content-Type" = "application/json" }
if ($InternalKey) {
    $headers["X-Billing-Internal-Key"] = $InternalKey.Trim()
}

function Invoke-SessionSync {
    param([string]$Label, [string]$Base)
    Write-Host "$Label" -ForegroundColor Yellow
    Write-Host "  $Base" -ForegroundColor DarkGray
    try {
        $res = Invoke-RestMethod -Uri "$Base/api/v1/auth/session-sync" -Method Post -Headers $headers -Body $body -TimeoutSec 45
        $active = $res.activeOrganizationId
        $name = ($res.organizations | Where-Object { $_.organizationId -eq $active } | Select-Object -First 1).organizationName
        Write-Host "  activeOrganizationId: $active" -ForegroundColor $(if ($active -eq $demoOrg) { "Green" } elseif ($active -eq $customerOrg) { "Red" } else { "White" })
        Write-Host "  active name:          $name" -ForegroundColor White
        foreach ($org in $res.organizations) {
            $mark = if ($org.organizationId -eq $active) { " <-- active" } else { "" }
            Write-Host "    $($org.organizationName) ($($org.organizationId))$mark" -ForegroundColor DarkGray
        }
        return $res
    }
    catch {
        $code = $_.Exception.Response.StatusCode.value__ 
        Write-Host "  FAIL: $_" -ForegroundColor Red
        if ($code -eq 401) {
            Write-Host "  -> 401: BILLING_INTERNAL_API_KEY mismatch" -ForegroundColor Yellow
        }
        return $null
    }
}

Write-Host ""
Write-Host "=== session-sync comparison ===" -ForegroundColor Cyan
Write-Host "Email: $Email" -ForegroundColor DarkGray
Write-Host ""

$staging = Invoke-SessionSync -Label "STAGING (want SMPL Demo Co)" -Base $StagingApi
Write-Host ""
$prod = Invoke-SessionSync -Label "PRODUCTION (likely Customer Corp)" -Base $ProductionApi
Write-Host ""

Write-Host "=== Your Preview /api/auth/session matched ===" -ForegroundColor Cyan
Write-Host "  activeOrganizationId: $customerOrg = Customer Corp" -ForegroundColor Red
Write-Host ""

if ($staging -and $staging.activeOrganizationId -eq $demoOrg -and $prod -and $prod.activeOrganizationId -eq $customerOrg) {
    Write-Host "Diagnosis: Preview session matches PRODUCTION sync, not staging." -ForegroundColor Red
    Write-Host "  -> session-sync on Vercel is failing OR not running; JWT is stale from prod-shaped login." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Fix:" -ForegroundColor Yellow
    Write-Host "  1. .\scripts\set-vercel-preview-billing-from-production.ps1" -ForegroundColor White
    Write-Host "  2. git push auth.ts + redeploy Preview" -ForegroundColor White
    Write-Host "  3. Sign out -> incognito -> NEW magic link" -ForegroundColor White
}
elseif ($staging -and $staging.activeOrganizationId -eq $demoOrg) {
    Write-Host "Staging API is correct. Preview JWT is stale or session re-sync is not deployed." -ForegroundColor Yellow
    Write-Host "  Push latest frontend/auth.ts, redeploy, sign out, new magic link." -ForegroundColor White
}
Write-Host ""
