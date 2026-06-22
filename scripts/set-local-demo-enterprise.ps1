# Set local auth DB org plan to enterprise (unlocks Forecast Engine + full modules).
#
# Usage:
#   .\scripts\set-local-demo-enterprise.ps1
#   .\scripts\set-local-demo-enterprise.ps1 -Email mattjustice@smpl-ai.com
#   .\scripts\set-local-demo-enterprise.ps1 -OrganizationId 8571e520-0687-4516-bdee-379f37c58c1f -Plan enterprise

param(
    [string]$Email = "",
    [string]$OrganizationId = "8571e520-0687-4516-bdee-379f37c58c1f",
    [ValidateSet("starter", "professional", "enterprise")]
    [string]$Plan = "enterprise",
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
    return $u.TrimEnd("?").TrimEnd("&")
}

if (-not $DatabaseUrl) {
    $localEnv = Join-Path $repoRoot "frontend\.env.local"
    if (Test-Path $localEnv) {
        foreach ($line in Get-Content $localEnv) {
            if ($line -match "^AUTH_DATABASE_URL=(.+)$") {
                $DatabaseUrl = $Matches[1].Trim()
                break
            }
        }
    }
}

if (-not $DatabaseUrl) {
    Write-Host "ERROR: AUTH_DATABASE_URL not found in frontend/.env.local" -ForegroundColor Red
    exit 1
}

$dbUrl = Normalize-DatabaseUrl $DatabaseUrl
$orgId = $OrganizationId.Trim()
$plan = $Plan.Trim().ToLower()
$email = $Email.Trim().ToLower()

Write-Host ""
Write-Host "=== Local org plan -> $plan ===" -ForegroundColor Cyan
Write-Host "DB: $dbUrl" -ForegroundColor DarkGray
Write-Host "Org: $orgId" -ForegroundColor DarkGray
if ($email) { Write-Host "User: $email" -ForegroundColor DarkGray }
Write-Host ""

$py = @'
import os
import sys
from sqlalchemy import create_engine, text

email = os.environ.get("SMPL_SETUP_EMAIL", "").strip().lower()
org_id = os.environ["SMPL_SETUP_ORG_ID"].strip()
plan = os.environ["SMPL_SETUP_PLAN"].strip().lower()
engine = create_engine(os.environ["DATABASE_URL"])

with engine.begin() as conn:
    org = conn.execute(
        text("SELECT id::text, name, COALESCE(plan, 'starter') FROM organizations WHERE id = CAST(:oid AS uuid)"),
        {"oid": org_id},
    ).first()
    if org is None:
        print(f"ERROR: Organization not found: {org_id}", file=sys.stderr)
        sys.exit(1)
    print(f"Before: {org[1]} plan={org[2]}")
    conn.execute(
        text("UPDATE organizations SET plan = :plan WHERE id = CAST(:oid AS uuid)"),
        {"plan": plan, "oid": org_id},
    )
    after = conn.execute(
        text("SELECT name, plan FROM organizations WHERE id = CAST(:oid AS uuid)"),
        {"oid": org_id},
    ).first()
    print(f"After:  {after[0]} plan={after[1]}")

    if email:
        user = conn.execute(
            text("SELECT id::text FROM users WHERE email = :email"),
            {"email": email},
        ).first()
        if user is None:
            print(f"WARN: No user row for {email}. Sign in once locally, then re-run with -Email.", file=sys.stderr)
        else:
            member = conn.execute(
                text('''
                    SELECT om.status FROM organization_members om
                    JOIN users u ON u.id = om.user_id
                    WHERE u.email = :email AND om.organization_id = CAST(:oid AS uuid)
                '''),
                {"email": email, "oid": org_id},
            ).first()
            if member is None:
                conn.execute(
                    text('''
                        INSERT INTO organization_members (id, user_id, organization_id, role, status, joined_at)
                        VALUES (gen_random_uuid(), CAST(:uid AS uuid), CAST(:oid AS uuid), 'admin', 'active', NOW())
                    '''),
                    {"uid": user[0], "oid": org_id},
                )
                print(f"Added active admin membership for {email} on {after[0]}")
            elif member[0] != 'active':
                conn.execute(
                    text('''
                        UPDATE organization_members SET status = 'active', role = 'admin'
                        WHERE user_id = CAST(:uid AS uuid) AND organization_id = CAST(:oid AS uuid)
                    '''),
                    {"uid": user[0], "oid": org_id},
                )
                print(f"Reactivated membership for {email} on {after[0]}")
            else:
                print(f"Membership OK for {email} on {after[0]}")

print("")
print("Next steps:")
print("  1. Sign out at http://localhost:3002/login")
print("  2. Request a new magic link and sign in")
print("  3. Banner should show Enterprise; open /forecast-engine and /app/board")
'@

$env:DATABASE_URL = $dbUrl
$env:SMPL_SETUP_ORG_ID = $orgId
$env:SMPL_SETUP_PLAN = $plan
$env:SMPL_SETUP_EMAIL = $email
$py | & $python -
Remove-Item Env:SMPL_SETUP_ORG_ID -ErrorAction SilentlyContinue
Remove-Item Env:SMPL_SETUP_PLAN -ErrorAction SilentlyContinue
Remove-Item Env:SMPL_SETUP_EMAIL -ErrorAction SilentlyContinue
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
