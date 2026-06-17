# One-shot gl-5b Preview fix: Vercel staging API + auth DB + billing key + demo workspace.
#
# Usage (repo root):
#   .\scripts\fix-gl5b-preview.ps1
#   .\scripts\fix-gl5b-preview.ps1 -SkipVercel
#   .\scripts\fix-gl5b-preview.ps1 -BillingKey "same-as-railway-staging"
#
# Requires: npx vercel login (or VERCEL_TOKEN), frontend/.env.staging.local

param(
    [string]$Email = "mattjustice@smpl-ai.com",
    [string]$BillingKey = "",
    [switch]$SkipVercel,
    [string]$Scope = "smplai",
    [string]$Project = "smpl-financial-intelligence"
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path $PSScriptRoot -Parent
$frontendDir = Join-Path $repoRoot "frontend"
$stagingFile = Join-Path $frontendDir ".env.staging.local"

if (-not (Test-Path $stagingFile)) {
    Write-Host "ERROR: Missing frontend/.env.staging.local - run save-staging-config.ps1 first." -ForegroundColor Red
    exit 1
}

$stagingApi = ""
foreach ($line in Get-Content $stagingFile) {
    if ($line -match "^STAGING_API_URL=(.+)$") {
        $stagingApi = $Matches[1].Trim().TrimEnd("/")
        break
    }
}

if (-not $stagingApi) {
    Write-Host "ERROR: STAGING_API_URL not in .env.staging.local" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== gl-5b Preview fix ===" -ForegroundColor Cyan
Write-Host "Staging API: $stagingApi" -ForegroundColor DarkGray
Write-Host ""

function Resolve-LocalBillingKey {
    param([string]$FrontendDir)

    $candidates = @(
        (Join-Path $FrontendDir ".env.local"),
        (Join-Path $FrontendDir ".env.vercel-production.local")
    )

    foreach ($file in $candidates) {
        if (-not (Test-Path $file)) { continue }
        $line = Get-Content $file | Where-Object { $_ -match "^BILLING_INTERNAL_API_KEY=" } | Select-Object -First 1
        if ($line -match "^BILLING_INTERNAL_API_KEY=(.+)$") {
            $value = $Matches[1].Trim()
            if ($value) {
                return @{ Value = $value; Source = (Split-Path $file -Leaf) }
            }
        }
    }

    return $null
}

function Set-VercelPreviewBillingKey {
    param(
        [string]$Key,
        [string]$ScopeName,
        [string]$ProjectName,
        [string]$FrontendDir
    )

    $npxBase = @("--yes", "vercel@latest")
    if ($env:VERCEL_TOKEN) {
        $npxBase += @("--token", $env:VERCEL_TOKEN)
    }

    $tempFile = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($tempFile, $Key.Trim(), [System.Text.UTF8Encoding]::new($false))
        Push-Location $FrontendDir
        try {
            $out = Get-Content -LiteralPath $tempFile -Raw | & npx @npxBase env add BILLING_INTERNAL_API_KEY preview --yes --force --scope $ScopeName --project $ProjectName 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Host ($out -join "`n") -ForegroundColor Red
                Write-Host "WARN: Could not set BILLING_INTERNAL_API_KEY - ensure it matches Railway sfi-api-staging." -ForegroundColor Yellow
                return $false
            }

            Write-Host "  OK: BILLING_INTERNAL_API_KEY (preview)" -ForegroundColor Green
            Write-Host "  IMPORTANT: Set the SAME value on Railway sfi-api-staging if not already." -ForegroundColor Yellow
            return $true
        }
        finally {
            Pop-Location
        }
    }
    finally {
        Remove-Item -LiteralPath $tempFile -Force -ErrorAction SilentlyContinue
    }
}

