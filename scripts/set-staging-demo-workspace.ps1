# Point Preview login at SMPL Demo Co (warehouse data) on Neon staging.
#
# Session-sync picks the active org with the oldest joined_at. This script:
#   1. Ensures the user has active admin membership on SMPL Demo Co
#   2. Sets that membership joined_at earliest; bumps other orgs later
#
# Usage:
#   .\scripts\set-staging-demo-workspace.ps1
#   .\scripts\set-staging-demo-workspace.ps1 -Email mattjustice@smpl-ai.com

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
$email = $Email.Trim().ToLower()
$orgId = $OrganizationId.Trim()

Write-Host ""
Write-Host "=== Staging default workspace -> SMPL Demo Co ===" -ForegroundColor Cyan
Write-Host "DB host: $safeHost" -ForegroundColor DarkGray
Write-Host "Email:   $email" -ForegroundColor DarkGray
Write-Host ""

$py = @"
import os
import sys
import uuid
from sqlalchemy import create_engine, text

email = "$email"
demo_org_id = "$orgId"
engine = create_engine(os.environ["DATABASE_URL"])

def list_memberships(conn):
    rows = conn.execute(
        text('''
            SELECT o.id::text, o.name, COALESCE(o.plan, 'starter'), om.joined_at, om.status
            FROM organization_members om
            JOIN organizations o ON o.id = om.organization_id
            JOIN users u ON u.id = om.user_id
            WHERE u.email = :email AND om.status = 'active'
            ORDER BY om.joined_at ASC
        '''),
        {"email": email},
    ).all()
    return rows

with engine.begin() as conn:
    user = conn.execute(
        text("SELECT id::text FROM users WHERE email = :email"),
        {"email": email},
    ).first()
    if user is None:
        print(f"ERROR: No users row for {email}. Sign in on Preview once, then re-run.", file=sys.stderr)
        sys.exit(1)
    user_id = user[0]

    org = conn.execute(
        text("SELECT name FROM organizations WHERE id = CAST(:oid AS uuid)"),
        {"oid": demo_org_id},
    ).first()
    if org is None:
        print(f"ERROR: Demo org not found: {demo_org_id}", file=sys.stderr)
        sys.exit(1)
    demo_name = org[0]

    conn.execute(
        text('''
            UPDATE organizations
            SET status = 'active'
            WHERE id = CAST(:oid AS uuid) AND status NOT IN ('active', 'trialing', 'past_due')
        '''),
        {"oid": demo_org_id},
    )

    member = conn.execute(
        text('''
            SELECT id::text, status FROM organization_members
            WHERE user_id = CAST(:uid AS uuid) AND organization_id = CAST(:oid AS uuid)
        '''),
        {"uid": user_id, "oid": demo_org_id},
    ).first()

    if member is None:
        conn.execute(
            text('''
                INSERT INTO organization_members (id, organization_id, user_id, role, status, joined_at)
                VALUES (:id, CAST(:oid AS uuid), CAST(:uid AS uuid), 'admin', 'active', TIMESTAMPTZ '2000-01-01 00:00:00+00')
            '''),
            {"id": str(uuid.uuid4()), "oid": demo_org_id, "uid": user_id},
        )
        print(f"Created active admin membership on {demo_name}")
    elif member[1] != "active":
        conn.execute(
            text('''
                UPDATE organization_members
                SET status = 'active', role = 'admin', joined_at = TIMESTAMPTZ '2000-01-01 00:00:00+00'
                WHERE user_id = CAST(:uid AS uuid) AND organization_id = CAST(:oid AS uuid)
            '''),
            {"uid": user_id, "oid": demo_org_id},
        )
        print(f"Reactivated membership on {demo_name}")
    else:
        conn.execute(
            text('''
                UPDATE organization_members
                SET joined_at = TIMESTAMPTZ '2000-01-01 00:00:00+00'
                WHERE user_id = CAST(:uid AS uuid) AND organization_id = CAST(:oid AS uuid)
            '''),
            {"uid": user_id, "oid": demo_org_id},
        )
        print(f"Set earliest joined_at on {demo_name}")

    conn.execute(
        text('''
            UPDATE organization_members
            SET joined_at = now() + interval '1 day'
            WHERE user_id = CAST(:uid AS uuid)
              AND organization_id != CAST(:oid AS uuid)
              AND status = 'active'
        '''),
        {"uid": user_id, "oid": demo_org_id},
    )

    rows = list_memberships(conn)

print("")
print("Active workspaces (first = default on next magic-link login):")
for i, (oid, name, plan, joined, status) in enumerate(rows):
    mark = "  <-- active on login" if i == 0 else ""
    print(f"  {name} ({oid})  plan={plan}  joined={joined}{mark}")

if rows and rows[0][0] != demo_org_id:
    print("", file=sys.stderr)
    print(f"ERROR: Expected {demo_name} first but got {rows[0][1]}", file=sys.stderr)
    sys.exit(1)

print("")
print("OK: Next fresh magic-link login should use SMPL Demo Co.")
print("Sign out on Preview, request a NEW link, click it (do not reuse an old tab).")
"@

Push-Location $backendDir
try {
    $env:DATABASE_URL = $dbUrl
    $py | & $python -
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
