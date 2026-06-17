# Test DATABASE_URL the same way FastAPI does (SQLAlchemy + psycopg).
#
# Usage:
#   .\scripts\test-database-url.ps1 -DatabaseUrl "postgresql://..."
#   .\scripts\test-database-url.ps1   # reads STAGING_DATABASE_URL from .env.staging.local

param(
    [string]$DatabaseUrl = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $repoRoot "backend"
$python = Join-Path $backendDir ".venv312\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

function Normalize-DatabaseUrl {
    param([string]$Url)
    $u = $Url.Trim().Trim('"').Trim("'")
    if ($u -match "^postgresql://") {
        $u = $u -replace "^postgresql://", "postgresql+psycopg://"
    }
    if ($u -match "^postgres://") {
        $u = $u -replace "^postgres://", "postgresql+psycopg://"
    }
    # channel_binding=require often breaks psycopg from cloud hosts (Railway, etc.)
    $u = $u -replace "[?&]channel_binding=require", ""
    $u = $u -replace "\?&", "?"
    $u = $u.TrimEnd("?").TrimEnd("&")
    return $u
}

if (-not $DatabaseUrl) {
    $stagingFile = Join-Path $repoRoot "frontend\.env.staging.local"
    if (Test-Path $stagingFile) {
        foreach ($line in Get-Content $stagingFile) {
            if ($line -match "^STAGING_DATABASE_URL=(.+)$") {
                $DatabaseUrl = $Matches[1].Trim()
                break
            }
        }
    }
}

if (-not $DatabaseUrl) {
    Write-Host "ERROR: Pass -DatabaseUrl or set STAGING_DATABASE_URL in frontend/.env.staging.local" -ForegroundColor Red
    exit 1
}

$dbUrl = Normalize-DatabaseUrl $DatabaseUrl
$safeHost = if ($dbUrl -match "@([^/]+)/") { $Matches[1] } else { "(unknown host)" }

Write-Host ""
Write-Host "Testing DB connection to: $safeHost" -ForegroundColor Cyan
Write-Host ""

$pyCode = @"
from sqlalchemy import create_engine, text
url = r'''$dbUrl'''
try:
    engine = create_engine(url, pool_pre_ping=True, connect_args={'connect_timeout': 10})
    with engine.connect() as conn:
        val = conn.execute(text('SELECT 1')).scalar()
    print(f'OK: SELECT 1 -> {val}')
except Exception as exc:
    print(f'FAIL: {type(exc).__name__}: {exc}')
    raise SystemExit(1)
"@

Push-Location $backendDir
try {
    & $python -c $pyCode
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host ""
    Write-Host "If this passes locally but Railway /health/db fails, compare DATABASE_URL on sfi-api-staging:" -ForegroundColor Yellow
    Write-Host "  - postgresql+psycopg:// (not plain postgresql://)" -ForegroundColor White
    Write-Host "  - same host as above, sslmode=require" -ForegroundColor White
    Write-Host "  - NO channel_binding=require" -ForegroundColor White
    Write-Host "  - CLI linked to sfi-api-staging (not sfi-api prod)" -ForegroundColor White
    Write-Host ""
}
finally {
    Pop-Location
}