if (-not $SkipVercel) {
    Write-Host "Step 1/4: Vercel Preview API URLs..." -ForegroundColor Yellow
    & (Join-Path $repoRoot "scripts\set-vercel-staging-env.ps1") -BackendUrl $stagingApi -Scope $Scope -Project $Project
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "Step 2/4: Vercel Preview AUTH_DATABASE_URL (staging Neon)..." -ForegroundColor Yellow
    & (Join-Path $repoRoot "scripts\set-vercel-preview-auth-db.ps1") -Scope $Scope -Project $Project
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    if (-not $BillingKey) {
        $found = Resolve-LocalBillingKey -FrontendDir $frontendDir
        if ($found) {
            $BillingKey = $found.Value
            Write-Host "Found BILLING_INTERNAL_API_KEY in $($found.Source) - will set on Preview." -ForegroundColor DarkGray
        }
    }

    if ($BillingKey) {
        Write-Host "Step 2b: Vercel Preview BILLING_INTERNAL_API_KEY..." -ForegroundColor Yellow
        Set-VercelPreviewBillingKey -Key $BillingKey -ScopeName $Scope -ProjectName $Project -FrontendDir $frontendDir | Out-Null
    }
    else {
        Write-Host "Step 2b: BILLING_INTERNAL_API_KEY not in local env - trying Production copy..." -ForegroundColor DarkGray
        & (Join-Path $repoRoot "scripts\set-vercel-preview-billing-from-production.ps1") -Scope $Scope -Project $Project
        if ($LASTEXITCODE -eq 0) {
            $found = Resolve-LocalBillingKey -FrontendDir $frontendDir
            if (-not $found) {
                $previewEnvFile = Join-Path $env:TEMP "sfi-billing-preview-check.env"
                Push-Location $frontendDir
                try {
                    $pullArgs = @("--yes", "vercel@latest", "env", "pull", $previewEnvFile, "--environment", "preview", "--yes", "--scope", $Scope, "--project", $Project)
                    if ($env:VERCEL_TOKEN) { $pullArgs += @("--token", $env:VERCEL_TOKEN) }
                    $null = & npx @pullArgs 2>&1
                    if (Test-Path $previewEnvFile) {
                        $line = Get-Content $previewEnvFile | Where-Object { $_ -match "^BILLING_INTERNAL_API_KEY=" } | Select-Object -First 1
                        if ($line -match "^BILLING_INTERNAL_API_KEY=(.+)$" -and $Matches[1].Trim()) {
                            $BillingKey = $Matches[1].Trim()
                        }
                    }
                }
                finally {
                    Pop-Location
                    Remove-Item $previewEnvFile -Force -ErrorAction SilentlyContinue
                }
            }
        }
        if (-not $BillingKey) {
            Write-Host "  If Railway sfi-api-staging HAS BILLING_INTERNAL_API_KEY, add it to Preview or remove from Railway." -ForegroundColor Yellow
        }
    }
}
else {
    Write-Host "Skipping Vercel env (--SkipVercel)." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Step 3/4: Staging Neon workspace -> SMPL Demo Co..." -ForegroundColor Yellow
& (Join-Path $repoRoot "scripts\set-staging-demo-workspace.ps1") -Email $Email
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Step 4/4: Verify staging session-sync..." -ForegroundColor Yellow
$syncArgs = @{
    Email   = $Email
    ApiBase = $stagingApi
}
if ($BillingKey) {
    $syncArgs["InternalKey"] = $BillingKey
}
& (Join-Path $repoRoot "scripts\verify-staging-session-sync.ps1") @syncArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "=== Manual checklist (Vercel dashboard -> Preview) ===" -ForegroundColor Cyan
Write-Host "  [ ] AUTH_SECRET - copy from Production, enable Preview" -ForegroundColor White
Write-Host "  [ ] AUTH_RESEND_KEY - copy from Production, enable Preview" -ForegroundColor White
Write-Host '  [ ] EMAIL_FROM - e.g. SMPL.ai <noreply@smpl-ai.com>' -ForegroundColor White
Write-Host "  [ ] AUTH_URL - leave UNSET on Preview (do not use prod URL)" -ForegroundColor White
Write-Host "  [ ] Railway: .\scripts\set-railway-sandbox-cors.ps1" -ForegroundColor White
Write-Host ""
Write-Host "=== After env changes ===" -ForegroundColor Cyan
Write-Host "  1. Vercel -> Deployments -> Redeploy gl-5b-sandbox (Preview, not Production)" -ForegroundColor White
Write-Host "  2. Incognito -> magic link login (new link, not old tab)" -ForegroundColor White
Write-Host "  3. While logged in: /api/debug/preview-workspace" -ForegroundColor White
Write-Host "     sync_ok:true and sync_workspace = 8571e520-... (SMPL Demo Co)" -ForegroundColor White
Write-Host "  4. Banner should show Workspace: SMPL Demo Co" -ForegroundColor White
Write-Host ""
Write-Host "Audit anytime: .\scripts\audit-gl5b-stack.ps1" -ForegroundColor DarkGray
Write-Host ""
