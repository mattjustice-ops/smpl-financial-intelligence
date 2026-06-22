# Set which organization is active on next login (oldest joined_at wins in session-sync).
#
# Usage:
#   .\scripts\set-prod-active-org.ps1 `
#     -Email mattjustice@smpl-ai.com `
#     -OrganizationId "cfa7c116-3a89-4dd1-91df-80d4ece5c59d"
#
# List your memberships first:
#   .\scripts\set-prod-active-org.ps1 -Email mattjustice@smpl-ai.com -ListOnly

param(
    [Parameter(Mandatory = $true)]
    [string]$Email,
    [string]$OrganizationId = "",
    [string]$DatabaseUrl = "",
    [switch]$ListOnly,
    [switch]$TryVercelPull
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\Resolve-ProdDatabaseUrl.ps1")

$repoRoot = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $repoRoot "backend"
$python = Join-Path $backendDir ".venv312\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

if (-not $DatabaseUrl) {
    $resolved = Resolve-ProdDatabaseUrl -RepoRoot $repoRoot -TryVercelPull:$TryVercelPull -PreferSavedProdFile
    if ($resolved) { $DatabaseUrl = $resolved.Url }
}
if (-not $DatabaseUrl) {
    Write-ProdDatabaseUrlHelp
    exit 1
}

$dbUrl = $DatabaseUrl
if ($dbUrl -match "^postgresql://") {
    $dbUrl = $dbUrl -replace "^postgresql://", "postgresql+psycopg://"
}

$listPy = @"
import os
from sqlalchemy import create_engine, text

email = "$($Email.Trim().ToLower())"
engine = create_engine(os.environ["DATABASE_URL"])
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
        {"email": email},
    ).all()
if not rows:
    print(f"No active memberships for {email}")
else:
    print(f"Active workspaces for {email} (first = default on login):\n")
    for i, (oid, name, plan, joined) in enumerate(rows):
        mark = " <-- active on login" if i == 0 else ""
        print(f"  {oid}")
        print(f"    name:  {name}")
        print(f"    plan:  {plan}")
        print(f"    joined: {joined}{mark}")
        print("")
"@

if ($ListOnly) {
    Push-Location $backendDir
    try {
        $env:DATABASE_URL = $dbUrl
        $listPy | & $python -
    }
    finally {
        Pop-Location
    }
    exit 0
}

if (-not $OrganizationId) {
    Write-Host "ERROR: Pass -OrganizationId or use -ListOnly." -ForegroundColor Red
    exit 1
}

$updatePy = @"
import os
import sys
from sqlalchemy import create_engine, text

email = "$($Email.Trim().ToLower())"
org_id = "$($OrganizationId.Trim())"
engine = create_engine(os.environ["DATABASE_URL"])
with engine.begin() as conn:
    row = conn.execute(
        text('''
            SELECT o.name
            FROM organization_members om
            JOIN organizations o ON o.id = om.organization_id
            JOIN users u ON u.id = om.user_id
            WHERE u.email = :email
              AND om.organization_id = CAST(:org_id AS uuid)
              AND om.status = 'active'
        '''),
        {"email": email, "org_id": org_id},
    ).first()
    if row is None:
        print(f"ERROR: {email} is not an active member of org {org_id}", file=sys.stderr)
        print("Run provision-prod-customer.ps1 for that org first.", file=sys.stderr)
        sys.exit(1)
    conn.execute(
        text('''
            UPDATE organization_members om
            SET joined_at = TIMESTAMPTZ '2010-01-01 00:00:00+00'
            FROM users u
            WHERE u.email = :email
              AND om.user_id = u.id
              AND om.organization_id = CAST(:org_id AS uuid)
        '''),
        {"email": email, "org_id": org_id},
    )
    print(f"OK: next login for {email} will prefer workspace: {row.name} ({org_id})")
    print("Sign out at https://smpl-financial-intelligence.vercel.app/login and sign in again.")
"@

Push-Location $backendDir
try {
    $env:DATABASE_URL = $dbUrl
    $updatePy | & $python -
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
