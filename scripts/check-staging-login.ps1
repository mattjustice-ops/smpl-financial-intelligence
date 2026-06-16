# Login + warehouse diagnostics against Neon *staging* (not local backend/.env).
#
# Usage:
#   .\scripts\check-staging-login.ps1
#   .\scripts\check-staging-login.ps1 -Email mattjustice@smpl-ai.com

param(
    [string]$Email = "mattjustice@smpl-ai.com",
    [string]$OrganizationId = "8571e520-0687-4516-bdee-379f37c58c1f",
    [string]$DatabaseUrl = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $repoRoot "backend"
$python = Join-Path $backendDir ".venv312\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "ERROR: backend venv not found (.venv312)." -ForegroundColor Red
    exit 1
}

function Normalize-DatabaseUrl {
    param([string]$Url)
    $u = $Url.Trim().Trim('"').Trim("'")
    if ($u -match "^postgresql://") {
        $u = $u -replace "^postgresql://", "postgresql+psycopg://"
    }
    $u = $u -replace "[?&]channel_binding=require", ""
    $u = $u -replace "\?&", "?"
    return $u.TrimEnd("?").TrimEnd("&")
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
    Write-Host "ERROR: STAGING_DATABASE_URL not found in frontend/.env.staging.local" -ForegroundColor Red
    exit 1
}

$dbUrl = Normalize-DatabaseUrl $DatabaseUrl
$safeHost = if ($dbUrl -match "@([^/]+)/") { $Matches[1] } else { "(unknown)" }

Write-Host ""
Write-Host "=== Staging login + warehouse check ===" -ForegroundColor Cyan
Write-Host "DB host: $safeHost" -ForegroundColor DarkGray
Write-Host "Email:   $Email" -ForegroundColor DarkGray
Write-Host ""

Push-Location $backendDir
try {
    $env:DATABASE_URL = $dbUrl

    Write-Host "--- Auth (organizations, invites, membership) ---" -ForegroundColor Yellow
    & $python scripts\check_login_access.py --email $Email --organization-id $OrganizationId
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host ""
    Write-Host "--- All active workspaces (first = default on Preview login) ---" -ForegroundColor Yellow
    $listPy = @"
import os
from sqlalchemy import create_engine, text
email = '$($Email.Trim().ToLower())'
engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    rows = conn.execute(
        text('''
            SELECT o.id::text, o.name, COALESCE(o.plan, 'starter'), om.joined_at
            FROM organization_members om
            JOIN organizations o ON o.id = om.organization_id
            JOIN users u ON u.id = om.user_id
            WHERE u.email = :email AND om.status = 'active'
            ORDER BY om.joined_at ASC
        '''),
        {'email': email},
    ).all()
if not rows:
    print('No active memberships')
else:
    for i, (oid, name, plan, joined) in enumerate(rows):
        mark = '  <-- active on login' if i == 0 else ''
        print(f'{oid}  {name}  plan={plan}{mark}')
demo = '$OrganizationId'
if rows and rows[0][0] != demo:
    print('')
    print(f'WARN: Login uses {rows[0][1]}, but demo warehouse data is on org {demo} (SMPL Demo Co).')
    print('Fix: seed_dev_invite + set-prod-active-org.ps1 -DatabaseUrl (staging URL)')
"@
    & $python -c $listPy
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host ""
    Write-Host "--- Warehouse row counts (demo org) ---" -ForegroundColor Yellow
    $pyCode = @"
from sqlalchemy import create_engine, text
import os
org = '$OrganizationId'
engine = create_engine(os.environ['DATABASE_URL'])
tables = ['organizations', 'mrr_waterfall', 'customers', 'gl_actuals', 'warehouse_csv_rows']
with engine.connect() as conn:
    row = conn.execute(text('SELECT name, status, plan FROM organizations WHERE id = :o'), {'o': org}).first()
    print(f'org row: {row}')
    for t in tables[1:]:
        try:
            n = conn.execute(text(f'SELECT COUNT(*) FROM {t} WHERE organization_id = :o'), {'o': org}).scalar()
            print(f'{t}: {n}')
        except Exception as exc:
            print(f'{t}: ERROR {exc}')
"@
    & $python -c $pyCode
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host ""
    Write-Host "If warehouse counts are 0, load staging data:" -ForegroundColor Yellow
    Write-Host "  .\scripts\setup-prod-warehouse.ps1 -DatabaseUrl `"<STAGING_DATABASE_URL>`"" -ForegroundColor White
    Write-Host ""
}
finally {
    Pop-Location
}
