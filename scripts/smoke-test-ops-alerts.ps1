# Phase 2 — SMPL Ops alerting smoke test (exit non-zero on failure).
#
# Checks Railway API, Vercel frontend proxy, and records a backend health_check
# event when BILLING_INTERNAL_API_KEY is available.
#
# Usage (repo root):
#   .\scripts\smoke-test-ops-alerts.ps1
#   .\scripts\smoke-test-ops-alerts.ps1 -RecordBackendCheck
#
# Schedule daily (Windows Task Scheduler) or run before customer outreach.

param(
    [string]$FrontendUrl = "https://www.smpl-ai.com",
    [string]$ApiBase = "https://sfi-api-production.up.railway.app",
    [switch]$RecordBackendCheck,
    [int]$MaxExportFailures24h = 0,
    [int]$MaxDbLatencyMs = 500
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path $PSScriptRoot -Parent
$failed = 0

function Test-JsonEndpoint {
    param(
        [string]$Label,
        [string]$Url,
        [string]$ExpectField = "",
        [string]$ExpectValue = ""
    )
    try {
        $res = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 45
        if ($res.StatusCode -ne 200) {
            Write-Host "FAIL: $Label (HTTP $($res.StatusCode))" -ForegroundColor Red
            $script:failed++
            return $null
        }
        $json = $res.Content | ConvertFrom-Json
        if ($ExpectField -and "$($json.$ExpectField)" -ne $ExpectValue) {
            Write-Host "FAIL: $Label ($ExpectField expected $ExpectValue, got $($json.$ExpectField))" -ForegroundColor Red
            $script:failed++
            return $null
        }
        Write-Host "OK:   $Label" -ForegroundColor Green
        return $json
    }
    catch {
        Write-Host "FAIL: $Label - $($_.Exception.Message)" -ForegroundColor Red
        $script:failed++
        return $null
    }
}

Write-Host ""
Write-Host "=== SMPL Ops alerts smoke (Phase 2) ===" -ForegroundColor Cyan
Write-Host "Frontend: $FrontendUrl" -ForegroundColor DarkGray
Write-Host "API:      $ApiBase" -ForegroundColor DarkGray
Write-Host ""

Test-JsonEndpoint -Label "Railway /health" -Url "$ApiBase/health" -ExpectField "status" -ExpectValue "ok" | Out-Null
Test-JsonEndpoint -Label "Railway /health/db" -Url "$ApiBase/health/db" -ExpectField "status" -ExpectValue "ok" | Out-Null
Test-JsonEndpoint -Label "Vercel /health" -Url "$FrontendUrl/health" -ExpectField "status" -ExpectValue "ok" | Out-Null

$internalKey = $null
. (Join-Path $PSScriptRoot "lib\Resolve-BillingInternalKey.ps1")
$resolvedKey = Resolve-BillingInternalKey -RepoRoot $repoRoot -TryVercelPull:$false
if ($resolvedKey) {
    $internalKey = $resolvedKey.Key
}

if ($RecordBackendCheck -and $internalKey) {
    Write-Host ""
    Write-Host "Recording backend health_check via /api/v1/ops/run-health-check ..." -ForegroundColor Yellow
    try {
        $headers = @{ "X-Billing-Internal-Key" = $internalKey }
        $check = Invoke-RestMethod -Method Post -Uri "$ApiBase/api/v1/ops/run-health-check" -Headers $headers -TimeoutSec 120
        $status = $check.status
        if ($status -ne "ok") {
            Write-Host "FAIL: backend health_check status=$status" -ForegroundColor Red
            $failed++
            foreach ($row in @($check.checks)) {
                if (-not $row.ok) {
                    Write-Host "  - $($row.name): $($row.detail)" -ForegroundColor DarkYellow
                }
            }
        }
        else {
            Write-Host "OK:   backend health_check recorded (status=ok)" -ForegroundColor Green
        }
        if ($check.storage.database_gb) {
            Write-Host "  Neon database_gb=$($check.storage.database_gb)" -ForegroundColor DarkGray
        }
    }
    catch {
        Write-Host "FAIL: backend health_check - $($_.Exception.Message)" -ForegroundColor Red
        $failed++
    }
}
elseif ($RecordBackendCheck) {
    Write-Host "SKIP: backend health_check (BILLING_INTERNAL_API_KEY not set)" -ForegroundColor Yellow
    Write-Host "  Tip: .\scripts\collect-ops-storage-snapshot.ps1 -Local  (no key needed)" -ForegroundColor DarkGray
    Write-Host "  Or:  .\scripts\collect-ops-storage-snapshot.ps1 -TryVercelPull" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Railway / Vercel native alerts (configure in consoles):" -ForegroundColor Cyan
Write-Host "  Railway -> sfi-api-production -> Settings -> Observability -> alerts on 5xx / restarts" -ForegroundColor DarkGray
Write-Host "  Vercel  -> smpl-financial-intelligence -> Monitoring -> 5xx / latency" -ForegroundColor DarkGray
Write-Host "  Neon    -> project -> Monitoring -> storage + compute thresholds" -ForegroundColor DarkGray
Write-Host ""

if ($failed -eq 0) {
    Write-Host "OK: SMPL Ops alerts smoke passed" -ForegroundColor Green
    exit 0
}

Write-Host "FAIL: $failed check(s) failed" -ForegroundColor Red
exit 1
